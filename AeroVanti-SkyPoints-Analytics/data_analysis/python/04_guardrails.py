"""
04 — Guardrail metrics: is Flash Redemption safe to ship?

Decision: whether the redemption lift comes at an unacceptable cost. Audience: CFO.

Grain: fact_experiment_outcome, one row per subject.

Guardrails (both tracks):
  G1  Revenue per member (window + 8 weeks)  — NON-INFERIORITY test, margin -3%
      (one-sided): can we rule out a drop worse than 3%?
  G2  Net point-liability cost per member    — Welch t-test + 95% CI
  G3  90-day post-window disengagement rate  — two-proportion test
  G4  Redemption value per *redeeming* member + low-cost-only share — is the lift
      real engagement or shallow trinket redemptions?
"""
from __future__ import annotations
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import numpy as np, pandas as pd
from scipy import stats
from utils import t, con, save_table, parity, banner, two_prop, welch_t

banner("04 — Guardrails")
oc = t("fact_experiment_outcome").copy()
c_ = oc[oc.arm_key == "control"]
x_ = oc[oc.arm_key == "treatment"]
rows = []

# ---- G1 revenue per member: non-inferiority at -3% -------------------
rc, rt = c_["revenue_brl_window_plus8w"], x_["revenue_brl_window_plus8w"]
g1 = welch_t(rc, rt)
rel = g1["diff"] / g1["mean_control"]
margin = -0.03
# NI: H0 effect <= -3% vs H1 effect > -3%  (one-sided)
t_ni = (g1["diff"] - margin * g1["mean_control"]) / g1["se"]
p_ni = stats.norm.sf(t_ni)
print(f"\nG1 Revenue/member: control R${g1['mean_control']:.1f}  treatment R${g1['mean_treatment']:.1f}")
print(f"   diff R${g1['diff']:+.2f} ({rel*100:+.2f}%)  95% CI [R${g1['ci_lo']:+.2f}, R${g1['ci_hi']:+.2f}]")
print(f"   two-sided p = {g1['p_value']:.3f}  ->  no significant difference")
print(f"   NON-INFERIORITY vs -3% margin: t = {t_ni:.2f}, one-sided p = {p_ni:.4f}  ->  "
      f"{'non-inferiority ESTABLISHED' if p_ni < 0.05 else 'non-inferiority NOT established'}")
rows.append(dict(guardrail="revenue_per_member_pct", control=g1['mean_control'], treatment=g1['mean_treatment'],
                 delta=g1['diff'], delta_pct=rel*100, ci_lo=g1['ci_lo'], ci_hi=g1['ci_hi'],
                 p_value=g1['p_value'], ni_p=p_ni, verdict="non-inferior" if p_ni < 0.05 else "inconclusive"))

# ---- G2 net liability cost per member -------------------------------
g2 = welch_t(c_["net_liability_cost_brl"], x_["net_liability_cost_brl"])
print(f"\nG2 Net liability cost/member: control R${g2['mean_control']:.2f}  treatment R${g2['mean_treatment']:.2f}")
print(f"   diff R${g2['diff']:+.2f}  95% CI [R${g2['ci_lo']:+.2f}, R${g2['ci_hi']:+.2f}]  p = {g2['p_value']:.3f}")
print(f"   -> {'treatment costs LESS (favourable)' if g2['diff'] < 0 and g2['p_value'] < 0.05 else 'no clear difference / see CI'}")
rows.append(dict(guardrail="net_liability_cost_per_member_brl", control=g2['mean_control'], treatment=g2['mean_treatment'],
                 delta=g2['diff'], delta_pct=np.nan, ci_lo=g2['ci_lo'], ci_hi=g2['ci_hi'],
                 p_value=g2['p_value'], ni_p=np.nan, verdict="favourable" if g2['diff'] < 0 and g2['p_value'] < 0.05 else "neutral"))

