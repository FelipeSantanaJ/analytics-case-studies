# Voxa+ — Data Quality

**Document status:** Phase 4 deliverable.
**Generated companion:** `data/quality/dq_report.md` (rebuilt every pipeline run by
`etl/dq_checks.py`), fed by `data/quality/dq_fragments/*.json`.

Every issue in the Phase-2 catalogue (Q01–Q15) is **injected** by `01_generate_raw.py`,
**handled** in staging or curated, **counted** into a DQ fragment, and — where it is an
invariant — **asserted** by `dq_checks.py`. Counts below are from the shipped full-scale run
(`SEED=20260902`, `POP_SCALE=1.0`).

---

## 1. Issue → handling → evidence

| # | Issue | Injected (count) | Handled in | Handling | Asserted |
|---|---|--:|---|---|---|
| Q01 | Multiple date formats + Excel serials | 47 serial cells + all date columns | `02` `parse_date_series` | per-style `to_datetime`; serial = `EXCEL_EPOCH + days`; 125,638 serials converted, 140,024 text dates parsed | `dates_unparseable = 0` |
| Q02 | Money as locale strings, parentheses negatives | 1,173,363 cells | `02` `parse_money_series` | decimal separator decided per row; `(x)` → −x (10,190); 1,161,624 parsed | no money column left as object dtype |
| Q03 | Encoding damage (Latin-1 mojibake, BOM) | 114,784 names + 3,500 titles + 1 BOM | `02` `ftfy.fix_text`, `utf-8-sig`, Latin-1 read | 117,061 strings repaired, BOM stripped | no `Ã/Â` runs in `dim_content.title` |
| Q04 | Duplicate rows (events, invoices, daily full-dump) | 4,771 + 303,064 + 303,064 events; 32,248 invoice; 2,442,218 snapshot copies | `02` `drop_duplicates`; per-file snapshot collapse | 623,966 dup events dropped; 32,310 invoice lines; 2,442,218 snapshot rows collapsed | `fact_subscription_event` unique on `event_id`; invoices unique on `invoice_id` |
| Q05 | Master rows missing (orphan subscriber / content) | 465 GDPR-deleted + 101,533 orphan content | `03` sentinel keys `-1`/`0` + count | 1,025 event rows, 8,003 billing rows, 101,533 viewing rows → sentinel | every fact FK resolves (real or sentinel); no null surrogate keys |
| Q06 | Mislabelled columns (`clicks`=impressions; `spend_usd`=MXN; `amount` gross/net) | 336 + 648 + 478,434 | `02` column correction; `03` re-derive amount | partner `clicks`→null, MX spend restored to MXN + USD recomputed (984 corrected); billing amount taken from the plan-price schedule | marketing `clicks ≤ impressions` |
| Q07 | Snapshot-vs-ledger drift | 14,652 drift rows | `03` snapshot folded **from** the ledger | Ketch snapshot used only to measure drift; curated status = ledger status by construction | base roll-forward identity holds (worst 0.00 % monthly) |
| Q08 | Sign errors (negative refunds, negative watch, negative recovery) | 11,546 + 33,569 | `02` sign normalisation | refunds stored with consistent sign; 33,569 negative watch rows → abs + flagged | `fact_viewing_daily.streamed_minutes ≥ 0` |
| Q09 | Unit inconsistency (watch s→ms, CDN MB/GB, CSAT /5 /10) | 12,954,757 + 6,736,491 + 79,380 | `02` unit normalisation | ms era + magnitude → seconds; edge-b bytes ÷1024; CSAT rescaled to 0–1 | watch minutes/sub-day ≤ 1440; `csat_score ∈ [0,1]` |
| Q10 | Categorical noise (channel/plan/market/device free text) | ~1.77 M values touched | `02` `norm_series` + `etl/vocab/*.csv` | 1,766,151 values normalised; **0** fell through to `unknown` this run | all `dim_*` category columns ∈ controlled vocab |
| Q11 | Schema break (Helpline v1 → Helpdesk v2) | 5,344 v1 + 74,036 v2; 164 cutover dupes | `02` schema unification + crosswalk | one `stg_support_tickets` schema + one taxonomy; 165 cutover dupes dropped | `fact_support_ticket` single schema; taxonomy ∈ `dim_support_reason` |
| Q12 | Late / partial / restating files | 4 FX months missing; last month partial | `02` FX forward-fill; `dim_date.is_partial_period` | 4 FX months filled; window-month 36 flagged partial | last-month completeness flagged, not silently averaged |
| Q13 | Null keys (guest billing rows, retired plan) | 3,424 null `account_id` | `02` flag; `03` sentinel | 3,424 flagged; billing rows with unresolved subscriber = 0.70 % | soft check ≤ 1.2 % |
| Q14 | Outliers (test campaign, 30h+/day, annual as one line) | test-campaign flag; annual invoices | `03` quarantine / explode / caps | annual plans explode to 12 monthly recognitions; test campaign excluded from `fact_marketing_spend` | marketing KPIs exclude the quarantined campaign |
| Q15 | Timezone / month-boundary bleed | UTC events vs local billing | `02` local-day derivation per market | `local_date` from tz-converted timestamp; `month_idx` from the local day | monthly viewing totals reconcile to daily within tolerance |

