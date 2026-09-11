# Data Analysis — Start Here

Orientation for the **LumaBank Activation Experiment** analysis (Phase 10 — the primary
deliverable): the incident, end to end — an onboarding A/B test that breaks mid-flight on
a production bug, is diagnosed, and is re-run clean.

Two standing rules:
- **Every headline number is computed twice — once in pandas, once in DuckDB — and the two
  must match.** Each `python/NN_*.py` runs both tracks inline and calls `utils.parity(...)`,
  which raises on any mismatch. `parity/run_all.py` runs them all.
- **It ends in two presentations** (`deliverables/`): a decision-first **board summary**
  and an exhaustive **deep dive** with a day-by-day incident timeline.

Paths are relative to the project root (`LumaBank-Activation-Experiment/`).

---

## 1. The analysis surface

`data/curated/*.parquet` — the Kimball star. This investigation uses:

| Table | Grain | Use for |
|---|---|---|
| `fact_activation` | one row per **signup, platform-wide** (`is_experiment_subject` flags the randomized ones) | the read-out — Day-7/1/30 activation, guardrails, `contaminated_flag`, `in_analysis_flag`, all pre-computed |
| `fact_variant_assignment` | one row per assignment **event** (≥2 for contaminated users) | the SRM re-derivation and the contamination/fallback audit — the raw material blocks 02–03 work from |
| `fact_srm_daily` | one row per experiment × calendar day | the pre-built integrity monitor — block 02 re-derives it independently and cross-checks |
| `dim_app_release` | one row per release | the deploy/hotfix cross-reference (block 03) |
| `dim_region`, `dim_acquisition_channel` | descriptors | the fallback's geographic bias (block 03) and the heterogeneity cut (block 05) |

All money is out of scope here (LumaBank tracks activation and risk, not revenue).

## 2. Read first

1. `docs/01_business_context_kpis.md` — the experiment design, every KPI definition, and
   **section 9, the SRM monitoring runbook** — the spec for block 02.
2. `docs/02_data_architecture.md` §7.3, §9 — the auditable effective-arm, contamination,
   and bug-catalogue rules this analysis relies on.
3. `docs/06_dax_measures.md` — how the same numbers are computed for the report.
4. `data/quality/dq_report.md` — what is clean, and the SRM check that already confirms
   the break is present and the re-run is clean before this analysis starts.

**The true treatment effect and the exact bug magnitudes are NOT in the docs.** They live
only in `etl/config.py::EFFECT` / `BUG`, and this analysis was written to detect and
quantify them from the data as if blind.

## 3. Environment

Python 3.12; `pandas`, `pyarrow`, `duckdb`, `scipy`, `statsmodels`, `matplotlib` (see
`etl/requirements.txt`). Data is static and seeded — fully reproducible from
`python etl/run_pipeline.py`.

## 4. The analyses (run order) — a 5-block investigation, not a flat finding list

| # | Script | Question | Key result |
|---|---|---|---|
| 01 | `01_setup_prereg` | What was known before the test ran? | platform baseline Day-7 45.9%; original 6-week design MDE 2.41 pp at ~6,750/arm |
| 02 | `02_srm_monitoring` | When did the standing SRM monitor first have grounds to say the experiment was broken? | **ALERT fires 2026-07-18** — 2 days after the 2026-07-16 deploy; re-derived independently from the raw assignment log, 100% agreement with the pre-built integrity table |
| 03 | `03_root_cause` | What broke, and can we prove it was the deploy? | the flagged release lands exactly on 2026-07-16; 191 contaminated users (4.4% of the original run); the fallback allocates 65.6% to treatment overall, geographically skewed (SE 76.5% vs N 35.3% treatment) |
| 04 | `04_decision_analysis` | Truncate, exclude-contaminated, or restart? | truncate MDE 5.4–6.6 pp, exclude-contaminated MDE 4.8 pp with unresolved residual bias — **neither could reliably detect the effect**; restart was the only option with zero bias |
| 05 | `05_rerun_readout` | Did the clean re-run work, safely? | **+4.58 pp** (95% CI [+2.55, +6.62], p ≈ 1e-5) against a recomputed MDE of 2.92 pp; KYC-rejection guardrail passes non-inferiority, **flagged-fraud guardrail does not**; heterogeneity favours paid_social/influencer but the formal interaction test is not significant |

Run everything + parity: `python data_analysis/parity/run_all.py`.
Standalone SQL track: `sql/*.sql` (`duckdb -c ".read data_analysis/sql/_prelude.sql"` first).
Outputs land in `outputs/tables/` (CSV) and `outputs/figures/` (PNG).

## 5. Folder layout

```
data_analysis/
  00_START_HERE.md   README.md   utils.py
  python/   NN_*.py   — pandas + DuckDB inline, self-checking parity
  sql/      NN_*.sql  — the readable SQL track (DuckDB dialect; .read _prelude.sql first)
  parity/   run_all.py
  findings/ NN_<slug>.md — one per investigation block
  outputs/  tables/  figures/
  deliverables/  build_deliverables.py -> board_summary.{html,pdf} + deep_dive.{html,pdf}
```
