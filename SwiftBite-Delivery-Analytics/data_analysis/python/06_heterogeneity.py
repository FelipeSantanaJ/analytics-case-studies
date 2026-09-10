"""
06 — Heterogeneity by baseline supply-stress tier.

  - per-tier fulfillment effect with cluster-robust CIs;
  - a formal arm x tier interaction test: OLS
        fulfillment_rate ~ treat * C(tier)
    with cluster-robust (by zone) SEs; Wald test on the two interaction terms,
    plus the plain and cluster LR-style F.
  - a forest plot.
"""
from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import statsmodels.formula.api as smf

from utils import (OUT_FIG, banner, con, diff_in_means_cluster, parity, save_table,
                   zone_day)

banner("06 — Heterogeneity by supply-stress tier")
d = zone_day()
d["tier"] = d["baseline_supply_stress_tier"]

rows = []
for tier, g in d.groupby("tier"):
    r = diff_in_means_cluster(g, "fulfillment_rate")
    rows.append(dict(tier=tier, n_zone=g.zone_key.nunique(), n_zone_day=len(g),
                     control=g.loc[g.arm == "control", "fulfillment_rate"].mean() * 100,
                     treatment=g.loc[g.arm == "treatment", "fulfillment_rate"].mean() * 100,
                     effect_pp=r["coef"] * 100, ci_lo_pp=r["ci_lo"] * 100,
                     ci_hi_pp=r["ci_hi"] * 100, cluster_p=r["p_value"]))
per = pd.DataFrame(rows).sort_values("tier")
print(per.round(3).to_string(index=False))
save_table(per, "06_per_tier")

# ---- formal interaction test ------------------------------------
d["tier"] = pd.Categorical(d["tier"], ["long", "balanced", "short"])   # long = ref
m_full = smf.ols("fulfillment_rate ~ treat * C(tier)", data=d).fit(
    cov_type="cluster", cov_kwds={"groups": d["zone_key"]})
inter = [p for p in m_full.params.index if ":" in p]
wald = m_full.wald_test_terms().table
w = m_full.wald_test(inter, scalar=True)
# plain OLS LR-style F for the interaction (nested models)
m0 = smf.ols("fulfillment_rate ~ treat + C(tier)", data=d).fit()
m1 = smf.ols("fulfillment_rate ~ treat * C(tier)", data=d).fit()
from statsmodels.stats.anova import anova_lm
lr = anova_lm(m0, m1)
print(f"\narm x tier interaction (cluster-robust Wald): "
      f"chi2/F = {float(w.statistic):.2f}, p = {float(w.pvalue):.4f}")
print(f"nested-model F (non-robust): F = {lr['F'].iloc[1]:.2f}, p = {lr['Pr(>F)'].iloc[1]:.4f}")
print("interaction coefficients (vs long-tier reference):")
for p in inter:
    print(f"  {p:32s}  {m_full.params[p]*100:+.2f} pp  (p={m_full.pvalues[p]:.3f})")
save_table(pd.DataFrame([dict(
    interaction_wald_stat=float(w.statistic), interaction_wald_p=float(w.pvalue),
    nested_F=float(lr["F"].iloc[1]), nested_p=float(lr["Pr(>F)"].iloc[1]),
    short_vs_long_pp=m_full.params.get("treat:C(tier)[T.short]", np.nan) * 100,
    balanced_vs_long_pp=m_full.params.get("treat:C(tier)[T.balanced]", np.nan) * 100)]),
    "06_interaction")

# ---- forest plot ---------------------------------------------
fig, ax = plt.subplots(figsize=(6.2, 3.0))
y = range(len(per))
ax.errorbar(per["effect_pp"], y,
            xerr=[per["effect_pp"] - per["ci_lo_pp"], per["ci_hi_pp"] - per["effect_pp"]],
            fmt="o", color="#1E6B4F", capsize=3)
ax.axvline(0, color="#8090A0", lw=1)
ax.set_yticks(list(y))
ax.set_yticklabels(per["tier"])
ax.set_xlabel("fulfillment-rate effect (pp)")
ax.set_title("Incentive effect by baseline supply-stress tier", loc="left")
fig.tight_layout()
fig.savefig(OUT_FIG / "06_forest.png", dpi=130)
print(f"wrote {OUT_FIG / '06_forest.png'}")

# ---- SQL parity -------------------------------------------
c = con()
q = c.execute("""
  SELECT tier,
         100*(AVG(CASE WHEN treat=1 THEN fulfillment_rate END)
            - AVG(CASE WHEN treat=0 THEN fulfillment_rate END)) eff
  FROM zd GROUP BY tier
""").df().set_index("tier")["eff"]
for tier in per["tier"]:
    parity(f"{tier} effect (pp)", per.set_index("tier").loc[tier, "effect_pp"], q.loc[tier])
print("\n06 heterogeneity: OK")
