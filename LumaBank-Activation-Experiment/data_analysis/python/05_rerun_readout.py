"""
05 — Re-run readout: power/MDE recomputed, primary effect, guardrails, heterogeneity.

Decision it informs: did the redesigned onboarding work, safely, once the experiment is
clean? Audience: Growth, Product, and Risk & Compliance — this is the number the business
actually acts on.

Grain: fact_activation, filtered to in_analysis_flag = TRUE (the clean re-run population:
rerun cohort, never contaminated, never touched the fallback).

Method (both tracks): recompute power/MDE for the actual re-run sample (NOT the original
6-week planning value); two-proportion test for the primary effect with a 95% CI; one-sided
non-inferiority tests for the two hard guardrails (KYC rejection +1.5pp, fraud +0.5pp) plus
a directional check on the secondary guardrail (tickets); a formal arm x channel
interaction test (logistic regression, likelihood-ratio) for heterogeneity.
"""
from __future__ import annotations
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import numpy as np, pandas as pd
from scipy import stats
import statsmodels.formula.api as smf
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from utils import t, con, save_table, parity, banner, two_prop, ni_test, n_for_power, mde_for_n, CHANNELS, OUT_FIG

banner("05 — Re-run readout (the clean population)")

fa = t("fact_activation")
clean = fa[fa["in_analysis_flag"]].copy()
clean["treat"] = (clean["arm_key"] == "treatment").astype(int)
n = len(clean)
n_per_arm = clean["treat"].value_counts()
print(f"Clean re-run population: n = {n:,}  (control {n_per_arm[0]:,} / treatment {n_per_arm[1]:,})")

# ---- power / MDE recomputed for the ACTUAL re-run sample -----------------
control_rate = clean.loc[clean.treat == 0, "day7_activated"].mean()
mde_rerun = mde_for_n(control_rate, int(n_per_arm.min()), power=0.80)
n_for_3pp = n_for_power(control_rate, 0.03, power=0.80)
mde_original_design = 0.0241  # from block 01, ~6,750/arm planned
print(f"\nRe-run control Day-7 rate: {control_rate:.4f}")
print(f"MDE at the actual re-run sample (80% power): {mde_rerun*100:.2f} pp "
      f"(vs {mde_original_design*100:.2f} pp the original 6-week design was powered for)")
print(f"n/arm that WOULD be needed to match the original design's MDE: "
      f"{n_for_power(control_rate, mde_original_design, power=0.80):,.0f}")
print("-> the deadline cost real precision: an effect between the re-run's MDE and the "
      "original design's MDE would have been reliably detected on the original timeline "
      "and is NOT guaranteed to be detected here.")

power_tbl = pd.DataFrame([dict(n_per_arm=int(n_per_arm.min()), control_rate=control_rate,
                               mde_rerun_pp=mde_rerun * 100, mde_original_design_pp=mde_original_design * 100)])
save_table(power_tbl, "05_power_recompute")

# ---- primary effect -------------------------------------------------
ctrl, treat = clean[clean.treat == 0], clean[clean.treat == 1]
prim = two_prop(ctrl["day7_activated"].sum(), len(ctrl), treat["day7_activated"].sum(), len(treat))
print(f"\nPRIMARY EFFECT (Day-7 Activation):")
print(f"  control   = {prim['p1']:.4f}  (n={prim['n1']:,})")
print(f"  treatment = {prim['p2']:.4f}  (n={prim['n2']:,})")
print(f"  lift      = {prim['diff']*100:+.2f} pp   95% CI [{prim['ci_lo']*100:+.2f}, {prim['ci_hi']*100:+.2f}]")
print(f"  z = {prim['z']:.2f}   p = {prim['p_value']:.2e}")
print(f"  {'SIGNIFICANT' if prim['p_value'] < 0.05 else 'not significant'} at alpha=0.05; "
      f"MDE for this sample was {mde_rerun*100:.2f} pp, observed lift is "
      f"{'above' if prim['diff']*100 > mde_rerun*100 else 'inside'} that threshold")
save_table(pd.DataFrame([prim]), "05_primary_effect")

