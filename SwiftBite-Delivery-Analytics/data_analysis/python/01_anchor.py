"""
01 — Anchor: reproduce the marketplace baseline and the naive experiment numbers.

Grain: fact_experiment_zone_day, one row per randomised zone-day (peak block).
Establishes the analysis frame the rest of the read-out uses; every later number
is checked against DuckDB on the same parquet.
"""
from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import numpy as np
import pandas as pd

from utils import banner, con, parity, save_table, t, zone_day

banner("01 — Anchor: experiment frame + naive numbers")
d = zone_day()
print(f"zone-days: {len(d)}   arms: {d['arm'].value_counts().to_dict()}")
print(f"zones: {d['zone_key'].nunique()}   dates: {d['date_key'].nunique()}   "
      f"tiers: {d.groupby('baseline_supply_stress_tier')['zone_key'].nunique().to_dict()}")

by_arm = d.groupby("arm").agg(
    n=("zone_key", "size"),
    fulfillment=("fulfillment_rate", "mean"),
    eta_p50=("eta_p50_min", "mean"),
    eta_p90=("eta_p90_min", "mean"),
    no_courier_rate=("cancel_no_courier_rate", "mean"),
    cancel_rate=("cancel_rate", "mean"),
    earn_per_active_hr=("courier_earnings_per_active_hour_brl", "mean"),
    orders_placed=("orders_placed", "sum"),
    orders_delivered=("orders_delivered", "sum"),
    incentive_spend=("incentive_spend_brl", "sum"),
).reset_index()
print("\nNaive by-arm means (NOT the causal estimate — see 03):")
print(by_arm.round(4).to_string(index=False))

tt = by_arm.set_index("arm")
naive = dict(
    fulfillment_lift_pp=100 * (tt.loc["treatment", "fulfillment"] - tt.loc["control", "fulfillment"]),
    eta_p90_lift_min=tt.loc["treatment", "eta_p90"] - tt.loc["control", "eta_p90"],
    no_courier_lift_pp=100 * (tt.loc["treatment", "no_courier_rate"] - tt.loc["control", "no_courier_rate"]),
    earn_per_active_hr_lift=tt.loc["treatment", "earn_per_active_hr"] - tt.loc["control", "earn_per_active_hr"],
    incentive_spend_total=tt.loc["treatment", "incentive_spend"],
)
print("\nNaive lifts:", {k: round(v, 3) for k, v in naive.items()})

# by tier
by_tier = (d.groupby(["baseline_supply_stress_tier", "arm"])["fulfillment_rate"].mean()
           .unstack().reset_index())
by_tier["lift_pp"] = 100 * (by_tier["treatment"] - by_tier["control"])
print("\nNaive fulfillment lift by tier:")
print(by_tier.round(4).to_string(index=False))

save_table(by_arm, "01_by_arm")
save_table(by_tier, "01_by_tier")

# ---- SQL parity -------------------------------------------------------
c = con()
q = c.execute("""
  SELECT 100*(AVG(CASE WHEN arm='treatment' THEN fulfillment_rate END)
            - AVG(CASE WHEN arm='control'   THEN fulfillment_rate END)) fulfillment_lift_pp,
         AVG(CASE WHEN arm='treatment' THEN eta_p90_min END)
       - AVG(CASE WHEN arm='control'   THEN eta_p90_min END) eta_p90_lift_min,
         SUM(CASE WHEN arm='treatment' THEN incentive_spend_brl END) incentive_spend_total,
         COUNT(*) n
  FROM ezd
""").df().iloc[0]
parity("zone-days", len(d), q["n"])
parity("naive fulfillment lift (pp)", naive["fulfillment_lift_pp"], q["fulfillment_lift_pp"])
parity("naive ETA p90 lift (min)", naive["eta_p90_lift_min"], q["eta_p90_lift_min"])
parity("incentive spend total", naive["incentive_spend_total"], q["incentive_spend_total"])
print("\n01 anchor: OK")
