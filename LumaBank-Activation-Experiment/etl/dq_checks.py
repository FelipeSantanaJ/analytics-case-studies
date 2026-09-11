"""
LumaBank — dq_checks.py

Hard assertions on the curated star, including the SRM check that WOULD CATCH the
production bug (a significant sample-ratio mismatch inside the original run, and a
clean re-run). Assembles data/quality/dq_report.md from the fragments. Exits
non-zero on any violated hard assertion.
"""

from __future__ import annotations

import sys
from datetime import datetime

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

import numpy as np
import pandas as pd

import config as C
from utils import banner, read_dq_fragments

CUR = C.CURATED_DIR
FAILURES: list[str] = []
NOTES: list[str] = []


def check(cond, msg, hard=True):
    print(f"  [{'PASS' if cond else ('FAIL' if hard else 'WARN')}] {msg}")
    if not cond:
        (FAILURES if hard else NOTES).append(msg)


def L(name):
    return pd.read_parquet(CUR / f"{name}.parquet")


def main():
    banner("LumaBank — dq_checks")
    du = L("dim_user")
    fva = L("fact_variant_assignment")
    fa = L("fact_activation")
    fos = L("fact_onboarding_step")
    ftd = L("fact_transaction_day")
    fsrm = L("fact_srm_daily")
    dstep = L("dim_onboarding_step")

    uk = set(du["user_key"]).union({-1})

    # ---- referential integrity --------------------------------------
    for t, df in [("fact_variant_assignment", fva), ("fact_activation", fa),
                  ("fact_onboarding_step", fos), ("fact_transaction_day", ftd),
                  ("fact_fraud_event", L("fact_fraud_event")), ("fact_support_ticket", L("fact_support_ticket"))]:
        check(df["user_key"].isin(uk).all(), f"{t}.user_key resolves (real or -1)")

    # ---- assignment integrity -------------------------------------
    check(not fva.duplicated(["user_id", "assignment_seq"]).any(),
          "fact_variant_assignment unique on (user_id, assignment_seq)")
    firsts = fva[fva["is_first_assignment"]].groupby("user_id").size()
    check((firsts == 1).all(), "exactly one is_first_assignment per user")
    eff = fva[fva["is_effective_assignment"]].groupby("user_id").size()
    check((eff == 1).all(), "exactly one is_effective_assignment per user")
    check(fa.loc[fa["is_experiment_subject"], "user_id"].isin(set(fva["user_id"])).all(),
          "every experiment-subject fact_activation user has a variant assignment")
    check(len(fa) == int((du["user_key"] > 0).sum()),
          "fact_activation has one row per real signup (platform-wide grain, excl. the dim_user sentinel)")

    # ---- activation identity (recomputed) ------------------------
    a = fa.copy()
    a["ft"] = pd.to_datetime(a["first_txn_ts"])
    a["as_"] = pd.to_datetime(a["assigned_ts"])
    recomputed = (a["account_opened_flag"].astype(bool) & a["ft"].notna()
                  & (a["ft"] <= a["as_"] + pd.Timedelta(days=7))).astype(int)
    check((recomputed == a["day7_activated"]).mean() > 0.999,
          "day7_activated == account_opened AND first_txn within 7 days")

    # ---- funnel monotonicity (core funnel to activation; limits_lifted is a
    #      parallel KYC-completion milestone, not downstream of first_transaction) ----
    reach = (fos.merge(dstep[["step_key", "step_order", "step_name"]], on="step_key", how="left")
             .groupby("step_order")["user_id"].nunique().sort_index())
    core = reach[reach.index <= 5]
    check((core.diff().dropna() <= 0).all(),
          f"core onboarding funnel non-increasing by order ({reach.to_dict()})")

    # ---- THE SRM CHECK (would catch the bug) --------------------
    orig = fsrm[fsrm["experiment_phase"] == "original"]
    rer = fsrm[fsrm["experiment_phase"] == "rerun"]
    orig_alert = orig[(orig["assign_date"] >= "2026-07-17") & (orig["alert_state"] == "alert")]
    check(len(orig_alert) > 0,
          f"original run hits an SRM ALERT on/after 2026-07-17 — the deploy is caught "
          f"(first: {orig_alert['assign_date'].min() if len(orig_alert) else 'NONE'})")
    warn_days = orig[orig["alert_state"].isin(["warn", "alert"])]["assign_date"].tolist()
    check(len(warn_days) >= 2, f"original run raises WARN/ALERT on >=2 days ({warn_days[:6]})")
    cum_hit = orig[orig["srm_p_cumulative"] < C.SRM_ALERT_P]
    check(len(cum_hit) > 0,
          f"cumulative SRM p also crosses {C.SRM_ALERT_P} at some point "
          f"(min p = {orig['srm_p_cumulative'].min():.4f})", hard=False)
    rer_min_p = rer["srm_p_trailing7"].min()
    check(rer_min_p >= 0.01,
          f"re-run trailing-7d SRM p stays >= 0.01 every day (min {rer_min_p:.3f})", hard=False)
    check((rer["alert_state"] == "ok").all(),
          f"re-run never leaves SRM state 'ok' ({rer['alert_state'].value_counts().to_dict()})")

    # ---- re-run cleanliness -----------------------------------
    clean = fa[fa["in_analysis_flag"]]
    check((~clean["contaminated_flag"]).all(), "in_analysis_flag users are all non-contaminated")
    check((clean["experiment_cohort"] == "rerun").all(), "in_analysis_flag users are all rerun cohort")
    fb_users = set(fva[fva["assignment_source"] == "fallback"]["user_id"])
    check(len(set(clean["user_id"]) & fb_users) == 0,
          "in_analysis_flag users never touched the biased fallback")

    # ---- near-future guard -----------------------------------
    check(ftd["date_key"].max() <= int(f"{C.WINDOW_END:%Y%m%d}"),
          "no transaction-day rows after the window end")
    rr = fa[fa["experiment_cohort"] == "rerun"]
    latest = pd.to_datetime(rr["assigned_ts"]).max()
    check(latest + pd.Timedelta(days=7) <= pd.Timestamp(C.WINDOW_END) + pd.Timedelta(days=1),
          "every re-run user's Day-7 window closes inside the data")

    # ---- benchmark bands (re-run control arm ~= pre-experiment steady state) -----
    rer_fa = fa[fa["experiment_cohort"] == "rerun"]
    ctrl = rer_fa[rer_fa["arm_key"] == "control"]
    d7 = ctrl["day7_activated"].mean()
    check(0.40 <= d7 <= 0.56, f"re-run control Day-7 activation {d7:.3f} in [0.40, 0.56]", hard=False)
    kyc_rej = ctrl["kyc_rejected_flag"].mean()
    check(0.04 <= kyc_rej <= 0.16, f"re-run control KYC rejection rate {kyc_rej:.3f} in [0.04, 0.16]", hard=False)
    fraud = ctrl[ctrl["day7_activated"] == 1]["fraud_flag_30d"].mean()
    check(0.003 <= fraud <= 0.035, f"re-run control flagged-fraud rate {fraud:.4f} in [0.003, 0.035]", hard=False)
    tickets = ctrl["onboarding_tickets_n"].sum() / len(ctrl) * 1000
    check(40 <= tickets <= 170, f"re-run control onboarding tickets per 1k {tickets:.0f} in [40, 170]", hard=False)

    # ---- truth peek (informational) ---------------------------
    for coh in ("pre_deploy", "rerun"):
        c = fa[fa["experiment_cohort"] == coh]
        rr_ = c.groupby("arm_key")["day7_activated"].mean()
        lift = rr_.get("treatment", np.nan) - rr_.get("control", np.nan)
        print(f"  [info] {coh}: control={rr_.get('control', float('nan')):.4f} "
              f"treatment={rr_.get('treatment', float('nan')):.4f} lift={lift*100:+.2f} pp  n={len(c)}")
    print(f"  [info] contaminated in exp1: {fa[fa.experiment_cohort.isin(['pre_deploy','post_deploy'])]['contaminated_flag'].sum()}")
    print(f"  [info] fallback assignments: {len(fb_users)}")

    # ---- assemble report ------------------------------------
    frags = read_dq_fragments()
    lines = ["# LumaBank — Data Quality Report",
             f"\n_Generated {datetime.utcnow().isoformat()}Z · SEED={C.SEED}_\n",
             "## Assertion results\n",
             f"- **{len(FAILURES)} hard failures**, {len(NOTES)} warnings\n"]
    lines += [f"- FAIL {f}" for f in FAILURES] + [f"- warn {w}" for w in NOTES]
    lines.append("\n## Per-entity counters\n")
    for fr in frags:
        lines.append(f"### `{fr['entity']}`\n")
        for k, v in fr["counters"].items():
            lines.append(f"- {k}: {v}")
        lines.append("")
    C.QUALITY_DIR.mkdir(parents=True, exist_ok=True)
    (C.QUALITY_DIR / "dq_report.md").write_text("\n".join(lines), encoding="utf-8")
    print(f"\n  dq_report.md written ({len(frags)} fragments)")

    if FAILURES:
        print(f"\n{'!' * 60}\n  {len(FAILURES)} HARD DQ FAILURES\n{'!' * 60}")
        sys.exit(1)
    banner("dq_checks complete — all hard assertions passed")


if __name__ == "__main__":
    main()
