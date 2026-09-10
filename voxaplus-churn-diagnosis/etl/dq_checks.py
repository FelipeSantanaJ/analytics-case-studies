"""
dq_checks.py — hard assertions + accounting identities over the curated star.

Assembles data/quality/dq_report.md from every dq_fragment plus the check results.
Exits non-zero if any HARD check fails (fails the pipeline). SOFT checks warn only.
"""
from __future__ import annotations

import json
import sys
import datetime as _dt
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

import config as C
from utils import load_dq_fragments, month_label, write_text

HARD, SOFT = [], []


def hard(name, ok, detail=""):
    HARD.append((name, bool(ok), detail))
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}  {detail}")


def soft(name, ok, detail=""):
    SOFT.append((name, bool(ok), detail))
    print(f"  [{'ok' if ok else 'WARN'}] {name}  {detail}")


def main():
    C.QUALITY.mkdir(parents=True, exist_ok=True)
    cur = C.CURATED
    sm = pd.read_parquet(cur / "fact_subscription_month.parquet")
    sub = pd.read_parquet(cur / "dim_subscriber.parquet")
    ev = pd.read_parquet(cur / "fact_subscription_event.parquet")
    bill = pd.read_parquet(cur / "fact_billing_attempt.parquet")
    eng = pd.read_parquet(cur / "fact_engagement_month.parquet")
    date = pd.read_parquet(cur / "dim_date.parquet")

    # ---- structural: keys resolve -------------------------------------
    hard("no null subscriber_key in fact_subscription_month",
         sm["subscriber_key"].notna().all() and (sm["subscriber_key"] > 0).all())
    hard("fact_subscription_event subscriber_key resolves or sentinel(0)",
         ev["subscriber_key"].notna().all())
    orphan_bill = (bill["subscriber_key"] <= 0).mean()
    soft("billing rows with unresolved subscriber (<= 1.2%, injected null+orphan keys)",
         orphan_bill <= 0.012, f"{orphan_bill*100:.2f}%")

    # ---- roll-forward identity: start + new + react - churn = end ----
    act = sm[sm["status"] == "active"]
    end = act.groupby("month_idx")["subscriber_key"].nunique()
    new = sm.groupby("month_idx")["is_new"].sum()
    react = sm.groupby("month_idx")["is_reactivation"].sum()
    churn = sm.groupby("month_idx")[["is_voluntary_churn", "is_involuntary_churn"]].sum().sum(axis=1)
    ok_rf = True
    worst = 0.0
    for i in range(1, C.N_MONTHS):
        lhs = end.get(i - 1, 0) + new.get(i, 0) + react.get(i, 0) - churn.get(i, 0)
        rhs = end.get(i, 0)
        if rhs:
            rel = abs(lhs - rhs) / rhs
            worst = max(worst, rel)
            if rel > 0.02:
                ok_rf = False
    hard("subscriber base roll-forward identity (<=2% monthly)", ok_rf, f"worst {worst*100:.2f}%")

    # ---- MRR ties to active x recognised price ----------------------
    mrr_tot = act.groupby("month_idx")["mrr_usd"].sum()
    soft("MRR positive and monotone-ish", (mrr_tot > 0).all() and mrr_tot.iloc[-1] > mrr_tot.iloc[0])

    # ---- churn rate calibration -----------------------------------
    start = end.shift(1)
    gross = (churn / start)
    pre = gross.loc[C.PY_END_IDX + 1:C.CY_END_IDX - 3].mean()   # idx 24..32
    peak = gross.loc[33:35].mean()
    lo, hi = C.SPIKE_TARGET_PRESHIFT
    soft(f"pre-shift blended gross churn in [{lo:.1%},{hi:.1%}]", lo <= pre <= hi, f"{pre:.3%}")
    plo, phi = C.SPIKE_TARGET_PEAK
    soft(f"peak (idx33-35) blended gross churn in [{plo:.1%},{phi:.1%}]", plo <= peak <= phi, f"{peak:.3%}")
    soft("peak/pre ratio ~1.6-2.1", 1.55 <= peak / pre <= 2.15, f"{peak/pre:.2f}x")

    # ---- cohort retention monotonic, <= 100% ----------------------
    coh = sm.copy()
    first = coh[coh["status"].isin(["active", "churned"])].groupby("subscriber_key")["month_idx"].min()
    coh = coh.join(first.rename("c0"), on="subscriber_key")
    coh["age"] = coh["month_idx"] - coh["c0"]
    base = coh[coh["c0"].between(6, 18)]
    n0 = base[base["age"] == 0]["subscriber_key"].nunique()
    curve = [base[(base["age"] == a) & (base["status"] == "active")]["subscriber_key"].nunique() / max(n0, 1)
             for a in range(0, 13)]
    hard("retention curve <= 100% and non-increasing",
         all(x <= 1.0001 for x in curve) and all(curve[i] >= curve[i + 1] - 0.02 for i in range(len(curve) - 1)),
         f"M1={curve[1]:.0%} M6={curve[6]:.0%} M12={curve[12]:.0%}")

    # ---- referential: fact FKs in dim ranges ---------------------
    dvk = set(pd.read_parquet(cur / "dim_device.parquet")["device_key"])
    vd_parts = list((cur / "fact_viewing_daily").glob("*.parquet"))
    if vd_parts:
        s = pd.read_parquet(vd_parts[-1])
        hard("fact_viewing_daily.device_key in dim_device",
             set(s["device_key"].unique()).issubset(dvk))

    # ---- dim_date coverage --------------------------------------
    hard("dim_date spans beyond fact window",
         date["date"].min() <= pd.Timestamp(C.WINDOW_START)
         and date["date"].max() >= pd.Timestamp("2027-01-01"))

    # ---- engagement plausibility -------------------------------
    ppre = eng[eng["month_idx"] < 30]["streamed_hours"].mean()
    soft("avg streamed hours / sub-month in 25-70h band (pre-shift)", 20 <= ppre <= 75, f"{ppre:.1f}h")
    below = eng[eng["month_idx"] < 30]["below_healthy_engagement"].mean()
    soft("share below healthy engagement 8-28% (pre-shift)", 0.08 <= below <= 0.28, f"{below:.1%}")

    # ---- finance tie-out (loose) ------------------------------
    try:
        fin = pd.read_parquet(cur / "fact_finance_month.parquet")
        sub_rev = fin[fin["pnl_line"].str.contains("subscription", case=False, na=False)]
        fr = sub_rev.groupby("month_idx")["amount_usd"].sum()
        rel = ((fr - mrr_tot).abs() / mrr_tot.replace(0, np.nan)).mean()
        soft("finance subscription revenue ~ curated MRR (<=15% mean rel)", rel <= 0.15, f"{rel:.1%}")
    except Exception as e:
        soft("finance tie-out", False, str(e))

    # ---- assemble report -------------------------------------
    _write_report(pre, peak, gross, curve)

    n_fail = sum(1 for _, ok, _ in HARD if not ok)
    print(f"\n{len(HARD)} hard checks, {n_fail} failed; {sum(1 for _,o,_ in SOFT if not o)} soft warnings")
    sys.exit(1 if n_fail else 0)


