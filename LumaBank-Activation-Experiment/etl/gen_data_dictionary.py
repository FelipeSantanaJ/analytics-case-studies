"""
LumaBank — gen_data_dictionary.py

Introspects data/curated/*.parquet on disk and (re)writes
docs/03_data_dictionary.md: one section per table with column name / dtype /
non-null % / distinct / example, row counts, and a short description.
"""

from __future__ import annotations

from datetime import datetime

import pandas as pd

import config as C

DOCS = C.PROJECT_DIR / "docs"

TABLE_DOC = {
    "dim_date": "Calendar spine, 2024-06-01 to 2027-12-31. Carries experiment_phase "
                "(pre / original / washout / rerun / post), experiment_day, is_post_deploy, "
                "and BR holiday / season attributes.",
    "dim_user": "One row per signup. Acquisition channel, region, device, app version at "
                "signup, and the derived experiment fields: effective arm, cohort "
                "(pre_deploy / post_deploy / rerun), contaminated_flag, in_analysis_flag.",
    "dim_acquisition_channel": "paid_social / organic / app_store_search / referral / influencer / unknown.",
    "dim_region": "27 UFs + macro region + timezone + utc_offset + is_amazon_tz; -1 = unknown. "
                  "The axis the post-deploy fallback bias correlates with.",
    "dim_app_release": "Mobile + backend releases. is_cache_reset_release flags the 2026-07-16 "
                       "release; a 2026-07-22 hotfix row follows; -1 = unknown.",
    "dim_kyc_outcome": "Distinct (outcome, reason_code, reason_group); is_rejection; -1 = none.",
    "dim_onboarding_step": "The six funnel steps in order.",
    "dim_experiment_arm": "Slicer helper: control / treatment / ambiguous.",
    "fact_variant_assignment": "One row per assignment EVENT (contaminated users have >=2). "
                               "assignment_source (primary / fallback), cache_reset_flag, "
                               "is_first_assignment, is_effective_assignment (the auditable rule).",
    "fact_onboarding_step": "One row per user x step (first occurrence) with seconds_since_signup.",
    "fact_kyc_decision": "One row per user's final KYC decision, joined to the submission "
                         "(doc_type, submitted_after_account = the treatment-flow signature).",
    "fact_activation": "ONE ROW PER SIGNUP, platform-wide (is_experiment_subject flags "
                       "the randomized ones). Effective arm, cohort, Day-1/7/30 "
                       "activation, TTFT, and the guardrail flags (kyc_rejected, "
                       "fraud_flag_30d, onboarding_tickets_n) pre-computed. "
                       "in_analysis_flag = the clean re-run population.",
    "fact_transaction_day": "User x local day: transaction count, BRL, per-type counts, is_first_txn_day.",
    "fact_fraud_event": "One row per fraud signal (flagged_ts in BRT), days_since_activation.",
    "fact_support_ticket": "One row per ticket; is_onboarding drives the support-cost guardrail.",
    "fact_srm_daily": "ONE ROW PER EXPERIMENT x CALENDAR DAY — the integrity-monitor surface. "
                      "Daily arm counts, cumulative + trailing-7d chi-square SRM p-values, "
                      "snapshot-vs-log mismatch count, alert_state. The 2026-07-16 break is here.",
    "fact_targets_month": "Plan / target values per month per KPI (doc 01 section 15).",
}


def describe(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for c in df.columns:
        s = df[c]
        ex = s.dropna().iloc[0] if s.notna().any() else ""
        if isinstance(ex, float):
            ex = round(ex, 3)
        rows.append(dict(column=c, dtype=str(s.dtype),
                         non_null_pct=f"{100 * s.notna().mean():.1f}%",
                         distinct=int(s.nunique(dropna=True)), example=str(ex)[:44]))
    return pd.DataFrame(rows)


def main():
    files = sorted(C.CURATED_DIR.glob("*.parquet"))
    o = ["# LumaBank — Data Dictionary",
         f"\n_Auto-generated from `data/curated/` on {datetime.utcnow():%Y-%m-%d} · "
         f"SEED={C.SEED}. Do not edit by hand — run `python etl/gen_data_dictionary.py`._\n",
         f"{len(files)} curated tables.\n"]
    for f in files:
        name = f.stem
        df = pd.read_parquet(f)
        o.append(f"\n## `{name}`  ·  {len(df):,} rows\n")
        o.append(TABLE_DOC.get(name, "_(no description)_") + "\n")
        d = describe(df)
        o.append("| column | dtype | non-null | distinct | example |")
        o.append("|---|---|---|---|---|")
        for _, r in d.iterrows():
            o.append(f"| `{r.column}` | {r.dtype} | {r.non_null_pct} | {r.distinct:,} | {r.example} |")
    DOCS.mkdir(exist_ok=True)
    (DOCS / "03_data_dictionary.md").write_text("\n".join(o), encoding="utf-8")
    print(f"wrote docs/03_data_dictionary.md ({len(files)} tables)")


if __name__ == "__main__":
    main()
