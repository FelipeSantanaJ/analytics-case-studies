"""
LumaBank — 01_generate_raw.py

Builds the whole synthetic world in memory (users, the onboarding/KYC funnel,
activation transactions, fraud signals, support tickets, app releases, and the
onboarding experiment WITH the deterministic 2026-07-16 break) and writes it out
as source-shaped, messy raw exports under data/raw/.

The true treatment effect comes from config.EFFECT and the bug magnitudes from
config.BUG. Nothing downstream (staging, curated, analysis) sees either.

Run:  python etl/01_generate_raw.py      (respects LB_SCALE env for dev)
"""

from __future__ import annotations

import shutil
from datetime import date, datetime, timedelta

import numpy as np
import pandas as pd
from faker import Faker

import config as C
from utils import (
    banner,
    fmt_money_brl,
    jitter_date_string,
    logistic,
    mojibake,
    rng,
    stable_hash_u01,
    to_excel_serial,
    write_raw_csv,
)

MONTH0 = C.WINDOW_START
DAY7 = timedelta(days=C.DAY7_WINDOW_DAYS)


def month_start(m_idx: int) -> date:
    m = MONTH0.month - 1 + m_idx
    return date(MONTH0.year + m // 12, m % 12 + 1, 1)


def as_dt(d: date) -> datetime:
    return datetime(d.year, d.month, d.day)


# ======================================================================== #
# App releases  (needed before users, to stamp app_version_at_signup)
# ======================================================================== #
def build_releases():
    g = rng("releases")
    rows = []
    ver = list(C.APP_VERSION_START)
    d = C.WINDOW_START
    while d <= C.WINDOW_END:
        for plat in ("iOS", "Android"):
            k = g.poisson(C.APP_RELEASES_PER_MONTH)
            days = sorted(g.integers(1, 28, size=k))
            for dd in days:
                rel_d = date(d.year, d.month, int(dd))
                if rel_d > C.WINDOW_END:
                    continue
                ver[1] += 1
                rows.append(dict(
                    version=f"{ver[0]}.{ver[1]}.{ver[2]}",
                    platform=plat,
                    released_at=rel_d,
                    rollout_pct=int(g.choice([50, 75, 90, 100, 100])),
                    release_type="feature",
                    notes=g.choice(["perf + bug fixes", "UI polish", "new home screen",
                                    "Pix improvements", "onboarding tweaks", "SDK bump"]),
                ))
        d = date(d.year + (d.month // 12), d.month % 12 + 1, 1)

    # the routine release that resets the on-device variant cache
    rows.append(dict(version="4.61.0", platform="Android", released_at=C.DEPLOY_DATE,
                     rollout_pct=100, release_type="feature",
                     notes="home screen refresh; local storage migration"))
    rows.append(dict(version="4.61.0", platform="iOS", released_at=C.DEPLOY_DATE,
                     rollout_pct=100, release_type="feature",
                     notes="home screen refresh; local storage migration"))
    # the hotfix
    rows.append(dict(version="4.61.1", platform="Android", released_at=C.HOTFIX_DATE,
                     rollout_pct=100, release_type="hotfix",
                     notes="fix variant assignment fallback + cache reset on upgrade"))
    rows.append(dict(version="4.61.1", platform="iOS", released_at=C.HOTFIX_DATE,
                     rollout_pct=100, release_type="hotfix",
                     notes="fix variant assignment fallback + cache reset on upgrade"))

    rel = pd.DataFrame(rows).sort_values("released_at").reset_index(drop=True)

    changelog = []
    for _, r in rel.iterrows():
        changelog.append(dict(component=f"mobile-{r['platform'].lower()}",
                              changed_at=datetime(r["released_at"].year, r["released_at"].month,
                                                  r["released_at"].day, int(g.integers(8, 20))).isoformat(),
                              change=f"release {r['version']}"))
    for _ in range(220):
        cd = C.WINDOW_START + timedelta(days=int(g.integers(0, (C.WINDOW_END - C.WINDOW_START).days)))
        changelog.append(dict(
            component=g.choice(["auth-svc", "ledger-svc", "risk-svc", "flag-svc", "kyc-svc"]),
            changed_at=datetime(cd.year, cd.month, cd.day, int(g.integers(0, 24))).isoformat(),
            change=g.choice(["deploy", "config change", "rollback", "feature flag toggle"])))
    changelog = pd.DataFrame(changelog).sort_values("changed_at").reset_index(drop=True)
    return rel, changelog


def version_at(rel: pd.DataFrame, when: np.ndarray, os_arr: np.ndarray) -> np.ndarray:
    """Latest released version for each (date, platform)."""
    out = np.empty(len(when), dtype=object)
    for plat in ("iOS", "Android"):
        sub = rel[rel["platform"] == plat].sort_values("released_at")
        rv = sub["version"].to_numpy()
        rd = np.array([as_dt(x) for x in sub["released_at"]])
        mask = os_arr == plat
        idx = np.searchsorted(rd, when[mask], side="right") - 1
        idx = np.clip(idx, 0, len(rv) - 1)
        out[mask] = rv[idx]
    return out


# ======================================================================== #
# Users + funnel + activation + experiment
# ======================================================================== #
def build_world(rel: pd.DataFrame):
    g = rng("world")
    n = C.N_USERS_TOTAL
    E, B = C.EFFECT, C.BUG

    # ---- signup timing ------------------------------------------------------
    w = np.array(C.SIGNUP_MONTH_WEIGHTS, dtype=float)
    w = w / w.sum()
    m_idx = g.choice(np.arange(C.N_MONTHS), size=n, p=w)
    # day within month + intraday; skew to evenings and Sun-Tue lightly
    dom = g.integers(0, 28, size=n)
    hod = np.clip(g.normal(19, 4, size=n).astype(int), 0, 23)
    signup_dt = np.array([as_dt(month_start(int(mm))) + timedelta(days=int(dd), hours=int(hh),
                                                                  minutes=int(g.integers(0, 60)))
                          for mm, dd, hh in zip(m_idx, dom, hod)])
    signup_date = np.array([d.date() for d in signup_dt])
    order = np.argsort(signup_dt)
    signup_dt, signup_date, m_idx = signup_dt[order], signup_date[order], m_idx[order]
    dom, hod = dom[order], hod[order]
    user_id = np.array([f"LB{1_000_000 + i}" for i in range(n)])

    # ---- region / UF / timezone ------------------------------------------
    uf_tab = pd.read_csv(C.VOCAB_DIR / "br_uf_region_tz.csv")
    reg_w = np.array([C.REGION_MIX[r] for r in uf_tab["macro_region"]]) * uf_tab["pop_weight"].to_numpy()
    reg_w = reg_w / reg_w.sum()
    ui = g.choice(np.arange(len(uf_tab)), size=n, p=reg_w)
    uf = uf_tab["uf"].to_numpy()[ui]
    macro_region = uf_tab["macro_region"].to_numpy()[ui]
    timezone = uf_tab["timezone"].to_numpy()[ui]
    utc_offset = uf_tab["utc_offset_hours"].to_numpy()[ui]
    is_amazon_tz = uf_tab["is_amazon_tz"].to_numpy()[ui].astype(bool)

    os_arr = g.choice(list(C.OS_MIX), size=n, p=list(C.OS_MIX.values()))

    # ---- acquisition channel (months 1-2 -> unknown) --------------------
    ch = g.choice(C.CHANNELS, size=n, p=[C.CHANNEL_MIX[c] for c in C.CHANNELS])
    ch = np.where(m_idx < (C.ORBITA_GOLIVE_MONTH - 1), "unknown", ch)

    # ---- latent intent -------------------------------------------------
    intent = g.normal(0, 1, size=n)
    shift = np.array([C.CHANNEL_INTENT_SHIFT.get(c, 0.0) for c in ch])
    intent = intent + shift

    app_version = version_at(rel, signup_dt, os_arr)

    # ---- experiment membership --------------------------------------
    d = signup_date
    in_exp1 = (d >= C.EXP1_START) & (d < C.EXP1_ENROLL_PAUSED)
    in_exp2 = (d >= C.EXP2_START) & (d <= C.EXP2_END)
    is_subject = in_exp1 | in_exp2
    post_deploy = in_exp1 & (d >= C.DEPLOY_DATE)
    pre_deploy = in_exp1 & (d < C.DEPLOY_DATE)

    experiment_cohort = np.full(n, "not_in_experiment", dtype=object)
    experiment_cohort[pre_deploy] = "pre_deploy"
    experiment_cohort[post_deploy] = "post_deploy"
    experiment_cohort[in_exp2] = "rerun"

    # base feature-flag arm (the intended randomisation)
    h1 = stable_hash_u01(user_id, "lumabank-onboarding-v1")
    base_arm_v1 = np.where(h1 < 0.5, "control", "treatment")
    h2 = stable_hash_u01(user_id, "lumabank-onboarding-v2")   # fresh re-hash for the re-run
    base_arm_v2 = np.where(h2 < 0.5, "control", "treatment")

    # assignment events: list of (user_idx, ts, arm, source, cache_reset, seq)
    a_uidx, a_ts, a_arm, a_src, a_reset, a_seq = [], [], [], [], [], []

    # -- pre-deploy exp1: clean primary assignment at signup
    for i in np.where(pre_deploy)[0]:
        a_uidx.append(i); a_ts.append(signup_dt[i]); a_arm.append(base_arm_v1[i])
        a_src.append("primary"); a_reset.append(False); a_seq.append(1)

    # -- post-deploy exp1: biased fallback for a decaying share
    fb_roll = stable_hash_u01(user_id, "fallback-roll")
    fb_geo = stable_hash_u01(user_id, "fallback-geo")
    days_since_deploy = np.array([(x - C.DEPLOY_DATE).days for x in d])
    fb_share = B["fallback_share_0"] * np.clip(1 - days_since_deploy / B["fallback_decay_days"], 0, 1)
    for i in np.where(post_deploy)[0]:
        if fb_roll[i] < fb_share[i]:
            frac = B["fallback_treat_frac_by_region"][macro_region[i]]
            arm = "treatment" if fb_geo[i] < frac else "control"
            src = "fallback"
        else:
            arm = base_arm_v1[i]
            src = "primary"
        a_uidx.append(i); a_ts.append(signup_dt[i]); a_arm.append(arm)
        a_src.append(src); a_reset.append(False); a_seq.append(1)

    # -- re-run exp2: clean primary assignment, fresh randomisation
    for i in np.where(in_exp2)[0]:
        a_uidx.append(i); a_ts.append(signup_dt[i]); a_arm.append(base_arm_v2[i])
        a_src.append("primary"); a_reset.append(False); a_seq.append(1)

    # -- BUG01/02: cache reset + arm switch for pre-deploy users who open post-deploy
    reset_roll = stable_hash_u01(user_id, "cache-reset")
    open_roll = stable_hash_u01(user_id, "post-deploy-open")
    reswitch_roll = stable_hash_u01(user_id, "reswitch")
    rehash = stable_hash_u01(user_id, "onboarding-rehash")
    cache_reset_ts = {}          # user_idx -> ts of the reset marker
    switched_arm = {}            # user_idx -> new arm from a 2nd assignment row
    for i in np.where(pre_deploy)[0]:
        opens = open_roll[i] < 0.85
        if not (opens and reset_roll[i] < B["reset_share"]):
            continue
        rts = as_dt(C.DEPLOY_DATE) + timedelta(days=int(reswitch_roll[i] * B["reset_open_window_days"]),
                                               hours=int(rehash[i] * 24))
        cache_reset_ts[i] = rts
        if reswitch_roll[i] < B["reswitch_share"]:
            new_arm = "control" if rehash[i] < 0.5 else "treatment"
            a_uidx.append(i); a_ts.append(rts); a_arm.append(new_arm)
            a_src.append("primary"); a_reset.append(True); a_seq.append(2)
            switched_arm[i] = new_arm

    asg = pd.DataFrame(dict(
        user_idx=a_uidx, assigned_ts=a_ts, arm=a_arm, assignment_source=a_src,
        cache_reset=a_reset, assignment_seq=a_seq,
    )).sort_values(["user_idx", "assignment_seq"]).reset_index(drop=True)

    # ---- effective arm + contamination (the auditable rule, doc 02 §7.3) ----
    first_arm = asg[asg.assignment_seq == 1].set_index("user_idx")["arm"]
    effective_arm = np.full(n, "not_in_experiment", dtype=object)
    contaminated = np.zeros(n, dtype=bool)
    switch_flag = np.zeros(n, dtype=bool)
    for i in np.where(is_subject)[0]:
        fa = first_arm.get(i, None)
        if fa is None:
            continue
        effective_arm[i] = fa
        if i in switched_arm and switched_arm[i] != fa:
            switch_flag[i] = True
            contaminated[i] = True
        if i in cache_reset_ts and cache_reset_ts[i] <= signup_dt[i] + DAY7:
            contaminated[i] = True

    # ---- onboarding funnel ----------------------------------------------
    flow = np.where(is_subject & (effective_arm == "treatment"), "treatment", "control")
    is_treat_flow = flow == "treatment"
    r_pd, r_kyc, r_acc = g.random(n), g.random(n), g.random(n)
    r_rej, r_man, r_act, r_late = g.random(n), g.random(n), g.random(n), g.random(n)

    reached_personal = r_pd < C.P_PERSONAL_DATA
    personal_ts = signup_dt + np.array([timedelta(minutes=int(x)) for x in g.integers(1, 12, n)])
    reject_rate_ctrl = np.clip(C.KYC_REJECT_RATE - 0.02 * intent / 3.0, 0.01, 0.5)
    p_submit_ctrl = logistic(C.KYC_SUBMIT_A0 + C.KYC_SUBMIT_INTENT_SLOPE * intent)

    # (A) counterfactual CONTROL-flow funnel — arm-independent, drives day7_base
    cf_submit = reached_personal & (r_kyc < p_submit_ctrl)
    cf_reject = cf_submit & (r_rej < reject_rate_ctrl)
    cf_manual = cf_submit & ~cf_reject & (r_man < C.KYC_MANUAL_RATE)
    cf_approve = cf_submit & ~cf_reject
    cf_lat_h = np.where(cf_manual, g.uniform(18, 96, n), g.uniform(0.5, 14, n))
    cf_submit_ts = personal_ts + np.array([timedelta(minutes=int(x)) for x in g.uniform(3, 40, n)])
    cf_decided_ts = cf_submit_ts + np.array([timedelta(hours=float(x)) for x in cf_lat_h])
    cf_elig = cf_approve & np.array([pd.Timestamp(t) <= pd.Timestamp(s) + DAY7
                                    for t, s in zip(cf_decided_ts, signup_dt)])

    base_logit = (C.ACT_A0 + C.ACT_INTENT_SLOPE * intent
                  + np.array([C.ACT_CHANNEL_SHIFT.get(c, 0.0) for c in ch]))
    p0 = logistic(base_logit)
    day7_base = cf_elig & (r_act < p0)

    # (B) actual funnel — flow-dependent. Control users == counterfactual;
    #     treatment users get account-first + deferred/skipped KYC.
    t_acc_first = is_treat_flow & reached_personal & (r_acc < 0.94)
    never_verify = t_acc_first & (stable_hash_u01(user_id, "never-verify")
                                  < C.EFFECT["treatment_limited_never_verified_share"])
    p_submit_treat = logistic(C.KYC_SUBMIT_A0 + C.KYC_SUBMIT_INTENT_SLOPE * intent
                              + C.EFFECT["treatment_kyc_submit_lift"] * 4)
    t_submit = t_acc_first & ~never_verify & (r_kyc < p_submit_treat)
    t_reject = t_submit & (r_rej < np.clip(reject_rate_ctrl + C.EFFECT["kyc_reject_delta_pp"], 0.01, 0.6))
    t_manual = t_submit & ~t_reject & (r_man < C.KYC_MANUAL_RATE)
    t_approve = t_submit & ~t_reject

    kyc_submitted = np.where(is_treat_flow, t_submit, cf_submit)
    kyc_rejected = np.where(is_treat_flow, t_reject, cf_reject)
    kyc_manual = np.where(is_treat_flow, t_manual, cf_manual)
    kyc_approved = np.where(is_treat_flow, t_approve, cf_approve)
    acc_created = np.where(is_treat_flow, t_acc_first,
                           cf_approve & (r_acc < C.P_ACCOUNT_GIVEN_KYC_OK))

    kyc_lat_h = np.where(kyc_manual, g.uniform(18, 96, n), g.uniform(0.5, 14, n))
    kyc_submit_ts = np.where(
        is_treat_flow,
        personal_ts + np.array([timedelta(hours=float(x)) for x in g.uniform(2, 110, n)]),
        cf_submit_ts)
    kyc_decided_ts = np.where(is_treat_flow,
                              kyc_submit_ts + np.array([timedelta(hours=float(x)) for x in kyc_lat_h]),
                              cf_decided_ts)
    acc_created_ts_arr = np.where(
        is_treat_flow,
        personal_ts + np.array([timedelta(minutes=int(x)) for x in g.integers(2, 20, n)]),
        cf_decided_ts + np.array([timedelta(minutes=int(x)) for x in g.integers(2, 30, n)]))

    # ---- activation (Day-7): baseline + deterministic treatment flips --------
    day7 = day7_base.copy()
    day7_eligible = cf_elig                            # flip candidate pool (arm-neutral)
    subj_treat = is_subject & (effective_arm == "treatment") & ~contaminated
    # Per cohort: flip a deterministic count of not-yet-activated treatment subjects
    # so the realised pooled ATE == the channel-mix-weighted config value, and the
    # per-channel split follows EFFECT["ate_day7_by_channel"]. Largest-remainder
    # rounding keeps the pooled count exact. Flips prefer higher-intent users (the
    # ones closest to converting). A faint week-1 novelty bump is layered on.
    _sdate = pd.to_datetime(pd.Series(signup_date))
    days_in = np.where(experiment_cohort == "rerun",
                       (_sdate - pd.Timestamp(C.EXP2_START)).dt.days.values,
                       (_sdate - pd.Timestamp(C.EXP1_START)).dt.days.values)
    week1 = (np.clip(days_in // 7, 0, None) == 0)

    for coh in ("pre_deploy", "post_deploy", "rerun"):
        cells = []
        for c in C.CHANNELS + ["unknown"]:
            sel = np.where(subj_treat & (experiment_cohort == coh) & (ch == c))[0]
            if sel.size == 0:
                continue
            want = C.EFFECT["ate_day7_by_channel"].get(c, 0.0) * sel.size + 0.010 * week1[sel].sum()
            cells.append([c, sel, want])
        if not cells:
            continue
        total = int(round(sum(w for _, _, w in cells)))
        base = [int(np.floor(w)) for _, _, w in cells]
        rem = [w - b for (_, _, w), b in zip(cells, base)]
        for j in np.argsort(rem)[::-1][:max(0, total - sum(base))]:
            base[j] += 1
        for (c, sel, _), k in zip(cells, base):
            cand = sel[(~day7[sel]) & day7_eligible[sel]]
            if k > 0 and cand.size:
                day7[cand[np.argsort(-intent[cand])][:min(k, cand.size)]] = True

    # late activation (day 8-30) for non-day7
    p_late = 0.22 * (0.6 + 0.4 * logistic(intent))
    late_act = acc_created & ~day7 & (r_late < p_late)

    # Any activated user (day7 or late) must have an account by construction, so the
    # curated recompute (account_opened AND first_txn<=D7) reproduces day7 exactly.
    # A day7 treatment user forced to have an account gets it minutes after signup.
    treat_forced = (day7 | late_act) & ~acc_created & is_treat_flow
    acc_created_ts_arr = np.where(
        treat_forced,
        personal_ts + np.array([timedelta(minutes=int(x)) for x in g.integers(3, 25, n)]),
        acc_created_ts_arr)
    acc_created = acc_created | day7 | late_act
    acc_created_ts = np.where(acc_created, acc_created_ts_arr, None)

    ttft_h = np.full(n, np.nan)
    act7_idx = np.where(day7)[0]
    ttft_h[act7_idx] = np.clip(
        np.exp(np.log(C.TTFT_HOURS_MEDIAN) + g.normal(0, C.TTFT_HOURS_SIGMA, act7_idx.size)),
        0.2, C.DAY7_WINDOW_DAYS * 24 - 0.5)
    late_idx = np.where(late_act)[0]
    ttft_h[late_idx] = g.uniform(C.DAY7_WINDOW_DAYS * 24 + 1, 30 * 24, late_idx.size)
    first_txn_ts = np.array([s + timedelta(hours=float(h)) if not np.isnan(h) else None
                             for s, h in zip(signup_dt, ttft_h)])
    day1 = day7 & (ttft_h <= 24)
    day30 = day7 | late_act

    first_txn_type = np.where(
        (day7 | late_act),
        g.choice(list(C.TXN_FIRST_TYPE_MIX), size=n, p=list(C.TXN_FIRST_TYPE_MIX.values())),
        None)

    # ---- fraud (guardrail) -------------------------------------------
    fr_roll = g.random(n)
    fr_rate = C.FRAUD_FLAG_RATE + C.FRAUD_INTENT_SLOPE * intent / 6.0
    fr_rate = fr_rate + np.where(is_treat_flow, C.EFFECT["fraud_flag_delta_pp"], 0.0)
    fr_rate = np.clip(fr_rate, 0.0005, 0.15)
    fraud_flag = (day7 | late_act) & (fr_roll < fr_rate)
    fraud_days = np.where(fraud_flag, g.integers(0, 30, n), -1)
    fraud_type = np.where(fraud_flag, g.choice(C.FRAUD_TYPES, size=n), None)

    # ---- support tickets (guardrail) --------------------------------
    tk_roll = g.random(n)
    tk_rate = C.ONBOARDING_TICKET_RATE + np.where(is_treat_flow, C.EFFECT["onboarding_ticket_delta_per_1k"] / 1000.0, 0.0)
    tk_rate = tk_rate + np.where(kyc_rejected, 0.35, 0) + np.where(kyc_manual, 0.15, 0)
    has_onb_ticket = tk_roll < np.clip(tk_rate, 0, 0.9)

    world = dict(
        n=n, user_id=user_id, signup_dt=signup_dt, signup_date=signup_date, m_idx=m_idx,
        uf=uf, macro_region=macro_region, timezone=timezone, utc_offset=utc_offset,
        is_amazon_tz=is_amazon_tz, os=os_arr, channel=ch, intent=intent, app_version=app_version,
        in_exp1=in_exp1, in_exp2=in_exp2, is_subject=is_subject,
        experiment_cohort=experiment_cohort, effective_arm=effective_arm,
        contaminated=contaminated, switch_flag=switch_flag, cache_reset_ts=cache_reset_ts,
        reached_personal=reached_personal, personal_ts=personal_ts,
        kyc_submitted=kyc_submitted, kyc_submit_ts=kyc_submit_ts, kyc_decided_ts=kyc_decided_ts,
        kyc_rejected=kyc_rejected, kyc_manual=kyc_manual, kyc_approved=kyc_approved,
        reject_reason=np.where(kyc_rejected,
                               g.choice(["DOC_ILLEGIBLE", "FACE_MISMATCH", "DATA_MISMATCH",
                                         "SANCTIONS_HIT", "SUSPECTED_FORGERY", "DOC_EXPIRED"],
                                        size=n, p=[0.34, 0.22, 0.20, 0.06, 0.10, 0.08]), None),
        acc_created=acc_created, acc_created_ts=acc_created_ts, never_verify=never_verify,
        day7=day7, day1=day1, day30=day30, late_act=late_act, ttft_h=ttft_h,
        first_txn_ts=first_txn_ts, first_txn_type=first_txn_type,
        fraud_flag=fraud_flag, fraud_days=fraud_days, fraud_type=fraud_type,
        has_onb_ticket=has_onb_ticket, flow=flow,
        asg=asg,
    )
    return world


# ======================================================================== #
# Transaction stream (thinned) for the platform trend + TTFT
# ======================================================================== #
def build_transactions(world):
    g = rng("txn")
    rows = []
    n = world["n"]
    activ = np.where(world["day7"] | world["late_act"])[0]
    wend = pd.Timestamp(C.WINDOW_END) + pd.Timedelta(days=1)
    for i in activ:
        first = pd.Timestamp(world["first_txn_ts"][i])
        if first >= wend:                      # near-future censoring
            continue
        rows.append((world["user_id"][i], first, world["first_txn_type"][i]))
        rate = C.TXN_TAIL_PER_DAY_MEAN * (0.5 + 0.9 * logistic(world["intent"][i]))
        k = g.poisson(rate * C.TXN_TAIL_DAYS)
        if k:
            offs = np.sort(g.uniform(0.05, C.TXN_TAIL_DAYS, k))
            for o in offs:
                ts = first + pd.Timedelta(days=float(o))
                if ts.date() > C.WINDOW_END:
                    break
                rows.append((world["user_id"][i], ts,
                             g.choice(list(C.TXN_FIRST_TYPE_MIX), p=list(C.TXN_FIRST_TYPE_MIX.values()))))
    tx = pd.DataFrame(rows, columns=["user_id", "ts", "type"])
    tx["txn_id"] = "TX" + pd.Series(np.arange(1, len(tx) + 1)).astype(str).str.zfill(10)
    amt = np.exp(np.log(C.TXN_AMOUNT_BRL_MEAN) - 0.5 * np.log(1 + C.TXN_AMOUNT_BRL_CV**2)
                 + np.sqrt(np.log(1 + C.TXN_AMOUNT_BRL_CV**2)) * g.normal(0, 1, len(tx)))
    tx["amount_brl"] = np.round(np.clip(amt, 1, 15000), 2)
    tx["mcc"] = g.choice(["5411", "5812", "5541", "4900", "5999", ""], len(tx))
    return tx


# ======================================================================== #
# RAW EMISSION
# ======================================================================== #
def emit_raw(world, tx, rel, changelog):
    g = rng("raw_emit")
    RAW = C.RAW_DIR
    for _try in range(6):
        try:
            if RAW.exists():
                shutil.rmtree(RAW)
            break
        except (PermissionError, OSError):
            import time as _t
            _t.sleep(1.0 + _try)
    for sub in ["lumencore", "flagfox", "trilha", "riskguard", "beacon", "orbita"]:
        (RAW / sub).mkdir(parents=True, exist_ok=True)

    n = world["n"]
    uid = world["user_id"]
    sdt = world["signup_dt"]
    fake = Faker("pt_BR")
    Faker.seed(C.SEED)
    names = np.array([fake.name() for _ in range(n)])
    moji = g.random(n) < C.DQ["mojibake_name_rate"]
    names_out = np.where(moji, [mojibake(x) for x in names], names)

    # ---------- Lumen Core: users_snapshot (monthly, dup-heavy) ----------
    banner("raw: Lumen Core user snapshots")
    for m in range(C.N_MONTHS):
        d0 = month_start(m)
        idx = np.where(world["m_idx"] <= m)[0]
        iso = g.random(idx.size) < 0.5
        opened = np.where(world["acc_created"][idx],
                          np.where(iso, pd.to_datetime([world["acc_created_ts"][i] for i in idx]).strftime("%Y-%m-%d"),
                                   pd.to_datetime([world["acc_created_ts"][i] for i in idx]).strftime("%d/%m/%Y")),
                          "")
        df = pd.DataFrame(dict(
            user_id=uid[idx],
            full_name=names_out[idx],
            cpf=[f"{g.integers(100,999)}.{g.integers(100,999)}.{g.integers(100,999)}-{g.integers(10,99)}"
                 for _ in idx],
            uf=world["uf"][idx],
            opened_at=opened,
            account_status=np.where(world["acc_created"][idx],
                                    np.where(world["never_verify"][idx], "limited", "active"), "none"),
            device_os=world["os"][idx],
        ))
        extra = df.sample(frac=C.DQ["users_snapshot_extra_dupe_rate"],
                          random_state=int(g.integers(1, 1 << 30)))
        df = pd.concat([df, extra], ignore_index=True).sample(frac=1.0, random_state=m).reset_index(drop=True)
        write_raw_csv(df, RAW / "lumencore" / f"lumencore__users_snapshot__{d0.isoformat()}.csv")

    # ---------- Lumen Core: accounts ----------
    ai = np.where(world["acc_created"])[0]
    acc = pd.DataFrame(dict(
        account_id=[f"AC{i:09d}" for i in range(ai.size)],
        user_id=uid[ai],
        opened_at=[pd.Timestamp(world["acc_created_ts"][i]).isoformat() for i in ai],
        status=np.where(world["never_verify"][ai], "limited",
                        np.where(world["kyc_approved"][ai], "active", "limited")),
    ))
    orph = acc.sample(n=max(3, int(0.004 * len(acc))), random_state=7).copy()
    orph["user_id"] = [f"LB{9_900_000 + j}" for j in range(len(orph))]
    write_raw_csv(pd.concat([acc, orph], ignore_index=True),
                  RAW / "lumencore" / "lumencore__accounts.csv")

    # ---------- Lumen Core: transactions (monthly, overlap dupes, epoch-ms) ----------
    banner("raw: Lumen Core transactions")
    tx = tx.merge(pd.DataFrame({"user_id": uid, "account_id_src": np.where(world["acc_created"], "y", "n")}),
                  on="user_id", how="left")
    accmap = dict(zip(acc["user_id"], acc["account_id"]))
    tx["account_id"] = tx["user_id"].map(accmap)
    tx = tx.dropna(subset=["account_id"])
    tx["ts"] = pd.to_datetime(tx["ts"])
    tx["epoch_ms"] = (tx["ts"].astype("int64") // 10**6).astype("int64")
    tx["ym"] = tx["ts"].dt.to_period("M").astype(str)
    tx["_day"] = tx["ts"].dt.day
    amt_txt_mask = g.random(len(tx)) < C.DQ["txn_amount_text_rate"]
    amt_out = np.where(amt_txt_mask,
                       [fmt_money_brl(v, "br_symbol") for v in tx["amount_brl"]],
                       tx["amount_brl"].astype(object))
    tx["amount"] = amt_out
    type_variants = {"pix": ["pix", "PIX", "pix_out"], "card": ["card", "card_purchase", "debito"],
                     "boleto": ["boleto", "boleto_payment"], "transfer": ["ted", "TED", "transferencia"]}
    tx["type_raw"] = [g.choice(type_variants[t]) for t in tx["type"]]
    cols = ["txn_id", "account_id", "user_id", "epoch_ms", "type_raw", "amount", "mcc"]
    months = sorted(tx["ym"].unique())
    for i, ym in enumerate(months):
        y, mo = map(int, ym.split("-"))
        cur = tx[tx["ym"] == ym]
        if i + 1 < len(months):
            ny, nmo = map(int, months[i + 1].split("-"))
            nxt = tx[(tx["ym"] == months[i + 1]) & (tx["_day"] <= C.DQ["txn_monthly_overlap_days"])]
            cur = pd.concat([cur, nxt], ignore_index=True)
        write_raw_csv(cur[cols].rename(columns={"type_raw": "type"}).sample(frac=1.0, random_state=i)
                      .reset_index(drop=True),
                      RAW / "lumencore" / f"lumencore__transactions__{y}-{mo:02d}.csv.gz", compression="gzip")

    # ---------- Lumen Core: account_status_events ----------
    se_rows = []
    for i in ai:
        se_rows.append(dict(event_id=f"ASE{len(se_rows):09d}", user_id=uid[i],
                            changed_at=pd.Timestamp(world["acc_created_ts"][i]).isoformat(),
                            from_status="none",
                            to_status="limited" if world["never_verify"][i] or not world["kyc_approved"][i] else "active"))
        if world["kyc_approved"][i] and not world["never_verify"][i] and world["kyc_submitted"][i]:
            se_rows.append(dict(event_id=f"ASE{len(se_rows):09d}", user_id=uid[i],
                                changed_at=pd.Timestamp(world["kyc_decided_ts"][i]).isoformat(),
                                from_status="limited", to_status="active"))
    se = pd.DataFrame(se_rows)
    se = pd.concat([se, se.sample(frac=C.DQ["event_dupe_rate"], random_state=3)], ignore_index=True)
    write_raw_csv(se, RAW / "lumencore" / "lumencore__account_status_events.csv")

    # ---------- Flagfox: variant_assignments ----------
    banner("raw: Flagfox experiment service")
    asg = world["asg"].copy()
    asg["user_id"] = uid[asg["user_idx"].to_numpy()]
    asg["assigned_at"] = pd.to_datetime(asg["assigned_ts"]).dt.tz_localize("America/Sao_Paulo").dt.tz_convert("UTC")
    asg["assigned_at"] = asg["assigned_at"].dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    asg["app_version"] = version_at(rel, np.array([as_dt(pd.Timestamp(t).date()) for t in asg["assigned_ts"]]),
                                    world["os"][asg["user_idx"].to_numpy()])
    va = asg[["user_id", "assigned_at", "arm", "assignment_source", "cache_reset",
              "assignment_seq", "app_version"]].copy()
    va["cache_reset"] = va["cache_reset"].map({True: "true", False: "false"})
    write_raw_csv(va, RAW / "flagfox" / "flagfox__variant_assignments.csv")

    # ---------- Flagfox: exposure_log (at-least-once, UTC, carries cache_reset) ----------
    exp_rows = []
    for _, r in asg.iterrows():
        i = int(r["user_idx"])
        k = 1 + int(g.integers(0, 3))
        for _ in range(k):
            t = pd.Timestamp(r["assigned_ts"]) + pd.Timedelta(hours=float(g.uniform(0, 240)))
            exp_rows.append(dict(user_id=uid[i],
                                 exposed_at=t.tz_localize("America/Sao_Paulo").tz_convert("UTC").strftime("%Y-%m-%dT%H:%M:%SZ"),
                                 surface=g.choice(["app_open", "onboarding", "home"]),
                                 cache_reset="false"))
    for i, rts in world["cache_reset_ts"].items():
        exp_rows.append(dict(user_id=uid[i],
                             exposed_at=pd.Timestamp(rts).tz_localize("America/Sao_Paulo").tz_convert("UTC").strftime("%Y-%m-%dT%H:%M:%SZ"),
                             surface="app_open", cache_reset="true"))
    ex = pd.DataFrame(exp_rows)
    ex = pd.concat([ex, ex.sample(frac=C.DQ["flagfox_exposure_at_least_once_rate"], random_state=5)],
                   ignore_index=True).sample(frac=1.0, random_state=6).reset_index(drop=True)
    write_raw_csv(ex, RAW / "flagfox" / "flagfox__exposure_log.csv")

    # ---------- Flagfox: variant_snapshot (monthly-lite; drifts after the break) ----------
    snap_rows = []
    eff = world["effective_arm"]
    subj = np.where(world["is_subject"])[0]
    for m in range(6, C.N_MONTHS):     # snapshots exist from mid-2025
        d0 = month_start(m)
        for i in subj:
            if world["signup_date"][i] > d0:
                continue
            # snapshot shows the LATEST assignment arm (so it drifts when a reswitch happened)
            arm = world.get("_latest_arm", {}).get(i, eff[i])
            if i in [int(x) for x in world["asg"][world["asg"].assignment_seq == 2]["user_idx"]]:
                arm = world["asg"][(world["asg"].user_idx == i) & (world["asg"].assignment_seq == 2)]["arm"].iloc[0]
            snap_rows.append(dict(snapshot_date=d0.isoformat(), user_id=uid[i], current_arm=arm))
    write_raw_csv(pd.DataFrame(snap_rows),
                  RAW / "flagfox" / "flagfox__variant_snapshot.csv.gz", compression="gzip")

    # ---------- Trilha: onboarding_step_events ----------
    banner("raw: Trilha onboarding service")
    step_rows = []
    for i in range(n):
        evs = [("signup_started", sdt[i])]
        if world["reached_personal"][i]:
            evs.append(("personal_data", world["personal_ts"][i]))
        if world["flow"][i] == "treatment":
            if world["acc_created"][i]:
                evs.append(("account_created", world["acc_created_ts"][i]))
            if world["kyc_submitted"][i]:
                evs.append(("kyc_upload", world["kyc_submit_ts"][i]))
        else:
            if world["kyc_submitted"][i]:
                evs.append(("kyc_upload", world["kyc_submit_ts"][i]))
            if world["acc_created"][i]:
                evs.append(("account_created", world["acc_created_ts"][i]))
        if world["day7"][i] or world["late_act"][i]:
            evs.append(("first_transaction", world["first_txn_ts"][i]))
        if world["kyc_approved"][i] and world["acc_created"][i] and not world["never_verify"][i]:
            evs.append(("limits_lifted", pd.Timestamp(world["kyc_decided_ts"][i]) + pd.Timedelta(minutes=5)))
        drop_terminal = g.random() < C.DQ["trilha_missing_terminal_step_rate"]
        if drop_terminal and len(evs) > 1:
            evs = evs[:-1]
        for name, t in evs:
            step_rows.append(dict(user_id=uid[i], step_name=name,
                                  occurred_at=pd.Timestamp(t).isoformat(),
                                  platform=world["os"][i]))
    st = pd.DataFrame(step_rows)
    # step_name casing / synonym noise
    variants = {"kyc_upload": ["kyc_upload", "KYC_UPLOAD", "doc_upload"],
                "account_created": ["account_created", "ACCOUNT_CREATED", "account_open"],
                "first_transaction": ["first_transaction", "first_txn", "activation"]}
    for canon, opts in variants.items():
        m = st["step_name"] == canon
        st.loc[m, "step_name"] = g.choice(opts, m.sum())
    st = pd.concat([st, st.sample(frac=C.DQ["trilha_step_at_least_once_rate"], random_state=9)],
                   ignore_index=True).sample(frac=1.0, random_state=10).reset_index(drop=True)
    write_raw_csv(st, RAW / "trilha" / "trilha__onboarding_step_events.csv.gz", compression="gzip")

    # ---------- Trilha: kyc_submissions ----------
    ks = np.where(world["kyc_submitted"])[0]
    kyc_sub = pd.DataFrame(dict(
        submission_id=[f"KS{j:08d}" for j in range(ks.size)],
        user_id=uid[ks],
        submitted_at=[pd.Timestamp(world["kyc_submit_ts"][i]).isoformat() for i in ks],
        doc_type=g.choice(["rg", "RG", "cnh", "CNH"], ks.size, p=[0.35, 0.15, 0.35, 0.15]),
        submitted_after_account=[(world["flow"][i] == "treatment") for i in ks],
    ))
    write_raw_csv(kyc_sub, RAW / "trilha" / "trilha__kyc_submissions.csv")

    # ---------- RiskGuard: kyc_decisions (UTC, date-only sometimes) ----------
    banner("raw: RiskGuard")
    kd_rows = []
    for i in ks:
        if world["kyc_rejected"][i]:
            outcome, reason = "rejected", world["reject_reason"][i]
        elif world["kyc_manual"][i]:
            outcome, reason = "manual_review", "NONE"
        else:
            outcome, reason = "approved", "NONE"
        dts = pd.Timestamp(world["kyc_decided_ts"][i]).tz_localize("America/Sao_Paulo").tz_convert("UTC")
        date_only = g.random() < 0.2
        kd_rows.append(dict(
            user_id=uid[i],
            decided_at=(dts.strftime("%Y-%m-%d") if date_only else dts.strftime("%Y-%m-%dT%H:%M:%SZ")),
            outcome=outcome, reason_code=reason,
            reviewer=g.choice(["auto", "auto", "auto", "analyst"]),
        ))
    kd = pd.DataFrame(kd_rows)
    orphan = kd.sample(frac=C.DQ["riskguard_orphan_user_rate"], random_state=11).copy()
    orphan["user_id"] = [f"LB{9_800_000 + j}" for j in range(len(orphan))]
    write_raw_csv(pd.concat([kd, orphan], ignore_index=True),
                  RAW / "riskguard" / "riskguard__kyc_decisions.csv")

    rmap = pd.read_csv(C.VOCAB_DIR / "kyc_reason_map.csv").drop_duplicates("canonical")
    write_raw_csv(rmap.rename(columns={"canonical": "reason_code", "reason_group": "group"})[["reason_code", "group"]],
                  RAW / "riskguard" / "riskguard__kyc_reason_codes.csv")

    # ---------- RiskGuard: fraud_signals (epoch-s, UTC) ----------
    fi = np.where(world["fraud_flag"])[0]
    fr = pd.DataFrame(dict(
        signal_id=[f"FS{j:07d}" for j in range(fi.size)],
        user_id=uid[fi],
        signal_ts=[int(pd.Timestamp(
            (pd.Timestamp(world["first_txn_ts"][i]) + pd.Timedelta(days=int(world["fraud_days"][i])))
        ).tz_localize("America/Sao_Paulo").tz_convert("UTC").timestamp()) for i in fi],
        signal_type=world["fraud_type"][fi],
        score=np.round(g.uniform(0.55, 0.99, fi.size), 3),
        confirmed=g.choice(["true", "false"], fi.size, p=[0.7, 0.3]),
    ))
    write_raw_csv(fr, RAW / "riskguard" / "riskguard__fraud_signals.csv")

    # ---------- Beacon: app_releases (xlsx, excel serial) + deploy_changelog ----------
    banner("raw: Beacon release log")
    rel_out = rel.copy()
    rel_out["released_at"] = rel_out["released_at"].map(to_excel_serial)
    rel_out["platform"] = rel_out["platform"].map({"iOS": "iOS", "Android": "android"}).fillna(rel_out["platform"])
    rel_out["rollout_pct"] = rel_out["rollout_pct"].astype(str) + "%"
    rel_out.to_excel(RAW / "beacon" / "beacon__app_releases.xlsx", index=False)
    write_raw_csv(changelog, RAW / "beacon" / "beacon__deploy_changelog.csv")

    # ---------- Órbita: acquisition + support_tickets ----------
    banner("raw: Orbita growth CRM + support")
    has_acq = world["m_idx"] >= (C.ORBITA_GOLIVE_MONTH - 1)
    qi = np.where(has_acq)[0]
    ch_variants = {"paid_social": ["paid_social", "Paid Social", "meta", "tiktok"],
                   "organic": ["organic", "direct", "organico"],
                   "app_store_search": ["app_store_search", "aso", "ASO"],
                   "referral": ["referral", "mgm", "indicacao"],
                   "influencer": ["influencer", "affiliate", "creator"],
                   "unknown": ["unknown"]}
    acq = pd.DataFrame(dict(
        user_id=uid[qi],
        channel=[g.choice(ch_variants[c]) for c in world["channel"][qi]],
        campaign=[f"cmp_{g.integers(100, 999)}" for _ in qi],
        first_touch_at=[jitter_date_string((pd.Timestamp(sdt[i]) - pd.Timedelta(days=int(g.integers(0, 8)))).date(),
                                           g.choice(["iso", "br"]), g) for i in qi],
    ))
    write_raw_csv(acq, RAW / "orbita" / "orbita__acquisition.csv")

    tk_rows = []
    for i in range(n):
        k = 0
        if world["has_onb_ticket"][i]:
            k = 1 + int(g.random() < 0.15)
        k += int(g.random() < 0.02)     # non-onboarding noise
        for _ in range(k):
            cat = "onboarding" if world["has_onb_ticket"][i] and g.random() < 0.7 else \
                g.choice(C.TICKET_CATEGORIES)
            base = pd.Timestamp(sdt[i]) + pd.Timedelta(days=float(g.uniform(0, 20)))
            tk_rows.append(dict(ticket_id=f"TK{len(tk_rows):08d}", user_id=uid[i],
                                opened_at=base.isoformat(),
                                category=g.choice({"onboarding": ["onboarding", "cadastro", "Onboarding"],
                                                   "kyc": ["kyc", "documento", "KYC"],
                                                   "card": ["card", "cartao"], "transaction": ["transaction", "pix"],
                                                   "other": ["other", "geral"]}[cat]),
                                channel=g.choice(C.TICKET_CHANNELS, p=[0.6, 0.3, 0.1]),
                                cidade=mojibake(fake.city()) if C.DQ["orbita_latin1_cidade"] else fake.city()))
    tks = pd.DataFrame(tk_rows)
    tks = pd.concat([tks, tks.sample(frac=C.DQ["event_dupe_rate"], random_state=12)], ignore_index=True)
    write_raw_csv(tks, RAW / "orbita" / "orbita__support_tickets.csv", encoding="latin-1")


# ======================================================================== #
def truth_peek(world):
    print("\n--- truth peek (not persisted) ---")
    for coh in ("pre_deploy", "post_deploy", "rerun"):
        m = world["experiment_cohort"] == coh
        if not m.any():
            continue
        d7 = pd.Series(world["day7"][m])
        arm = pd.Series(world["effective_arm"][m])
        rr = d7.groupby(arm).mean()
        n_arm = arm.value_counts().to_dict()
        lift = rr.get("treatment", np.nan) - rr.get("control", np.nan)
        print(f"  {coh:11s} n={m.sum():5d}  arms={n_arm}  "
              f"ctrl={rr.get('control', float('nan')):.3f} treat={rr.get('treatment', float('nan')):.3f} "
              f"lift={lift*100:+.2f}pp")
    m2 = world["experiment_cohort"] == "rerun"
    clean = m2 & ~world["contaminated"]
    by = pd.DataFrame({"ch": world["channel"][clean], "arm": world["effective_arm"][clean],
                       "d7": world["day7"][clean]})
    print(by.groupby(["ch", "arm"])["d7"].mean().unstack().round(3).to_string())
    tot = world["is_subject"]
    print(f"  contaminated among exp1: {world['contaminated'][world['in_exp1']].sum()} / {world['in_exp1'].sum()}")
    print(f"  blended Day-7 (all accounts, non-subject controls): "
          f"{world['day7'][~world['is_subject'] & world['acc_created']].mean():.3f}")


def main():
    banner("LumaBank — 01_generate_raw")
    print(f"SEED={C.SEED}  SCALE={C.SCALE}  users={C.N_USERS_TOTAL:,}")
    rel, changelog = build_releases()
    world = build_world(rel)
    tx = build_transactions(world)
    truth_peek(world)
    emit_raw(world, tx, rel, changelog)
    banner("01_generate_raw complete")


if __name__ == "__main__":
    main()
