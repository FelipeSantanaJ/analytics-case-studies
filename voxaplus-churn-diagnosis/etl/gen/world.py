"""
The clean generative world model for Voxa+.

`build_world()` returns a dict of tidy pandas DataFrames describing the *true*
state of the business, month by month, subscriber by subscriber. Nothing here is
messy — `01_generate_raw.py` takes these frames and serialises them into
source-shaped, messy exports.

The month-34 churn spike emerges from three overlapping effects wired in via
`config.py` section 9 (F1 app-v3 CTV regression, F2 Brazil price increase,
F3 Mexico acquisition-quality decline). It is not narrated anywhere in docs/01.

Implementation note: every per-subscriber attribute is a full-length NumPy buffer
indexed by subscriber row (0..n-1). Each month we slice `arr[active]`; there is no
positional re-alignment anywhere, so engagement -> churn coupling stays exact even
as subscribers leave mid-month.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

import config as C
from utils import rng, month_start, month_end, progress

# --------------------------------------------------------------------------
# calendar-month multipliers
# --------------------------------------------------------------------------
_ENG_SEASON = {
    "BR": {12: 1.18, 1: 1.15, 2: 0.92, 6: 1.08, 7: 1.10},
    "MX": {12: 1.12, 11: 1.05, 4: 1.04, 7: 1.03},
    "US": {12: 1.10, 1: 1.06, 2: 0.96, 7: 0.93},
}
_ACQ_SEASON = {
    "BR": {12: 1.35, 1: 1.28, 3: 0.92, 7: 1.06},
    "MX": {12: 1.30, 1: 1.20, 9: 1.08},
    "US": {12: 1.25, 1: 1.18, 6: 0.90},
}


def _season(table, market, idx):
    return table.get(market, {}).get(month_start(idx).month, 1.0)


def _tenure_hazard(t: int) -> float:
    tbl = C.CHURN_BASE_BY_TENURE
    keys = sorted(tbl)
    if t <= keys[0]:
        return tbl[keys[0]]
    if t >= keys[-1]:
        return tbl[keys[-1]]
    lo = max(k for k in keys if k <= t)
    hi = min(k for k in keys if k >= t)
    if lo == hi:
        return tbl[lo]
    w = (t - lo) / (hi - lo)
    return tbl[lo] * (1 - w) + tbl[hi] * w


_HAZARD_VEC = np.vectorize(_tenure_hazard, otypes=[float])


# --------------------------------------------------------------------------
# acquisition
# --------------------------------------------------------------------------
def _acquisition_plan() -> pd.DataFrame:
    rows = []
    for market, mconf in C.MARKETS.items():
        r = rng("world", "acq", market)
        a0 = C.ACQ_BASE[market] * C.POP_SCALE
        grow = C.ACQ_GROWTH_TO_END[market]
        for idx in range(C.N_MONTHS):
            if idx < mconf["active_from_idx"]:
                continue
            months_live = idx - mconf["active_from_idx"]
            ramp = C.LAUNCH_RAMP[months_live] if months_live < len(C.LAUNCH_RAMP) else 1.0
            growth = 1.0 + (grow - 1.0) * idx / (C.N_MONTHS - 1)
            mu = a0 * ramp * growth * _season(_ACQ_SEASON, market, idx)
            n = int(max(0, r.poisson(mu)))
            if n == 0:
                continue

            mix = dict(C.CHANNEL_MIX_PRE if idx < C.CHANNEL_SHIFT_IDX else C.CHANNEL_MIX_POST)
            if market == "MX" and idx >= C.CHANNEL_SHIFT_IDX:
                mix["partner_bundle"] = C.MX_BUNDLE_SHARE_AFTER
                s = sum(v for k, v in mix.items() if k != "partner_bundle")
                for k in mix:
                    if k != "partner_bundle":
                        mix[k] = mix[k] / s * (1 - C.MX_BUNDLE_SHARE_AFTER)
            chans = list(mix)
            cp = np.array([mix[c] for c in chans], float)
            cp /= cp.sum()
            ch = r.choice(chans, size=n, p=cp)

            tiers = r.choice(C.TIERS, size=n, p=[C.TIER_MIX[t] for t in C.TIERS])
            billing = np.array(["annual" if r.random() < C.ANNUAL_SHARE[t] else "monthly"
                                for t in tiers], dtype=object)
            dev = r.choice(C.DEVICE_FAMILIES, size=n,
                           p=[C.DEVICE_MIX_POP[d] for d in C.DEVICE_FAMILIES])
            ctv_share = np.clip(np.where(np.isin(dev, C.CTV_FAMILIES),
                                         r.beta(4.5, 2.2, n), r.beta(1.6, 5.0, n)), 0, 1)
            eng = r.lognormal(0.0, 0.42, n)
            price_sens = np.clip(r.beta(2.4, 3.2, n), 0, 1)
            incent = np.array([r.random() < C.INCENTIVISED_SIGNUP_RATE[c] for c in ch])
            pm_mix = C.PAYMENT_METHOD_MIX[market]
            pmk = list(pm_mix)
            pay = r.choice(pmk, size=n, p=[pm_mix[k] for k in pmk])
            d = month_start(idx)
            q = f"{d.year}Q{(d.month - 1) // 3 + 1}"
            for i in range(n):
                rows.append((market, idx, ch[i], tiers[i], billing[i], dev[i],
                             float(ctv_share[i]), float(eng[i]), float(price_sens[i]),
                             bool(incent[i]), pay[i], f"cmp_{market}_{ch[i]}_{q}"))
    cols = ["market", "signup_idx", "channel", "first_tier", "first_billing_period",
            "primary_device_family", "ctv_share", "eng_propensity", "price_sensitivity",
            "is_incentivised", "payment_method", "campaign_id"]
    df = pd.DataFrame(rows, columns=cols)
    # shuffle so subscriber_id order is not sorted by market/month
    df = df.sample(frac=1.0, random_state=C.SEED % (2**32)).reset_index(drop=True)
    df.insert(0, "subscriber_id", [f"S{1_000_000 + i}" for i in range(len(df))])
    df["signup_date"] = [month_start(i) + pd.Timedelta(days=int(rng("world", "signday", s).integers(0, 27)))
                         for s, i in zip(df["subscriber_id"], df["signup_idx"])]
    return df


def _price_local(tier, market, idx, migrated) -> float:
    base = C.PRICE_LOCAL_END[tier][market]
    if market == "BR" and tier in ("Standard", "Premium"):
        pre = base / (1.0 + C.BR_PRICE_HIKE_PCT[tier])
        if idx < C.BR_PRICE_HIKE_IDX:
            return pre
        return base if migrated else pre
    return base


# --------------------------------------------------------------------------
# main simulation
# --------------------------------------------------------------------------
def build_world() -> dict:
    progress("world: acquisition plan")
    subs = _acquisition_plan()
    n = len(subs)
    r = rng("world", "sim")

    sid = subs["subscriber_id"].to_numpy()
    market = subs["market"].to_numpy()
    signup_idx = subs["signup_idx"].to_numpy()
    channel = subs["channel"].to_numpy()
    dev_family = subs["primary_device_family"].to_numpy()
    tier = subs["first_tier"].to_numpy().astype(object).copy()
    billing = subs["first_billing_period"].to_numpy().astype(object)
    ctv_share = subs["ctv_share"].to_numpy().astype(float)
    eng_prop = subs["eng_propensity"].to_numpy().astype(float)
    price_sens = subs["price_sensitivity"].to_numpy().astype(float)
    incent = subs["is_incentivised"].to_numpy().astype(bool)
    pay_method = subs["payment_method"].to_numpy().astype(object)
    is_lowq = np.isin(channel, C.LOWQ_CHANNELS)

    status = np.zeros(n, np.int8)              # 0 pending / 1 active / 2 paused / 3 churned
    tenure = np.full(n, -1, np.int32)
    churn_idx = np.full(n, -1, np.int32)
    churn_kind = np.zeros(n, np.int8)          # 1 voluntary / 2 involuntary
    annual_anchor = np.full(n, -1, np.int32)
    migrated = np.zeros(n, bool)
    migrate_at = np.where(market == "BR",
                          C.BR_PRICE_HIKE_IDX + 1 + r.integers(0, C.PRICE_MIGRATION_SPREAD_MONTHS, n),
                          9999).astype(np.int32)
    dunning_left = np.zeros(n, np.int8)
    hours_buf = np.zeros(n, float)

    ctv_first_v3 = min(C.APP_V3_ROLLOUT_IDX[f] for f in C.CTV_FAMILIES)

    gap = {}
    for mk in C.MARKETS:
        rg = rng("world", "contentgap", mk)
        gap[mk] = rg.poisson(C.TENTPOLES_PER_QUARTER[mk] / 3.0, C.N_MONTHS) == 0

    sub_month_rows, events, billing_rows, viewing_month_rows = [], [], [], []

    def emit(i, etype, idx, **kw):
        d = month_start(idx) + pd.Timedelta(days=int(r.integers(0, 27)),
                                            hours=int(r.integers(0, 24)), minutes=int(r.integers(0, 60)))
        events.append({"subscriber_id": sid[i], "event_type": etype,
                       "event_ts": d.isoformat(), **kw})

    for idx in range(C.N_MONTHS):
        joining = (signup_idx == idx) & (status == 0)
        status[joining] = 1
        tenure[joining] = 0
        annual_anchor[joining & (billing == "annual")] = idx
        for i in np.where(joining)[0]:
            emit(i, "paid_start", idx, to_tier=tier[i])

        act = np.where(status == 1)[0]
        if len(act) == 0:
            continue

        # ---- engagement -------------------------------------------------
        mk = market[act]
        tn = tenure[act].astype(float)
        h = np.array([C.ENGAGEMENT_HOURS_MEAN[t] for t in tier[act]], float)
        h *= eng_prop[act]
        h *= C.TENURE_ENGAGEMENT_DECAY ** np.clip(tn, 0, 60)
        h *= np.array([_season(_ENG_SEASON, m, idx) for m in mk])
        h *= np.where(np.array([gap[m][idx] for m in mk]), C.CONTENT_GAP_ENGAGEMENT_HIT, 1.0)
        if idx >= C.BR_LICENCE_EXPIRY_MONTH:
            h *= np.where(mk == "BR", C.BR_LICENCE_EXPIRY_ENGAGEMENT_HIT, 1.0)
        if idx >= ctv_first_v3:
            eng_mult = np.where(mk == "US",
                                1.0 - (1.0 - C.CTV_QOE_ENGAGEMENT_MULT) * C.APP_V3_CTV_US_SENSITIVITY,
                                C.CTV_QOE_ENGAGEMENT_MULT)
            h *= np.where(ctv_share[act] >= C.CTV_HEAVY_SHARE_THRESHOLD, eng_mult, 1.0)
        h *= np.where((mk == "MX") & is_lowq[act] & (idx >= C.CHANNEL_SHIFT_IDX),
                      C.MX_LOWQ_ENGAGEMENT_MULT, 1.0)
        h = h * r.lognormal(0.0, C.ENGAGEMENT_HOURS_CV, len(act))
        dark = r.random(len(act)) > C.ACTIVE_RATE_BASE
        h[dark] *= r.random(int(dark.sum())) * 0.12
        h = np.clip(h, 0, 500)
        hours_buf[:] = 0.0
        hours_buf[act] = h

        # ---- billing --------------------------------------------------
        is_cyc = (billing[act] == "monthly") | (
            (billing[act] == "annual") & (annual_anchor[act] >= 0)
            & (((idx - annual_anchor[act]) % 12) == 0))
        for k, i in enumerate(act):
            if not is_cyc[k]:
                continue
            if migrate_at[i] <= idx:
                migrated[i] = True
            p = _price_local(tier[i], market[i], idx, migrated[i])
            amt = p * (C.ANNUAL_MONTHS_CHARGED if billing[i] == "annual" else 1)
            method = pay_method[i]
            auth = C.AUTH_RATE[method]
            if market[i] == "MX" and idx >= C.CHANNEL_SHIFT_IDX and method in ("oxxo", "carrier_billing"):
                auth = 1 - (1 - auth) * C.MX_INVOL_CHURN_MULT_AFTER
            ok = r.random() < auth
            billing_rows.append({
                "subscriber_id": sid[i], "month_idx": idx,
                "billing_day": int(r.integers(1, 28)), "method": method,
                "amount_local": round(float(amt), 2),
                "status": "approved" if ok else "failed", "attempt_number": 1,
                "is_dunning": False, "failure_reason": "" if ok else _fail_reason(method, r),
            })
            if not ok:
                dunning_left[i] = C.DUNNING_RETRIES

        # ---- dunning resolution ------------------------------------------
        for i in np.where((dunning_left > 0) & (status == 1))[0]:
            method = pay_method[i]
            rr_rate = C.DUNNING_RECOVERY_RATE[method]
            if market[i] == "MX" and idx >= C.CHANNEL_SHIFT_IDX and method in ("oxxo", "carrier_billing"):
                rr_rate *= 0.8
            rec = r.random() < rr_rate
            attempt_n = C.DUNNING_RETRIES - int(dunning_left[i]) + 2
            billing_rows.append({
                "subscriber_id": sid[i], "month_idx": idx, "billing_day": int(r.integers(1, 28)),
                "method": method, "amount_local": _price_local(tier[i], market[i], idx, migrated[i]),
                "status": "approved" if rec else "failed", "attempt_number": attempt_n,
                "is_dunning": True, "failure_reason": "" if rec else _fail_reason(method, r),
            })
            if rec:
                dunning_left[i] = 0
            else:
                dunning_left[i] -= 1
                if dunning_left[i] == 0:
                    if r.random() < C.INVOLUNTARY_CHURN_ON_EXHAUST:
                        status[i] = 3
                        churn_idx[i] = idx
                        churn_kind[i] = 2
                        emit(i, "churn", idx, reason_code="involuntary_payment")
                    # else: a manual save / grace period — stays active

        # ---- voluntary churn hazard -----------------------------------
        act = np.where(status == 1)[0]
        if len(act):
            mk = market[act]
            tn = tenure[act].astype(float)
            hh = hours_buf[act]
            haz = _HAZARD_VEC(tn)
            haz *= np.array([C.CHURN_MULT_TIER[t] for t in tier[act]])
            haz *= np.array([C.CHURN_MULT_MARKET[m] for m in mk])
            haz *= np.where(billing[act] == "annual", C.CHURN_MULT_ANNUAL, 1.0)
            haz *= np.where(hh < C.HEALTHY_ENGAGEMENT_HOURS, C.CHURN_MULT_LOW_ENGAGEMENT,
                            np.clip(1.0 + C.CHURN_MULT_ENGAGEMENT_SLOPE * (hh - C.HEALTHY_ENGAGEMENT_HOURS),
                                    0.55, 1.0))
            haz *= np.where(incent[act] & (tn < 3), C.CHURN_MULT_INCENTIVISED_EARLY, 1.0)

            if (idx - 1) >= ctv_first_v3:                       # F1, lagged 1 month
                f1_add = np.where(ctv_share[act] >= C.CTV_HEAVY_SHARE_THRESHOLD,
                                  C.CTV_QOE_CHURN_ADD, 0.0)
                f1_add = f1_add * np.where(mk == "US", C.APP_V3_CTV_US_SENSITIVITY, 1.0)
                haz = haz + f1_add

            recently_migrated = ((migrate_at[act] <= idx)
                                 & (migrate_at[act] >= idx - C.PRICE_MIGRATION_TAIL_MONTHS))  # F2
            br_hit = (mk == "BR") & np.isin(tier[act], ["Standard", "Premium"]) & recently_migrated
            add = np.where(hh < C.HEALTHY_ENGAGEMENT_HOURS,
                           C.PRICE_CHURN_ADD_DISENGAGED, C.PRICE_CHURN_ADD_ENGAGED)
            add = add * np.where(billing[act] == "annual", C.PRICE_ANNUAL_SHIELD_MULT, 1.0)
            add = add * (0.5 + 1.1 * price_sens[act])
            haz = haz + np.where(br_hit, add, 0.0)
            # BR Basico reaction to the month-32 plan-lineup change (downloads removed, ad load up)
            br_basico = (mk == "BR") & (tier[act] == "Basico") & (idx >= 33)
            haz = haz + np.where(br_basico, C.PRICE_CHURN_ADD_BR_BASICO * (0.6 + 0.9 * price_sens[act]), 0.0)

            lowq_add = np.array([C.LOWQ_CHURN_ADD_BY_AGE.get(int(t), 0.0) for t in tn])  # F3
            haz = haz + np.where(is_lowq[act], lowq_add, 0.0)
            haz = haz + np.where((mk == "MX") & (idx >= C.MX_DRIFT_START_IDX),
                                 0.0018 + 0.0014 * max(0, idx - C.MX_DRIFT_START_IDX), 0.0)

            haz = np.clip(haz, 0.0, 0.92)
            draw = r.random(len(act)) < haz
            for k, i in enumerate(act):
                if draw[k]:
                    status[i] = 3
                    churn_idx[i] = idx
                    churn_kind[i] = 1
                    emit(i, "cancel_request", idx,
                         reason_code=_vol_reason(hh[k] < C.HEALTHY_ENGAGEMENT_HOURS, r))
                    emit(i, "churn", idx, reason_code="voluntary")

        # ---- plan changes / pause / resume / reactivation ---------------
        still = np.where(status == 1)[0]
        for i in still[r.random(len(still)) < C.PLAN_CHANGE_RATE["upgrade"]]:
            c = C.TIERS.index(tier[i])
            if c < 2:
                emit(i, "plan_change", idx, from_tier=tier[i], to_tier=C.TIERS[c + 1])
                tier[i] = C.TIERS[c + 1]
        for i in still[r.random(len(still)) < C.PLAN_CHANGE_RATE["downgrade"]]:
            c = C.TIERS.index(tier[i])
            if c > 0:
                emit(i, "plan_change", idx, from_tier=tier[i], to_tier=C.TIERS[c - 1])
                tier[i] = C.TIERS[c - 1]
        for i in still[r.random(len(still)) < C.PAUSE_RATE]:
            status[i] = 2
            emit(i, "pause", idx)
        paused = np.where(status == 2)[0]
        for i in paused[r.random(len(paused)) < C.RESUME_RATE]:
            status[i] = 1
            emit(i, "resume", idx)
        churned = np.where(status == 3)[0]
        elig = churned[(churn_idx[churned] < idx) & (churn_idx[churned] >= idx - 12)]
        for i in elig[r.random(len(elig)) < (C.REACTIVATION_RATE / 12.0)]:
            status[i] = 1
            tenure[i] = 0
            churn_idx[i] = -1
            churn_kind[i] = 0
            emit(i, "reactivate", idx, to_tier=tier[i])

        # ---- record monthly rows (active + paused + churned-this-month) ----
        churned_now = (churn_idx == idx) & (status == 3)
        rec = np.where((status == 1) | (status == 2) | churned_now)[0]
        for i in rec:
            p = _price_local(tier[i], market[i], idx, migrated[i])
            mrr = p if billing[i] == "monthly" else round(p * C.ANNUAL_MONTHS_CHARGED / 12.0, 2)
            st = {1: "active", 2: "paused", 3: "churned"}[int(status[i])]
            hv = 0.0 if status[i] == 2 else float(hours_buf[i])   # real hours for active & churned-now
            sub_month_rows.append({
                "subscriber_id": sid[i], "month_idx": idx, "status": st,
                "tier": tier[i], "billing_period": billing[i],
                "mrr_local": round(mrr, 2) if status[i] == 1 else 0.0,
                "tenure_months": int(max(tenure[i], 0)), "streamed_hours": round(hv, 2),
                "is_below_healthy_engagement": bool(st != "paused" and hv < C.HEALTHY_ENGAGEMENT_HOURS),
                "primary_device_family": dev_family[i], "ctv_share": round(float(ctv_share[i]), 3),
                "is_voluntary_churn": bool(churn_idx[i] == idx and churn_kind[i] == 1),
                "is_involuntary_churn": bool(churn_idx[i] == idx and churn_kind[i] == 2),
            })
            if status[i] == 1 and hv > 0:
                viewing_month_rows.append({"subscriber_id": sid[i], "month_idx": idx,
                                           "streamed_hours": round(hv, 2),
                                           "primary_device_family": dev_family[i],
                                           "ctv_share": float(ctv_share[i])})

        tenure[status == 1] += 1
        progress(f"world: month {idx + 1:02d}/{C.N_MONTHS}  active={int((status == 1).sum()):,}")

    world = {
        "subscribers": subs,
        "subscription_month": pd.DataFrame(sub_month_rows),
        "subscription_events": pd.DataFrame(events),
        "billing_attempts": pd.DataFrame(billing_rows),
        "viewing_month": pd.DataFrame(viewing_month_rows),
    }
    ch = subs[["subscriber_id", "market", "signup_idx", "channel", "first_tier",
               "primary_device_family"]].copy()
    ch["churn_month_idx"] = churn_idx
    ch["churn_kind"] = np.where(churn_kind == 1, "voluntary",
                                np.where(churn_kind == 2, "involuntary", ""))
    world["subscriber_churn"] = ch
    return world


# --------------------------------------------------------------------------
def _fail_reason(method, r):
    pool = {
        "card": ["insufficient_funds", "do_not_honor", "expired_card", "card_declined"],
        "pix": ["timeout", "user_abandoned"],
        "boleto": ["not_paid", "expired"],
        "oxxo": ["not_paid", "voucher_expired"],
        "carrier_billing": ["carrier_reject", "spend_limit"],
    }[method]
    return str(r.choice(pool))


def _vol_reason(below_healthy, r):
    if below_healthy:
        return str(r.choice(["not_watching", "nothing_to_watch", "not_watching", "too_expensive"]))
    return str(r.choice(["too_expensive", "switched_service", "technical_issues", "temporary_break"]))
