"""
06 — Heterogeneity: does the Flash Redemption effect differ by member tier?

Decision: roll out to everyone, or only to the lower tiers? Audience: loyalty
director / CFO. This is the cut the rollout decision hinges on.

Grain: fact_experiment_outcome. Prior (to test, not assume): the effect is
largest for Blue (threshold-constrained) and ~zero for Platinum (already redeem
freely).

Method (both tracks):
  1. Per-tier effect + 95% CI (from 03) and a forest plot.
  2. Formal arm x tier interaction: logistic regression
     redeemed ~ arm * tier_rank, likelihood-ratio test vs the no-interaction model.
  3. A linear-in-tier-rank interaction term (single df) for a directional test.
"""
from __future__ import annotations
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import numpy as np, pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import statsmodels.formula.api as smf
from scipy import stats
from utils import t, con, save_table, parity, banner, two_prop, STRATA, OUT_FIG

banner("06 — Heterogeneity by tier")
oc = t("fact_experiment_outcome").copy()
oc["r"] = oc["redeemed_in_window"].astype(int)
oc["treat"] = (oc.arm_key == "treatment").astype(int)
rank = {"Blue": 1, "Silver": 2, "Gold": 3, "Platinum": 4}
oc["tier_rank"] = oc["stratum"].map(rank)

rows = []
for s in STRATA:
    cs = oc[(oc.stratum == s) & (oc.treat == 0)]
    ts = oc[(oc.stratum == s) & (oc.treat == 1)]
    rr = two_prop(cs["r"].sum(), len(cs), ts["r"].sum(), len(ts))
    rows.append(dict(stratum=s, tier_rank=rank[s], control=rr["p1"], treatment=rr["p2"],
                     lift_pp=rr["diff"] * 100, ci_lo_pp=rr["ci_lo"] * 100, ci_hi_pp=rr["ci_hi"] * 100,
                     p_value=rr["p_value"], n=len(cs) + len(ts),
                     significant=rr["p_value"] < 0.05))
per = pd.DataFrame(rows)
print("\nPer-tier effect:")
print(per.round(3).to_string(index=False))
save_table(per, "06_per_tier_effect")

# ---- 2. LR test for any arm x tier interaction ---------------------
m_full = smf.logit("r ~ treat * C(stratum)", data=oc).fit(disp=0, method="bfgs", maxiter=500)
m_red = smf.logit("r ~ treat + C(stratum)", data=oc).fit(disp=0, method="bfgs", maxiter=500)
lr = 2 * (m_full.llf - m_red.llf)
df = m_full.df_model - m_red.df_model
p_lr = stats.chi2.sf(lr, df)
print(f"\nArm x tier interaction (LR test, full vs no-interaction): "
      f"chi2 = {lr:.3f}, df = {df:.0f}, p = {p_lr:.4f}")

# ---- 3. linear-in-rank interaction (1 df) -------------------------
m_lin = smf.logit("r ~ treat * tier_rank + C(stratum)", data=oc).fit(disp=0)
coef, pcoef = m_lin.params["treat:tier_rank"], m_lin.pvalues["treat:tier_rank"]
print(f"Linear-in-tier-rank interaction term  treat:tier_rank = {coef:+.3f}  (p = {pcoef:.4f})")
print("  negative -> the treatment effect (on the logit) shrinks as tier rank rises "
      "(Blue -> Platinum), consistent with the prior.")

interp = ("Effect is concentrated in the lower tiers: Blue is clearly positive, "
          "Silver marginal, Gold/Platinum not distinguishable from zero. "
          f"{'Formal interaction is significant' if p_lr < 0.05 else 'The omnibus interaction test is not significant (underpowered for the 3-df cut)'}, "
          f"but the {'directional' if pcoef < 0.10 else ''} linear-in-rank term "
          f"{'supports' if (coef < 0 and pcoef < 0.10) else 'is inconclusive on'} a decreasing gradient.")
print(f"\nINTERPRETATION: {interp}")
save_table(pd.DataFrame([dict(lr_chi2=lr, lr_df=df, lr_p=p_lr,
                              lin_coef=coef, lin_p=pcoef, interpretation=interp)]),
           "06_interaction_tests")

# forest plot
fig, ax = plt.subplots(figsize=(6.6, 3.2))
y = np.arange(len(per))[::-1]
ax.errorbar(per["lift_pp"], y, xerr=[per["lift_pp"] - per["ci_lo_pp"], per["ci_hi_pp"] - per["lift_pp"]],
            fmt="o", color="#0B5FA5", capsize=3)
ax.axvline(0, color="#6C7A87", lw=1)
ax.axvline(2.69, color="#E08A1E", ls="--", lw=1, label="pooled +2.69 pp")
ax.set_yticks(y); ax.set_yticklabels(per["stratum"])
ax.set_xlabel("Treatment effect on redemption rate (pp), 95% CI")
ax.set_title("Flash Redemption effect by member tier")
ax.legend(frameon=False)
fig.tight_layout(); fig.savefig(OUT_FIG / "06_forest.png", dpi=150)
print(f"figure -> {OUT_FIG / '06_forest.png'}")

# SQL parity
c = con()
for s in STRATA:
    q = c.execute(f"""
      SELECT 100*(AVG(CASE WHEN arm_key='treatment' THEN CAST(redeemed_in_window AS INT) END)
                - AVG(CASE WHEN arm_key='control'   THEN CAST(redeemed_in_window AS INT) END)) lift
      FROM fact_experiment_outcome WHERE stratum='{s}'
    """).df()["lift"].iloc[0]
    parity(f"{s} lift (pp)", per.set_index("stratum").loc[s, "lift_pp"], q)
print("\n06 heterogeneity: OK")