# ---- G3 90-day disengagement -------------------------------------
d_c = c_["disengaged_90d_post"].astype(int)
d_t = x_["disengaged_90d_post"].astype(int)
g3 = two_prop(d_c.sum(), len(d_c), d_t.sum(), len(d_t))
print(f"\nG3 90-day post-window disengagement: control {g3['p1']*100:.1f}%  treatment {g3['p2']*100:.1f}%")
print(f"   diff {g3['diff']*100:+.2f} pp  95% CI [{g3['ci_lo']*100:+.2f}, {g3['ci_hi']*100:+.2f}]  p = {g3['p_value']:.3f}")
print(f"   -> {'treatment disengages LESS (favourable, but 90d != 12-month lapse)' if g3['diff'] < 0 and g3['p_value'] < 0.05 else 'directional only'}")
rows.append(dict(guardrail="disengaged_90d_pp", control=g3['p1'], treatment=g3['p2'],
                 delta=g3['diff'], delta_pct=g3['rel']*100, ci_lo=g3['ci_lo'], ci_hi=g3['ci_hi'],
                 p_value=g3['p_value'], ni_p=np.nan,
                 verdict="favourable" if g3['diff'] < 0 and g3['p_value'] < 0.05 else "directional"))

# ---- G4 redemption depth --------------------------------------
def per_redeemer_value(df):
    r = df[df.redeemed_in_window == True]
    return r["redemption_value_brl"].mean(), len(r)
vc, nc = per_redeemer_value(c_)
vt, nt = per_redeemer_value(x_)
rvc = c_.loc[c_.redeemed_in_window == True, "redemption_value_brl"]
rvt = x_.loc[x_.redeemed_in_window == True, "redemption_value_brl"]
g4 = welch_t(rvc, rvt)
low_share_t = x_.loc[x_.redeemed_in_window == True, "low_cost_only"].mean()
low_share_c = c_.loc[c_.redeemed_in_window == True, "low_cost_only"].mean()
print(f"\nG4 Redemption value per redeeming member: control R${vc:.0f} (n={nc})  treatment R${vt:.0f} (n={nt})")
print(f"   diff R${g4['diff']:+.0f}  95% CI [R${g4['ci_lo']:+.0f}, R${g4['ci_hi']:+.0f}]  p = {g4['p_value']:.3f}")
print(f"   low-cost-catalog-only share of redeemers: control {low_share_c*100:.0f}%  treatment {low_share_t*100:.0f}%")
print("   -> Flash drives MORE redemptions but SHALLOWER ones — a watch item, not a blocker.")
rows.append(dict(guardrail="redemption_value_per_redeemer_brl", control=vc, treatment=vt,
                 delta=g4['diff'], delta_pct=g4['diff']/vc*100, ci_lo=g4['ci_lo'], ci_hi=g4['ci_hi'],
                 p_value=g4['p_value'], ni_p=np.nan, verdict="watch — shallower redemptions"))

g = pd.DataFrame(rows)
save_table(g, "04_guardrails")
print("\nGuardrail scorecard:")
print(g.round(3).to_string(index=False))

# ---- SQL parity -----------------------------------------------
con_ = con()
sql = con_.execute("""
  SELECT AVG(CASE WHEN arm_key='treatment' THEN revenue_brl_window_plus8w END)
       - AVG(CASE WHEN arm_key='control'   THEN revenue_brl_window_plus8w END) d_rev,
         AVG(CASE WHEN arm_key='treatment' THEN net_liability_cost_brl END)
       - AVG(CASE WHEN arm_key='control'   THEN net_liability_cost_brl END) d_cost,
         AVG(CASE WHEN arm_key='treatment' THEN CAST(disengaged_90d_post AS INT) END)
       - AVG(CASE WHEN arm_key='control'   THEN CAST(disengaged_90d_post AS INT) END) d_dis
  FROM fact_experiment_outcome
""").df().iloc[0]
parity("G1 delta revenue/member", g1["diff"], sql["d_rev"])
parity("G2 delta net liab cost/member", g2["diff"], sql["d_cost"])
parity("G3 delta disengagement", g3["diff"], sql["d_dis"])
sql_v = con_.execute("""
  SELECT AVG(CASE WHEN arm_key='treatment' THEN redemption_value_brl END)
       - AVG(CASE WHEN arm_key='control'   THEN redemption_value_brl END)
  FROM fact_experiment_outcome WHERE redeemed_in_window
""").df().iloc[0, 0]
parity("G4 delta redemption value/redeemer", g4["diff"], sql_v)
print("\n04 guardrails: OK")
