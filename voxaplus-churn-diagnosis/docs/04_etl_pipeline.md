# Voxa+ — ETL Pipeline

**Document status:** Phase 4 deliverable · describes `etl/` as built.
**Companion:** `docs/02_data_architecture.md` (the spec), `docs/03_data_dictionary.md`
(auto-generated column reference), `docs/08_data_quality.md` (issue handling & limitations).

```
python -m pip install -r etl/requirements.txt
python etl/run_pipeline.py            # raw -> staging -> curated -> dq_checks   (~28 min at full scale)
python etl/run_pipeline.py --from 02  # staging onward
python etl/gen_data_dictionary.py     # regenerate docs/03 from data/curated/
```

Everything is driven by one `SEED` in `etl/config.py`. `POP_SCALE` (env `VOXA_POP_SCALE`)
scales the simulated population — `1.0` produces ~116k sign-ups / ~66k active subscribers at
window end; smaller values are used for fast calibration (churn/retention rates are
scale-invariant).

Runtime at `POP_SCALE=1.0` on a Windows/OneDrive workstation: raw ≈ 19 min (≈ 13.5 M
subscriber-day viewing rows across 36 monthly Parquet files), staging ≈ 2.5 min, curated
≈ 7 min, DQ checks ≈ 4 s.

---

## 1. Design rules that shaped the code

| Rule | How it is enforced |
|---|---|
| **Deterministic** | `utils.rng("stage", "topic", …)` derives an independent NumPy `Generator` from `SEED` + a stable hash of the name parts. Every random draw names its own stream, so adding a step never shifts another step's numbers. |
| **Idempotent** | Each script wipes and rebuilds only its own layer. Re-running with the same config yields byte-identical output. |
| **Layered** | Staging reads only `data/raw/`; curated reads only `data/staging/`; the semantic model reads only `data/curated/`. Never upward. |
| **Crash-safe on OneDrive** | `utils._atomic_write` writes to a temp file in the same folder then `os.replace`, retrying ~5× with backoff on `PermissionError`/`OSError` (WinError 5/32). |
| **Every fix is counted** | Staging and curated push named counters into `data/quality/dq_fragments/*.json`; `dq_checks.py` assembles them into `dq_report.md`. |

---

## 2. Stage 0 — the generative world model (`etl/gen/`)

`01_generate_raw.py` first builds a **clean, internally-consistent picture of the business**,
then dirties it. The clean model is three modules:

### 2.1 `gen/world.py` — subscribers, month by month
Every per-subscriber attribute is a full-length NumPy buffer indexed by subscriber row. The
simulation loops over the 36 window-months and, each month, vectorises over the currently
active set:

1. **Acquisition** (`_acquisition_plan`) — Poisson monthly sign-ups per market with a launch
   ramp for MX/US, organic growth, and calendar seasonality; each new subscriber draws a
   channel (from the pre- or post-`CHANNEL_SHIFT_IDX` mix), tier, billing period, a
   persistent primary device and connected-TV viewing share, an engagement propensity, a
   price sensitivity, an incentivised-sign-up flag, and a payment method.
2. **Engagement** — monthly streamed hours from a tier base × propensity × tenure decay ×
   seasonality × content-gap factor, with a log-normal shock and an "inactive this month"
   tail; `below_healthy` = < 5 h.
3. **Billing & dunning** — monthly (or annual-anchor) charge at the plan-price schedule;
   authorisation by method; failures enter a 3-retry dunning sequence; exhausted dunning
   becomes **involuntary churn**.
4. **Voluntary churn hazard** — a tenure base hazard × multipliers for tier, market, annual
   lock-in, engagement (low-engagement ×1.5, otherwise a mild slope), and incentivised
   early tenure; then **additive terms from `config.py` §9** (see 2.4). A uniform draw
   against the clipped hazard decides the churn.
5. **Plan changes / pause / resume / reactivation** — small monthly probabilities; each
   emits a lifecycle event.
6. **Recording** — one `subscription_month` row per active, paused, **or churned-this-month**
   subscriber; MRR recognised at the monthly price (annual = list ÷ 12).

Outputs: `subscribers`, `subscription_month`, `subscription_events` (the movement ledger),
`billing_attempts`, `viewing_month`.

### 2.2 `gen/content.py`
~3,500 titles with language-appropriate names (PT/ES/EN), genre, an originals flag, a
release vintage (some pre-window), licence windows per market (a few BR licences expire
mid-window), a tentpole release schedule, and a per-title amortisation + lumpy cash-spend
schedule calibrated so content amortisation lands near ~55 % of subscription revenue.

### 2.3 `gen/economics.py`
FX as a clamped random walk (BRL ≈ 4.9–5.5, MXN ≈ 17–20 per USD); marketing spend derived
from sign-up volume × CAC-by-channel with impressions/clicks; SSP ad revenue from Básico
viewing × fill × eCPM; support tickets driven by billing failures + app issues + a reason
mix; a monthly GL roll-up (`fact_finance_month` source) that ties to the operational
aggregates within tolerance.

