# LumaBank — ETL Pipeline

**Document status:** Phase 4 deliverable. **Depends on:** `02_data_architecture.md`.
**Describes:** the code under `etl/` — what each script does, in what order, and the
guarantees it gives.

> **PT.** Este documento descreve o pipeline `etl/` já implementado: quatro scripts
> (`01_generate_raw` → `02_clean_stage` → `03_build_curated` → `dq_checks`), o que cada um
> garante, e como rodar. Um único `SEED` em `config.py` torna tudo reproduzível
> byte-a-byte — **incluindo a quebra de 16/07/2026**, que é determinística, não ruído.

---

## 1. Run

```bash
python -m pip install -r etl/requirements.txt
python etl/run_pipeline.py            # 01 -> 02 -> 03 -> dq_checks (~9 min)
python etl/run_pipeline.py --from 02  # skip regeneration
python etl/run_pipeline.py --from 03  # rebuild curated + dq only (~90s)
python etl/gen_data_dictionary.py     # regenerate docs/03 from data/curated/
```

`run_pipeline.py` runs each step as a subprocess and times it. `dq_checks.py` exits
non-zero on any failed **hard** check, so a broken build fails loudly rather than
publishing a silently-wrong `data/quality/dq_report.md`.

**Determinism.** `config.SEED` seeds `utils.rng(name)`, which derives one independent
`numpy` Generator per named stream (`"world"`, `"txn"`, `"releases"`, `"raw_emit"`, …), and
`utils.stable_hash_u01(ids, salt)` derives a reproducible uniform draw per user id + salt —
used for the feature-flag arm hash and for every step of the production bug (cache-reset
roll, re-hash, fallback roll, fallback geo-skew). Same seed → byte-identical raw exports →
identical curated tables, break included.

**Idempotency.** Each script wipes and rebuilds its own layer. `utils._atomic_write`
retries on Windows/OneDrive file locks (`WinError 5/32`) with backoff.

---

## 2. `01_generate_raw.py` — the world simulator

Builds the whole synthetic world **in memory** as flat NumPy arrays (one row per user),
then serialises it to six source-shaped, messy exports.

### 2.1 Users, timing, geography

`build_world` draws 135,000 signups against `SIGNUP_MONTH_WEIGHTS` (21 months, launch ramp
+ Jan/Nov-Dec seasonality), assigns UF/macro-region/timezone from
`vocab/br_uf_region_tz.csv` (population-weighted), OS, acquisition channel (with a
CRM-go-live gap → `unknown` for months 1–2), and a latent **intent** ~ N(0,1) shifted by
channel — the single confound that drives KYC-submission, activation and (mildly)
fraud propensity throughout.

### 2.2 The experiment and the break

- **Membership.** `in_exp1` = signup in `[EXP1_START, EXP1_ENROLL_PAUSED)`;
  `in_exp2` = signup in `[EXP2_START, EXP2_END]`. `pre_deploy` / `post_deploy` split exp1
  at `DEPLOY_DATE`.
- **Base assignment.** `stable_hash_u01(user_id, "...-v1")` for the original run,
  a **fresh** salt `"...-v2"` for the re-run — no arm carries over between runs.
- **BUG01 (cache reset).** For pre-deploy users who "open the app" (an 85% roll) within
  `BUG.reset_open_window_days` of `DEPLOY_DATE`, a `reset_share` roll marks a
  `cache_reset` exposure event.
- **BUG02 (contamination).** Of the reset users, a `reswitch_share` roll gives them a
  **second** `variant_assignments` row, re-hashed with a different salt — landing in
  either arm independently of the first (so ~half actually switch).
- **BUG03 (biased fallback).** For post-deploy signups, a `fallback_share` roll (constant
  over the ~6 remaining enrollment days, since the incident pauses enrollment before it
  would naturally decay) routes them to `assignment_source='fallback'`, whose arm is
  `stable_hash_u01(user_id, "fallback-geo") < fallback_treat_frac_by_region[macro_region]`
  — deterministic on geography, not the RNG.
- All of this is emitted as **assignment events**, not resolved arms — the resolution
  (effective arm, contamination) happens in curated (§4), from the event log alone, exactly
  as the real monitoring pipeline would see it.

### 2.3 Onboarding, KYC, activation — the identity that makes Day-7 exact

Two funnels are computed side by side:

1. **Counterfactual control-flow** (`cf_*`) — arm-independent: would this user submit KYC
   fast, get approved, and have a decision inside 7 days? This drives `day7_base`, the
   **common baseline for both arms**, so the treatment effect is never a byproduct of the
   flow difference.
