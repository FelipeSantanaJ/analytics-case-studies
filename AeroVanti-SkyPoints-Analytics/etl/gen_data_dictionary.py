"""
AeroVanti SkyPoints — gen_data_dictionary.py

Introspects data/curated/*.parquet on disk and (re)writes
docs/03_data_dictionary.md: one section per table, column name / dtype /
non-null % / distinct / example, plus row counts and a short hand-written
description per table pulled from TABLE_DOC below.
"""

from __future__ import annotations

from datetime import datetime

import pandas as pd

import config as C

DOCS = C.PROJECT_DIR / "docs"

TABLE_DOC = {
    "dim_date": "Calendar spine, 2024-01-01 to 2027-12-31. Carries the experiment "
                "phase/week tags and BR holiday / season attributes.",
    "dim_member": "One row per SkyPoints member. Enrolment attributes + current "
                  "ledger-derived tier + experiment arm/stratum.",
    "dim_tier": "The four tiers (Blue/Silver/Gold/Platinum) with earn multipliers and thresholds.",
    "dim_earn_source": "SkyPoints issuance sources; -1 = unknown.",
    "dim_reward_type": "Redemption catalogue; is_low_cost_catalog flags the Flash additions; -1 = unknown.",
    "dim_route": "Distinct flown routes with a haul band; -1 = unknown.",
    "dim_experiment_arm": "Slicer helper: control / treatment / not_enrolled.",
    "dim_experiment_stratum": "Slicer helper: the tier strata used for randomisation.",
    "fact_point_transaction": "One SkyPoints ledger entry (earn / redeem / expire / adjust). "
                              "Signed points; points_value_brl in BRL; earn_month_key on earn rows.",
    "fact_member_month": "Member x month panel — the retention / program-health workhorse. "
                         "balance, earn/burn/expiry, tier, activity, and lapse "
                         "(null until the 12-month rule is evaluable).",
    "fact_flight_segment": "One flown segment. member_key -1 = non-member booking, -2 = orphan. "
                           "skypoints_earned recomputed with the month's tier multiplier.",
    "fact_card_spend_month": "Member x month co-brand card spend and card SkyPoints earned.",
    "fact_tier_change": "Tier-change events (the movement source of truth).",
    "fact_liability_month": "Monthly point-liability roll-forward from the transaction ledger, "
                            "with the finance sub-ledger figures alongside for tie-out.",
    "fact_experiment_assignment": "One row per assigned subject (eligible only; late "
                                  "corrections reconciled out). Frozen pre-period covariates.",
    "fact_experiment_member_week": "Assigned subject x experiment week — the weekly redemption "
                                   "series for the novelty diagnostic.",
    "fact_experiment_outcome": "One row per subject with the full window + post-window "
                               "outcomes: primary metric, guardrails, diagnostics.",
    "fact_targets_month": "Plan / target values per month per KPI (doc 01 section 12).",
}


def describe(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    n = len(df)
    for c in df.columns:
        s = df[c]
        ex = s.dropna().iloc[0] if s.notna().any() else ""
        if isinstance(ex, float):
            ex = round(ex, 3)
        rows.append(dict(
            column=c, dtype=str(s.dtype),
            non_null_pct=f"{100 * s.notna().mean():.1f}%",
            distinct=int(s.nunique(dropna=True)),
            example=str(ex)[:40],
        ))
    return pd.DataFrame(rows)


def main():
    files = sorted(C.CURATED_DIR.glob("*.parquet"))
    out = [f"# AeroVanti SkyPoints — Data Dictionary",
           f"\n_Auto-generated from `data/curated/` on {datetime.utcnow():%Y-%m-%d} · "
           f"SEED={C.SEED}. Do not edit by hand — run `python etl/gen_data_dictionary.py`._\n",
           f"{len(files)} curated tables.\n"]
    for f in files:
        name = f.stem
        df = pd.read_parquet(f)
        out.append(f"\n## `{name}`  ·  {len(df):,} rows\n")
        out.append(TABLE_DOC.get(name, "_(no description)_") + "\n")
        d = describe(df)
        out.append("| column | dtype | non-null | distinct | example |")
        out.append("|---|---|---|---|---|")
        for _, r in d.iterrows():
            out.append(f"| `{r.column}` | {r.dtype} | {r.non_null_pct} | {r.distinct:,} | {r.example} |")
    DOCS.mkdir(exist_ok=True)
    (DOCS / "03_data_dictionary.md").write_text("\n".join(out), encoding="utf-8")
    print(f"wrote docs/03_data_dictionary.md ({len(files)} tables)")


if __name__ == "__main__":
    main()
