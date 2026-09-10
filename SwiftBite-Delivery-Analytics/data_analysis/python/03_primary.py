"""
03 — Primary effect: the zone-hour incentive on fulfillment rate (+ the two
co-primaries, ETA p90 and the no-courier cancellation rate).

Unit = zone-day. Inference three ways:
  A. OLS with cluster-robust (by zone, 12 clusters) SE — a floor, anti-conservative.
  B. Randomization inference — permute `arm` within zone x weekday/weekend, 3000 draws.
  C. Wild-cluster bootstrap (Rademacher, by zone), 2000 draws.
Also a covariate-adjusted estimate (pre-period fulfillment + liquidity) for variance
reduction, and the realised MDE / power for the zone-day design.
"""
from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import numpy as np
import pandas as pd

from utils import (banner, con, diff_in_means_cluster, parity, randomization_inference,
                   save_table, welch_t, wild_cluster_bootstrap, zone_day)

banner("03 — Primary effect (fulfillment) + co-primaries")
d = zone_day()

rows = []
for y, label, unit, scale in [
    ("fulfillment_rate", "Fulfillment rate", "pp", 100),
    ("eta_p90_min", "ETA p90", "min", 1),
    ("cancel_no_courier_rate", "No-courier cancel rate", "pp", 100),
]:
    naive = welch_t(d.loc[d.arm == "control", y], d.loc[d.arm == "treatment", y])
    cl = diff_in_means_cluster(d, y)
    cl_adj = diff_in_means_cluster(
        d, y, covars="pre_fulfillment_rate + pre_liquidity_ratio + C(baseline_supply_stress_tier)")
    ri = randomization_inference(d, y, n=3000)
    wb = wild_cluster_bootstrap(d, y, n=2000)
    rows.append(dict(
        metric=label, unit=unit,
        control=d.loc[d.arm == "control", y].mean() * scale,
        treatment=d.loc[d.arm == "treatment", y].mean() * scale,
        effect=cl["coef"] * scale,
        welch_ci_lo=naive["ci_lo"] * scale, welch_ci_hi=naive["ci_hi"] * scale,
        cluster_se=cl["se"] * scale, cluster_ci_lo=cl["ci_lo"] * scale,
        cluster_ci_hi=cl["ci_hi"] * scale, cluster_p=cl["p_value"],
        cluster_adj_effect=cl_adj["coef"] * scale, cluster_adj_p=cl_adj["p_value"],
        ri_p=ri["p_value"],
        wildboot_ci_lo=wb["ci_lo"] * scale, wildboot_ci_hi=wb["ci_hi"] * scale,
        wildboot_p=wb["p_value"]))
res = pd.DataFrame(rows)
pd.set_option("display.width", 200)
print(res.round(3).to_string(index=False))
save_table(res, "03_primary")

prim = res.iloc[0]
print(f"\nPRIMARY — fulfillment rate: {prim['effect']:+.2f} pp  "
      f"(cluster 95% CI [{prim['cluster_ci_lo']:+.2f}, {prim['cluster_ci_hi']:+.2f}], "
      f"cluster p={prim['cluster_p']:.4f}; RI p={prim['ri_p']:.4f}; "
      f"wild-boot 95% CI [{prim['wildboot_ci_lo']:+.2f}, {prim['wildboot_ci_hi']:+.2f}], "
      f"p={prim['wildboot_p']:.4f})")
print(f"co-primary ETA p90: {res.iloc[1]['effect']:+.2f} min ; "
      f"no-courier rate: {res.iloc[2]['effect']:+.2f} pp")

# ---- realised MDE / power for the zone-day design -------------------
from scipy import stats
n_arm = int((d.arm == "control").sum())
sd = d.groupby("zone_key")["fulfillment_rate"].apply(lambda s: s.mean()).std()  # between-zone
sd_zd = d["fulfillment_rate"].std()
# design effect from intra-zone correlation
grp = d.groupby("zone_key")["fulfillment_rate"]
icc_num = grp.apply(lambda s: (s - d["fulfillment_rate"].mean()).sum() ** 2).sum()
mss = grp.var().mean()
m_per_zone = len(d) / d["zone_key"].nunique()
# crude ICC via one-way ANOVA
import statsmodels.formula.api as smf
aov = smf.ols("fulfillment_rate ~ C(zone_key)", data=d).fit()
ms_between = aov.ess / (d["zone_key"].nunique() - 1)
ms_within = aov.ssr / (len(d) - d["zone_key"].nunique())
icc = max((ms_between - ms_within) / (ms_between + (m_per_zone - 1) * ms_within), 0)
deff = 1 + (m_per_zone - 1) * icc
mde = 2.8 * sd_zd * np.sqrt(deff) / np.sqrt(n_arm)   # ~ (z_.975 + z_.8) * SE
print(f"\nDesign: {n_arm}/arm, zone-day SD {sd_zd:.3f}, ICC~{icc:.3f}, design effect ~{deff:.2f}"
      f"  ->  MDE (80% power) ~ {mde*100:+.2f} pp on fulfillment.")
save_table(pd.DataFrame([dict(n_per_arm=n_arm, zone_day_sd=sd_zd, icc=icc,
                              design_effect=deff, mde_pp=mde * 100)]), "03_power")

# ---- SQL parity ---------------------------------------------------
c = con()
q = c.execute("""
  SELECT 100*(AVG(CASE WHEN treat=1 THEN fulfillment_rate END)
            - AVG(CASE WHEN treat=0 THEN fulfillment_rate END)) lift_pp
  FROM zd
""").df()["lift_pp"].iloc[0]
parity("primary fulfillment effect (pp)", prim["effect"], q)
print("\n03 primary: OK")
