"""
05 — Novelty / decay. Does the lift fade over the 10 weeks?

Uses fact_experiment_zone_block_week (zone x experiment-week x peak hour-block).
  - weekly treated-minus-control fulfillment lift;
  - OLS of the weekly lift on week number (is the slope < 0?);
  - the settled lift (weeks 8-10) vs the week-1 lift.
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

from utils import OUT_FIG, banner, con, parity, save_table, t

banner("05 — Novelty / decay")
w = t("fact_experiment_zone_block_week").copy()
wk = (w.groupby(["experiment_week", "arm"])["fulfillment_rate"].mean().unstack().reset_index())
wk["lift_pp"] = 100 * (wk["treatment"] - wk["control"])
print(wk.round(4).to_string(index=False))

# slope of weekly lift on week
m = smf.ols("lift_pp ~ experiment_week", data=wk).fit()
slope = m.params["experiment_week"]
slope_p = m.pvalues["experiment_week"]
week1 = wk.loc[wk.experiment_week == 1, "lift_pp"].iloc[0]
settled = wk.loc[wk.experiment_week >= 8, "lift_pp"].mean()
print(f"\nweekly-lift slope: {slope:+.3f} pp/week (p={slope_p:.3f})")
print(f"week-1 lift {week1:+.2f} pp  ->  settled (weeks 8-10) {settled:+.2f} pp  "
      f"(decay {week1 - settled:+.2f} pp)")
save_table(wk, "05_weekly_lift")
save_table(pd.DataFrame([dict(slope_pp_per_week=slope, slope_p=slope_p,
                              week1_lift_pp=week1, settled_lift_pp=settled)]), "05_decay")

# ---- figure ----------------------------------------------------
fig, ax = plt.subplots(figsize=(6.6, 3.4))
ax.plot(wk["experiment_week"], wk["control"] * 100, "-o", color="#8090A0", label="control")
ax.plot(wk["experiment_week"], wk["treatment"] * 100, "-o", color="#E8823C", label="treatment")
ax.set_xlabel("experiment week")
ax.set_ylabel("fulfillment rate (%)")
ax.set_title("Weekly fulfillment by arm — launch bump vs settled", loc="left")
ax.legend(frameon=False)
fig.tight_layout()
fig.savefig(OUT_FIG / "05_novelty.png", dpi=130)
print(f"wrote {OUT_FIG / '05_novelty.png'}")

# ---- SQL parity ----------------------------------------------
c = con()
q = c.execute("""
  WITH k AS (
    SELECT experiment_week,
           100*(AVG(CASE WHEN arm='treatment' THEN fulfillment_rate END)
              - AVG(CASE WHEN arm='control'   THEN fulfillment_rate END)) lift_pp
    FROM ebw GROUP BY experiment_week)
  SELECT AVG(CASE WHEN experiment_week>=8 THEN lift_pp END) settled,
         AVG(CASE WHEN experiment_week=1  THEN lift_pp END) week1 FROM k
""").df().iloc[0]
parity("settled lift (weeks 8-10, pp)", settled, q["settled"])
parity("week-1 lift (pp)", week1, q["week1"])
print("\n05 novelty: OK")
