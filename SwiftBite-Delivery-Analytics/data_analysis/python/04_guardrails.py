"""
04 — Guardrails.

  G1  Incentive cost per incremental delivered order (BRL) — the go/no-go economics,
      with a zone-cluster bootstrap CI on the ratio, vs the delivered-order
      contribution margin.
  G2  ETA p50 / p90 by arm (cluster-robust).
  G3  Cancellation rate, total and no-courier, by arm.
  G4  Courier earnings per active hour by arm.
"""
from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import numpy as np
import pandas as pd

from utils import (banner, con, diff_in_means_cluster, parity, ratio_bootstrap,
                   save_table, zone_day)

CONTRIB_MARGIN_BRL = 10.0   # delivered-order contribution margin (doc 01 §9.4 mid-band)

banner("04 — Guardrails")
d = zone_day()
ctrl, trt = d[d.arm == "control"], d[d.arm == "treatment"]

# ---- G1: incentive cost per incremental delivered order ------------
# Incremental delivered orders = (treated fulfillment - control fulfillment) x treated
# orders placed, evaluated per zone (matched control) and POOLED (sum/sum) so that
# zones with ~zero real lift correctly contribute ~zero incremental, not a clipped
# near-zero denominator. Cluster (zone) bootstrap of the pooled ratio.
lift = trt["fulfillment_rate"].mean() - ctrl["fulfillment_rate"].mean()
trt_by_zone = trt.groupby("zone_key")
spend_by_zone = trt_by_zone["incentive_spend_brl"].sum()
ctrl_ff_by_zone = ctrl.groupby("zone_key")["fulfillment_rate"].mean()
placed_by_zone = trt_by_zone["orders_placed"].sum()
incr_by_zone = placed_by_zone * (trt_by_zone["fulfillment_rate"].mean() - ctrl_ff_by_zone)
g1 = ratio_bootstrap(spend_by_zone, incr_by_zone)      # pooled sum/sum, zone-resampled
total_spend = float(spend_by_zone.sum())
total_incr = float(incr_by_zone.sum())
subsidised = float(trt["deliveries"].sum())
print(f"G1  incentive spend (treated)      : R$ {total_spend:,.0f}   on {subsidised:,.0f} delivered orders")
print(f"    incremental delivered orders   : {total_incr:,.0f}   "
      f"({total_incr/subsidised*100:.1f}% of the subsidised orders; lift {lift*100:+.2f} pp)")
print(f"    cost per incremental order     : R$ {g1['point']:.2f}   "
      f"(zone-bootstrap 95% CI [R$ {g1['ci_lo']:.2f}, R$ {g1['ci_hi']:.2f}])")
print(f"    vs contribution margin R$ {CONTRIB_MARGIN_BRL:.2f}  ->  "
      f"{'PAYS FOR ITSELF' if g1['point'] < CONTRIB_MARGIN_BRL else 'COSTS MORE THAN THE MARGIN OF A SAVED ORDER'} "
      f"(CI {'excludes' if g1['ci_lo'] > CONTRIB_MARGIN_BRL else 'straddles' if g1['ci_lo'] <= CONTRIB_MARGIN_BRL <= g1['ci_hi'] else 'below'} the margin)")
print(f"    value destroyed per subsidised order ~ R$ {(total_spend - CONTRIB_MARGIN_BRL*total_incr)/subsidised:.2f}"
      f"  (bonus paid on every delivery; only ~{total_incr/subsidised*100:.0f}% are incremental)")

# ---- G2 / G3 / G4 -------------------------------------------------
rows = []
for y, label, unit, scale in [
    ("eta_p50_min", "ETA p50", "min", 1),
    ("eta_p90_min", "ETA p90", "min", 1),
    ("cancel_rate", "Cancellation rate", "pp", 100),
    ("cancel_no_courier_rate", "No-courier cancel rate", "pp", 100),
    ("courier_earnings_per_active_hour_brl", "Courier earnings / active hr", "BRL", 1),
]:
    cl = diff_in_means_cluster(d, y)
    rows.append(dict(guardrail=label, unit=unit,
                     control=ctrl[y].mean() * scale, treatment=trt[y].mean() * scale,
                     effect=cl["coef"] * scale, ci_lo=cl["ci_lo"] * scale,
                     ci_hi=cl["ci_hi"] * scale, cluster_p=cl["p_value"]))
gr = pd.DataFrame(rows)
print("\nG2-G4 (cluster-robust):")
print(gr.round(3).to_string(index=False))

save_table(pd.DataFrame([dict(
    incentive_spend_brl=total_spend, incremental_orders=total_incr,
    cost_per_incremental_order_brl=g1["point"], ci_lo=g1["ci_lo"], ci_hi=g1["ci_hi"],
    contribution_margin_brl=CONTRIB_MARGIN_BRL,
    verdict="pays" if g1["point"] < CONTRIB_MARGIN_BRL else "too costly")]), "04_g1")
save_table(gr, "04_guardrails")

# ---- SQL parity -------------------------------------------------
c = con()
q = c.execute("""
  SELECT SUM(CASE WHEN treat=1 THEN incentive_spend_brl END) spend,
         AVG(CASE WHEN treat=1 THEN courier_earnings_per_active_hour_brl END)
       - AVG(CASE WHEN treat=0 THEN courier_earnings_per_active_hour_brl END) earn_effect
  FROM zd
""").df().iloc[0]
parity("G1 incentive spend", total_spend, q["spend"])
parity("G4 earnings/active-hr effect",
       gr.set_index("guardrail").loc["Courier earnings / active hr", "effect"], q["earn_effect"])
print("\n04 guardrails: OK")