### 2.4 The churn-shift mechanism
`config.py` §9 holds a small set of **tunable effect sizes** that make company-wide gross
churn step up at window-month 34 (from ~4.1 % to ~6.8 %, a 1.66× "near-doubling") as an
**emergent property** of several overlapping parameter changes rather than one switch. The
factors are intentionally *not* enumerated in `docs/01` — the point of the Phase 10
investigation is to recover them from the curated data. `docs/walkthrough.md` records what
they are for maintainers.

---

## 3. Stage 1 — raw (`01_generate_raw.py` → `data/raw/<source>/`)

Serialises the clean world into 13 source-shaped exports, injecting every data-quality issue
Q01–Q15 and counting each into `dq_fragments/raw_injection.json`.

| Source folder | Files | Deliberate mess |
|---|---|---|
| `ketch/` | `plan_catalog.xlsx`, `invoices__YYYY-MM.csv`, `subscriptions_snapshot__YYYY-MM.csv` | Excel-serial dates + text prices; overlapping monthly invoice ranges; a daily full-dump snapshot (3 copies/month) that **drifts from the ledger**; plan/market free-text. |
| `pagstream/` | `transactions__YYYY-MM.csv`, `settlement__YYYY-MM.csv` | semi-structured `meta` JSON; `amount` gross-for-some / net-of-fee-for-others; negative refunds; ~0.3 % null `account_id`. |
| `voxaid/` | `accounts.csv` (UTF-8 **BOM**), `device_registrations.csv` | free-text market; GDPR-deleted accounts omitted though still referenced; unnormalised device names. |
| `entitlement/` | `events.jsonl` | at-least-once delivery → ~1.8 % duplicate `event_id`; shuffled order. |
| `bonsai/` | `crm_contacts.csv` (**Latin-1**), `winback_membership.csv` | mojibake names; free-text lifecycle stage; `birth_year` 0/1900; early cohorts absent. |
| `trackpad/` | `app_events__YYYY-MM.parquet` | session-rollup per account/day/device; duplicate `event_id`; device/version noise; UTC. |
| `playlog/` | `playlog__YYYY-MM.parquet` | watch time **seconds → milliseconds** from window-month 20; CDN bytes MB vs GB by edge provider; a batch of negative `watch_time`; `asset_id`s not in the catalogue. |
| `reelbase/` | `titles.xlsx`, `licence_windows.csv` | encoding damage; mixed `DD/MM/YYYY` and Excel-serial dates; missing genre; `is_original` as Y/N/1/0/"". |
| `contentfin/` | `amort_schedule.xlsx`, `cash_milestones.xlsx` | parentheses negatives; month columns as Excel serials; implied currency. |
| `adbridge/` | `spend_weekly.csv`, `attribution.csv` | channel-name noise; MX rows carry MXN in the `spend_usd` column; `clicks` holds impressions on partner rows; attribution has no account key. |
| `voxaads/` | `ssp_daily_revenue.csv` | `MM/DD/YYYY` dates; duplicate day rows. |
| `helpline/` + `helpdesk/` | `v1_tickets.csv`, `v2_tickets.csv` | **schema break** at the window-month-13 migration: different column names, reason taxonomy, id format, CSAT scale (1–5 vs 0–10); some tickets duplicated across the cutover. |
| `ledger/` | `gl_trial_balance__YYYY-MM.csv`, `fx_rates.csv` | free-text account names; a few FX months missing. |

`data/raw/_truth/` also holds a handful of clean frames (`subscription_month`, `gl`, …) that
`dq_checks.py` reconciles against — never read by staging or curated.

---

## 4. Stage 2 — staging (`02_clean_stage.py` → `data/staging/stg_*`)

One typed `stg_*` table per raw entity. **No cross-source joins, no metric definitions.**

| Fix class | Technique |
|---|---|
| **Date parsing** | Vectorised `parse_date_series` — explicit `pd.to_datetime(format=…)` per known style (`iso`, `dmy`, `mdy`, `%d-%b-%y`), Excel-serial branch via `EXCEL_EPOCH + to_timedelta`. |
| **Money parsing** | Vectorised `parse_money_series` — strip non-numeric, decide decimal separator per row by which of `,`/`.` appears last, parentheses → negative. Invoices parse per `currency` group (BRL = 1.234,56; USD/MXN = 1,234.56). |
| **Encoding repair** | `ftfy.fix_text` for mojibake; read the Latin-1 CRM file with the right codec; `utf-8-sig` to drop the BOM. |
| **De-duplication** | `drop_duplicates` on `event_id` / `invoice_id` / `beacon_id`; the daily full-dump snapshot is collapsed to the latest row per account **per file**. |
| **Unit normalisation** | PlayLog watch time → seconds by era + magnitude; CDN bytes MB→GB by `edge_provider`; CSAT → 0–1 (÷5 for v1, ÷10 for v2). |
| **Category harmonisation** | `norm_series` maps free text to a controlled vocabulary via `etl/vocab/*.csv` (`.str.strip().map(dict)`); unmatched → explicit `"unknown"`. |
| **Mislabelled columns** | AdBridge MX `spend_usd`→`spend_local` (MXN) then recompute USD; partner-row `clicks`→null. PagStream `amount` kept as `amount_reported` + `amount_is_trusted = False` — curated re-derives the billed amount from the plan-price schedule. |
| **Schema unification** | Helpline v1 + Helpdesk v2 mapped to one `stg_support_tickets` schema and one reason taxonomy via `vocab/support_reason_crosswalk.csv`, tagged `source_version`; cutover duplicates dropped. |
| **Timezones** | All event timestamps → tz-aware UTC. |

