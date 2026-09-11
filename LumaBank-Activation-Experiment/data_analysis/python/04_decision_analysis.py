"""
04 — Decision analysis: truncate, exclude-contaminated, or restart?

Decision it informs: which of the three fixes to a broken experiment to take, under
business deadline pressure. Audience: Growth + Experimentation leadership — the
call that has to be defended afterwards.

Grain: fact_activation (experiment_cohort, contaminated_flag, assignment_switch_flag),
fact_variant_assignment (assignment_source) for how much each option actually keeps and
how biased what's kept still is.

Method (both tracks): for each option, count the usable sample, the achievable MDE at
that sample (via the two-proportion formula, control rate from block 01), and a residual-
bias check (regional composition of what's kept vs what's dropped, for option 2).
"""
from __future__ import annotations
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import numpy as np, pandas as pd
from scipy import stats
from utils import t, con, save_table, parity, banner, mde_for_n

banner("04 — Decision analysis: three options")

fa = t("fact_activation")
control_rate = fa.loc[fa["experiment_cohort"] == "not_in_experiment", "day7_activated"].mean()
exp1 = fa[fa["experiment_cohort"].isin(["pre_deploy", "post_deploy"])].copy()

fva = t("fact_variant_assignment")
du = t("dim_user")[["user_key", "region_key"]]
dreg = t("dim_region")[["region_key", "macro_region"]]
first = fva[fva["is_first_assignment"]].merge(du, on="user_key", how="left").merge(dreg, on="region_key", how="left")
fa_reg = fa.merge(dreg, on="region_key", how="left")   # fact_activation already carries region_key