# ---- guardrails -------------------------------------------------
# KYC rejection: rate of submissions
def kyc_reject_rate_arm(df):
    sub = df[df["kyc_submitted_flag"]]
    return int(sub["kyc_rejected_flag"].sum()), len(sub)

kx_c, kn_c = kyc_reject_rate_arm(ctrl)
kx_t, kn_t = kyc_reject_rate_arm(treat)
kyc_ni = ni_test(kx_c, kn_c, kx_t, kn_t, margin_abs=0.015)
print(f"\nGUARDRAIL 1 -- KYC rejection rate (non-inferiority margin +1.5 pp):")
print(f"  control {kyc_ni['p_control']:.4f}  treatment {kyc_ni['p_treatment']:.4f}  "
      f"delta {kyc_ni['diff']*100:+.2f} pp")
print(f"  one-sided 95% upper bound = {kyc_ni['upper_95']*100:+.2f} pp  "
      f"(margin {kyc_ni['margin']*100:.1f} pp) -> "
      f"{'NON-INFERIORITY ESTABLISHED' if kyc_ni['ni_established'] else 'NOT established'}")

fx_c = int(ctrl.loc[ctrl["day7_activated"] == 1, "fraud_flag_30d"].sum())
fn_c = int((ctrl["day7_activated"] == 1).sum())
fx_t = int(treat.loc[treat["day7_activated"] == 1, "fraud_flag_30d"].sum())
fn_t = int((treat["day7_activated"] == 1).sum())
fraud_ni = ni_test(fx_c, fn_c, fx_t, fn_t, margin_abs=0.005)
print(f"\nGUARDRAIL 2 -- Flagged-fraud rate, 30d (non-inferiority margin +0.5 pp):")
print(f"  control {fraud_ni['p_control']:.4f}  treatment {fraud_ni['p_treatment']:.4f}  "
      f"delta {fraud_ni['diff']*100:+.2f} pp")
print(f"  one-sided 95% upper bound = {fraud_ni['upper_95']*100:+.2f} pp  "
      f"(margin {fraud_ni['margin']*100:.1f} pp) -> "
      f"{'NON-INFERIORITY ESTABLISHED' if fraud_ni['ni_established'] else 'NOT established'}")

tix_c = ctrl["onboarding_tickets_n"].sum() / len(ctrl) * 1000
tix_t = treat["onboarding_tickets_n"].sum() / len(treat) * 1000
print(f"\nGUARDRAIL 3 (secondary, directional) -- Onboarding tickets / 1k signups:")
print(f"  control {tix_c:.1f}  treatment {tix_t:.1f}  delta {tix_t - tix_c:+.1f}")

guardrails = pd.DataFrame([
    dict(guardrail="kyc_rejection_rate", control=kyc_ni["p_control"], treatment=kyc_ni["p_treatment"],
        delta_pp=kyc_ni["diff"] * 100, upper_95_pp=kyc_ni["upper_95"] * 100, margin_pp=1.5,
        ni_established=kyc_ni["ni_established"]),
    dict(guardrail="flagged_fraud_rate", control=fraud_ni["p_control"], treatment=fraud_ni["p_treatment"],
        delta_pp=fraud_ni["diff"] * 100, upper_95_pp=fraud_ni["upper_95"] * 100, margin_pp=0.5,
        ni_established=fraud_ni["ni_established"]),
    dict(guardrail="onboarding_tickets_per_1k", control=tix_c, treatment=tix_t,
        delta_pp=tix_t - tix_c, upper_95_pp=np.nan, margin_pp=np.nan, ni_established=np.nan),
])
print("\nGuardrail summary:")
print(guardrails.round(4).to_string(index=False))
save_table(guardrails, "05_guardrails")

both_ni = kyc_ni["ni_established"] and fraud_ni["ni_established"]
close_call = both_ni and (kyc_ni["margin"] - kyc_ni["upper_95"] < 0.003 or
                          fraud_ni["margin"] - fraud_ni["upper_95"] < 0.001)
print(f"\nBoth hard guardrails {'PASS' if both_ni else 'DO NOT both pass'} non-inferiority.")
if close_call:
    print("  At least one upper bound sits close enough to its margin that this should be "
          "read as a MONITORED pass, not a clean one.")

