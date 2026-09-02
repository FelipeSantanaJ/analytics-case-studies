"""
03 — Primary metric: the Flash Redemption effect on redemption rate.

Decision it informs: should Flash Redemption roll out at all? Audience: loyalty
director / CFO.

Grain: fact_experiment_outcome, one row per subject. Primary metric = redemption
rate (share with >= 1 redemption in the 12-week window).

Method (both tracks):
  1. Two-proportion z-test, effect size (abs pp, relative, Cohen's h), 95% CI
     (Wald + Newcombe score).
  2. Post-stratification: re-weight the per-stratum effects to the population
     active-member tier mix (68/20/9/3) — the pooled estimate is on the
     oversampled design, which under-weights Blue.
  3. Covariate-adjusted estimate: logistic regression of redeemed_in_window on
     arm + frozen pre-period covariates (variance reduction / CUPED-style).
  4. Hypothesis, achieved power and MDE from the realised control rate.
"""
from __future__ import annotations
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import numpy as np, pandas as pd
import statsmodels.formula.api as smf
from utils import (t, con, save_table, parity, banner, two_prop, newcombe_ci,
                   power_two_prop, n_for_power, POP_TIER_MIX, STRATA)

banner("03 — Primary effect: redemption rate")
oc = t("fact_experiment_outcome").copy()
oc["r"] = oc["redeemed_in_window"].astype(int)
ctrl = oc[oc.arm_key == "control"]
trt = oc[oc.arm_key == "treatment"]

# ---- 1. pooled two-proportion test ------------------------------------
res = two_prop(ctrl["r"].sum(), len(ctrl), trt["r"].sum(), len(trt))
nc_lo, nc_hi = newcombe_ci(ctrl["r"].sum(), len(ctrl), trt["r"].sum(), len(trt))
print(f"\nControl   : {res['p1']:.4f}  (n={res['n1']}, {ctrl['r'].sum()} redeemers)")
print(f"Treatment : {res['p2']:.4f}  (n={res['n2']}, {trt['r'].sum()} redeemers)")
print(f"Lift      : {res['diff']*100:+.2f} pp   ({res['rel']*100:+.1f}% relative)")
print(f"95% CI    : [{res['ci_lo']*100:+.2f}, {res['ci_hi']*100:+.2f}] pp (Wald)   "
      f"[{nc_lo*100:+.2f}, {nc_hi*100:+.2f}] pp (Newcombe)")
print(f"z = {res['z']:.3f}   p = {res['p_value']:.3e}   Cohen's h = {res['cohens_h']:.3f}")

# ---- 2. post-stratification to population tier mix -------------------
rows = []
for s in STRATA:
    cs, ts = ctrl[ctrl.stratum == s], trt[trt.stratum == s]
    rr = two_prop(cs["r"].sum(), len(cs), ts["r"].sum(), len(ts))
    rows.append(dict(stratum=s, w_design=len(oc[oc.stratum == s]) / len(oc),
                     w_pop=POP_TIER_MIX[s], control=rr["p1"], treatment=rr["p2"],
                     lift_pp=rr["diff"] * 100, se_pp=rr["se_unpool"] * 100,
                     ci_lo_pp=rr["ci_lo"] * 100, ci_hi_pp=rr["ci_hi"] * 100,
                     n_ctrl=rr["n1"], n_trt=rr["n2"]))
per = pd.DataFrame(rows)
pooled_design = np.average(per["lift_pp"], weights=per["w_design"])
pooled_pop = np.average(per["lift_pp"], weights=per["w_pop"])
# SE of the post-stratified estimate (weights treated as fixed)
se_pop = np.sqrt(np.sum((per["w_pop"] * per["se_pp"]) ** 2))
print("\nPer-stratum effects:")
print(per.round(3).to_string(index=False))
print(f"\nDesign-weighted pooled lift : {pooled_design:+.2f} pp   (matches the raw pooled: {res['diff']*100:+.2f})")
print(f"Population-weighted (post-strat) lift : {pooled_pop:+.2f} pp  ± {1.96*se_pop:.2f}  "
      f"[{pooled_pop-1.96*se_pop:+.2f}, {pooled_pop+1.96*se_pop:+.2f}]")
print("  -> the pooled estimate UNDER-states the population effect because Blue "
      "(largest effect) is under-sampled by the oversampling design.")
save_table(per, "03_per_stratum")

