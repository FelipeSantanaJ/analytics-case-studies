# SwiftBite Delivery — build walkthrough

A log of how this project was built, phase by phase — decisions, dead ends, and
calibration passes.

---

## Phase 0 — scope & scaffold

Locked the brief: one Brazilian metro (Belo Horizonte), **12 zones** with an adjacency
graph, BRL only, **20-month** window (2025-01 → 2026-08), a **10-week** zone-hour incentive
experiment in months 16–18, **randomization unit = zone-day**. Chose a supply-side
intervention on a two-sided marketplace specifically because it is a rarer, higher-value
problem shape than another conversion A/B test, and because it carries a real
**neighbour-zone cannibalisation** risk (spatial confounding).

Folder scaffold mirrors the other three portfolio projects (`docs/00–09`, `etl/`,
`powerbi/`, `data_analysis/`, `portfolio/`).

## Phase 1 — business context & KPIs

`docs/01_business_context_kpis.md`: the two marketplace sides kept strictly separate
(supply = available courier-hours, demand = demanded delivery-hours; liquidity = their
ratio per zone × hour). Primary metric = **fulfillment rate**; five guardrails including
**G1 incentive cost per incremental delivered order** (the go/no-go economics) and **G5
neighbour-zone spillover**. Power/MDE worked for the **zone-day** unit (~420/arm, ICC
≈ 0.15, design effect ≈ 1.9 → pooled MDE ≈ +1.3 pp, short-tier ≈ +2.2 pp), with
cluster-robust SEs + randomization inference as the small-cluster cross-checks.

## Phase 2 — data architecture

`docs/02_data_architecture.md`: medallion, one `SEED`. Six simulated systems (OrderCore,
RiderApp, Trace GPS, Dispatch telemetry, PayHub, Boost) + a static GeoRef. Curated star:
`dim_zone` (+ `dim_zone_adjacency` bridge), `dim_time_block`, `fact_zone_hour` as the
liquidity spine, `fact_incentive_assignment` + `fact_experiment_zone_day` at the zone-day
grain. Eight data-quality classes (Q01–Q08) with hard checks. The true effect and the
cannibalisation term stay only in `etl/config.py`.

## Phase 3 — ETL pipeline

`etl/` — `config.py`, `utils.py`, `01_generate_raw.py`, `02_clean_stage.py`,
`03_build_curated.py`, `dq_checks.py`, `run_pipeline.py`, `vocab/`.

**`01` is a marketplace simulator**, vectorised at the zone-hour grain: per zone × day ×
hour it draws demand (Poisson around a shape with day-of-week, month, rainy-season,
per-day rain and local-event multipliers), allocates courier supply by a demand-share ×
attractiveness tilt (so central zones run long and peripheral zones run short), computes
the **liquidity ratio**, and clears the market through smooth `fulfillment / ETA /
cancellation` curves in `L`. On a treated peak zone-day it multiplies effective supply by
a tier-dependent response (short 1.34× / balanced 1.15× / long 1.04×) with a week-1
novelty bump that decays, and **pulls a 28% share of that added supply out of adjacent
control zones** (cannibalisation). It then emits messy source exports (mixed datetime
formats, epoch-ms GPS, UTC-vs-local feeds, money-as-text, retry duplicates, orphan courier
ids, the zone boundary redraw, mojibake).

**`02`** parses/types/dedups each raw entity → `stg_*`, reduces the 7-day GPS ping
reference to courier-minute state, reconciles the assignment funnel to one outcome per
order, and reconciles the Boost post-midnight campaign edits to the 00:00 assignment.
**`03`** builds the Kimball star: resolves each order's zone two ways (as-booked label vs
current, recovered from the address centroid), puts supply and demand in courier-hours,
builds `fact_zone_hour`, derives the baseline supply-stress tier from months 1–15
liquidity, and pre-computes the zone-day experiment tables.

### Calibration passes (Phase 3)

1. **Supply allocation.** First cut put 10/12 zones "short" with liquidity from 0.27 to
   3.7 — the softmax zone-choice model concentrated supply into 2–3 zones. Fix: allocate
   supply proportional to *courier-hour* demand share (not order share — service time
   differs by zone) times a small attractiveness tilt `exp(0.20·z)`. Landed at
   6 short / 2 balanced / 4 long, baseline liquidity 0.77–1.20.