# ---- Option 1: TRUNCATE (use only pre-deploy signups) --------------------
trunc = exp1[exp1["experiment_cohort"] == "pre_deploy"]
n_trunc = len(trunc)
n_trunc_arm = n_trunc // 2
mde_trunc = mde_for_n(control_rate, n_trunc_arm, power=0.80)
# real-time nuance: at the moment of the decision (deploy + investigation, ~day 13-15),
# users assigned in the final 2-3 pre-deploy days would not yet have a CLOSED Day-7
# window -- a live analysis would have to drop them too.
trunc_closed = trunc[pd.to_datetime(trunc["assigned_ts"]) <= pd.Timestamp("2026-07-13")]
n_trunc_realtime = len(trunc_closed)
mde_trunc_rt = mde_for_n(control_rate, n_trunc_realtime // 2, power=0.80)
print(f"OPTION 1 -- Truncate (pre-deploy signups only)")
print(f"  retrospective n = {n_trunc:,} ({n_trunc_arm:,}/arm) -> MDE {mde_trunc*100:.2f} pp")
print(f"  in real time (day-7 windows actually closed by the decision point) n = "
      f"{n_trunc_realtime:,} ({n_trunc_realtime//2:,}/arm) -> MDE {mde_trunc_rt*100:.2f} pp")
print(f"  bias: {int(trunc['contaminated_flag'].sum())} of {n_trunc} ({trunc['contaminated_flag'].mean():.1%}) "
      f"are still contaminated (their Day-7 window reaches into the post-deploy period)")

# ---- Option 2: EXCLUDE CONTAMINATED / BIASED -----------------------------
# narrow reading: drop only users who literally switched arms
narrow_keep = exp1[~exp1["assignment_switch_flag"]]
# broad / auditable reading: drop the full contaminated_flag rule AND post-deploy
# fallback-sourced users (they are not "contaminated" by the pre-deploy definition, but
# they ARE biased -- doc 00 section 4.4 explicitly calls this out as needing separate handling)
fallback_users = set(first.loc[first["assignment_source"] == "fallback", "user_key"])
broad_keep = exp1[(~exp1["contaminated_flag"]) & (~exp1["user_key"].isin(fallback_users))]
print(f"\nOPTION 2 -- Exclude contaminated / biased")
print(f"  narrow (drop arm-switchers only): keep {len(narrow_keep):,} of {len(exp1):,}")
print(f"  broad / auditable (drop contaminated_flag + fallback-sourced): "
      f"keep {len(broad_keep):,} of {len(exp1):,} ({len(broad_keep)//2:,}/arm)")
mde_broad = mde_for_n(control_rate, len(broad_keep) // 2, power=0.80)
print(f"  MDE at the broad-keep sample: {mde_broad*100:.2f} pp")

# residual bias: does the REGION mix of what's kept still differ from what's excluded?
excluded = exp1[~exp1["user_key"].isin(broad_keep["user_key"])]
kept_reg = fa_reg[fa_reg["user_key"].isin(broad_keep["user_key"])]["macro_region"].value_counts(normalize=True)
excl_reg = fa_reg[fa_reg["user_key"].isin(excluded["user_key"])]["macro_region"].value_counts(normalize=True)
resid = pd.DataFrame({"kept_share": kept_reg, "excluded_share": excl_reg}).fillna(0)
resid["abs_diff_pp"] = (resid["kept_share"] - resid["excluded_share"]).abs() * 100
print("\n  residual composition check (region mix, kept vs excluded):")
print(resid.round(3).to_string())
print(f"  max |diff| = {resid['abs_diff_pp'].max():.1f} pp -- residual imbalance is small but "
      f"not provably zero (unobserved contamination cannot be ruled out)")
save_table(resid.reset_index().rename(columns={"index": "macro_region"}), "04_option2_residual_bias")

# ---- Option 3: RESTART (reference -- quantified fully in block 05) ------
print(f"\nOPTION 3 -- Restart clean")
print(f"  bug fixed, fresh randomisation, re-run in a 4-week window (vs the original 6) "
      f"-- see block 05 for the recomputed power/MDE and the full read-out.")

# ---- summary table --------------------------------------------------
summary = pd.DataFrame([
    dict(option="1. Truncate", n_per_arm=n_trunc_arm, mde_pp=mde_trunc * 100,
         bias="low in principle, but the last ~2-3 days are still contaminated by the "
              "reset window; unusable at the actual decision point without further cuts",
         timeline="immediate"),
    dict(option="2. Exclude contaminated", n_per_arm=len(broad_keep) // 2, mde_pp=mde_broad * 100,
         bias="residual -- cannot prove every contaminated user was caught; "
              f"observed residual region-mix gap {resid['abs_diff_pp'].max():.1f} pp",
         timeline="a few days (no new data collection)"),
    dict(option="3. Restart", n_per_arm=None, mde_pp=None,
         bias="none -- clean randomisation, fixed bug",
         timeline="worst -- but capped at 4 weeks by the business, not another 6"),
])
print("\nDecision summary:")
print(summary.to_string(index=False))
save_table(summary, "04_decision_summary")

print(f"\nCHOSEN: Option 3 (restart), 4-week window, power/MDE recomputed from scratch "
      f"-- see block 05. Rationale: options 1 and 2 both trade an unresolved, unquantifiable "
      f"bias for speed; a fintech activation guardrail decision (KYC rejection, fraud) is not "
      f"a reasonable place to accept unquantified bias in either direction.")

# ---- SQL parity ------------------------------------------------------
c = con()
sql_n_trunc = c.execute("""
    SELECT COUNT(*) n FROM fa WHERE experiment_cohort = 'pre_deploy'
""").df()["n"].iloc[0]
parity("truncate n", n_trunc, sql_n_trunc, tol=0, rel=False)

sql_broad_keep = c.execute("""
    SELECT COUNT(*) n FROM fa
    WHERE experiment_cohort IN ('pre_deploy','post_deploy') AND NOT contaminated_flag
      AND user_key NOT IN (
        SELECT DISTINCT user_key FROM fva WHERE assignment_source = 'fallback'
      )
""").df()["n"].iloc[0]
parity("option 2 broad-keep n", len(broad_keep), sql_broad_keep, tol=0, rel=False)

print("\n04 decision analysis: OK")
