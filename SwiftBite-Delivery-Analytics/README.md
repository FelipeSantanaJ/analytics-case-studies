# SwiftBite Delivery — Marketplace Liquidity & the Zone-Hour Incentive Experiment

A data / BI portfolio project: diagnose *where and when* a food-delivery marketplace runs
short of couriers, and read out the **zone-hour incentive** experiment
— a supply-side intervention on a two-sided marketplace, randomized by **zone-day**, with a
real risk of cannibalising supply from neighbouring zones.

> Fictional company and synthetic data. Fully reproducible from a single random seed.
> Every deliverable also explains each step in Portuguese.

📄 [Visual case study (PDF)](portfolio/SwiftBite-Delivery-case-study.pdf) — 7-page carousel summary.

## Priority

1. **Data analysis + the zone-hour incentive experiment** (`data_analysis/`) — the primary deliverable.
2. Power BI report (`powerbi/`) — a lighter, 4-page secondary deliverable.

## The question

At Friday/Saturday dinner peak, and in a few structurally supply-short zones, demand
outruns courier supply: ETA climbs, orders cancel for want of a courier, and couriers sit
idle in *other* zones at the same moment. Operations piloted a **dynamic per-delivery bonus**
for a named zone during the peak block, run as a **randomized experiment with the zone-day
as the unit**. Does it lift fulfillment enough to beat the bonus cost? Only in the
supply-short zones, or everywhere? And how much of the local gain is just supply
**pulled from adjacent zones**?

## Scope at a glance

| | |
|---|---|
| Geography | One Brazilian metro (Belo Horizonte), 12 delivery zones, BRL only |
| Window | 20 months, 2025-01-01 → 2026-08-31 |
| Experiment | 10 weeks, 2026-04-06 → 2026-06-14 (window-months 16–18), peak block 18:00–22:00 |
| Unit of randomization | **Zone-day** (zone × hour-block as a secondary cut) |
| Scale | ~3,500 couriers over the window · ~15k orders/day · ~7.5M orders total |
| Primary metric | Fulfillment rate (delivered ÷ placed), zone-day peak block |
| Guardrails | Incentive cost / incremental delivered order · ETA p50/p90 · cancellation rate by cause · courier earnings / active hour · **neighbour-zone spillover** |

## Layout

```
docs/            business context → architecture → data dictionary → model → DAX → DQ → walkthrough
etl/             config + pipeline (raw → staging → curated) + hard dq_checks
data/            raw / staging / curated (CSV + Parquet) / quality
data_analysis/   sql/  python/  findings/  parity/  deliverables/   ← primary deliverable
powerbi/         semantic model as code, theme, build script, 4-page report
assets/          logo + page-background generators
portfolio/       gallery images
```

See [docs/00_scope.md](docs/00_scope.md) for the full locked scope,
[docs/01_business_context_kpis.md](docs/01_business_context_kpis.md) for the KPI framework
and [docs/02_data_architecture.md](docs/02_data_architecture.md) for the build spec.

## Running the pipeline

```bash
python -m pip install -r etl/requirements.txt
# regenerated data layers are big and git-ignored; on Windows/OneDrive point them
# outside the synced tree to avoid file-locks:
export SB_DATA_DIR="$LOCALAPPDATA/Temp/sb_data"      # optional; defaults to ./data
python etl/run_pipeline.py            # raw → staging → curated → dq_checks
python etl/run_pipeline.py --from 02  # rebuild staging + curated + dq only
```

One `SEED` (`etl/config.py`) drives every draw. `data/quality/dq_report.md` is the one
committed data artifact; everything under `data/` else is reproducible from the seed.

## Status

- [x] Phase 0 — Scope & scaffold
- [x] Phase 1 — Business context & KPI framework
- [x] Phase 2 — Data architecture
- [x] Phase 3 — ETL pipeline  (seeded generator → staging → curated star → dq_checks; 13/13 hard checks pass, baseline metrics in band)
- [x] Phase 4 — Data documentation  (03 auto-generated dictionary · 04 ETL · 05 model · 08 data quality)
- [x] Phase 5 — Visual identity  (forest green + tangerine + stone; `assets/brand.py`, logo/backgrounds, `theme.json`, docs/07)
- [x] Phase 6 — Semantic model as code  (`powerbi/gen_semantic_model.py` → TMDL: 15 tables + _Measures, 28 relationships)
- [x] Phase 7 — DAX measures  (`etl/pbi_measures.py` → 71 measures in 6 folders; `docs/06` auto-generated)
- [x] Phase 8 — Report build  (`powerbi/gen_report_visuals.py` + `_drive_pbir.py` → 4-page PBIR, 56 visuals, `pbir validate --all` passes)
- [x] Phase 9 — Build log  (`docs/walkthrough.md`)
- [x] Phase 10 — Data analysis  ← PRIMARY  (`data_analysis/` dual-track; 8 analyses, parity all pass; board summary + deep dive)
- [x] Phase 11 — Portfolio assets  (`portfolio/` — 5 gallery images)
- [x] Phase 12 — Docs bundle  (`docs/SwiftBite-Delivery-Documentation.pdf` 2.5 MB · `-Summary.pdf` 0.9 MB)

## Result

The zone-hour incentive **improves marketplace liquidity** — fulfillment **+1.87 pp**
(cluster CI [+1.27, +2.46]; randomization-inference p = 3×10⁻⁴; wild-cluster bootstrap
agrees), ETA p90 **−6 min**, no-courier cancels **−0.36 pp**, concentrated in the
supply-short and balanced zones (interaction p = 0.004), with only a small (~17%, not
significant) neighbour-zone drag — **but it does not pay for itself**: ~R$ 281 per
incremental delivered order vs a ~R$ 10 contribution margin, because a flat per-delivery
bonus subsidises every delivery while only ~2% are incremental. **Don't ship the flat
bonus; restructure it to reward incremental supply and cap it to the short + balanced
zones.** See `data_analysis/deliverables/`.

*Complete. Final polish left: Power BI Desktop spacing pass on the report, and syncing
the built PDFs to Drive.*
