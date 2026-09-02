# AeroVanti SkyPoints — ETL Pipeline

**Document status:** Phase 4 deliverable. **Depends on:** `02_data_architecture.md`.
Stage-by-stage narrative of what `etl/` actually does, and the techniques used.

Run it all with:

```
python -m pip install -r etl/requirements.txt
python etl/run_pipeline.py            # 01 raw -> 02 stage -> 03 curate -> dq_checks
python etl/gen_data_dictionary.py     # regenerate docs/03_data_dictionary.md
```

Dev knobs: `SKP_SCALE` (fraction of the 120k member population, for fast iterations) and
`SKP_NO_CSV=1` (skip the curated CSV mirror). Both default to the full build.

---

## 0. `config.py` — the single source of truth

One `SEED` (`20260902`). Every generator draws a **named sub-stream** from it
(`utils.rng("members")`, `rng("point_engine")`, …) so adding a draw in one place does not
shift draws everywhere else. `config.py` also holds the window dates, program scale,
tier / points / earn / redemption parameters, the seasonality curves, the experiment
design, the DQ-injection knobs — and `FLASH_EFFECT`, the **true experiment effect**, which
is applied only in `01_generate_raw.py` and never read downstream.

---

## 1. `01_generate_raw.py` — synthetic world → messy source exports

Builds the whole program in memory, vectorised over the 120k members × 24 months, then
writes **source-shaped, deliberately messy** files under `data/raw/<system>/`.

### 1.1 Members (`build_members`)
Enrolment month from a weighted curve (relaunch surge in months 1–3, Black-Friday bumps),
channel, home region/city, a latent `engagement ~ N(0,1)`, and a **status tier drawn to hit
the 68/20/9/3 mix** (tilted by engagement). Flight propensity is heavy-tailed
(`Gamma × e^{0.3·eng}`) and **boosted by tier** (Blue 1× … Platinum 7×) so revenue per
member rises steeply by tier. Members enrolled in months 1–3 are "migrated" and carry an
**opening SkyPoints balance** (mixture: a big block in the 3.5k–15k "can't do much yet"
band) with a lot-expiry month in the Feb–Aug 2026 wave.

### 1.2 Activity, tiers, earn (`build_activity`)
Monthly flight counts ~ `Poisson(propensity/12 · seasonality · tenure-ramp)`, expanded to
individual segments with a fare draw and a flexible-fare flag. **Effective tier per
member-month** = Blue until `enrol + ramp_delay`, then the status tier, with ~11% of
Silver+ members losing a tier and ~7% of lower members gaining one mid-window (this is what
populates the tier-change ledger). SkyPoints earned per segment = `base_fare × tier
multiplier × (1 + flex bonus)`. Co-brand card adoption follows a per-channel logistic;
card spend is lognormal with a Nov–Dec bump; card SkyPoints = `spend / 2.5` plus a welcome
bonus. Partner / promo / service-recovery earn are sparse small draws.