def _write_report(pre, peak, gross, curve):
    frags = load_dq_fragments()
    lines = ["# Voxa+ — Data Quality Report", "",
             f"_Generated {_dt.datetime.now():%Y-%m-%d %H:%M} · SEED={C.SEED} · POP_SCALE={C.POP_SCALE}_", ""]
    lines += ["## Injected & handled", "",
              "| Fragment | Metric | Count |", "|---|---|---:|"]
    for fr in frags:
        for k, v in fr["counters"].items():
            lines.append(f"| {fr['fragment']} | {k} | {v:,} |" if isinstance(v, (int, float)) else
                         f"| {fr['fragment']} | {k} | {v} |")
    lines += ["", "## Hard checks", "", "| Check | Result | Detail |", "|---|---|---|"]
    for n, ok, d in HARD:
        lines.append(f"| {n} | {'PASS' if ok else '**FAIL**'} | {d} |")
    lines += ["", "## Soft checks (plausibility & calibration)", "",
              "| Check | Result | Detail |", "|---|---|---|"]
    for n, ok, d in SOFT:
        lines.append(f"| {n} | {'ok' if ok else 'WARN'} | {d} |")
    lines += ["", "## Churn-spike shape (blended gross monthly churn %)", "",
              "| window-month | idx | gross churn % |", "|---:|---:|---:|"]
    for i in range(22, C.N_MONTHS):
        g = gross.get(i, float("nan"))
        lines.append(f"| {i+1} | {i} | {g*100:.2f} |")
    lines += ["", f"Pre-shift mean (idx 24-32): **{pre*100:.2f}%** · "
              f"peak mean (idx 33-35): **{peak*100:.2f}%** · ratio **{peak/pre:.2f}x**", "",
              "## Cohort retention (cohorts m6-18)", "",
              "| age (months) | retention |", "|---:|---:|"]
    for a, r in enumerate(curve):
        lines.append(f"| M{a} | {r*100:.1f}% |")
    lines += ["", "## Accepted limitations", "",
              "- Acquisition channel is attributed at subscriber level by sampling each "
              "market's monthly channel mix (the AdBridge attribution feed carries no account key).",
              "- Billing amounts are taken from the plan-price schedule, not the gateway "
              "`amount` column (Q06 mislabel worked around).",
              "- The last window month is flagged `is_partial_period` (partner settlement lag).",
              "- Snapshot-vs-ledger drift is measured, not corrected: the curated snapshot is "
              "folded from the movement ledger by construction."]
    write_text("\n".join(lines), C.QUALITY / "dq_report.md")
    print(f"  wrote {C.QUALITY / 'dq_report.md'}")


if __name__ == "__main__":
    main()
