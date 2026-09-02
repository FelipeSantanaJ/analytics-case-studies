"""
05 — Novelty effect: does the lift decay over the 12-week window?

Decision: what durable effect to expect after rollout (the headline includes a
launch bump). Audience: loyalty director.

Grain: fact_experiment_member_week = one row per subject x experiment week
(15,000 x 12 = 180,000). `redeemed_w` = redeemed at least once that week.

Method (both tracks): weekly redeemers-per-subject by arm; the weekly incremental
(treatment - control); OLS of the incremental on week number (slope < 0 = decay);
weeks 1-4 vs 9-12 comparison; a "settled" effect estimate = mean weekly increment
over weeks 9-12, scaled to a 12-week-equivalent cumulative lift.
"""
from __future__ import annotations
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import numpy as np, pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import statsmodels.formula.api as smf
from utils import t, con, save_table, parity, banner, two_prop, OUT_FIG

banner("05 — Novelty effect")
w = t("fact_experiment_member_week").copy()
w["rw"] = w["redeemed_w"].astype(int)
n_arm = t("fact_experiment_outcome").groupby("arm_key").size()

wk = (w.groupby(["week", "arm_key"])["rw"].sum().unstack("arm_key"))
wk["control_rate"] = wk["control"] / n_arm["control"]
wk["treatment_rate"] = wk["treatment"] / n_arm["treatment"]
wk["incr_pp"] = (wk["treatment_rate"] - wk["control_rate"]) * 100
wk = wk.reset_index()
print("\nWeekly redeemers-per-subject and treatment-control increment:")
print(wk[["week", "control_rate", "treatment_rate", "incr_pp"]].round(4).to_string(index=False))

# slope of the increment on week
ols = smf.ols("incr_pp ~ week", data=wk).fit()
slope, sp = ols.params["week"], ols.pvalues["week"]
early = wk.loc[wk.week <= 4, "incr_pp"].mean()
late = wk.loc[wk.week >= 9, "incr_pp"].mean()
print(f"\nOLS increment ~ week : slope = {slope:+.4f} pp/week  (p = {sp:.3f})")
print(f"weeks 1-4 mean increment = {early:+.3f} pp/wk   weeks 9-12 = {late:+.3f} pp/wk   "
      f"decay = {early-late:+.3f} pp/wk")

# cumulative first-redeemer curve by arm (monotone) — the "redeemed by week k" share
cum = []
for a in ("control", "treatment"):
    sub = w[w.arm_key == a]
    seen = set()
    for k in range(1, 13):
        seen |= set(sub.loc[(sub.week == k) & (sub.rw == 1), "member_key"])
        cum.append(dict(arm_key=a, week=k, cum_redeemed=len(seen) / n_arm[a]))
cum = pd.DataFrame(cum)
cw = cum.pivot(index="week", columns="arm_key", values="cum_redeemed")
cw["cum_lift_pp"] = (cw["treatment"] - cw["control"]) * 100
cw = cw.reset_index()
final_lift = cw.loc[cw.week == 12, "cum_lift_pp"].iloc[0]
# settled: extrapolate the late per-week increment across all 12 weeks
settled_equiv = late * 12 / (early * 4 + late * 8) * final_lift if (early * 4 + late * 8) else final_lift
print(f"\nCumulative 'redeemed by week 12' lift = {final_lift:+.2f} pp")
print(f"~{(1 - late*8/ (final_lift - early*0) if final_lift else 0):.0%} of it is the early bump; "
      f"durable (late-rate-equivalent) lift ~ {settled_equiv:+.2f} pp")
save_table(wk, "05_weekly_increment")
save_table(cw, "05_cumulative_lift")

# figure
fig, ax = plt.subplots(1, 2, figsize=(9.6, 3.4))
ax[0].plot(wk["week"], wk["control_rate"] * 100, "-o", color="#5C8CB8", label="control", ms=4)
ax[0].plot(wk["week"], wk["treatment_rate"] * 100, "-o", color="#E08A1E", label="treatment", ms=4)
ax[0].set_title("Weekly redeemers per subject (%)")
ax[0].set_xlabel("experiment week"); ax[0].legend(frameon=False)
ax[1].bar(wk["week"], wk["incr_pp"], color="#0B5FA5")
ax[1].plot(wk["week"], ols.predict(wk), "--", color="#C0453B", label=f"trend {slope:+.3f} pp/wk")
ax[1].axhline(0, color="#6C7A87", lw=1)
ax[1].set_title("Treatment - control increment (pp), by week")
ax[1].set_xlabel("experiment week"); ax[1].legend(frameon=False)
fig.tight_layout(); fig.savefig(OUT_FIG / "05_novelty.png", dpi=150)
print(f"figure -> {OUT_FIG / '05_novelty.png'}")

# SQL parity
c = con()
sqlwk = c.execute(f"""
  SELECT week,
         SUM(CASE WHEN arm_key='treatment' THEN CAST(redeemed_w AS INT) END)::DOUBLE / {n_arm['treatment']}
       - SUM(CASE WHEN arm_key='control'   THEN CAST(redeemed_w AS INT) END)::DOUBLE / {n_arm['control']}
         AS incr
  FROM fact_experiment_member_week GROUP BY week ORDER BY week
""").df()
for k in (1, 6, 12):
    parity(f"week {k} increment", wk.loc[wk.week == k, "incr_pp"].iloc[0] / 100,
           sqlwk.loc[sqlwk.week == k, "incr"].iloc[0])
print("\n05 novelty: OK")