### 1.3 Point-lot engine (`run_point_engine`)
A **vectorised monthly loop** over a `(members × 25)` lot matrix (column 0 = the legacy
lot, columns 1–24 = each window month's issuance). Each month:

1. add the month's earnings to the current lot column;
2. compute each member's redemption probability —
   `logit = A0 + 0.62·eng + 0.55·tenure + 0.40·(season−1) + 0.30·(tier−1) + 0.18·log1p(balance/10k)`,
   gated on `balance ≥ 10,000` (the pre-Flash minimum redemption threshold);
3. for redeemers, pick a pre-Flash reward (award short / medium / points-plus-cash),
   cost = price × jitter capped at balance, and **subtract FIFO** across lot columns;
4. expire the legacy lot in its assigned month.

`A0` was calibrated so the pre-experiment steady state sits mid-band for the doc-01 KPIs.

### 1.4 Lapse (`build_lapse`)
A running "months since last activity" per member. `is_lapsed` = 12 consecutive months
with no earn and no redemption; **left null** for the first 11 months / any member with
< 12 months tenure. Reactivation = activity after a lapsed month.

### 1.5 The Flash Redemption experiment (`build_experiment`)
- **Eligible pool** frozen at 2026-03-01: active (earn or flight in trailing 12m) and not
  lapsed.
- **Stratified sample** with Gold/Platinum oversampling — `{Blue 7000, Silver 3800, Gold
  2600, Platinum 1600}` — 50/50 within each stratum.
- **Pre-period covariates** (trailing-12m earn / flights / redemptions, balance, prior-
  redeemer flag, tenure) frozen at the same date.
- **Treatment incremental redemptions**: for each stratum a **deterministic count**
  `round(effect_pp × n_treatment)` of eligible non-redeemers (balance ≥ 3,500) is converted
  to redeemers, so the per-stratum incremental rate equals the baked effect up to
  which-members noise; the analysis still faces real binomial sampling variance. Reward mix
  ≈ 46% low-cost-catalog-only. Redemption **week** is drawn from a novelty-weighted
  distribution (week-1 hazard ×1.9, decaying with τ = 2.5 weeks).
- **Guardrail outcomes** per subject: revenue (window + 8 weeks) scaled by
  `1 + FLASH_EFFECT.revenue_per_member_rel`; liability drawdown and partner reward cash
  cost from the redemptions; a 90-day post-window disengagement proxy with the baked
  favourable shift.
- Emits `flesk__ab_assignments`, `flesk__exposure_log`, and the reconstructable
  `redemption_week_feed` / `outcome_feed`.

### 1.6 Messy raw emission (`emit_raw`)
The clean internal frames are degraded into source-faithful exports — see
`08_data_quality.md` for the full injection list. Highlights: SkyCore member snapshots as
monthly files with ~15% duplicated rows; `point_transactions` as monthly files with a
3-day overlap into the next file; gzip files correctly named `.csv.gz`; BancoAV in Latin-1
with `"R$ 1.234,56"` money strings and Excel-serial months and a re-delivered June-2025
file; Reserva in `MM/DD/YYYY` with orphan / non-member ids; Aurora with mojibake and
invalid birth years and no rows for the first 3 cohorts; Flesk timestamps in UTC with 30
ineligible late corrections and at-least-once exposure rows; the sub-ledger `.xlsx` with
parenthesis negatives and two restated months.

---

## 2. `02_clean_stage.py` — typed `stg_*` tables + DQ fragments

One `stg_<source>_<entity>.parquet` per raw entity. No cross-source joins, no metrics.
Vectorised parsers:

| Parser | Handles |
|---|---|
| `parse_dates(hint)` | ISO, `DD/MM/YYYY`, `MM/DD/YYYY` (per-source locale rule), Excel serials (epoch 1899-12-30). |
| `parse_money_brl` | `R$`, `.`-thousands / `,`-decimal, `(x)` → `-x`, blank → null (never 0). `pd.NA`-safe. |
| `parse_points` | text magnitudes (`"1.500"`), sign by `txn_type`. |
| `map_vocab` | controlled vocabularies in `etl/vocab/*.csv`; unknowns → explicit `"unknown"` + counted. |
| `fix_encoding` | `ftfy.fix_text` + BOM strip for BancoAV / Aurora. |

De-duplication: SkyCore member snapshots collapsed to one row per member per month;
`point_transactions` deduped on `txn_id` across the file overlap; the re-delivered BancoAV
month dropped on `(card_id, competencia_month)`; at-least-once event/exposure rows dropped;
the ledger's restated months resolved to the last occurrence. Every fix increments a
counter that lands in `data/quality/dq_fragments/<entity>.json`.

---

## 3. `03_build_curated.py` — the Kimball star + experiment tables

Reads only staging. `dim_date` first (2024-01-01 → 2027-12-31; carries `experiment_phase`,
`experiment_week`, BR holidays, season tags).

- **`dim_member`** — latest snapshot per member + card / CRM enrichment + `is_steady_state_cohort`
  + experiment arm/stratum + **ledger-derived current tier**.
- **`fact_tier_change`** — deduped tier-change events (incl. the initial Blue → status
  qualification event); **curated tier status is folded forward from this ledger**, and the
  monthly tier snapshot is used only to compute a drift metric.
- **`fact_point_transaction`** — every ledger entry with signed points, `points_value_brl`,
  `earn_month_key` on earn rows, and resolved dimension keys (`-2` for orphan members).
- **`fact_flight_segment`** — one flown segment; `member_key` `-1` non-member / `-2` orphan;
  `skypoints_earned` recomputed with the month's ledger tier multiplier; a slim `dim_route`.
- **`fact_card_spend_month`**, **`fact_liability_month`** (transaction roll-forward with the
  finance sub-ledger alongside for the tie-out), **`fact_targets_month`**.
- **`fact_member_month`** — the panel: balance (cumulative earn − redeem − expire),
  earn/burn/expiry, tier, flights & revenue, card spend, `has_redeemed_ever`,
  `months_since_last_activity` (vectorised forward-fill), `is_active_eom`, `is_lapsed_eom`
  (null until evaluable), `became_lapsed_this_month`, `is_reactivation`.
- **`fact_experiment_assignment` / `_member_week` / `_outcome`** — reconciled to eligible
  subjects; the outcome table pre-computes the primary metric, the four guardrails and the
  diagnostics so Phase 10 goes straight to the tests.

Cross-cutting: FIFO lot accounting in the engine; breakage-adjusted liability unit cost;
sentinel keys never dropped; all money BRL.

---

## 4. `dq_checks.py` — hard assertions + `dq_report.md`

Fails the build (non-zero exit) on any hard violation. Checks: key uniqueness and
referential integrity; **points roll-forward identity** (program balance == Σ member
balance, exact); **liability tie-out** to the sub-ledger; lapse null-honesty and
stickiness; experiment integrity (assignment count, subject membership, 50/50 allocation,
`redeemed_in_window` == OR of weekly flags, ≥ 90-day post horizon); and the doc-01
benchmark bands on the pre-experiment steady state (redemption rate, ever-redeemed share,
burn/earn ratio, Blue share). Then it assembles every DQ fragment into
`data/quality/dq_report.md`.