**Performance note.** The first implementation used `Series.map(python_fn)` for every parse
and ran ~45 min at full scale on the 2–4 M-row Ketch tables and the 13.5 M-row PlayLog/
Trackpad loop. Rewriting the hot paths as the vectorised `*_series` helpers above (and
replacing per-row `json.loads` on the PagStream `meta` blob with vectorised regex extract)
brought staging to ~2.5 min.

The big two (`stg_playlog`, `stg_trackpad_app_events`) are written **partitioned by month**
under `data/staging/<name>/YYYY-MM.parquet` so neither staging nor curated has to hold the
full 13.5 M rows in memory.

---

## 5. Stage 3 — curated (`03_build_curated.py` → `data/curated/`)

Conformed Kimball star: **10 dimensions + 13 facts** (+ `fact_viewing_daily` partitioned by
month). Written as Parquet **and** a CSV mirror.

Key build logic:

- **`dim_date` first**, spanning **2023-01-01 → 2027-12-31** — deliberately wider than the
  fact window so no stray "(blank)" date member appears when annual renewals or settlement
  land past the last window month. Carries `window_month_idx`, `in_analysis_window`,
  per-market holiday flags, `season_tag`, `is_partial_period`.
- **Surrogate keys** minted 1..n per dimension; business keys kept as `*_id`. Sentinels:
  `-1` unknown, `0` unresolved. Facts referencing a missing dimension get a sentinel and a
  counted DQ row — rows are **never dropped** for referential problems.
- **`dim_subscriber`** joins VoxaID accounts + first-paid month from the ledger + first/
  current tier + a billing-period detection (annual if any invoice ≈ ≥ 6× the subscriber's
  median invoice) + CRM lifecycle. Acquisition channel is **sampled from each market's
  monthly channel mix** (the AdBridge attribution feed has no account key — see limitations).
  `is_comparable_base` (= Brazil) and `is_l4l_cohort` (first-paid ≤ PY end) stamped here.
- **`fact_subscription_month` is folded from the movement ledger.** Events are sorted
  `subject, month_idx, event-type-priority, timestamp` (priority so `paid_start` precedes a
  same-month `churn` despite random within-month timestamps), then replayed per subject into
  active spells `[start, end, is_reactivation, tier, churn_kind]`. Monthly rows are emitted
  per spell with `tenure_months`, `is_new`/`is_reactivation` on the first month and
  `is_voluntary_churn`/`is_involuntary_churn` on the churn month. The Ketch snapshot is used
  **only** to quantify drift, never as input.
- **`fact_billing_attempt`** takes the billed amount from the plan-price schedule (working
  around the PagStream `amount` mislabel), keeps status/method/attempt/dunning from the
  gateway, and adds `processing_cost_*` from the method fee model.
- **`fact_viewing_daily`** aggregates the PlayLog beacons to subscriber × local date ×
  device family per month; `fact_engagement_month` rolls that up to subscriber × month with
  `below_healthy_engagement`, `active_days`, `pct_days_ctv`.
- **USD everywhere.** Every `_local` money column gets a `_usd` sibling at the month's
  average FX rate from `fact_fx_rate` (= 1 for USD).
- **`fact_targets_month`** builds the plan (`PY actual × (1 + planned growth)` per market,
  flat target churn) local-then-converted.

---

## 6. DQ gate (`dq_checks.py`)

Runs last; **fails the pipeline (non-zero exit) on any hard check**. Assembles
`data/quality/dq_report.md` from all fragments + the results.

**Hard checks** (structural / accounting): no null surrogate keys in facts; every event
resolves to a real or sentinel subscriber; the subscriber base **roll-forward identity**
(`start + new + reactivation − churn = end`, ≤ 2 % monthly — actual worst 0.00 %); cohort
retention ≤ 100 % and non-increasing; `fact_viewing_daily` device keys ⊆ `dim_device`;
`dim_date` spans beyond the fact window.

**Soft checks** (plausibility / calibration, warn only): unresolved-subscriber share on
billing ≤ 1.2 %; MRR positive & rising; pre-shift blended gross churn in 3.6–4.6 %
(actual 4.11 %); peak (idx 33–35) in 6.4–8.6 % (actual 6.82 %); peak/pre ratio 1.6–2.1×
(actual 1.66×); pre-shift streamed hours 25–70 h (47.6 h); below-healthy share 8–28 %
(11.1 %); GL subscription revenue vs curated MRR ≤ 15 % mean rel. (4.0 %).

Latest run: **6 hard PASS, 0 soft warnings.**
