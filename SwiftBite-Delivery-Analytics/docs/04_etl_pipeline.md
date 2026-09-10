# SwiftBite Delivery — ETL Pipeline

**Document status:** Phase 4 deliverable. **Depends on:** `02_data_architecture.md`.
**Describes:** the code under `etl/` — what each script does, in what order, and the
guarantees it gives.

> **PT.** Este documento descreve o pipeline `etl/` já implementado: os quatro scripts
> (`01_generate_raw` → `02_clean_stage` → `03_build_curated` → `dq_checks`), o que cada um
> garante, e como rodar. Um único `SEED` em `config.py` torna tudo reproduzível byte-a-byte.

---

## 1. Run

```bash
python -m pip install -r etl/requirements.txt
export SB_DATA_DIR="$LOCALAPPDATA/Temp/sb_data"   # optional; keeps the big layers out of OneDrive
python etl/run_pipeline.py            # 01 → 02 → 03 → dq_checks
python etl/run_pipeline.py --from 02  # skip regeneration
python etl/gen_data_dictionary.py     # regenerate docs/03 from data/curated/
```

`run_pipeline.py` imports each step module and calls its `main()` in order, timing each.
`dq_checks` exits non-zero on any failed **hard** check.

**Determinism.** `config.SEED` seeds `utils.rng(name)`, which derives one independent
`numpy` Generator per named stream (`"demand"`, `"supply"`, `"clear"`, `"emit_orders"`, …)
so adding a draw in one place does not shift draws elsewhere. Same seed → byte-identical
`data/raw/` → identical `data/curated/`.

**Idempotency.** Each script rebuilds its own layer. On Windows/OneDrive `utils._atomic_write`
retries on lock (`WinError 5/32`) and falls back to an in-place write; pointing
`SB_DATA_DIR` outside the synced tree avoids the locks entirely.

---

## 2. `01_generate_raw.py` — the marketplace simulator

A seeded simulation, **vectorised at the zone-hour grain**, then serialised to messy
source exports.

### 2.1 World
`gen_georef` writes the 12-zone grid, the adjacency graph and the boundary-redraw history.
`gen_couriers` / `gen_customers` / `gen_restaurants` write the masters (with id-casing
noise and mojibake injected).

### 2.2 Demand
For each zone × day × hour: `orders ~ Poisson(λ)` where λ =
`ORDERS_PER_DAY_METRO_BASE` × day-of-week × month-seasonality × rainy-season × per-day-rain
× local-event, split across zones by a fixed demand share and across hours by `HOUR_SHAPE`
(a lunch + dinner double peak).

### 2.3 Supply
Metro courier-hours for the hour = `demanded_courier_hours × BASE_SUP_RATIO` (× rainy /
per-day-rain penalties, × a slow 2026 decline). Distributed across zones by
`SUPPLY_W = courier-hour-demand-share × exp(0.20 · attractiveness_z)` — deliberately **not**
proportional to demand, so central zones run long and peripheral zones run short. This is
the structural source of the liquidity mismatch the experiment targets.

### 2.4 Clearing
`liquidity_ratio L = available_courier_hours / demanded_courier_hours`. Fulfillment rate,
ETA p50, the p90/p50 spread and assignment latency are smooth piecewise functions of `L`
(`FULFILL_AT_L`, `ETA_P50_AT_L`, …). Delivered count `~ Binomial(orders, fulfillment(L))`;
the non-delivered remainder is split by cause (`no_courier` a minority, then `customer`,
`courier`, `restaurant`). Per-order ETA and latency are log-normal around the zone-hour
central values.

### 2.5 The experiment  *(peak hours only, experiment window only)*
`assign_experiment` splits every peak-eligible zone-day 50/50 treatment/control, stratified
by zone × baseline stress tier and balanced on weekday/weekend. On a **treated** zone-day
the peak-block `available_courier_hours` is multiplied by
`INCENTIVE_EFFECT.supply_response_mult_by_tier` (short 1.34 / balanced 1.15 / long 1.04),
amplified in week 1 by a novelty factor that decays with `τ = 2.5` weeks, with lognormal
per-zone-day noise. **`cannibalisation_share = 0.28`** of the *added* courier-hours is then
subtracted from **adjacent control zones** on the same day — the spatial spillover the
Phase-10 read-out must recover. None of these numbers appear outside `config.py`.

### 2.6 Messy exports (the DQ injection — see `08_data_quality.md`)
Orders written monthly with mixed `DD/MM/YYYY HH:MM` / ISO timestamps, money as text
(`"R$ 62,90"`), ~1.5 % retry duplicates; status/offer/assignment logs at-least-once;
PayHub & Boost in UTC `Z`; GPS reference (last 7 days) as epoch-ms NDJSON with jitter,
far-away and null-island pings; orphan courier ids; the zone boundary redraw carried in the
as-booked label; mojibake in address / restaurant text; a re-delivered PayHub month; ~20
post-midnight Boost campaign edits.

---

## 3. `02_clean_stage.py` — raw → `stg_*`

One typed table per raw entity. Responsibilities:

| Fix | How | Counter(s) |
|---|---|---|
| Datetime | split parser: `^\d{4}-` → ISO fast path, else `%d/%m/%Y %H:%M`; local feeds localised `America/Sao_Paulo` → UTC; PayHub/Boost parsed as UTC | `datetimes_unparseable`, `utc_datetimes_unparseable` |
| GPS ping → minute | drop null-island + out-of-bbox, resample to courier × minute with a `moving`/`idle` state from inter-ping displacement (7-day reference only) | `gps_null_island_dropped`, `gps_out_of_area_dropped`, `ping_minutes_materialised` |
| Money | strip `R$` / thousands `.`; `,`→`.`; `(x)` → `-x` | `money_strings_parsed`, `money_negatives_from_parens` |
| Encoding | `ftfy.fix_text` on address / restaurant text | `mojibake_repaired` |
| De-dup | exact retry rows, at-least-once event/offer/bonus rows, the re-delivered PayHub month | `retry_dupes_dropped`, `dupe_events_dropped`, `redelivered_rows_dropped` |
| Reconcile | Boost post-midnight edits → earliest (`00:00`-fixed) row per zone-day; dispatch funnel latency ms-text → seconds | `campaign_late_edits_reconciled`, `latency_coerced` |
| Category | `status`, offer `outcome` → controlled vocab in `etl/vocab/` | `category_unknowns` |

Staging performs **no** cross-source joins, address→zone resolution, or metric logic.

---

## 4. `03_build_curated.py` — `stg_*` → the star

- **`dim_date`** (day grain, unique `date_key`), **`dim_time_block`** (24 hours),
  **`dim_zone`** (+ tier, filled after `fact_zone_hour`), **`dim_zone_adjacency`** bridge,
  **`dim_courier` / `dim_customer` / `dim_restaurant`**, **`dim_incentive_campaign`**.
- **Zone resolution.** Every order gets `dropoff_zone_key_asbooked` (the messy label, which
  carries the pre-redraw swaps) **and** `dropoff_zone_key_current` (recovered as the nearest
  zone centroid to the — de-swapped — address point). All zone-hour / experiment facts key
  off `_current`; the redraw predates the experiment window by 7 months, so within the
  experiment the two agree.
- **`fact_order`** (order grain) — outcome from the reconciled dispatch funnel, assignment
  latency joined from dispatch, `courier_key` filled for delivered orders from the
  zone-hour courier pool.
- **`fact_courier_shift_block`** (courier × zone × date × hour) — `logged_in` from the shift
  blocks, `present` from the GPS dwell rollup, `deliveries` split from PayHub payouts by
  present-minute share, `active = deliveries × service_min`, `idle = present − active −
  cooldown`, earnings split from payouts, bonus joined direct.
- **`fact_delivery`** (delivered order) — courier drawn from the same zone-hour's blocks
  weighted by their deliveries; payout = base (`6.4 + 1.15·km`) + tip + incentive bonus.
- **`fact_zone_hour`** (zone × date × hour) — the liquidity spine. Demand side aggregated
  from `fact_order`; supply side from `fact_courier_shift_block`
  (`available_courier_hours = Σ(active+idle)/60`); `liquidity_ratio`, `idle_courier_ratio`,
  `unmet_demand`, ETA p50/p90, cancellation split, rain / event flags, and the experiment
  `arm` / `on_treated_zone_day` / `is_adjacent_to_treated_zone_day` for peak-block window
  rows.
- **Baseline stress tier** — mean `liquidity_ratio` per zone over months 1–15, classified
  `< 0.93` short / `> 1.13` long / else balanced. Written onto `dim_zone`.
- **`fact_incentive_assignment`** (zone-day, ~840) — arm, bonus, stratum, adjacency counts,
  and the frozen pre-period covariates (`pre_fulfillment_rate`, `pre_eta_p90_min`,
  `pre_liquidity_ratio`, …) for Phase-10 balance checks.
- **`fact_experiment_zone_day`** (~840) — one tidy row per unit of randomization: the
  primary metric and every guardrail, pre-aggregated over the peak block.
- **`fact_experiment_zone_block_week`** — the weekly × block series for the novelty cut.

---

## 5. `dq_checks.py`

Hard assertions (build fails on violation): referential integrity, `fact_order` /
`fact_delivery` key uniqueness, every experiment zone-day present in
`fact_incentive_assignment`, **order conservation** (`placed = delivered + Σ cancels`),
rate sanity (`fulfillment ∈ [0,1]`, `eta_p50 ≤ eta_p90`, `idle_ratio ∈ [0,1]`), treated
bonus > 0 / control bonus = 0, ≥ 75 days of post-experiment data.

Soft checks (reported to `dq_report.md`, not fatal): 50/50 allocation per stratum,
non-degenerate stress tiers, and **benchmark bands** on the pre-experiment baseline —
fulfillment, ETA p50/p90, cancellation rate, idle ratio, courier earnings per active hour.
It also prints a **naïve** experiment read (fulfillment by arm and by tier, cost per
delivered order) as a smoke test — the real read-out is Phase 10.

Current run: **13/13 hard pass · 0 soft warnings** (see `data/quality/dq_report.md`).

---

## 6. Performance notes

Full pipeline ≈ 6.5 min on the dev box (`01` ≈ 70 s, `02` ≈ 35 s, `03` ≈ 4.5 min, `dq`
instant). The simulator is vectorised at the zone-hour grain (a per-order Python loop was
~3× slower); `02` uses split ISO/BR datetime fast paths (pandas `format="mixed"` was a
3-minute trap); `03`'s courier→delivery assignment is a per-zone-hour `choice` call, not a
per-order loop.

*End of Phase 4 deliverable (ETL).*