2. **OneDrive file-locks.** The project lives in a synced folder; `rm -rf data/` + rewrite
   fought OneDrive and the atomic-write retries stalled the run. Fix: `SB_DATA_DIR` env
   var points the regenerated layers outside the synced tree; `_atomic_write` falls back
   to an in-place write after retries.
3. **Runtime.** First `01` took 3.5 min (per-order Python loop). Vectorised order-attribute
   generation per zone-hour → ~70 s. `02` datetime parsing with `format="mixed"` was
   ~3.5 min → split ISO/BR fast paths → ~35 s. `03` courier→delivery assignment per-row
   loop → per-group `choice` call. Full pipeline now ~6.5 min (`03` ~4.5 min).
4. **Marketplace bands.** Raised metro supply ratio 1.05 → 1.12 and softened the
   `fulfillment(L)` / cancellation-split curves (no-courier is a minority of failures, not
   the majority). Baseline now: fulfillment 0.956, ETA p50 38 / p90 46 min, cancel 4.4 %,
   no-courier 1.4 %, idle 29 %, courier earnings R$33/active-hr — all mid-band.

**Result:** `dq_checks` — **13/13 hard checks pass, 0 soft warnings.** Naive experiment
read (not the Phase-10 analysis): fulfillment control 0.957 → treatment 0.975 (**+1.7 pp**),
ETA p90 47 → 41 min, no-courier 1.2 % → 0.8 %; heterogeneity short (+2.3 pp) > balanced
(+1.9) > long (+0.7).

