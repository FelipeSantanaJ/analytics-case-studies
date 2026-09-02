# AeroVanti SkyPoints — Data Quality

**Document status:** Phase 4 deliverable. Where each injected issue is handled, what the
generated `data/quality/dq_report.md` contains, and the accepted limitations.

The pipeline **injects** realistic source defects in `01_generate_raw.py`, **handles** them
in `02_clean_stage.py` / `03_build_curated.py` with a counter for every fix, and **asserts**
the invariants in `dq_checks.py` (non-zero exit on any hard failure).

---

## 1. The six primary issue classes

| # | Issue | Injected in | Handled in | Hard assertion |
|---|---|---|---|---|
| Q01 | Multiple date formats + Excel serials | SkyCore `member_since`, BancoAV, Reserva (`MM/DD/YYYY`), Ledger, reward catalog | `parse_dates(hint)` — per-source locale rule + Excel-serial epoch 1899-12-30 | `dates_unparseable = 0` on the key columns |
| Q02 | Money as locale strings / parenthesis negatives / symbol-in-value | BancoAV `card_spend`, Ledger `.xlsx`, some SkyCore `value_brl` | `parse_money_brl` — strips `R$`, `.`-thousands / `,`-decimal, `(x)`→`-x`, blank→null | no non-null money column is object dtype; `liability_brl_gross ≥ 0` |
| Q03 | Encoding damage (Latin-1 mojibake, BOM) | BancoAV names/city, Aurora `cidade` | `ftfy.fix_text` + BOM strip | no `Ã`/`Â` mojibake sequences remain in `dim_member.home_city` |
| Q04 | Duplicate rows (daily full-dump snapshot, overlapping monthly `point_transactions`, re-delivered BancoAV month, at-least-once event/exposure rows) | SkyCore, BancoAV, Flesk | collapse to one row per member per month · dedupe on `txn_id` · drop re-delivered file on `(card_id, month)` · dedupe events/exposures | `fact_point_transaction.txn_id` unique · `fact_flight_segment.segment_id` unique |
| Q05 | Missing master rows / orphan keys (bookings → members absent from SkyCore, point rows for unknown members, months-1–3 cohorts with no CRM row) | Reserva, SkyCore, Aurora late go-live | sentinel keys (`-1` non-member, `-2` orphan) + count; CRM attributes left null with `crm_present` flag | every fact FK resolves to a real or sentinel key |
| Q06 | Snapshot-vs-ledger drift (`tier_snapshots_monthly` disagrees with `tier_change_events`) | SkyCore | curated tier status folded forward from the **event ledger** (incl. an initial Blue→status qualification event); snapshot used only to measure drift | curated tier status == ledger-derived **by construction**; drift rate reported (target 3–6%) |

### Also handled, without ceremony
Null / placeholder keys → sentinels · invalid birth years (`1900-01-01`, `0`) → null +
`birth_year_valid = false` · Flesk UTC timestamps → tz-aware, Brazil-local calendar day for
`*_date_key` · ledger restated months → last occurrence wins · free-text `txn_type` /
lifecycle stage / booking channel / tier labels → controlled vocab in `etl/vocab/`.

---

## 2. Accounting identities asserted (`dq_checks.py`)

- **Points roll-forward** (program-wide, per month): opening + earned − redeemed − expired
  = closing, exact. Program balance == Σ member balance.
- **Liability tie-out**: the transaction-ledger roll-up matches the finance sub-ledger's
  issued / redeemed / expired within tolerance.
- **Lapse honesty**: `is_lapsed_eom` is null (never `False`) for tenure < 12 months; a
  lapsed member stays lapsed until a reactivation row.
- **Experiment integrity**: exactly 15,000 assigned subjects; every weekly / outcome row is
  an assigned subject; 50/50 allocation within every stratum; `redeemed_in_window` == OR of
  the 12 weekly flags; data extends ≥ 90 days past the experiment end.
- **Benchmark bands** on the pre-experiment steady-state cohort: quarterly redemption rate,
  ever-redeemed share, burn/earn ratio and the Blue share of active members all land inside
  their doc-01 §11 ranges.

---

## 3. Generated report

`data/quality/dq_report.md` (built by `dq_checks.py`) contains:

1. the pass/fail list for every assertion above;
2. a per-entity counter block from the `data/quality/dq_fragments/*.json` files — e.g. how
   many Excel serials were converted, mojibake strings repaired, duplicate transactions
   dropped, snapshot rows collapsed, orphan keys sentinelled, restated months resolved.

_(latest run summary is pasted in §5 once the final pipeline lands.)_

---

## 4. Accepted limitations

- **No per-lot FIFO attribution in curated.** The point-lot engine consumes lots FIFO, but
  `fact_point_transaction` only carries `earn_month_key` on **earn** rows. Cohort breakage
  in Phase 10 is computed as an aggregate roll-forward (issued vs redeemed vs expired by
  calendar month) plus a legacy-vs-window split, not a full per-lot ledger. This was a
  deliberate simplification under the Phase-0 "reduced ETL" decision.
- **90-day lapse proxy only.** The experiment sits in months 19–21 and the data ends at
  month 24, so the guardrail uses a 90-day post-window disengagement proxy, not a true
  12-month lapse outcome.
- **Synthetic data.** All members, flights, card spend, earn and redemption events are
  seed-generated. Benchmark ranges are directional, from public airline-loyalty
  disclosures, and are used only to set targets.
- **Contamination not modelled.** Household / referral spillover between experiment arms is
  assumed negligible.
