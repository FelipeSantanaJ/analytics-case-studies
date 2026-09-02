# AeroVanti SkyPoints — Data Quality Report

_Generated 2026-09-02T18:25:29.039614Z · SEED=20260902_

## Assertion results

- **0 hard failures**, 0 warnings


## Per-entity counters

### `curated__dim_date`

- rows: 1461

### `curated__dim_earn_source`

- rows: 9

### `curated__dim_experiment_arm`

- rows: 3

### `curated__dim_experiment_stratum`

- rows: 4

### `curated__dim_member`

- rows: 120000

### `curated__dim_reward_type`

- rows: 10

### `curated__dim_route`

- rows: 290

### `curated__dim_tier`

- rows: 4

### `curated__fact_card_spend_month`

- rows: 670216

### `curated__fact_experiment_assignment`

- dropped_ineligible: 30
- n_assigned: 15000
- rows: 15000

### `curated__fact_experiment_member_week`

- rows: 180000

### `curated__fact_experiment_outcome`

- rows: 15000

### `curated__fact_flight_segment`

- rows: 672320

### `curated__fact_liability_month`

- rows: 24

### `curated__fact_member_month`

- rows: 1897349

### `curated__fact_point_transaction`

- rows: 1593188

### `curated__fact_targets_month`

- rows: 120

### `curated__fact_tier_change`

- rows: 46476

### `curated__liability_tie_out`

- mean_rel_error_points_issued: 0.0
- months: 24

### `curated__tier_snapshot_drift`

- member_months_compared: 1897349
- drift_member_months: 54876
- drift_rate: 0.0289

### `stg_aurora_campaign_membership`

- dates_parsed: 86489
- dates_unparseable: 0
- dupe_membership_dropped: 0
- rows_in: 86489
- rows_out: 86489

### `stg_aurora_crm_contacts`

- mojibake_repaired: 28170
- categories_normalised: 78286
- categories_unknowns: 0
- dates_parsed: 77129
- dates_unparseable: 1157
- birthyear_invalidated: 2360
- rows_in: 78286
- rows_out: 78286

### `stg_bancoav_card_accounts`

- mojibake_repaired: 29059
- dates_parsed: 48318
- dates_unparseable: 0
- null_member_id: 1437
- rows_in: 48318
- rows_out: 48318

### `stg_bancoav_card_spend`

- excel_serials_converted: 715773
- dates_parsed: 715773
- dates_unparseable: 0
- dupe_month_rows_dropped: 25154
- money_strings_parsed: 690619
- money_negatives_from_parens: 0
- money_null_from_blank: 0
- rows_in: 715773
- rows_out: 690619

### `stg_flesk_ab_assignments`

- timestamps_localized: 15030
- rows_in: 15030
- rows_out: 15030

### `stg_flesk_exposure_log`

- dupe_exposure_dropped: 1198
- rows_in: 16172
- rows_out: 14974

### `stg_flesk_outcome`

- rows_in: 15000
- rows_out: 15000

### `stg_flesk_redemption_week`

- rows_in: 180000
- rows_out: 180000

### `stg_ledger_liability_rollforward`

- excel_serials_converted: 26
- dates_parsed: 26
- dates_unparseable: 0
- restated_months_resolved: 2
- money_strings_parsed: 48
- money_negatives_from_parens: 0
- money_null_from_blank: 0
- rows_in: 26
- rows_out: 24

### `stg_ledger_reward_cost`

- excel_serials_converted: 96
- dates_parsed: 96
- dates_unparseable: 0
- money_strings_parsed: 96
- money_negatives_from_parens: 0
- money_null_from_blank: 0
- rows_in: 96
- rows_out: 96

### `stg_reserva_bookings`

- dupe_bookings_dropped: 0
- dates_parsed: 1240890
- dates_unparseable: 0
- categories_normalised: 710595
- categories_unknowns: 0
- nonmember_bookings: 180300
- rows_in: 710595
- rows_out: 710595

### `stg_reserva_segments`

- dupe_segments_dropped: 10085
- dates_parsed: 672320
- dates_unparseable: 0
- taxes_imputed: 308154
- rows_in: 682405
- rows_out: 672320

### `stg_skycore_members`

- snapshot_rows_collapsed: 369984
- dates_parsed: 1897349
- dates_unparseable: 0
- points_strings_parsed: 0
- points_unparseable: 0
- rows_in: 2267333
- rows_out: 1897349

### `stg_skycore_point_transactions`

- dupe_txn_dropped: 168027
- categories_normalised: 1593188
- categories_unknowns: 0
- dates_parsed: 1593188
- dates_unparseable: 0
- points_strings_parsed: 25970
- points_unparseable: 0
- money_strings_parsed: 57067
- money_negatives_from_parens: 0
- money_null_from_blank: 1536121
- points_sign_fixed: 0
- rows_in: 1761215
- rows_out: 1593188

### `stg_skycore_reward_catalog`

- excel_serials_converted: 9
- dates_parsed: 9
- dates_unparseable: 0
- points_strings_parsed: 9
- points_unparseable: 0
- rows_in: 9
- rows_out: 9

### `stg_skycore_tier_change_events`

- dupe_events_dropped: 465
- dates_parsed: 46476
- dates_unparseable: 0
- rows_in: 46941
- rows_out: 46476

### `stg_skycore_tier_snapshots`

- rows_in: 1897349
- rows_out: 1897349