**Decision taken:** keep the calibration and let Phase 10 carry **ETA p90 and no-courier
rate as co-primary evidence** alongside fulfillment (option B) — a maturity-realistic
framing (a #2 player already fulfils ~96 %; the customer-felt pain is ETA and cancels).

## Phase 4 — data documentation

- `etl/gen_data_dictionary.py` introspects `data/curated/*.parquet` → `docs/03_data_dictionary.md`
  (15 tables, column / dtype / non-null % / distinct / example, + a hand-written blurb each).
- `docs/04_etl_pipeline.md` — what each script guarantees and how to run it.
- `docs/05_data_model.md` — bus matrix, grain & measures per fact, dimension attributes,
  the full relationship table (three zone roles on `fact_order`; only dropoff-current
  active), an ER diagram, and the Phase-7 measure-group preview.
- `docs/08_data_quality.md` — the eight injected classes Q01–Q08, the hard operational
  identities, the benchmark bands, and the current status.

Two DQ gaps found and fixed during this phase:
1. **Q08 was a no-op** — the generated address / restaurant text was pure ASCII, so
   `mojibake()` had nothing to corrupt. Gave the generator accented BH street / bairro
   names ("Funcionários", "São Pedro", "Rua Antônio de Albuquerque", …); now
   `mojibake_repaired` = ~69k address fields + 46 restaurants.
2. **Inflated zone drift** — recovering `dropoff_zone_key_current` by nearest-centroid on
   jittered address points mislabelled ~13 % of orders. Fixed: `_current` = the as-booked
   label everywhere **except** the two redrawn zones on pre-redraw dates (the only place
   the label is legitimately stale). Drift dropped 47k → 4.4k (~1.2 %, the redraw pair
   only), and orphan-courier deliveries went to 0 with a zone-day courier fallback.

Pipeline after the fixes: **13/13 hard pass · 0 soft warnings**, ~8 min end-to-end
(`03` ~6.5 min — the slow step; `run_pipeline.py --from 03` reuses raw + staging).

## Phase 5 — visual identity

Palette chosen from three options: **forest green `#1E6B4F` + tangerine `#E8823C` accent
+ cool stone `#8090A0` comparison**, warm-neutral ground `#F2F4F1`. Deliberately clear of
the siblings (AeroVanti sky-blue/navy, VoltEdge navy, Voxa+ violet). Supply-short zones
and the treated arm both map to tangerine ("hot"); healthy / long zones and the control
arm map to green / stone.

- `assets/brand.py` — the single source of truth (palette, tier & arm ramps, type,
  layout constants, the 4 page titles + questions).
- `assets/gen_logo.py` → `powerbi/assets/` — mark (two forward speed chevrons + a
  trailing tangerine dot), "SwiftBite" wordmark, four full-page backgrounds carrying the
  green header band + tangerine hairline + title, `_page_heights.json`.
- `powerbi/theme/theme.json` — data-colour ramp, semantic + diverging colours, 4 text
  classes, a `visualStyles` baseline (white card, 8 px `#D6DAD3` border, no shadow, page
  ground). Per-visual-type overrides come in Phase 6/8 via the `pbir` CLI.
- `docs/07_visual_identity.md`.

## Phase 6 — semantic model as code (TMDL)

`powerbi/gen_semantic_model.py` reads the curated Parquet schemas and writes
`powerbi/SwiftBiteDelivery.SemanticModel/**` as TMDL: **15 tables** (import partitions via
a `pDataFolder` parameter, committed with a `C:/PATH/TO/REPO/...` placeholder) + an empty
`_Measures` table that Phase 7 fills.

- All facts are day/hour grain, so every fact joins **`dim_date[date_key]`** (unique — no
  `dim_month` helper needed, unlike AeroVanti) and, where relevant,
  `dim_time_block[time_block_key]`.
- **`fact_order` role-plays `dim_zone` three ways**: dropoff-current (active), dropoff-as-booked
  and pickup (both inactive, for `USERELATIONSHIP` measures).
- `dim_zone_adjacency` is a bridge (`dim_zone[zone_key] 1:* dim_zone_adjacency[zone_key]`);
  `neighbour_zone_key` is measure-driven, not a physical relationship.
- Sentinel courier rows `-1` (no courier) / `-2` (orphan) added to `dim_courier` so every
  `fact_order` / `fact_delivery` FK resolves.
- `summarizeBy` set from the column name: `sum` for additive counts / amounts / hours,
  `none` for keys, rates, ratios, `*_p50/p90`, `per_active_hour`, `pre_*` covariates.
- **28 relationships** (2 inactive). `fact_delivery` gained `date_key` / `time_block_key`
  in `03` so it joins the calendar directly rather than through `fact_order`.

Full `pbir` validation runs in Phase 8 alongside the report.

## Phase 7 — DAX measure library

`etl/pbi_measures.py` holds **63 measures** in 6 display folders; `powerbi/gen_semantic_model.py`
injects them into `_Measures.tmdl` and `etl/gen_dax_doc.py` renders `docs/06_dax_measures.md`
from the same list.

- **01 Marketplace Health** — orders, fulfillment rate, cancellation & no-courier rate,
  order-weighted ETA p50 / p90, assignment latency, peak-only variants.
- **02 Liquidity** — available vs demanded courier-hours, liquidity ratio, idle-courier
  ratio, unmet demand, supply-short peak zone-hours %, deliveries/active-hour.
- **03 Courier Economics** — earnings, active hours, utilisation, payout/delivery,
  incentive spend, and **contribution margin per delivered order** (take − payout − support).
- **04 Experiment** — treated/control fulfillment, **lift (pp) + two-sample normal CI**,
  ETA p90 lift, no-courier lift, incremental delivered orders, **G1 incentive cost per
  incremental order + verdict vs contribution margin**, per-tier lift (short/balanced/long)
  + short−long contrast, **cannibalisation: adjacent-control gap + cannibalisation-adjusted
  net lift**, pre-period balance gap, settled lift (weeks 8–10).
- **05 Targets & Context** — vs-target deltas (fulfillment ≥ 98%, peak ETA p90 ≤ 55,
  no-courier ≤ 0.5%, idle ≤ 25%).
- **06 Exec Insight** — one dynamic narrative measure for the Executive Overview.

The live experiment CI is deliberately the simple two-sample interval; the cluster-robust
SE, randomization-inference p and the formal arm×tier interaction test are Phase-10 work,
not measures. Measure names kept ASCII (no em-dash / ×) for `pbir` safety.

## Phase 8 — report build

`powerbi/gen_report_visuals.py` writes `_report_layout.json` (4 pages, one business
question each: Executive Overview · Marketplace Health · Pricing & Incentive Experiment ·
Courier Economics); `powerbi/_drive_pbir.py` turns that manifest into
`SwiftBiteDelivery.Report/**` via the `pbir` CLI (`new report` → `rebind --local` →
`add page`/`background` → `add visual --from-json` per page → sort / conditional-format /
KPI-frame styling pass → `validate`). `powerbi/build_report.sh` is the full orchestrator
(regenerates brand assets + model + DAX doc + layout first; aborts if Power BI Desktop is
running so `pbir` validates the TMDL, not a stale live model).

Each page: a KPI frame with 6 value cards, 4 content visuals, and 3 slicers (period /
zone / supply-stress tier). 56 visuals total.

Two build fixes:
1. `pbir` `lineChart` rejects a `Series` role — the two "weekly fulfillment by arm" line
   charts were rewritten as two explicit Y measures (`Weekly Fulfillment (Treated) %` /
   `(Control) %`), no series.
2. OneDrive held a lock on the just-deleted `.Report` tree, so `pbir new report`
   half-created it. `scaffold()` now retries the delete up to 6× with a back-off.

**`pbir validate --all` → "✓ SwiftBiteDelivery validation passed"** (4 pages, 56 visuals,
116 fields, model loaded). The 93 advisory warnings are `VISUAL_OVERLAP` /
`VISUAL_UNDERSIZED` — the KPI cards sit inside the frame shape by design; final spacing is
a Power BI Desktop polish pass (as with the sibling projects).

## Phase 9 — build log

This document. Maintained per phase, not written at the end.

## Phase 10 — the read-out (primary deliverable)

`data_analysis/` — dual-track (pandas + DuckDB) analysis of the zone-hour incentive
experiment. `utils.py` carries the loaders and the three inference routes the zone-day
design needs: cluster-robust (by zone) OLS SEs, **randomization inference** (permute `arm`
within zone × weekday/weekend, 3,000 draws), and a **wild-cluster bootstrap** (Rademacher,
resampled by zone). Eight `python/NN_*.py` scripts each compute their headline number on
both tracks and call `utils.parity(...)`; `parity/run_all.py` runs them all —
**8/8 scripts, every parity check passes**. `sql/NN_*.sql` is the readable SQL reference.

| # | Analysis | Result |
|---|---|---|
| 01 | anchor | 840 zone-days, 420/arm; naive fulfillment lift +1.87 pp |
| 02 | balance | exact 50/50 by design; zone-level covariates balance by construction (SMD = 0) |
| 03 | primary | **fulfillment +1.87 pp** (cluster CI [+1.27, +2.46]; RI p = 3×10⁻⁴; wild-boot [+1.20, +2.55]); ETA p90 −6.06 min; no-courier −0.36 pp |
| 04 | guardrails | ops guardrails all favourable; **G1 fails** — R$ 281 per incremental delivered order vs R$ 10 margin |
| 05 | novelty | no detectable decay trend (weekly series too thin) |
| 06 | heterogeneity | short +2.29 · balanced +2.43 · **long +0.94** pp; interaction Wald p = 0.004; short-CI ∩ long-CI = ∅ |
| 07 | cannibalisation | ≈ 17% of local, **not significant** (adjacent-control gap p = 0.76); metro net ≈ 83% |
| 08 | synthesis | **don't ship the flat bonus; restructure to reward incrementality; cap to short + balanced zones** |

Two calibration calls made while writing the read-out: (1) G1's cost-per-incremental-order
is computed as a **pooled** Σ/Σ ratio with a zone-cluster bootstrap — a per-zone ratio with
clipping had inflated it via near-zero denominators in ~zero-effect zones. (2) The result
is deliberately a **"do not roll out"** with a restructure path — the intervention improves
the marketplace but is priced wrong (flat bonus on every delivery, ~2% incremental). This
is a stronger analytical demonstration than a "yes, ship it" and matches the ceiling-
compressed primary metric flagged back in Phase 3.

`findings/01`–`08` write each analysis up; `deliverables/build_deliverables.py` renders the
decision-first **board summary** and the exhaustive **deep dive** to HTML + PDF in the
SwiftBite identity, embedding the Love / novelty / forest figures.

## Phase 11 — portfolio assets

`portfolio/gen_portfolio_images.py` → **5 gallery images only** (1600×820, SwiftBite
green): a branded cover with the headline result, the medallion pipeline, the curated
star schema, six key DAX measures as code cards, and the 4-page report map. No marketing
/ Fiverr / pricing / LinkedIn files in the repo.

## Phase 12 — docs bundle

`docs/build_docs_bundle.py` (markdown → HTML → headless-Chrome PDF, green identity) →
`docs/SwiftBite-Delivery-Documentation.pdf` (full 00–09 + walkthrough, 2.5 MB) and
`docs/SwiftBite-Delivery-Summary.pdf` (scope + context + model + DQ + report structure,
0.9 MB). `docs/09_report_structure.md` was written here to complete the 00–09 set.

---

*Project complete. Remaining polish: a Power BI Desktop spacing pass on the report
(open `powerbi/SwiftBiteDelivery.pbip`, set `pDataFolder`, apply `theme.json`), and a
Drive sync of the built PDFs.*
