"""
SwiftBite Delivery — dq_checks.py

Hard assertions on the curated star + operational identities + benchmark bands,
then assemble data/quality/dq_report.md from the staging/curated DQ fragments.
Exits non-zero on any violated HARD check. SOFT checks are reported, not fatal.
"""
from __future__ import annotations

import sys
from datetime import timedelta

import numpy as np
import pandas as pd

import config as C
from utils import banner, date_key, read_dq_fragments, read_parquet

CUR = C.CURATED_DIR
HARD, SOFT = [], []


def check(cond: bool, msg: str, hard: bool = True):
    (HARD if hard else SOFT).append((bool(cond), msg))
    tag = "PASS" if cond else ("FAIL" if hard else "WARN")
    print(f"  [{tag}] {msg}")


def main():
    banner("SwiftBite — dq_checks")
    fo = read_parquet(CUR / "fact_order.parquet")
    fd = read_parquet(CUR / "fact_delivery.parquet")
    zh = read_parquet(CUR / "fact_zone_hour.parquet")
    fb = read_parquet(CUR / "fact_courier_shift_block.parquet")
    fia = read_parquet(CUR / "fact_incentive_assignment.parquet")
    ezd = read_parquet(CUR / "fact_experiment_zone_day.parquet")
    dz = read_parquet(CUR / "dim_zone.parquet")
    dd = read_parquet(CUR / "dim_date.parquet")

    # ---- referential integrity
    zk_ok = set(dz["zone_key"]) | {-1, -2}
    check(fo["dropoff_zone_key_current"].isin(zk_ok).all(), "fact_order.dropoff_zone_key_current resolves")
    check(fo["pickup_zone_key"].isin(zk_ok).all(), "fact_order.pickup_zone_key resolves")
    check(fo["order_id"].is_unique, "fact_order unique on order_id")
    check(fd["delivery_key"].is_unique, "fact_delivery unique on delivery_key")
    check(ezd[["zone_key", "date_key"]].apply(tuple, axis=1).isin(
        set(fia[["zone_key", "date_key"]].apply(tuple, axis=1))).all(),
        "every fact_experiment_zone_day zone-day is in fact_incentive_assignment")

    # ---- order conservation per zone-hour
    cc = zh["orders_delivered"] + zh[["cancelled_customer", "cancelled_courier",
                                      "cancelled_no_courier", "cancelled_restaurant"]].sum(axis=1)
    check((cc == zh["orders_placed"]).all(), "order conservation: placed == delivered + all cancels")

    # ---- rate sanity
    fr = zh["fulfillment_rate"].dropna()
    check(fr.between(0, 1).all(), "fulfillment_rate in [0,1]")
    e = zh.dropna(subset=["eta_p50_min", "eta_p90_min"])
    check((e["eta_p50_min"] <= e["eta_p90_min"] + 1e-6).all(), "eta_p50 <= eta_p90")
    check((zh["liquidity_ratio"].dropna() >= 0).all(), "liquidity_ratio >= 0")
    check(zh["idle_courier_ratio"].dropna().between(0, 1).all(), "idle_courier_ratio in [0,1]")

    # ---- experiment integrity
    tr = fia[fia["arm"] == "treatment"]; co = fia[fia["arm"] == "control"]
    check((tr["bonus_brl_per_delivery"] > 0).all(), "treated zone-days have bonus > 0")
    check((co["bonus_brl_per_delivery"] == 0).all(), "control zone-days have bonus == 0")
    for strat, grp in fia.groupby("stratum"):
        share = (grp["arm"] == "treatment").mean()
        check(0.40 <= share <= 0.60, f"allocation ~50/50 in stratum {strat} (got {share:.2f})", hard=False)
    last = ezd["date_key"].max()
    horizon_ok = (pd.Timestamp(C.WINDOW_END) - pd.Timestamp(C.EXPERIMENT_END)).days >= 75
    check(horizon_ok, "fact data extends >= 75 days past experiment end")

    # ---- stress tier recovered == counts plausible
    tc = dz["baseline_supply_stress_tier"].value_counts().to_dict()
    check(tc.get("short", 0) >= 2 and tc.get("long", 0) >= 1,
          f"stress tiers non-degenerate: {tc}", hard=False)

    # ---- benchmark bands on the PRE-experiment baseline (months 1-15)
    base = zh[(zh["date_key"] <= date_key(C.BASELINE_END))]
    peak = base[base["hour"].isin(range(18, 22))]
    m = dict(
        fulfillment=base["fulfillment_rate"].mean(),
        fulfillment_peak=peak["fulfillment_rate"].mean(),
        eta_p50=base["eta_p50_min"].mean(),
        eta_p90=base["eta_p90_min"].mean(),
        cancel_rate=1 - base["fulfillment_rate"].mean(),
        no_courier_rate=(base["cancelled_no_courier"].sum() / base["orders_placed"].sum()),
        idle_ratio=base["idle_courier_ratio"].mean(),
        liquidity=base["liquidity_ratio"].mean(),
    )
    bdk = date_key(C.BASELINE_END)
    ea = fb[fb["date_key"] <= bdk]
    earn_hr = ea["earnings_brl"].sum() / max(ea["active_min"].sum() / 60.0, 1e-6)
    print("  baseline metrics:", {k: round(float(v), 3) for k, v in m.items()},
          "| earn/active-hr:", round(float(earn_hr), 2))
    check(0.93 <= m["fulfillment"] <= 0.995, f"baseline fulfillment {m['fulfillment']:.3f} in [0.93,0.995]", hard=False)
    check(24 <= m["eta_p50"] <= 42, f"baseline ETA p50 {m['eta_p50']:.1f} in [24,42]", hard=False)
    check(42 <= m["eta_p90"] <= 80, f"baseline ETA p90 {m['eta_p90']:.1f} in [42,80]", hard=False)
    check(0.01 <= m["cancel_rate"] <= 0.07, f"baseline cancel rate {m['cancel_rate']:.3f} in [0.01,0.07]", hard=False)
    check(0.10 <= m["idle_ratio"] <= 0.40, f"baseline idle ratio {m['idle_ratio']:.3f} in [0.10,0.40]", hard=False)
    check(20 <= earn_hr <= 40, f"courier earnings/active-hr {earn_hr:.1f} in [20,40]", hard=False)

    # ---- naive experiment read-out (sanity, not the real Phase 10 analysis)
    t = ezd[ezd["arm"] == "treatment"]["fulfillment_rate"].mean()
    c = ezd[ezd["arm"] == "control"]["fulfillment_rate"].mean()
    tsh = ezd.merge(dz[["zone_key", "baseline_supply_stress_tier"]], on="zone_key")
    by_tier = (tsh.groupby(["baseline_supply_stress_tier", "arm"])["fulfillment_rate"].mean().unstack())
    g1 = ezd[ezd["arm"] == "treatment"]["incentive_cost_per_delivered_order_brl"].replace([np.inf], np.nan).mean()
    print(f"\n  NAIVE experiment read (not the Phase-10 analysis):")
    print(f"    fulfillment  treatment={t:.4f}  control={c:.4f}  diff={100*(t-c):+.2f} pp")
    print(f"    by tier (control -> treatment):")
    for tt in by_tier.index:
        row = by_tier.loc[tt]
        print(f"      {tt:9s}  {row.get('control', float('nan')):.3f} -> {row.get('treatment', float('nan')):.3f}"
              f"   ({100*(row.get('treatment',0)-row.get('control',0)):+.2f} pp)")
    print(f"    naive incentive cost / delivered order (treated): R$ {g1:.2f}")

    # ---- assemble dq_report.md
    frags = read_dq_fragments()
    lines = ["# SwiftBite Delivery — Data Quality Report", "",
             f"_Generated by `etl/dq_checks.py`. SEED = {C.SEED}. "
             f"Window {C.WINDOW_START} … {C.WINDOW_END}._", "",
             "## Hard checks", ""]
    for ok, msg in HARD:
        lines.append(f"- {'✅' if ok else '❌'} {msg}")
    lines += ["", "## Soft checks (benchmark bands / calibration)", ""]
    for ok, msg in SOFT:
        lines.append(f"- {'✅' if ok else '⚠️'} {msg}")
    lines += ["", "## Staging / curated fix counters", ""]
    for f in frags:
        lines.append(f"### `{f['entity']}`")
        for k, v in f["counters"].items():
            lines.append(f"- {k}: {v}")
        lines.append("")
    C.QUALITY_DIR.mkdir(parents=True, exist_ok=True)
    (C.QUALITY_DIR / "dq_report.md").write_text("\n".join(lines), encoding="utf-8")
    print(f"\n  wrote {C.QUALITY_DIR / 'dq_report.md'}")

    n_fail = sum(1 for ok, _ in HARD if not ok)
    n_warn = sum(1 for ok, _ in SOFT if not ok)
    banner(f"dq_checks: {len(HARD)-n_fail}/{len(HARD)} hard pass · {n_warn} soft warnings")
    if n_fail:
        sys.exit(1)


if __name__ == "__main__":
    main()
