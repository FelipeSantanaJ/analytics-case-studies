"""
AeroVanti SkyPoints — dq_checks.py

Hard assertions on the curated star + accounting identities. Assembles
data/quality/dq_report.md from the fragments written by 02 / 03. Exits non-zero
on any violated assertion so the pipeline fails loudly.
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


def check(cond: bool, msg: str, hard: bool = True):
    tag = "PASS" if cond else ("FAIL" if hard else "WARN")
    print(f"  [{tag}] {msg}")
    if not cond:
        (FAILURES if hard else NOTES).append(msg)


def L(name):
    return pd.read_parquet(CUR / f"{name}.parquet")


def main():
    banner("AeroVanti SkyPoints — dq_checks")
    dm = L("dim_member")
    mm = L("fact_member_month")
    fpt = L("fact_point_transaction")
    fseg = L("fact_flight_segment")
    fli = L("fact_liability_month")
    asg = L("fact_experiment_assignment")
    ow = L("fact_experiment_outcome")
    fw = L("fact_experiment_member_week")

    # ---- keys / referential integrity --------------------------------
    check(fpt["txn_id"].is_unique, "fact_point_transaction.txn_id unique")
    check(fseg["member_key"].isin(dm["member_key"].tolist() + [-1, -2]).all(),
          "every flight-segment member_key resolves (real or sentinel)")
    check(mm["member_key"].isin(dm["member_key"]).all(),
          "every fact_member_month.member_key in dim_member")
    check(set(fpt["txn_type"].unique()) <= {"earn", "redeem", "expire", "adjust"},
          "fact_point_transaction.txn_type in controlled set")
    check((fpt.loc[fpt.txn_type.eq("earn"), "points"] > 0).all(), "earn points positive")
    check((fpt.loc[fpt.txn_type.isin(["redeem", "expire"]), "points"] < 0).all(),
          "redeem/expire points negative")

    # ---- points roll-forward identity (program-wide, per month) ------
    roll = (fpt.groupby(["month_key", "txn_type"])["points"].sum().unstack(fill_value=0))
    for c in ("earn", "redeem", "expire"):
        roll[c] = roll.get(c, 0)
    roll["net"] = roll["earn"] + roll["redeem"] + roll["expire"] + roll.get("adjust", 0)
    prog_balance = roll["net"].cumsum()
    mm_balance = mm.groupby("month_key")["balance_pts_eom"].sum()
    common = prog_balance.index.intersection(mm_balance.index)
    rel = ((prog_balance[common] - mm_balance[common]).abs()
           / prog_balance[common].abs().replace(0, np.nan)).max()
    check(rel < 0.01, f"points roll-forward: program balance == sum(member balance) (max rel err {rel:.4f})")

    # ---- liability tie-out ------------------------------------------
    j = fli.dropna(subset=["points_issued_m_ledger"])
    if len(j):
        e = ((j["points_issued_m"] - j["points_issued_m_ledger"]).abs()
             / j["points_issued_m"].replace(0, np.nan)).mean()
        check(e < 0.02, f"liability ledger tie-out: issued points within 2% (mean {e:.3%})", hard=False)

    # ---- lapse honesty --------------------------------------------
    early = mm[mm["tenure_months"] < C.LAPSE_INACTIVITY_MONTHS]
    check(early["is_lapsed_eom"].isna().all(),
          "is_lapsed_eom is null for tenure < 12 months (not coerced False)")
    # lapsed is sticky until reactivation
    s = mm.sort_values(["member_key", "month_key"])
    lap = s["is_lapsed_eom"].fillna(0)
    same = s["member_key"].eq(s["member_key"].shift(1))
    bad = int((same & lap.shift(1).eq(1) & lap.eq(0) & ~s["is_reactivation"].fillna(False)).sum())
    check(bad == 0, f"lapsed members stay lapsed until a reactivation ({bad} violations)", hard=False)

    # ---- experiment integrity -----------------------------------
    check(len(asg) == C.EXPERIMENT_TOTAL_N,
          f"fact_experiment_assignment has {C.EXPERIMENT_TOTAL_N} rows (got {len(asg)})", hard=False)
    check(fw["member_key"].isin(asg["member_key"]).all(),
          "every experiment-week member_key is an assigned subject")
    check(ow["member_key"].isin(asg["member_key"]).all(),
          "every experiment-outcome member_key is an assigned subject")
    # SRM sanity at build time: 50/50 within stratum
    r = asg.groupby("stratum")["arm_key"].value_counts().unstack()
    ratio = (r["treatment"] / (r["treatment"] + r["control"]))
    check(ratio.between(0.47, 0.53).all(),
          f"build-time allocation ~50/50 within every stratum ({ratio.round(3).to_dict()})")
    # primary outcome consistent with weekly OR
    wk_any = fw.groupby("member_key")["redeemed_w"].any()
    o = ow.set_index("member_key")["redeemed_in_window"].astype(bool)
    common = wk_any.index.intersection(o.index)
    agree = (wk_any[common] == o[common]).mean()
    check(agree > 0.98, f"redeemed_in_window == OR(weekly redeemed_w) ({agree:.3%} agree)", hard=False)
    # post-window horizon
    check(pd.Timestamp(C.WINDOW_END) - pd.Timestamp(C.EXPERIMENT_END) >= pd.Timedelta(days=90),
          "data extends >= 90 days past experiment end")

    # ---- benchmark bands (pre-experiment steady state) --------------
    dm_ss = set(dm.loc[dm["is_steady_state_cohort"], "member_key"])
    pre = mm[(mm["month_key"] <= 202512) & (mm["member_key"].isin(dm_ss))]
    active_pre = pre[pre["is_active_eom"]]
    # quarterly redemption rate (approx: monthly redeemers *3 / active)
    q_red = (pre.groupby("month_key").apply(
        lambda x: (x["redemptions_m"] > 0).sum() / max(1, x["is_active_eom"].sum()))
        * 3).mean()
    check(0.06 <= q_red <= 0.18, f"pre-experiment quarterly redemption rate {q_red:.3f} in [0.06,0.18]", hard=False)
    ever = mm[(mm["month_key"] == 202512)]
    ever_sh = ever["has_redeemed_ever_eom"].mean()
    check(0.18 <= ever_sh <= 0.55, f"ever-redeemed share @2025-12 {ever_sh:.3f} in [0.18,0.55]", hard=False)
    # burn/earn ratio window-to-date
    tot_e = fpt.loc[fpt.txn_type.eq("earn"), "points"].sum()
    tot_r = -fpt.loc[fpt.txn_type.eq("redeem"), "points"].sum()
    be = tot_r / tot_e
    check(0.30 <= be <= 0.85, f"burn/earn ratio {be:.3f} in [0.30,0.85]", hard=False)
    # tier mix of active members at window end
    last = mm[mm["month_key"] == 202608]
    mix = last[last["is_active_eom"]]["tier_key"].value_counts(normalize=True).sort_index()
    check(0.55 <= mix.get(1, 0) <= 0.80, f"Blue share of active @end {mix.get(1,0):.3f} in [0.55,0.80]", hard=False)

    # ---- experiment truth peek (informational) --------------------
    rr = ow.groupby("arm_key")["redeemed_in_window"].mean()
    lift = rr.get("treatment", np.nan) - rr.get("control", np.nan)
    print(f"\n  [info] control={rr.get('control',float('nan')):.4f}  "
          f"treatment={rr.get('treatment',float('nan')):.4f}  lift={lift*100:+.2f} pp")
    by = ow.groupby(["stratum", "arm_key"])["redeemed_in_window"].mean().unstack()
    print(by.round(4).to_string())

    # ---- assemble report --------------------------------------------
    frags = read_dq_fragments()
    lines = [f"# AeroVanti SkyPoints — Data Quality Report",
             f"\n_Generated {datetime.utcnow().isoformat()}Z · SEED={C.SEED}_\n",
             f"## Assertion results\n",
             f"- **{len(FAILURES)} hard failures**, {len(NOTES)} warnings\n"]
    for f in FAILURES:
        lines.append(f"- ❌ {f}")
    for w in NOTES:
        lines.append(f"- ⚠️ {w}")
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
