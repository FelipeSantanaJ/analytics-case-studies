"""
07 — Neighbour-zone cannibalisation (the spatial spillover / SUTVA violation).

  A. Adjacent-control gap: fulfillment on control zone-days that ARE next to a
     treated zone that day, minus control zone-days that are NOT — cluster-robust.
  B. Spatial regression on control zone-days:
        fulfillment_rate ~ n_adjacent_zones_treated + pre_fulfillment_rate
                           + C(zone_key) + C(day_of_week)
     the coefficient on n_adjacent_zones_treated is the per-treated-neighbour drag.
  C. Bounded primary effect: re-estimate the fulfillment lift EXCLUDING control
     zone-days adjacent to a treated zone (a clean-control bound).
  D. Cannibalisation-adjusted metro net: summed local lift x (1 - implied share).
  E. Supply elasticity: available_courier_hours ~ treat, cluster-robust — R$ of bonus
     per extra courier-hour and per incremental delivered order.
"""
from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import numpy as np
import pandas as pd
import statsmodels.formula.api as smf

from utils import (banner, con, diff_in_means_cluster, parity, save_table, welch_t,
                   zone_day)

banner("07 — Neighbour-zone cannibalisation")
d = zone_day()
ctrl = d[d.arm == "control"].copy()

# ---- A. adjacent-control gap ----------------------------------
adj = ctrl[ctrl.is_adjacent_to_treated == True]
noadj = ctrl[ctrl.is_adjacent_to_treated == False]
gapA = welch_t(noadj["fulfillment_rate"], adj["fulfillment_rate"])
clA = diff_in_means_cluster(
    ctrl.assign(treat=ctrl["is_adjacent_to_treated"].astype(int)), "fulfillment_rate")
print(f"A. control zone-days: adjacent-to-treated {adj['fulfillment_rate'].mean()*100:.2f}%  "
      f"vs not {noadj['fulfillment_rate'].mean()*100:.2f}%  -> gap {clA['coef']*100:+.2f} pp "
      f"(cluster 95% CI [{clA['ci_lo']*100:+.2f}, {clA['ci_hi']*100:+.2f}], p={clA['p_value']:.3f})")

# ---- B. spatial regression on control zone-days --------------
mB = smf.ols("fulfillment_rate ~ n_adjacent_zones_treated + pre_fulfillment_rate "
             "+ C(zone_key) + C(day_of_week)", data=ctrl).fit(
    cov_type="cluster", cov_kwds={"groups": ctrl["zone_key"]})
bB = mB.params["n_adjacent_zones_treated"]
print(f"B. per-treated-neighbour drag on a control zone-day: {bB*100:+.3f} pp "
      f"(p={mB.pvalues['n_adjacent_zones_treated']:.3f})")

# ---- C. clean-control bound on the primary lift --------------
clean = d[(d.arm == "treatment") | ((d.arm == "control") & (d.is_adjacent_to_treated == False))]
clC = diff_in_means_cluster(clean, "fulfillment_rate")
full = diff_in_means_cluster(d, "fulfillment_rate")
print(f"C. primary lift  full-control {full['coef']*100:+.2f} pp   "
      f"clean-control (drop adj) {clC['coef']*100:+.2f} pp   "
      f"(the clean bound is larger — adjacent controls are depressed)")

# ---- D. cannibalisation-adjusted metro net ------------------
# summed local lift = treated-zone lift applied to treated placed orders
trt = d[d.arm == "treatment"]
placed = trt["orders_placed"].sum()
local_incr = placed * full["coef"]
# neighbour loss = drag per neighbour * (avg neighbours treated) * control placed on adj days
adj_days = adj
neigh_loss = -bB * adj_days["n_adjacent_zones_treated"].mean() * adj_days["orders_placed"].sum() \
    if len(adj_days) else 0.0
share_cannibalised = neigh_loss / local_incr if local_incr else np.nan
net_incr = local_incr - neigh_loss
print(f"D. local incremental delivered orders  ~ {local_incr:,.0f}")
print(f"   neighbour-zone loss on adjacent control days ~ {neigh_loss:,.0f}")
print(f"   implied cannibalised share ~ {share_cannibalised*100:.0f}%  ->  "
      f"metro NET incremental ~ {net_incr:,.0f}  ({net_incr/local_incr*100:.0f}% of local)")

# ---- E. supply elasticity ---------------------------------
clE = diff_in_means_cluster(d, "available_courier_hours")
bonus = 4.5
extra_ch = clE["coef"]
deliveries_effect = diff_in_means_cluster(d, "orders_delivered")["coef"]
spend_per_zd = trt["incentive_spend_brl"].mean()
print(f"E. treated zone-day: +{extra_ch:.1f} available courier-hours "
      f"(cluster p={clE['p_value']:.3f}); +{deliveries_effect:.1f} delivered orders; "
      f"bonus spend ~ R$ {spend_per_zd:.0f}/zone-day  ->  "
      f"R$ {spend_per_zd/max(extra_ch,1e-6):.2f} per extra courier-hour, "
      f"R$ {spend_per_zd/max(deliveries_effect,1e-6):.2f} per incremental delivered order")

save_table(pd.DataFrame([dict(
    adj_control_gap_pp=clA["coef"] * 100, adj_control_gap_p=clA["p_value"],
    per_neighbour_drag_pp=bB * 100, per_neighbour_drag_p=mB.pvalues["n_adjacent_zones_treated"],
    primary_full_pp=full["coef"] * 100, primary_clean_pp=clC["coef"] * 100,
    local_incremental_orders=local_incr, neighbour_loss_orders=neigh_loss,
    cannibalised_share=share_cannibalised, net_incremental_orders=net_incr,
    net_pct_of_local=net_incr / local_incr * 100,
    extra_courier_hours_per_zd=extra_ch,
    brl_per_extra_courier_hour=spend_per_zd / max(extra_ch, 1e-6),
    brl_per_incremental_delivered_order=spend_per_zd / max(deliveries_effect, 1e-6))]),
    "07_cannibalisation")

# ---- SQL parity ------------------------------------------
c = con()
q = c.execute("""
  SELECT 100*(AVG(CASE WHEN is_adjacent_to_treated THEN fulfillment_rate END)
            - AVG(CASE WHEN NOT is_adjacent_to_treated THEN fulfillment_rate END)) gap
  FROM zd WHERE arm='control'
""").df()["gap"].iloc[0]
parity("adjacent-control gap (pp)", clA["coef"] * 100, q)
print("\n07 cannibalisation: OK")
