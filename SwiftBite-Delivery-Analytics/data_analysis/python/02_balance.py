"""
02 — Randomisation & balance. Can the zone-day assignment be trusted?

  1. Sample-ratio: chi-square on treated/control counts overall, per stress tier,
     per weekday/weekend.
  2. Covariate balance: standardized mean differences (treatment - control) on the
     frozen pre-period (months 1-15) covariates. |SMD| < 0.10 = balanced.
  3. A Love plot of the SMDs.
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

from utils import OUT_FIG, banner, chisq_srm, con, parity, save_table, smd, zone_day

banner("02 — Randomisation & balance")
d = zone_day()

# ---- 1. sample-ratio checks ----------------------------------------
srm_rows = [dict(cut="overall", **chisq_srm(d["arm"].value_counts().to_dict()))]
for tier, g in d.groupby("baseline_supply_stress_tier"):
    srm_rows.append(dict(cut=f"tier={tier}", **chisq_srm(g["arm"].value_counts().to_dict())))
for we, g in d.groupby("is_weekend"):
    srm_rows.append(dict(cut=f"weekend={we}", **chisq_srm(g["arm"].value_counts().to_dict())))
srm = pd.DataFrame(srm_rows)[["cut", "chi2", "p_value"]]
print("Sample-ratio (chi-square):")
print(srm.round(4).to_string(index=False))
worst_p = srm["p_value"].min()

# ---- 2. covariate balance (SMD) -----------------------------------
covs = ["pre_fulfillment_rate", "pre_eta_p90_min", "pre_orders_placed_mean",
        "pre_liquidity_ratio", "pre_idle_courier_ratio", "is_weekend"]
ctrl, trt = d[d.arm == "control"], d[d.arm == "treatment"]
bal = pd.DataFrame([dict(
    covariate=c, mean_control=ctrl[c].mean(), mean_treatment=trt[c].mean(),
    smd=smd(ctrl[c], trt[c])) for c in covs])
bal["abs_smd"] = bal["smd"].abs()
print("\nCovariate balance (frozen pre-period):")
print(bal.round(4).to_string(index=False))
max_abs_smd = bal["abs_smd"].max()
print(f"\nmax |SMD| = {max_abs_smd:.3f}  ->  "
      f"{'balanced' if max_abs_smd < 0.10 else 'CHECK — imbalance'}")
save_table(srm, "02_srm")
save_table(bal, "02_balance")

# ---- 3. Love plot ------------------------------------------------
fig, ax = plt.subplots(figsize=(6.4, 3.4))
b = bal.sort_values("abs_smd")
ax.scatter(b["smd"], range(len(b)), color="#1E6B4F", zorder=3)
ax.axvline(0, color="#8090A0", lw=1)
for x in (-0.1, 0.1):
    ax.axvline(x, color="#C0453B", ls=":", lw=1)
ax.set_yticks(range(len(b)))
ax.set_yticklabels(b["covariate"])
ax.set_xlabel("standardized mean difference (treatment - control)")
ax.set_title("Covariate balance — zone-day randomisation", loc="left")
fig.tight_layout()
fig.savefig(OUT_FIG / "02_love_plot.png", dpi=130)
print(f"wrote {OUT_FIG / '02_love_plot.png'}")

# ---- SQL parity -------------------------------------------------
c = con()
q = c.execute("""
  SELECT (AVG(CASE WHEN treat=1 THEN pre_fulfillment_rate END)
        - AVG(CASE WHEN treat=0 THEN pre_fulfillment_rate END))
       / SQRT((VAR_SAMP(CASE WHEN treat=1 THEN pre_fulfillment_rate END)
             + VAR_SAMP(CASE WHEN treat=0 THEN pre_fulfillment_rate END))/2) AS smd_pre_fulfillment,
         SUM(treat) AS n_treat, COUNT(*) AS n
  FROM zd
""").df().iloc[0]
parity("SMD pre_fulfillment_rate", bal.set_index("covariate").loc["pre_fulfillment_rate", "smd"],
       q["smd_pre_fulfillment"])
parity("treated share", (d.treat.mean()), q["n_treat"] / q["n"])
print("\n02 balance: OK" if (worst_p > 0.01 and max_abs_smd < 0.15)
      else "\n02 balance: WARN (inspect)")
