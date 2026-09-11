"""
01 — Setup & pre-registration: what was known BEFORE the experiment ran.

Decision it informs: was the original 6-week design reasonable given what the platform's
own pre-experiment history said? Audience: whoever reviews the experiment plan.

Grain: fact_activation, restricted to experiment_cohort = 'not_in_experiment' (the 18
months of platform history before the original run) as the planning baseline; fact_kyc_
decision / fact_fraud_event / fact_activation for the guardrail baselines.

Method (both tracks): the platform's own Day-7 Activation rate, KYC rejection rate,
flagged-fraud rate and onboarding-ticket rate over the pre-experiment window; the
two-proportion sample-size formula solved for n (required) and for MDE at the ~6,750/arm
the original 6-week design expected.
"""
from __future__ import annotations
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import numpy as np, pandas as pd
from utils import t, con, save_table, parity, banner, n_for_power, mde_for_n

banner("01 — Setup & pre-registration")

fa = t("fact_activation")
pre = fa[fa["experiment_cohort"] == "not_in_experiment"].copy()
print(f"Pre-experiment platform history: {len(pre):,} signups (months before the original run)")

# ---- planning baseline: Day-7 Activation --------------------------------
control_rate = pre["day7_activated"].mean()
print(f"\nPlatform Day-7 Activation rate (pre-experiment): {control_rate:.4f}")

# ---- guardrail baselines -----------------------------------------------
kyc_submit_pre = pre["kyc_submitted_flag"].mean()
kyc_reject_pre = pre.loc[pre["kyc_submitted_flag"], "kyc_rejected_flag"].mean()
fraud_pre = pre.loc[pre["day7_activated"] == 1, "fraud_flag_30d"].mean()
tickets_pre = pre["onboarding_tickets_n"].sum() / len(pre) * 1000
print(f"KYC-submit rate: {kyc_submit_pre:.4f}  |  KYC rejection rate (of submissions): {kyc_reject_pre:.4f}")
print(f"Flagged-fraud rate (of Day-7 activators): {fraud_pre:.4f}  |  Tickets / 1k signups: {tickets_pre:.1f}")

baselines = pd.DataFrame([dict(
    n_pre=len(pre), control_day7=control_rate, kyc_submit_rate=kyc_submit_pre,
    kyc_reject_rate=kyc_reject_pre, fraud_rate_30d=fraud_pre, tickets_per_1k=tickets_pre,
)])
save_table(baselines, "01_baselines")

# ---- power / MDE for the ORIGINAL 6-week design -------------------------
# doc 01 A10/A12: ~13,500 users expected over 6 weeks (~6,750/arm)
n_per_arm_planned = 6750
mde_planned = mde_for_n(control_rate, n_per_arm_planned, power=0.80)
n_for_3pp = n_for_power(control_rate, 0.03, power=0.80)
print(f"\nOriginal design: control rate {control_rate:.3f}, ~{n_per_arm_planned:,}/arm expected "
      f"over the planned 6 weeks")
print(f"  -> MDE at 80% power: {mde_planned*100:.2f} pp")
print(f"  -> n/arm required to detect +3.0 pp at 80% power: {n_for_3pp:,.0f}")

setup = pd.DataFrame([dict(
    control_day7_baseline=control_rate, n_per_arm_planned=n_per_arm_planned,
    mde_planned_pp=mde_planned * 100, n_required_for_3pp=n_for_3pp,
)])
save_table(setup, "01_power_plan")

# ---- SQL parity ----------------------------------------------------------
c = con()
sql_rate = c.execute("""
    SELECT AVG(CAST(day7_activated AS DOUBLE)) r, COUNT(*) n
    FROM fa WHERE experiment_cohort = 'not_in_experiment'
""").df().iloc[0]
parity("pre-experiment control Day-7 rate", control_rate, sql_rate["r"])
parity("pre-experiment n", len(pre), sql_rate["n"], tol=0, rel=False)

sql_tickets = c.execute("""
    SELECT SUM(onboarding_tickets_n) * 1000.0 / COUNT(*) t
    FROM fa WHERE experiment_cohort = 'not_in_experiment'
""").df()["t"].iloc[0]
parity("tickets per 1k (pre-experiment)", tickets_pre, sql_tickets)

print("\n01 setup & pre-registration: OK")
