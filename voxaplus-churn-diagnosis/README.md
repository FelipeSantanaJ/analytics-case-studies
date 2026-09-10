# Voxa+ — Subscriber Churn Diagnosis

A data & BI portfolio project. **Voxa+** is a fictional SVOD (subscription video-on-demand)
streaming service operating in Brazil, Mexico, and the United States. Monthly subscriber
churn nearly doubled starting in month 34 of a 36-month window and has stayed elevated.
Leadership needs a data-driven root-cause diagnosis before the next board meeting.

This repository simulates the full analytics stack end to end: messy source exports, a
medallion ETL pipeline, a Kimball star schema, a code-generated Power BI semantic model and
report, and a dual-track (SQL + Python) root-cause investigation.

> All data is synthetic and generated from a single random seed. Any resemblance to real
> companies or people is coincidental.

## Scope (locked in Phase 0)

| | |
|---|---|
| Deliverable language | English |
| Data window | 36 months; churn shift begins month 34 |
| Markets / currencies | Brazil / BRL (home, month 1) · Mexico / MXN (month 10) · United States / USD (month 16) |
| Reporting currency | USD default, with a currency slicer (BRL / MXN / USD) |
| Data scale | ~120k cumulative subscribers, ~70k active at window end; viewing at subscriber-day grain |
| North Star | Paid Active Subscribers · watch metric: Gross Monthly Churn % |
| Depth | Balanced (data engineering + analysis) |
| PBI environment | `.pbip` / PBIR, generated from code |

## Report pages (Phase 1)

1. Executive Summary — how bad is the spike, is it still going
2. Subscriber Retention & Cohorts — which cohorts / segments are driving it
3. Content & Engagement — did viewing behavior drop before cancellation
4. Pricing & Plans — did a price / plan change trigger it
5. Acquisition Quality & Channels — did subscriber quality shift
6. Customer Experience, Billing & App Quality — payment failures / app issues
7. Market Context — global or concentrated in one market

## The diagnosis

The near-doubling of churn is **three overlapping factors**, none sufficient alone:

1. an **app "v3" connected-TV playback regression** (the acute trigger — CTV-heavy churn
   4.1% → 8.4% while the rest went 4.1% → 5.6%);
2. the **Brazil price increase**, which did nothing to engaged subscribers and **+18 pp**
   to already-disengaged ones (the amplifier, Brazil-only);
3. a **months-old Mexico cohort-quality drag** (newer Mexican cohorts retain ~8 pp worse
   at month 3 — the pre-existing drain).

Payments were tested and ruled out. Deliverables (built by
[`data_analysis/deliverables/build_deliverables.py`](data_analysis/deliverables/build_deliverables.py)):
board read — [`board_summary.pdf`](data_analysis/deliverables/board_summary.pdf) /
[`.html`](data_analysis/deliverables/board_summary.html) · full write-up with all ten
findings — [`deep_dive.pdf`](data_analysis/deliverables/deep_dive.pdf) /
[`.html`](data_analysis/deliverables/deep_dive.html)
(source: [`deep_dive_00_index.md`](data_analysis/deliverables/deep_dive_00_index.md)).

## Repository layout

```
docs/            01–09 docs · 06_dax_measures & 03_data_dictionary auto-generated ·
                 walkthrough.md (build log) ·
                 build_docs_pdf.py → Voxa+_Documentation.pdf / Voxa+_Summary.pdf
etl/             config.py (one SEED) · gen/ world+content+economics · 01_generate_raw ·
                 02_clean_stage · 03_build_curated · dq_checks · run_pipeline ·
                 pbi_measures.py (113 DAX measures) · gen_data_dictionary / gen_dax_doc
data/            raw / staging / curated (Parquet + CSV mirror for compact tables) / quality
powerbi/         gen_semantic_model.py → VoxaChurnDiagnosis.SemanticModel (TMDL) ·
                 gen_report_visuals.py + _drive_pbir.py + build_report.sh → 7-page report ·
                 theme/theme.json · assets/ (brand PNGs)
assets/          brand.py (palette) · gen_logo.py (mark, wordmark, page backgrounds)
data_analysis/   run_analysis.py (10 questions × SQL + pandas, parity-checked) ·
                 sql/ · results/ · parity/ · findings/F01–F10 · deliverables/
portfolio/       gallery/ (diagram + screenshot sources)
```

## Reproduce

```
python -m pip install -r etl/requirements.txt
python etl/run_pipeline.py                 # raw → staging → curated → dq_checks (~28 min)
cd powerbi && bash build_report.sh         # semantic model + 7-page report (Desktop closed)
python data_analysis/run_analysis.py       # the dual-track diagnosis
python docs/build_docs_pdf.py              # the documentation PDFs
```

## Status

Phases 0–13 complete — pipeline, semantic model, report, dual-track diagnosis and
deliverables all build clean. Build log in [`docs/walkthrough.md`](docs/walkthrough.md).