2. **Actual flow** (`is_treat_flow`) — control users get the counterfactual funnel exactly;
   treatment users get **account-first** (immediate, ~94%), KYC **deferred** (submitted
   hours later, a `treatment_limited_never_verified_share` never submit at all), and a
   `kyc_reject_delta_pp` / `fraud_flag_delta_pp` bump on the guardrails. This actual funnel
   drives every emitted onboarding-step / KYC / account row.

`day7` starts as `day7_base`, then a **deterministic largest-remainder flip**: for each
(cohort, channel) cell of treatment subjects, `round(ATE_channel × n_cell)` not-yet-
activated, day7-eligible users are flipped to activated, preferring the highest-intent
candidates first. This makes the realised pooled and per-channel lift track `config.EFFECT`
up to which-users noise — real binomial noise still comes from which half of the population
landed in which (randomly assigned) arm.

**The identity guarantee.** Any user who ends up `day7` or a later (`late_act`) activator
is **forced to have an account** (`acc_created |= day7 | late_act`) with a timestamp inside
their flow's normal timing. This is why `dq_checks` can assert
`day7_activated == account_opened_flag AND first_txn_ts <= assigned_ts + 7d` **exactly** —
the curated recompute is not an approximation of the generator's truth, it reproduces it.

TTFT is drawn from a log-normal (median 26h) capped at 167.5h for Day-7 activators, and
from a uniform(169h, 720h) for day-8-to-30 late activators; transactions past
`WINDOW_END` are dropped (near-future censoring) rather than fabricated.

### 2.4 Messy exports

Six source systems (`lumencore`, `flagfox`, `trilha`, `riskguard`, `beacon`, `orbita`), each
with its own quirks — see `02_data_architecture.md` §4–5 for the full inventory. Highlights:
monthly user snapshots with intra-month duplicate rows; overlapping-month transaction files
(cross-file dupes); `amount` as `"R$ 1.234,56"` on ~6% of rows; transaction timestamps as
Unix epoch-**milliseconds**; KYC decisions in UTC with ~20% date-only; app releases as
Excel-serial dates in `.xlsx`; Latin-1 city names; at-least-once event logs.

---

## 3. `02_clean_stage.py` — raw → `stg_*`

One typed table per raw entity. `parse_dt_flex` handles ISO-8601 (mixed with/without
fractional seconds — `format="ISO8601"`, not the pandas default, which silently returns
`NaT` on a mixed-precision column), `DD/MM/YYYY` / `MM/DD/YYYY`, Excel serials, and epoch
milliseconds/seconds all in one call, dispatching on the string shape.

| Fix | How | Counter(s) |
|---|---|---|
| Date/time | `parse_dt_flex`; RiskGuard `decided_at` additionally parsed as UTC with `format="ISO8601"` (mixed full-timestamp / date-only) | `dates_parsed`, `epochs_or_serials_converted`, `decisions_date_only` |
| Money | strip `R$` / thousands `.`; `,` → `.` | `money_strings_parsed` |
| Encoding | `ftfy.fix_text` on Latin-1-damaged names / `cidade` | `mojibake_repaired` |
| De-dup | exact-duplicate rows on the natural key per entity (`txn_id`, `event_id`, `ticket_id`, …); the monthly user snapshot collapses to one row per user (`keep="last"`) | `dupe_txn_dropped`, `dupe_events_dropped`, `snapshot_rows_collapsed` |
| **Not** de-duped | `variant_assignments` rows are kept **as-is** across `assignment_seq` — a second row per user is the contamination signal, not noise | `multi_assignment_users` (counted, not dropped) |
| Category | `step_name`, transaction `type`, ticket `category`, acquisition `channel`, release `platform`, KYC reason → controlled vocab in `etl/vocab/` | `*_normalised`, `*_unknowns` |
| Boolean | `cache_reset`, `confirmed`, `submitted_after_account` from `"true"/"1"` text | — |

Staging performs **no** cross-source joins, no arm resolution, and no metric logic.

---

## 4. `03_build_curated.py` — `stg_*` → the star

- **`dim_date`** stamps `experiment_phase` (pre / original / washout / rerun / post),
  `experiment_day` (1..N within each run), and `is_post_deploy` (the original run, on/after
  the deploy).
- **`dim_user`** — one row per signup, joined to acquisition channel, region, and the
  **experiment derivation** below.
