"""
02 — Randomisation check: sample-ratio mismatch (SRM) + covariate balance.

Decision it informs: whether the experiment's randomisation can be trusted before
we read any effect. Audience: experimentation lead / anyone reviewing the result.

Grain: fact_experiment_assignment = one row per assigned subject (15,000), with
pre-period covariates frozen at 2026-03-01.

Method (both tracks): chi-square goodness-of-fit on arm counts overall and within
each tier stratum (H0: 50/50); standardized mean differences (SMD) on the frozen
covariates, with |SMD| < 0.1 the usual balance threshold; a Love plot.
"""
from __future__ import annotations
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import numpy as np, pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from utils import t, con, save_table, parity, banner, chisq_srm, smd, STRATA, OUT_FIG

banner("02 — SRM + covariate balance")
asg = t("fact_experiment_assignment")
asg["treat"] = (asg["arm_key"] == "treatment").astype(int)

# ---- SRM: overall + per stratum -----------------------------------------
overall = chisq_srm(asg["arm_key"].value_counts().to_dict())
print(f"\nOverall SRM: n={len(asg)}  counts={overall['observed']}  "
      f"chi2={overall['chi2']:.3f}  p={overall['p_value']:.3f}")
srm_rows = [dict(stratum="ALL", n=len(asg), **{k: overall['observed'].get(k, 0) for k in ('control', 'treatment')},
                 chi2=overall['chi2'], p_value=overall['p_value'])]
for s in STRATA:
    d = asg[asg.stratum == s]
    r = chisq_srm(d["arm_key"].value_counts().to_dict())
    srm_rows.append(dict(stratum=s, n=len(d), control=r['observed'].get('control', 0),
                         treatment=r['observed'].get('treatment', 0),
                         chi2=r['chi2'], p_value=r['p_value']))
    print(f"  {s:9s} n={len(d):5d}  {r['observed']}  chi2={r['chi2']:.3f}  p={r['p_value']:.3f}")
srm = pd.DataFrame(srm_rows)
save_table(srm, "02_srm")

# ---- covariate balance -------------------------------------------------
covs = ["pre_earn_12m_pts", "pre_flights_12m", "pre_redemptions_12m",
        "pre_balance_pts", "pre_tenure_months", "prior_redeemer_flag"]
bal_rows = []
for cvar in covs:
    a = asg.loc[asg.treat == 0, cvar].astype(float)
    b = asg.loc[asg.treat == 1, cvar].astype(float)
    bal_rows.append(dict(covariate=cvar, mean_control=a.mean(), mean_treatment=b.mean(),
                         smd=smd(a, b)))
bal = pd.DataFrame(bal_rows)
print("\nCovariate balance (SMD; |SMD|<0.1 = balanced):")
print(bal.round(4).to_string(index=False))
print(f"max |SMD| = {bal['smd'].abs().max():.4f}")
save_table(bal, "02_balance")

# Love plot
fig, ax = plt.subplots(figsize=(6.4, 3.4))
order = bal.reindex(bal["smd"].abs().sort_values().index)
ax.scatter(order["smd"], range(len(order)), color="#0B5FA5", zorder=3)
ax.axvline(0, color="#6C7A87", lw=1)
for x in (-0.1, 0.1):
    ax.axvline(x, color="#C0453B", ls="--", lw=1)
ax.set_yticks(range(len(order)))
ax.set_yticklabels(order["covariate"])
ax.set_xlabel("Standardized mean difference (treatment - control)")
ax.set_title("Covariate balance — Love plot (blocked randomisation)")
ax.set_xlim(-0.15, 0.15)
fig.tight_layout()
fig.savefig(OUT_FIG / "02_love_plot.png", dpi=150)
print(f"figure -> {OUT_FIG / '02_love_plot.png'}")

# ---- SQL parity ------------------------------------------------------
c = con()
sql_counts = c.execute("""
    SELECT arm_key, COUNT(*) n FROM fact_experiment_assignment GROUP BY 1 ORDER BY 1
""").df().set_index("arm_key")["n"]
parity("assignment control count", asg["arm_key"].value_counts()["control"], sql_counts["control"], tol=0, rel=False)
parity("assignment treatment count", asg["arm_key"].value_counts()["treatment"], sql_counts["treatment"], tol=0, rel=False)
sql_bal = c.execute("""
    SELECT AVG(CASE WHEN arm_key='treatment' THEN pre_balance_pts END)
         - AVG(CASE WHEN arm_key='control'   THEN pre_balance_pts END) AS d_balance,
           AVG(CASE WHEN arm_key='treatment' THEN pre_flights_12m END)
         - AVG(CASE WHEN arm_key='control'   THEN pre_flights_12m END) AS d_flights
    FROM fact_experiment_assignment
""").df().iloc[0]
py_d_bal = (asg.loc[asg.treat == 1, "pre_balance_pts"].mean()
            - asg.loc[asg.treat == 0, "pre_balance_pts"].mean())
py_d_fl = (asg.loc[asg.treat == 1, "pre_flights_12m"].mean()
           - asg.loc[asg.treat == 0, "pre_flights_12m"].mean())
parity("delta mean pre_balance", py_d_bal, sql_bal["d_balance"], tol=1e-6, rel=True)
parity("delta mean pre_flights", py_d_fl, sql_bal["d_flights"], tol=1e-6, rel=True)

verdict = ("randomisation OK — no SRM (all p > 0.05) and all |SMD| < 0.1"
           if (srm["p_value"].min() > 0.05 and bal["smd"].abs().max() < 0.1)
           else "randomisation CONCERN — investigate")
print(f"\nVERDICT: {verdict}")