# ---- heterogeneity by channel -----------------------------------------
dch = t("dim_acquisition_channel")[["channel_key", "channel_name"]]
clean_ch = clean.merge(dch, on="channel_key", how="left")
rows = []
for ch in CHANNELS:
    d = clean_ch[clean_ch["channel_name"] == ch]
    c_, tr_ = d[d.treat == 0], d[d.treat == 1]
    if len(c_) < 5 or len(tr_) < 5:
        continue
    r = two_prop(c_["day7_activated"].sum(), len(c_), tr_["day7_activated"].sum(), len(tr_))
    rows.append(dict(channel=ch, control=r["p1"], treatment=r["p2"], lift_pp=r["diff"] * 100,
                     ci_lo_pp=r["ci_lo"] * 100, ci_hi_pp=r["ci_hi"] * 100, p_value=r["p_value"],
                     n=len(c_) + len(tr_)))
per_ch = pd.DataFrame(rows).sort_values("lift_pp", ascending=False)
print("\nEffect by acquisition channel:")
print(per_ch.round(3).to_string(index=False))
save_table(per_ch, "05_heterogeneity_by_channel")

m_full = smf.logit("day7_activated ~ treat * C(channel_name)", data=clean_ch).fit(disp=0, method="bfgs", maxiter=500)
m_red = smf.logit("day7_activated ~ treat + C(channel_name)", data=clean_ch).fit(disp=0, method="bfgs", maxiter=500)
lr = 2 * (m_full.llf - m_red.llf)
df_lr = m_full.df_model - m_red.df_model
p_lr = stats.chi2.sf(lr, df_lr)
print(f"\nArm x channel interaction (LR test): chi2 = {lr:.2f}, df = {df_lr:.0f}, p = {p_lr:.4f}")
save_table(pd.DataFrame([dict(lr_chi2=lr, lr_df=df_lr, lr_p=p_lr)]), "05_interaction_test")

fig, ax = plt.subplots(figsize=(6.6, 3.2))
y = np.arange(len(per_ch))[::-1]
ax.errorbar(per_ch["lift_pp"], y, xerr=[per_ch["lift_pp"] - per_ch["ci_lo_pp"], per_ch["ci_hi_pp"] - per_ch["lift_pp"]],
           fmt="o", color="#0E4A52", capsize=3)
ax.axvline(0, color="#93A29C", lw=1)
ax.axvline(prim["diff"] * 100, color="#E2624B", ls="--", lw=1, label=f"pooled {prim['diff']*100:+.1f} pp")
ax.set_yticks(y); ax.set_yticklabels(per_ch["channel"])
ax.set_xlabel("Treatment effect on Day-7 Activation (pp), 95% CI")
ax.set_title("Effect by acquisition channel — clean re-run")
ax.legend(frameon=False)
fig.tight_layout()
fig.savefig(OUT_FIG / "05_heterogeneity_forest.png", dpi=150)
print(f"figure -> {OUT_FIG / '05_heterogeneity_forest.png'}")

# ---- SQL parity ------------------------------------------------------
c = con()
sql_rates = c.execute("""
    SELECT arm_key, AVG(CAST(day7_activated AS DOUBLE)) r, COUNT(*) n
    FROM fa WHERE in_analysis_flag GROUP BY 1
""").df().set_index("arm_key")
parity("control rate", prim["p1"], sql_rates.loc["control", "r"])
parity("treatment rate", prim["p2"], sql_rates.loc["treatment", "r"])
parity("control n", prim["n1"], sql_rates.loc["control", "n"], tol=0, rel=False)
parity("treatment n", prim["n2"], sql_rates.loc["treatment", "n"], tol=0, rel=False)

sql_kyc = c.execute("""
    SELECT arm_key, AVG(CAST(kyc_rejected_flag AS DOUBLE)) r
    FROM fa WHERE in_analysis_flag AND kyc_submitted_flag GROUP BY 1
""").df().set_index("arm_key")["r"]
parity("kyc reject control", kyc_ni["p_control"], sql_kyc["control"])
parity("kyc reject treatment", kyc_ni["p_treatment"], sql_kyc["treatment"])

print("\n05 re-run readout: OK")
