# 08 — Data Quality

Data quality is handled in two places and reported in one.

## Where issues are handled

| Stage | Role |
|---|---|
| **01_generate_raw.py** | *Injects* realistic defects into the raw layer (see the `DQ` block in `config.py` and the table in [`02_data_architecture.md`](02_data_architecture.md#4-data-quality-issues-deliberately-injected)). |
| **02_clean_stage.py** | *Fixes* them — parsing, typing, de-duplication, encoding detection, category standardization, identity resolution, reconciliation — and counts every fix into a Markdown fragment. |
| **dq_checks.py** | *Gates* the curated layer with HARD / SOFT assertions and assembles the full report. |

## The report

`dq_checks.py` writes **[`../data/quality/dq_report.md`](../data/quality/dq_report.md)** on
every run. It contains:

1. **Curated-layer gate** — every structural and business assertion with pass/fail:
   - no null surrogate keys in fact tables;
   - referential integrity for every fact → dimension key (unresolved keys land on the
     `-1` *Unknown* member, never dropped);
   - every fact date present in `dim_date`;
   - accounting identities: `net = gross − discount` per line; order lines roll up to the
     order header; the payment schedule sums back to the order total;
   - invariants: `comparable base = US only`, FX `USD = 1.0`, no non-positive rates;
   - sanity bands: order count, AOV, blended gross margin, share of below-cost lines.
   A **HARD** failure exits non-zero and halts `run_pipeline.py`.

2. **Stage 02 cleaning log** — counts for each fix applied (categories normalized,
   duplicate rows dropped, e-mails missing, encoding detected, PSP rows unmatched,
   snapshot-vs-ledger variance, negative sessions corrected, …).

## Known, accepted limitations

| Item | Why it's acceptable |
|---|---|
| Web analytics only covers market·channel·device cells that had ≥ 1 order that day | Phase 1 uses web data only for the acquisition funnel; a zero-conversion backfill is a Phase 2 task. |
| Inventory is modelled at SKU × market-primary-warehouse grain | Order fulfilment can still split across a market's FCs for carrier analysis; inventory accounting rolls to the primary FC. |
| Affiliate cost is a commission on affiliate-channel orders; attribution is last-touch at channel level | Realistic ad-platform attribution is explicitly out of scope (see `01`, §11). |
| FX uses a synthetic mean-reverting series, not historical rates | The point is to exercise multi-currency modelling, not to reproduce real markets. |