# ---- 3. covariate-adjusted (logistic) --------------------------------
d = oc.copy()
d["treat"] = (d["arm_key"] == "treatment").astype(int)
for cvar in ("pre_earn_12m_pts", "pre_flights_12m", "pre_redemptions_12m",
             "pre_balance_pts", "pre_tenure_months"):
    d[cvar] = t("fact_experiment_assignment").set_index("member_key")[cvar].reindex(d["member_key"]).values
d["prior_redeemer"] = t("fact_experiment_assignment").set_index("member_key")["prior_redeemer_flag"].reindex(d["member_key"]).astype(int).values
m = smf.logit("r ~ treat + C(stratum) + prior_redeemer + pre_balance_pts + pre_flights_12m "
              "+ pre_earn_12m_pts + pre_redemptions_12m + pre_tenure_months", data=d).fit(disp=0)
# average marginal effect of `treat`
d0, d1 = d.copy(), d.copy()
d0["treat"] = 0
d1["treat"] = 1
ame = (m.predict(d1) - m.predict(d0)).mean()
print(f"\nCovariate-adjusted average marginal effect of treatment: {ame*100:+.2f} pp "
      f"(logit coef {m.params['treat']:+.3f}, p={m.pvalues['treat']:.2e})")

# ---- 4. hypothesis / power / MDE -----------------------------------
n_per = len(ctrl)
p1 = res["p1"]
mde_planned = 0.022
pw_planned = power_two_prop(0.11, mde_planned, 3450)
pw_real_mde = power_two_prop(p1, mde_planned, n_per)
detectable_80 = None
for m_abs in np.arange(0.005, 0.05, 0.0005):
    if power_two_prop(p1, m_abs, n_per) >= 0.80:
        detectable_80 = m_abs
        break
print(f"\nHypothesis  H0: rate_treatment = rate_control ; H1: treatment > control (one-sided a=0.05)")
print(f"Planning: control 11.0%, MDE +2.2 pp -> ~{n_for_power(0.11, mde_planned):.0f}/arm for 80% power.")
print(f"Realised: control {p1*100:.1f}%, {n_per}/arm -> power at the +2.2 pp MDE = {pw_real_mde:.3f}; "
      f"80%-detectable effect ~ {detectable_80*100:.2f} pp.")
one_sided = two_prop(ctrl['r'].sum(), len(ctrl), trt['r'].sum(), len(trt), alt='larger')
print(f"One-sided p (treatment > control): {one_sided['p_value']:.3e}")

save_table(pd.DataFrame([dict(
    control_rate=res['p1'], treatment_rate=res['p2'], lift_pp=res['diff']*100,
    rel_pct=res['rel']*100, ci_lo_pp=res['ci_lo']*100, ci_hi_pp=res['ci_hi']*100,
    newcombe_lo_pp=nc_lo*100, newcombe_hi_pp=nc_hi*100, z=res['z'], p_two_sided=res['p_value'],
    p_one_sided=one_sided['p_value'], cohens_h=res['cohens_h'],
    post_strat_lift_pp=pooled_pop, post_strat_ci_lo=pooled_pop-1.96*se_pop,
    post_strat_ci_hi=pooled_pop+1.96*se_pop, covariate_adj_ame_pp=ame*100,
    power_at_mde=pw_real_mde, detectable_80_pp=detectable_80*100)]), "03_primary_summary")

# ---- SQL parity --------------------------------------------------
c = con()
s = c.execute("""
  SELECT SUM(CASE WHEN arm_key='control'   THEN CAST(redeemed_in_window AS INT) END) x1,
         SUM(CASE WHEN arm_key='control'   THEN 1 END) n1,
         SUM(CASE WHEN arm_key='treatment' THEN CAST(redeemed_in_window AS INT) END) x2,
         SUM(CASE WHEN arm_key='treatment' THEN 1 END) n2
  FROM fact_experiment_outcome
""").df().iloc[0]
sql_res = two_prop(s.x1, s.n1, s.x2, s.n2)
parity("primary lift (pp)", res["diff"], sql_res["diff"])
parity("primary z-stat", res["z"], sql_res["z"])
for s_ in STRATA:
    q = c.execute(f"""
      SELECT 100*(AVG(CASE WHEN arm_key='treatment' THEN CAST(redeemed_in_window AS INT) END)
                - AVG(CASE WHEN arm_key='control'   THEN CAST(redeemed_in_window AS INT) END)) lift
      FROM fact_experiment_outcome WHERE stratum='{s_}'
    """).df()["lift"].iloc[0]
    parity(f"{s_} lift (pp)", per.set_index("stratum").loc[s_, "lift_pp"], q)
print("\n03 primary effect: OK")
