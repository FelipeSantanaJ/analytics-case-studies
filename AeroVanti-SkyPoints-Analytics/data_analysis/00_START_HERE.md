# Data Analysis — Method & Analysis Surface

Detailed orientation for the **AeroVanti SkyPoints** analysis (Phase 10 — the primary
deliverable). Landed here from outside `data_analysis/`? Start at
[`README.md`](README.md) instead — it has the run command and the deliverable links; this
file is the deep-dive method reference it points to.

Two standing rules:
- **Every number that lands in a finding is computed twice — once in pandas, once in
  DuckDB — and the two must match.** Each `python/NN_*.py` runs both tracks inline and calls
  `utils.parity(...)`, which raises on any mismatch. `parity/run_all.py` runs them all.
- **It ends in two presentations** (`deliverables/`): a decision-first **board summary** and
  an exhaustive **deep dive**, one section per business problem.

Paths below are relative to the project root (`AeroVanti-SkyPoints-Analytics/`).

---

## 1. The analysis surface

`data/curated/*.parquet` — the Kimball star (18 tables). Prefer the parquet.

| Table | Grain | Use for |
|---|---|---|
| `fact_experiment_outcome` | one row per assigned subject (15,000) | **the A/B read-out** — primary metric + guardrails + diagnostics, pre-computed |
| `fact_experiment_assignment` | one row per subject | randomisation check — frozen pre-period covariates |
| `fact_experiment_member_week` | subject × experiment week (180,000) | novelty-effect (weekly series) |
| `fact_member_month` | member × month (~1.9M) | program health, hoarding funnel, lapse |
| `fact_point_transaction` | one ledger entry | earn / burn / breakage roll-forward |
| `fact_liability_month` | one calendar month | liability trajectory + sub-ledger tie-out |
| `fact_flight_segment`, `fact_card_spend_month`, `fact_tier_change` | see `docs/05` | commercial value, tier movement |
| `dim_*` | descriptors | join on the `*_key` columns |

All money is **BRL**. Facts are never joined to each other — slice by shared dimensions.

## 2. Read first

1. `docs/01_business_context_kpis.md` — the program, the point economics, the experiment
   design, every KPI definition. **The experiment section (§7) is the spec for the read-out.**
2. `docs/05_data_model.md` §1–2 — bus matrix + fact grains.
3. `docs/06_dax_measures.md` — how each reported metric is calculated.
4. `data/quality/dq_report.md` — what is clean and what is a known limitation.

**The true treatment effect is NOT in the docs.** It lives only in `etl/config.py::FLASH_EFFECT`
and this analysis was written to detect it from the data, not read it off.

## 3. Environment

Python 3.12; `pandas`, `pyarrow`, `duckdb`, `scipy`, `statsmodels`, `matplotlib` installed
(`pip install -r etl/requirements.txt`). Data is static and seeded — fully reproducible.

## 4. The analyses (run order)

| # | Script | Question | Key result |
|---|---|---|---|
| 01 | `01_anchor` | Reproduce the redemption-rate numbers | pooled control 12.8%, treatment 15.5% |
| 02 | `02_srm_balance` | Can the randomisation be trusted? | SRM χ² p = 1.0; max \|SMD\| = 0.04 → yes |
| 03 | `03_primary_effect` | Did Flash Redemption work? | **+2.69 pp** (95% CI [+1.6, +3.8], p ≈ 2e-6); post-stratified **+3.2 pp** |
| 04 | `04_guardrails` | Is it safe? | disengagement −2.0 pp (good); revenue flat but NI **not** established; redemptions **shallower** −R$19/redeemer |
| 05 | `05_novelty` | Does the lift decay? | slope −0.044 pp/wk (p = 0.017); durable ≈ **+1.5 pp** |
| 06 | `06_heterogeneity` | Same for every tier? | interaction LR χ² = 17.0, **p = 0.0007**; Blue +3.8 · Silver +2.2 · Gold/Platinum n.s. |
| 07 | `07_hoarding_and_liability` | How big is the prize / the liability? | 32% of active members ever redeemed; liability R$25.7M gross; card = 55% of issuance |
| 08 | `08_redeemer_retention` | Do redeemers stay? | raw lapse gap −10.5 pp; adjusted −6.0 pp; latent-engagement caveat |

Run everything + parity: `python data_analysis/parity/run_all.py`.
Outputs land in `outputs/tables/` (CSV) and `outputs/figures/` (PNG).

## 5. Folder layout

```
data_analysis/
  00_START_HERE.md   README.md   utils.py
  python/   NN_*.py   — pandas + DuckDB inline, self-checking parity
  sql/      NN_*.sql  — the readable SQL track (DuckDB dialect; .read _prelude.sql first)
  parity/   run_all.py
  findings/ 2026-09_NN_<slug>.md — one per business problem
  outputs/  tables/  figures/
  deliverables/  board_summary.html  ·  deep_dive_00_index.md + deep_dive_NN_*.md
```
