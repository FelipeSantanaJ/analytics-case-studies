# LumaBank — Data Quality Report

_Generated 2026-09-11T02:54:30.413256Z · SEED=20260910_

## Assertion results

- **0 hard failures**, 1 warnings

- warn cumulative SRM p also crosses 0.001 at some point (min p = 0.0295)

## Per-entity counters

### `curated__dim_acquisition_channel`

- rows: 6

### `curated__dim_app_release`

- rows: 144

### `curated__dim_date`

- rows: 1309

### `curated__dim_experiment_arm`

- rows: 3

### `curated__dim_kyc_outcome`

- rows: 9

### `curated__dim_onboarding_step`

- rows: 6

### `curated__dim_region`

- rows: 28

### `curated__dim_user`

- rows: 135001

### `curated__fact_activation`

- rows: 135000

### `curated__fact_fraud_event`

- rows: 944

### `curated__fact_kyc_decision`

- rows: 107028

### `curated__fact_onboarding_step`

- rows: 626520

### `curated__fact_srm_daily`

- rows: 44

### `curated__fact_support_ticket`

- rows: 20324

### `curated__fact_targets_month`

- rows: 105

### `curated__fact_transaction_day`

- rows: 2002414

### `curated__fact_variant_assignment`

- rows: 13709

### `stg_beacon_app_releases`

- epochs_or_serials_converted: 143
- dates_parsed: 143
- dates_unparseable: 0
- platform_normalised: 143
- platform_unknowns: 0
- rows_in: 143
- rows_out: 143

### `stg_beacon_deploy_changelog`

- dates_parsed: 363
- dates_unparseable: 0
- rows_in: 363
- rows_out: 363

### `stg_flagfox_exposure_log`

- dupe_exposure_dropped: 2209
- rows_in: 29824
- rows_out: 27615

### `stg_flagfox_variant_assignments`

- timestamps_localized: 13709
- multi_assignment_users: 132
- rows_in: 13709
- rows_out: 13709

### `stg_flagfox_variant_snapshot`

- snapshot_rows_collapsed: 0
- rows_in: 10727
- rows_out: 10727

### `stg_lumencore_account_status_events`

- dupe_events_dropped: 1909
- dates_parsed: 190861
- dates_unparseable: 0
- rows_in: 192770
- rows_out: 190861

### `stg_lumencore_accounts`

- dates_parsed: 96630
- dates_unparseable: 0
- rows_in: 97016
- rows_out: 96630

### `stg_lumencore_transactions`

- dupe_txn_dropped: 245009
- epochs_or_serials_converted: 2624926
- dates_parsed: 2624926
- dates_unparseable: 0
- txn_type_normalised: 2624926
- txn_type_unknowns: 0
- money_strings_parsed: 157479
- rows_in: 2869935
- rows_out: 2624926

### `stg_lumencore_users`

- snapshot_rows_collapsed: 1310293
- mojibake_repaired: 16227
- dates_parsed: 96630
- dates_unparseable: 0
- rows_in: 1445293
- rows_out: 135000

### `stg_orbita_acquisition`

- channel_normalised: 127406
- channel_unknowns: 0
- dates_parsed: 127406
- dates_unparseable: 0
- rows_in: 127406
- rows_out: 127406

### `stg_orbita_support_tickets`

- dupe_tickets_dropped: 203
- mojibake_repaired: 2408
- category_normalised: 20324
- category_unknowns: 0
- dates_parsed: 20324
- dates_unparseable: 0
- rows_in: 20527
- rows_out: 20324

### `stg_riskguard_fraud_signals`

- epochs_or_serials_converted: 944
- dates_parsed: 944
- dates_unparseable: 0
- rows_in: 944
- rows_out: 944

### `stg_riskguard_kyc_decisions`

- decisions_date_only: 21405
- rows_in: 107028
- rows_out: 107028

### `stg_riskguard_kyc_reason_codes`

- rows_in: 11
- rows_out: 11

### `stg_trilha_kyc_submissions`

- dates_parsed: 105446
- dates_unparseable: 0
- rows_in: 105446
- rows_out: 105446

### `stg_trilha_onboarding_steps`

- step_normalised: 657846
- step_unknowns: 0
- dates_parsed: 657846
- dates_unparseable: 0
- dupe_steps_dropped: 31326
- rows_in: 657846
- rows_out: 626520
