# Data Analysis — Start Here

Orientation for the **SwiftBite Delivery** analysis (Phase 10 — the primary deliverable):
the read-out of the **zone-hour incentive experiment**.

Two standing rules:
- **Every headline number is computed twice — once in pandas, once in DuckDB — and the two
  must match.** Each `python/NN_*.py` runs both tracks inline and calls `utils.parity(...)`,
  which raises on any mismatch. `parity/run_all.py` runs them all.
- **It ends in two presentations** (`deliverables/`): a decision-first **board summary** and
  an exhaustive **deep dive**, one section per finding.

Paths are relative to the project root (`SwiftBite-Delivery-Analytics/`).

---

## 1. The analysis surface

`data/curated/*.parquet` — the Kimball star. The experiment read-out uses:

| Table | Grain | Use for |
|---|---|---|
| `fact_experiment_zone_day` | one row per randomised **zone-day** (~840, 420/arm) | **the read-out** — primary metric + guardrails, pre-computed |
| `fact_incentive_assignment` | one row per zone-day | design + **frozen pre-period (months 1–15) covariates** |
| `fact_experiment_zone_block_week` | zone × experiment week × peak block (~480) | novelty / decay (weekly series) |
| `fact_zone_hour` | zone × date × hour | context — the standing liquidity picture |
| `dim_zone` (+ `dim_zone_adjacency`) | zone | `baseline_supply_stress_tier`; the adjacency graph for the cannibalisation analysis |

`utils.zone_day()` returns the joined analysis frame (outcomes + covariates + tier).
All money is **BRL**. Facts are never joined to each other — slice by shared dimensions.

## 2. Read first

1. `docs/01_business_context_kpis.md` §5 — the experiment design (unit = **zone-day**,
   50/50 within zone × weekday/weekend, peak block 18:00–22:00), the primary metric
   (fulfillment rate) + the five guardrails, the zone-day MDE/power.
2. `docs/05_data_model.md` §2 — fact grains.
3. `docs/06_dax_measures.md` — the "04 Experiment" folder mirrors this analysis for the report.
4. `data/quality/dq_report.md` — what is clean; what is a known limitation.

**The true effect is NOT in the docs.** It lives only in `etl/config.py::INCENTIVE_EFFECT`
(supply response by tier, novelty decay, a 28% neighbour-zone cannibalisation term). This
analysis was written to recover it from the data.

## 3. Environment

Python 3.12; `pandas`, `pyarrow`, `duckdb`, `scipy`, `statsmodels`, `matplotlib`. Data is
static and seeded. If the curated layer is outside the repo, set `SB_DATA_DIR`.

## 4. The analyses (run order)

| # | Script | Question | Headline |
|---|---|---|---|
| 01 | `01_anchor` | The frame + the naive numbers | 840 zone-days; naive fulfillment lift +1.87 pp |
| 02 | `02_balance` | Can the assignment be trusted? | exact 50/50; zone-level covariates balance by construction |
| 03 | `03_primary` | Does it lift fulfillment? | **+1.87 pp** (cluster CI [+1.27,+2.46]; RI p = 3e-4; wild-boot agrees); ETA p90 −6.1 min; no-courier −0.36 pp |
| 04 | `04_guardrails` | Is it safe / does it pay? | ops guardrails all favourable; **G1 fails** — R$ 281 per incremental order vs R$ 10 margin |
| 05 | `05_novelty` | Does the lift decay? | no detectable trend; weekly series too thin to say |
| 06 | `06_heterogeneity` | Same for every zone? | short +2.29 · balanced +2.43 · **long +0.94**; interaction Wald p = 0.004 |
| 07 | `07_cannibalisation` | Is the local win a transfer? | ≈ 17% of local, **not significant**; metro net ≈ 83% |
| 08 | `08_synthesis` | The decision | **Don't ship the flat bonus. Restructure to pay for incrementality; cap to short + balanced zones.** |

Run everything + parity: `python data_analysis/parity/run_all.py`
Standalone SQL track: `sql/*.sql` (`duckdb -c ".read data_analysis/sql/_prelude.sql"` first).
Outputs land in `outputs/tables/` (CSV) and `outputs/figures/` (PNG).

## 5. Folder layout

```
data_analysis/
  00_START_HERE.md   README.md   utils.py
  python/   NN_*.py   — pandas + DuckDB inline, self-checking parity
  sql/      NN_*.sql  — the readable SQL track (DuckDB; .read _prelude.sql first)
  parity/   run_all.py
  findings/ NN_<slug>.md — one per analysis
  outputs/  tables/  figures/
  deliverables/  build_deliverables.py -> board_summary.{html,pdf} + deep_dive.{html,pdf}
```
