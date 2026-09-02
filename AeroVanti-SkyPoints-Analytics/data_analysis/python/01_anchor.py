"""
01 — Anchor: reproduce the Flash Redemption redemption-rate numbers.

Decision it informs: none directly — this establishes the dual-track habit on a
known number before the real tests. Audience: the analyst.

Grain: fact_experiment_outcome = one row per assigned subject (15,000).
Anchor: pooled control vs treatment redemption rate (share redeeming >= 1 time in
the 12-week window), and the per-stratum split. Cross-checked against the DAX
measures [Exp Control Rate] / [Exp Treatment Rate] logic in etl/pbi_measures.py.
"""
from __future__ import annotations
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import pandas as pd
from utils import t, con, save_table, parity, banner, STRATA

banner("01 — Anchor: redemption rate by arm")

oc = t("fact_experiment_outcome")
assert len(oc) == 15000, len(oc)
oc["r"] = oc["redeemed_in_window"].astype(int)

pooled = oc.groupby("arm_key")["r"].agg(n="count", redeemers="sum", rate="mean").reset_index()
by_str = (oc.groupby(["stratum", "arm_key"])["r"].agg(n="count", redeemers="sum", rate="mean")
          .reset_index())
wide = by_str.pivot(index="stratum", columns="arm_key", values="rate").reindex(STRATA)
wide["lift_pp"] = (wide["treatment"] - wide["control"]) * 100
wide["n_ctrl"] = by_str[by_str.arm_key == "control"].set_index("stratum")["n"].reindex(STRATA)
wide["n_treat"] = by_str[by_str.arm_key == "treatment"].set_index("stratum")["n"].reindex(STRATA)

print("\nPooled:")
print(pooled.to_string(index=False))
print(f"\nPooled lift (pp): {(pooled.set_index('arm_key').loc['treatment','rate'] - pooled.set_index('arm_key').loc['control','rate'])*100:+.2f}")
print("\nBy stratum:")
print(wide.round(4).to_string())

save_table(pooled, "01_anchor_pooled")
save_table(wide.reset_index(), "01_anchor_by_stratum")

# ---- SQL track ----
c = con()
sql_pooled = c.execute("""
    SELECT arm_key, COUNT(*) n, SUM(CAST(redeemed_in_window AS INT)) redeemers,
           AVG(CAST(redeemed_in_window AS INT)) rate
    FROM fact_experiment_outcome GROUP BY 1 ORDER BY 1
""").df()
sql_str = c.execute("""
    SELECT stratum, arm_key, AVG(CAST(redeemed_in_window AS INT)) rate
    FROM fact_experiment_outcome GROUP BY 1,2
""").df()

parity("pooled control rate", pooled.set_index("arm_key").loc["control", "rate"],
       sql_pooled.set_index("arm_key").loc["control", "rate"])
parity("pooled treatment rate", pooled.set_index("arm_key").loc["treatment", "rate"],
       sql_pooled.set_index("arm_key").loc["treatment", "rate"])
for s in STRATA:
    for a in ("control", "treatment"):
        pv = by_str[(by_str.stratum == s) & (by_str.arm_key == a)]["rate"].iloc[0]
        sv = sql_str[(sql_str.stratum == s) & (sql_str.arm_key == a)]["rate"].iloc[0]
        parity(f"{s}/{a} rate", pv, sv)

print("\n01 anchor: OK")
