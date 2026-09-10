"""
SwiftBite Delivery — gen_data_dictionary.py

Introspects data/curated/*.parquet on disk and (re)writes
docs/03_data_dictionary.md: one section per table — column / dtype / non-null % /
distinct / example — plus row counts and a short hand-written description.

    python etl/gen_data_dictionary.py
"""
from __future__ import annotations

from datetime import datetime, timezone

import pandas as pd

import config as C

DOCS = C.PROJECT_DIR / "docs"

TABLE_DOC = {
    "dim_date": "Calendar spine (2024-06 → 2027-06). Carries experiment_phase / "
                "experiment_week, BR holidays, rainy-season flag.",
    "dim_time_block": "One row per hour of day (0–23) with daypart and is_peak_block "
                      "(18:00–21:59, the experiment's block).",
    "dim_zone": "The 12 delivery zones. baseline_supply_stress_tier (short/balanced/long) "
                "is derived from months 1–15 liquidity; is_boundary_redrawn flags the two "
                "zones re-cut at window-month 9.",
    "dim_zone_adjacency": "Undirected zone adjacency as a bridge table — the basis for the "
                          "neighbour-zone cannibalisation analysis.",
    "dim_courier": "One row per courier. Signup cohort, vehicle, acquisition channel, "
                   "modal home zone. courier_key -1 = no courier assigned, -2 = orphan.",
    "dim_customer": "One row per ordering customer, with a coarse activity segment.",
    "dim_restaurant": "One row per restaurant, its zone, cuisine and price band.",
    "dim_incentive_campaign": "One row per peak-eligible zone-day in the 10-week experiment "
                              "window: arm, bonus, stratum (zone × stress tier), day-of-week.",
    "fact_order": "One row per placed order. Dual zone resolution "
                  "(dropoff_zone_key_asbooked vs _current); outcome, ETA, assignment "
                  "latency; experiment flags (on_treated_zone_day, "
                  "is_adjacent_to_treated_zone_day). courier_key filled for delivered orders.",
    "fact_delivery": "One row per delivered order: courier, trip, payout split "
                     "(base / tip / incentive bonus / total).",
    "fact_courier_shift_block": "Courier × zone × date × hour: logged-in / active / idle / "
                                "cooldown minutes, deliveries, earnings. The supply side of "
                                "liquidity.",
    "fact_zone_hour": "Zone × date × hour — the liquidity spine. Orders placed/delivered/"
                      "cancelled by cause, fulfillment_rate, ETA p50/p90, "
                      "available vs demanded courier-hours, liquidity_ratio, "
                      "idle_courier_ratio, unmet_demand, rain / event flags, experiment_arm.",
    "fact_incentive_assignment": "One row per experiment zone-day (~840). Arm, bonus, "
                                 "stratum, adjacency-to-treated flags, and pre-period "
                                 "(months 1–15) covariates frozen for the balance checks.",
    "fact_experiment_zone_day": "One tidy row per unit of randomization (~840): "
                                "fulfillment_rate (primary), ETA p50/p90, cancel & "
                                "no-courier rate, courier earnings/active-hr, incentive "
                                "spend and cost per delivered order, adjacency-to-treated.",
    "fact_experiment_zone_block_week": "Zone × experiment week × peak hour-block — the "
                                       "weekly series for the novelty / decay diagnostic.",
}


def describe(df: pd.DataFrame) -> list[dict]:
    rows = []
    for c in df.columns:
        s = df[c]
        ex = s.dropna().iloc[0] if s.notna().any() else ""
        if isinstance(ex, float):
            ex = round(ex, 3)
        rows.append(dict(column=c, dtype=str(s.dtype),
                         non_null=f"{100 * s.notna().mean():.1f}%",
                         distinct=f"{s.nunique(dropna=True):,}",
                         example=str(ex)[:44]))
    return rows


def main():
    files = sorted(C.CURATED_DIR.glob("*.parquet"))
    if not files:
        raise SystemExit(f"no curated parquet in {C.CURATED_DIR} — run the pipeline first")
    out = ["# SwiftBite Delivery — Data Dictionary", "",
           f"_Auto-generated from `data/curated/` on {datetime.now(timezone.utc):%Y-%m-%d} · "
           f"SEED={C.SEED}. Do not edit by hand — run `python etl/gen_data_dictionary.py`._", "",
           f"{len(files)} curated tables.", ""]
    for f in files:
        name = f.stem
        df = pd.read_parquet(f)
        out += [f"## `{name}`  ·  {len(df):,} rows", "",
                TABLE_DOC.get(name, "_(no description)_"), "",
                "| column | dtype | non-null | distinct | example |",
                "|---|---|---|---|---|"]
        for r in describe(df):
            out.append(f"| `{r['column']}` | {r['dtype']} | {r['non_null']} | {r['distinct']} | {r['example']} |")
        out.append("")
    DOCS.mkdir(exist_ok=True)
    (DOCS / "03_data_dictionary.md").write_text("\n".join(out), encoding="utf-8")
    print(f"wrote docs/03_data_dictionary.md ({len(files)} tables)")


if __name__ == "__main__":
    main()