---

## 2. Hard checks (fail the build)

From the latest run — **6/6 PASS**:

| Check | Result |
|---|---|
| No null subscriber_key in `fact_subscription_month` | PASS |
| `fact_subscription_event` subscriber_key resolves or sentinel | PASS |
| Subscriber base roll-forward identity `start + new + reactivation − churn = end` (≤ 2 %/month) | PASS — worst 0.00 % |
| Cohort retention ≤ 100 % and non-increasing | PASS — M1 89 % / M6 74 % / M12 64 % |
| `fact_viewing_daily.device_key ⊆ dim_device` | PASS |
| `dim_date` spans beyond the fact window | PASS |

## 3. Soft checks (plausibility & calibration — warn only)

From the latest run — **0 warnings**:

| Check | Value | Band |
|---|---|---|
| Billing rows with unresolved subscriber | 0.70 % | ≤ 1.2 % |
| Pre-shift blended gross monthly churn (idx 24–32) | 4.11 % | 3.6–4.6 % |
| Peak blended gross churn (idx 33–35) | 6.82 % | 6.4–8.6 % |
| Peak / pre ratio | 1.66× | 1.6–2.1× |
| Avg streamed hours / sub-month (pre-shift) | 47.6 h | 25–70 h |
| Share below healthy engagement (pre-shift) | 11.1 % | 8–28 % |
| GL subscription revenue vs curated MRR (mean rel. error) | 4.0 % | ≤ 15 % |

The full churn-spike shape and cohort-retention curve are tabulated in
`data/quality/dq_report.md`.

---

## 4. Accepted limitations

These are known and left in on purpose; the report and the Phase-10 analysis annotate them.

1. **Acquisition channel is a sampled attribute.** The AdBridge attribution feed carries no
   account key, so each subscriber's `acquisition_channel` is drawn from their market's
   monthly channel mix. Channel-level retention and quality trends are directionally sound
   but not row-exact; conclusions about acquisition quality are stated as cohort-level, not
   individual-level.
2. **Billing amount is taken from the plan-price schedule**, not the gateway `amount`
   column (Q06 mislabel). Revenue and payment-cost figures are therefore schedule-accurate;
   the gateway's reported amount is kept as `amount_reported` for audit only.
3. **The last window month is partial.** `dim_date.is_partial_period` flags window-month 36;
   partner settlement and some carrier-billing rows lag by a month. Trend visuals should
   exclude or annotate it.
4. **Snapshot-vs-ledger drift is measured, not corrected.** `fact_subscription_month` is
   folded from the movement ledger; the 14,652 drifting Ketch snapshot rows are reported as
   a DQ metric, not reconciled.
5. **`fact_finance_month` is a modelled roll-up**, not a general ledger. It ties to
   operational MRR within ~4 % and is adequate for margin trend and the CFO page, not for
   statutory reporting.
6. **M12 cohort retention (~64 %) sits a little above the `docs/01` benchmark band
   (38–55 %).** The simulated base carries a ~15–19 % annual-plan mix (locked in) and
   counts win-backs as re-activations, both of which lift 12-month logo retention. The
   Phase-10 analysis uses first-spell-only retention where a stricter figure is needed.
7. **Gross margin is thin and ramps.** Content amortisation is ~90 %+ of revenue early in
   the window on a small base and settles near ~55 % by window-end (26 % gross margin at
   window-month 34) — a deliberate scaling-company trajectory, slightly below the
   `docs/01` steady-state band.
8. **No external / competitor data.** The "Market Context" page compares Voxa+'s own three
   markets, not the competitive market.