- **Effective arm + contamination (vectorised, not a per-row loop).** From
  `fact_variant_assignment`'s event log: `first_arm` = the seq-1 arm; if a seq-2 row exists
  with a **different** arm **and** it lands before 50% of the user's Day-7 window has
  elapsed, that later arm is effective instead. `contaminated_flag` = an arm switch **or**
  a `cache_reset` exposure inside the active Day-7 window — the exact auditable rule from
  doc 02 §7.3, reproduced here as `pandas` boolean algebra over one `per`-user frame (no
  Python-level loop over 135k rows).
- **`experiment_cohort`** from the user's local signup date against the run boundaries;
  **`in_analysis_flag`** = `rerun` **and** not contaminated **and** never touched the
  fallback (`assignment_source == 'primary'` on every one of the user's rows) — the exact
  population the primary read-out filters on.
- **`fact_activation`** — one row per randomized user; `day7_activated` /
  `day1_activated` / `day30_activated` **recomputed from `fact_transaction_day` and the
  account-open timestamp**, not carried over from the generator — this is what makes the
  `dq_checks` identity assertion meaningful.
- **`fact_srm_daily`** — for each of the two runs, walks every calendar day and computes,
  from `fact_variant_assignment` alone: daily arm counts, a **cumulative** and a
  **trailing-7-day** Pearson χ² goodness-of-fit vs 50/50 (`scipy.stats.chi2.sf`),
  `snapshot_log_mismatch_n` / `multi_assignment_n` (cumulative to date), and `alert_state`
  per the doc 01 §9 runbook thresholds (`WARN` p < 0.01, `ALERT` p < 0.001, on either test).
- **Sentinel keys.** `user_key = -1` for any event whose `user_id` is absent from
  `dim_user` (queue-lag orphans). Facts are never dropped for a missing dimension.
- **User-local calendar day.** UTC timestamps (Flagfox, RiskGuard) are converted to
  `America/Sao_Paulo` before bucketing (`to_brt_naive`); everything else is emitted
  already-local by the generator. *(Simplification flagged here: bucketing uses BRT for
  every user rather than each region's own timezone — the Amazon-timezone nuance from
  doc 02 §7.3 is preserved as a user attribute (`dim_region.timezone`) but not used for
  day-bucketing. Immaterial to the SRM signal, which is driven by the fallback's
  geographic skew, not by which clock a day boundary uses.)*

---

## 5. `dq_checks.py`

Hard assertions (build fails on violation): referential integrity on every fact;
`fact_variant_assignment` unique on `(user_id, assignment_seq)`; exactly one
`is_first_assignment` and one `is_effective_assignment` per user; the Day-7 identity
recompute; core-funnel step-reach monotonicity (`signup → … → first_transaction`;
`limits_lifted` is excluded — it is a parallel KYC-completion milestone, not downstream of
activation); **the SRM check** — the original run must hit `alert_state == 'alert'` on or
after 2026-07-17 and raise WARN/ALERT on ≥ 2 days, while the re-run's trailing-7-day SRM
p-value never drops below 0.01; every `in_analysis_flag` user is non-contaminated, `rerun`
cohort, and never touched the fallback; no transaction-day rows past `WINDOW_END`; every
re-run user's Day-7 window closes inside the data.

Soft checks (reported, not fatal): whether the *cumulative* SRM p-value also crosses 0.001
(it doesn't, in this build — the trailing-7-day test is the one that fires, which is the
point of running both); benchmark bands on the re-run control arm (Day-7 activation, KYC
rejection, flagged-fraud, tickets/1k).

**Current run: 0 hard failures, 1 warning** (see `data/quality/dq_report.md`).

---

## 6. Performance notes

Full pipeline ≈ 9 min on the dev box (`01` ≈ 7 min, `02` ≈ 40 s, `03` ≈ 80 s, `dq` a few
seconds). Two traps worth naming for anyone extending this: **(1)** `pandas.to_datetime` on
a column that mixes timestamps with and without fractional seconds silently returns `NaT`
for the non-matching rows unless `format="ISO8601"` is passed — this broke `signup_ts` for
every user on the first pass and is why every ISO parse call here pins the format
explicitly; **(2)** a per-group `.agg(..., lambda s: (s == x).sum())` on a multi-million-row
`groupby` is dramatically slower than pre-computing the boolean columns and summing them —
`fact_transaction_day`'s per-type counts went from several minutes to a few seconds this
way.

*End of Phase 4 deliverable (ETL).*
