# Voxa+ — Churn Diagnosis Analysis

**The question.** Gross monthly subscriber churn nearly doubled at window-month 34
(Jun 2026) and has stayed elevated. Leadership needs one evidence-backed root-cause
diagnosis before the board meeting.

**The method.** Every analytical question is answered **twice** — once in **SQL**
(DuckDB over the curated Parquet) and once in **Python** (pandas over the same files) —
and the two results are asserted equal within tolerance. This is a guard against a single
buggy query becoming a "finding".

```
python data_analysis/run_analysis.py          # runs all 10 questions, both tracks
                                              #   -> results/*.csv, parity/parity_report.md
```

Reads only `../data/curated/`. Nothing here writes back to the pipeline.

## Layout

| Path | What |
|---|---|
| `run_analysis.py` | orchestrates the 10 questions; each has a SQL string and a pandas function; `parity()` compares them |
| `lib/io.py` | DuckDB connection with views over the curated Parquet; pandas loaders |
| `lib/parity.py` | `assert_parity(sql_df, py_df, key)` — aligns, rounds, diffs, records pass/fail |
| `sql/` | the SQL for each question, also written out standalone for review |
| `results/qNN_*.csv` | the agreed result table for each question |
| `parity/parity_report.md` | every question's SQL-vs-Python parity check |
| `findings/FNN_*.md` | one note per business problem: context · question · hypothesis · both-track method · evidence · conclusion · limitations · recommendation |
| `deliverables/board_summary.html` | short, decision-first |
| `deliverables/deep_dive_00_index.md` + `deep_dive_NN_*.md` | the full write-up, one section per problem |

## The ten questions

| # | Question | Finding |
|---|---|---|
| Q1 | How large is the spike, and is it still going? | `F01` |
| Q2 | Is it global or concentrated in one market? | `F02` |
| Q3 | Which cohorts, tenures, plans and channels are churning? | `F03` |
| Q4 | Did viewing behaviour drop *before* people cancelled? | `F04` |
| Q5 | Is there a device / app-quality signal? | `F05` |
| Q6 | Did the Brazil price change trigger it? | `F06` |
| Q7 | Did the quality of acquisition shift (and where)? | `F07` |
| Q8 | Payment failures and involuntary churn | `F08` |
| Q9 | Financial and LTV impact of the elevated churn | `F09` |
| Q10 | **Synthesis** — decompose the excess churn into contributing factors | `F10` |

## Conventions

- **Window months** are 0-indexed (`month_idx`): `0` = Sep 2023 … `35` = Aug 2026.
  The shift begins at `month_idx = 33` (window-month 34, Jun 2026).
- **Pre-shift baseline** = `month_idx` 24–32. **Peak** = `month_idx` 33–35.
- **Gross monthly churn** = churned paid subs in the month ÷ paid subs active at the
  start of the month, averaged across the months in scope.
- **Comparable Base** = Brazil (the only full-window market). **Expansion** = MX + US.
- All money in USD (curated `*_usd` columns).
- `fact_viewing_daily` (13.5 M rows) is used here for the device-level cuts that the
  semantic model leaves out.
