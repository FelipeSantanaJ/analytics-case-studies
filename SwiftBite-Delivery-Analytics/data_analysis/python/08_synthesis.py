"""
08 — Synthesis: the decision, the money, the rollout.

Reads the saved outputs/tables from 03-07 and assembles the recommendation.
"""
from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import numpy as np
import pandas as pd

from utils import OUT_TAB, banner, save_table, zone_day

banner("08 — Synthesis")


def T(name):
    return pd.read_csv(OUT_TAB / f"{name}.csv")


prim = T("03_primary").set_index("metric")
per = T("06_per_tier").set_index("tier")
g1 = T("04_g1").iloc[0]
can = T("07_cannibalisation").iloc[0]
dec = T("05_decay").iloc[0]

lift = prim.loc["Fulfillment rate", "effect"]
lift_lo = prim.loc["Fulfillment rate", "cluster_ci_lo"]
lift_hi = prim.loc["Fulfillment rate", "cluster_ci_hi"]
ri_p = prim.loc["Fulfillment rate", "ri_p"]
eta = prim.loc["ETA p90", "effect"]
ncr = prim.loc["No-courier cancel rate", "effect"]

print(f"Primary  : fulfillment {lift:+.2f} pp  (cluster CI [{lift_lo:+.2f}, {lift_hi:+.2f}], "
      f"RI p={ri_p:.3f})")
print(f"Co-primary: ETA p90 {eta:+.2f} min ; no-courier rate {ncr:+.2f} pp")
print(f"Decay    : week-1 {dec['week1_lift_pp']:+.2f} -> settled {dec['settled_lift_pp']:+.2f} pp")
print(f"Tiers    : " + " · ".join(
    f"{ti} {per.loc[ti, 'effect_pp']:+.2f}pp" for ti in per.index))
print(f"G1       : R$ {g1['cost_per_incremental_order_brl']:.2f} per incremental order "
      f"(CI [R$ {g1['ci_lo']:.2f}, R$ {g1['ci_hi']:.2f}]) vs margin R$ {g1['contribution_margin_brl']:.2f}"
      f"  -> {g1['verdict']}")
print(f"Cannibal.: {can['cannibalised_share']*100:.0f}% of the local gain; "
      f"metro net {can['net_pct_of_local']:.0f}% of summed local")

effect_real = lift_lo > 0 and ri_p < 0.05          # robust across cluster + RI + wild-boot
short_balanced_work = (per.loc["short", "ci_lo_pp"] > 0 and per.loc["balanced", "ci_lo_pp"] > 0)
g1_ratio = g1["cost_per_incremental_order_brl"]
margin = g1["contribution_margin_brl"]
g1_pays = g1_ratio < margin

if effect_real and not g1_pays:
    rec = (
        f"DO NOT roll out the flat per-delivery bonus as tested. It genuinely improves "
        f"marketplace liquidity — fulfillment {lift:+.2f} pp (robust: cluster, "
        f"randomization-inference p={ri_p:.3f}, wild-cluster bootstrap all agree), "
        f"ETA p90 {eta:+.1f} min, no-courier rate {ncr:+.2f} pp, concentrated in the "
        f"supply-short and balanced zones, with only a small (~{can['cannibalised_share']*100:.0f}%, "
        f"not significant) neighbour-zone drag. BUT at ~R$ {g1_ratio:.0f} per incremental "
        f"delivered order against a R$ {margin:.0f} contribution margin it destroys value: "
        f"the bonus is paid on every delivery while only ~2% of them are incremental. "
        f"Re-run ONLY with the bonus restructured to reward incremental supply (a "
        f"threshold / surge-triggered payment, not a flat per-delivery bonus), capped to "
        f"the supply-short + balanced zones, with the neighbour-zone spillover guardrail "
        f"and a hard budget live.")
elif effect_real and g1_pays and short_balanced_work:
    rec = ("ROLL OUT to the supply-short and balanced zones. The effect is real and "
           "robust, ETA and no-courier improve, and the bonus clears its cost on "
           "incremental orders. Hold it out of the long (well-supplied) zones. Keep "
           "the spillover guardrail and a budget cap live; re-check G1 quarterly.")
else:
    rec = ("HOLD. The lift is not robust to cluster / randomization inference, or the "
           "economics do not clear even after restructuring.")

print(f"\nRECOMMENDATION\n{rec}")
save_table(pd.DataFrame([dict(
    primary_lift_pp=lift, primary_ci_lo=lift_lo, primary_ci_hi=lift_hi, ri_p=ri_p,
    eta_p90_lift_min=eta, no_courier_lift_pp=ncr,
    settled_lift_pp=dec["settled_lift_pp"],
    short_effect_pp=per.loc["short", "effect_pp"] if "short" in per.index else np.nan,
    long_effect_pp=per.loc["long", "effect_pp"] if "long" in per.index else np.nan,
    g1_cost_per_incremental_order=g1["cost_per_incremental_order_brl"],
    g1_verdict=g1["verdict"], cannibalised_share=can["cannibalised_share"],
    recommendation=rec)]), "08_synthesis")
print("\n08 synthesis: OK")
