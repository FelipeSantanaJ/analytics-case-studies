# Voxa+ — Data Quality Report

_Generated 2026-09-02 09:28 · SEED=20260902 · POP_SCALE=1.0_

## Injected & handled

| Fragment | Metric | Count |
|---|---|---:|
| curated_build | billing_period_detected_annual | 1,104 |
| curated_build | orphan_event_rows_sentinel | 1,025 |
| curated_build | null_or_orphan_billing_rows_sentinel | 8,003 |
| curated_build | orphan_content_rows_sentinel | 101,533 |
| curated_build | test_campaign_rows_excluded | 0 |
| raw_injection | excel_serial_date_cells | 47 |
| raw_injection | money_string_cells | 1,173,363 |
| raw_injection | overlapping_invoice_rows | 32,248 |
| raw_injection | snapshot_drift_rows | 14,652 |
| raw_injection | snapshot_dump_extra_rows | 2,442,218 |
| raw_injection | gross_net_mislabeled_rows | 478,434 |
| raw_injection | negative_refund_rows | 11,546 |
| raw_injection | null_account_id_rows | 3,424 |
| raw_injection | gdpr_deleted_omitted | 465 |
| raw_injection | bom_files | 1 |
| raw_injection | crm_missing_early_rows | 1,409 |
| raw_injection | mojibake_name_rows | 114,784 |
| raw_injection | dupe_entitlement_rows | 4,771 |
| raw_injection | reelbase_encoding_rows | 3,500 |
| raw_injection | reelbase_mixed_date_rows | 3,500 |
| raw_injection | contentfin_parens_negative_cells | 18,581 |
| raw_injection | mxn_in_usd_column_rows | 648 |
| raw_injection | clicks_are_impressions_rows | 336 |
| raw_injection | ssp_duplicate_day_rows | 26 |
| raw_injection | support_cutover_dupe_rows | 164 |
| raw_injection | fx_missing_month_rows | 4 |
| raw_injection | negative_watch_rows | 33,569 |
| raw_injection | orphan_content_rows | 101,533 |
| raw_injection | cdn_mb_rows | 6,736,491 |
| raw_injection | dupe_playlog_rows | 303,064 |
| raw_injection | dupe_app_rows | 303,064 |
| raw_injection | watchtime_ms_era_rows | 12,954,757 |
| stg_fixes | excel_serials_converted | 125,638 |
| stg_fixes | dates_parsed | 140,024 |
| stg_fixes | money_negatives_from_parens | 10,190 |
| stg_fixes | money_strings_parsed | 1,161,624 |
| stg_fixes | category_unknowns | 0 |
| stg_fixes | categories_normalised | 1,766,151 |
| stg_fixes | dupe_invoice_lines_dropped | 32,310 |
| stg_fixes | snapshot_rows_collapsed | 2,442,218 |
| stg_fixes | timestamps_localized | 1,141,115 |
| stg_fixes | null_keys_flagged | 3,424 |
| stg_fixes | bom_stripped | 1 |
| stg_fixes | dupe_events_dropped | 623,966 |
| stg_fixes | mojibake_repaired | 117,061 |
| stg_fixes | implausible_birth_year_nulled | 132 |
| stg_fixes | missing_genre_rows | 140 |
| stg_fixes | mislabeled_columns_corrected | 984 |
| stg_fixes | support_rows_v1 | 5,344 |
| stg_fixes | support_rows_v2 | 74,036 |
| stg_fixes | csat_rescaled | 79,380 |
| stg_fixes | cutover_dupes_dropped | 165 |
| stg_fixes | fx_months_forward_filled | 4 |
| stg_fixes | watchtime_unit_fixed | 12,954,788 |
| stg_fixes | sign_errors_fixed | 33,569 |
| stg_fixes | bytes_unit_fixed | 6,736,491 |

## Hard checks

| Check | Result | Detail |
|---|---|---|
| no null subscriber_key in fact_subscription_month | PASS |  |
| fact_subscription_event subscriber_key resolves or sentinel(0) | PASS |  |
| subscriber base roll-forward identity (<=2% monthly) | PASS | worst 0.00% |
| retention curve <= 100% and non-increasing | PASS | M1=89% M6=74% M12=64% |
| fact_viewing_daily.device_key in dim_device | PASS |  |
| dim_date spans beyond fact window | PASS |  |

## Soft checks (plausibility & calibration)

| Check | Result | Detail |
|---|---|---|
| billing rows with unresolved subscriber (<= 1.2%, injected null+orphan keys) | ok | 0.70% |
| MRR positive and monotone-ish | ok |  |
| pre-shift blended gross churn in [3.6%,4.6%] | ok | 4.108% |
| peak (idx33-35) blended gross churn in [6.4%,8.6%] | ok | 6.816% |
| peak/pre ratio ~1.6-2.1 | ok | 1.66x |
| avg streamed hours / sub-month in 25-70h band (pre-shift) | ok | 47.6h |
| share below healthy engagement 8-28% (pre-shift) | ok | 11.1% |
| finance subscription revenue ~ curated MRR (<=15% mean rel) | ok | 4.0% |

## Churn-spike shape (blended gross monthly churn %)

| window-month | idx | gross churn % |
|---:|---:|---:|
| 23 | 22 | 3.86 |
| 24 | 23 | 3.83 |
| 25 | 24 | 3.90 |
| 26 | 25 | 3.82 |
| 27 | 26 | 4.03 |
| 28 | 27 | 4.19 |
| 29 | 28 | 4.20 |
| 30 | 29 | 4.13 |
| 31 | 30 | 4.01 |
| 32 | 31 | 4.20 |
| 33 | 32 | 4.50 |
| 34 | 33 | 6.85 |
| 35 | 34 | 6.58 |
| 36 | 35 | 7.02 |

Pre-shift mean (idx 24-32): **4.11%** · peak mean (idx 33-35): **6.82%** · ratio **1.66x**

## Cohort retention (cohorts m6-18)

| age (months) | retention |
|---:|---:|
| M0 | 93.3% |
| M1 | 88.6% |
| M2 | 84.3% |
| M3 | 81.2% |
| M4 | 78.5% |
| M5 | 76.2% |
| M6 | 74.0% |
| M7 | 72.2% |
| M8 | 70.6% |
| M9 | 68.9% |
| M10 | 67.3% |
| M11 | 65.8% |
| M12 | 64.4% |

## Accepted limitations

- Acquisition channel is attributed at subscriber level by sampling each market's monthly channel mix (the AdBridge attribution feed carries no account key).
- Billing amounts are taken from the plan-price schedule, not the gateway `amount` column (Q06 mislabel worked around).
- The last window month is flagged `is_partial_period` (partner settlement lag).
- Snapshot-vs-ledger drift is measured, not corrected: the curated snapshot is folded from the movement ledger by construction.