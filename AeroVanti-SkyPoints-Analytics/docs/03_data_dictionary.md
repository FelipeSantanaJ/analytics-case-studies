# AeroVanti SkyPoints — Data Dictionary

_Auto-generated from `data/curated/` on 2026-09-02 · SEED=20260902. Do not edit by hand — run `python etl/gen_data_dictionary.py`._

18 curated tables.


## `dim_date`  ·  1,461 rows

Calendar spine, 2024-01-01 to 2027-12-31. Carries the experiment phase/week tags and BR holiday / season attributes.

| column | dtype | non-null | distinct | example |
|---|---|---|---|---|
| `date` | object | 100.0% | 1,461 | 2024-01-01 00:00:00 |
| `date_key` | object | 100.0% | 1,461 | 20240101 |
| `year` | object | 100.0% | 4 | 2024 |
| `quarter` | object | 100.0% | 4 | 1 |
| `month` | object | 100.0% | 12 | 1 |
| `month_key` | object | 100.0% | 48 | 202401 |
| `month_name` | object | 100.0% | 48 | Jan 2024 |
| `month_sort` | object | 100.0% | 48 | 24289 |
| `iso_week` | object | 100.0% | 53 | 1 |
| `day_of_week` | object | 100.0% | 7 | 0 |
| `is_month_end` | object | 100.0% | 2 | False |
| `is_school_break` | object | 100.0% | 2 | False |
| `is_holiday_br` | object | 100.0% | 2 | False |
| `season_tag` | object | 100.0% | 4 | Summer peak |
| `experiment_phase` | object | 100.0% | 4 | out_of_window |
| `experiment_week` | object | 5.7% | 12 | 1 |

## `dim_earn_source`  ·  9 rows

SkyPoints issuance sources; -1 = unknown.

| column | dtype | non-null | distinct | example |
|---|---|---|---|---|
| `earn_source_key` | object | 100.0% | 9 | -1 |
| `source_name` | object | 100.0% | 9 | unknown |
| `source_group` | object | 100.0% | 4 | other |
| `earns_tier_points` | object | 100.0% | 2 | False |

## `dim_experiment_arm`  ·  3 rows

Slicer helper: control / treatment / not_enrolled.

| column | dtype | non-null | distinct | example |
|---|---|---|---|---|
| `arm_key` | object | 100.0% | 3 | control |

## `dim_experiment_stratum`  ·  4 rows

Slicer helper: the tier strata used for randomisation.

| column | dtype | non-null | distinct | example |
|---|---|---|---|---|
| `stratum` | object | 100.0% | 4 | Blue |

## `dim_member`  ·  120,000 rows

One row per SkyPoints member. Enrolment attributes + current ledger-derived tier + experiment arm/stratum.

| column | dtype | non-null | distinct | example |
|---|---|---|---|---|
| `member_key` | object | 100.0% | 120,000 | 1 |
| `member_id` | object | 100.0% | 120,000 | SKP100000 |
| `enrollment_date_key` | object | 100.0% | 648 | 20250714 |
| `enrollment_cohort_month` | object | 100.0% | 24 | 2025-07 |
| `enrollment_channel` | object | 100.0% | 4 | card |
| `home_city` | object | 100.0% | 21 | Vitória |
| `home_region` | object | 100.0% | 5 | Sudeste |
| `has_cobrand_card` | object | 100.0% | 2 | True |
| `current_tier_key` | object | 100.0% | 4 | 1 |
| `current_tier_name` | object | 100.0% | 4 | Blue |
| `crm_present` | object | 100.0% | 2 | True |
| `crm_lifecycle_stage` | object | 100.0% | 5 | engaged |
| `age_band` | object | 63.3% | 5 | 35-44 |
| `is_steady_state_cohort` | object | 100.0% | 2 | False |
| `is_test_account` | object | 100.0% | 1 | False |
| `experiment_arm` | object | 100.0% | 3 | not_enrolled |
| `experiment_stratum` | object | 100.0% | 5 | n/a |
| `is_experiment_subject` | object | 100.0% | 2 | False |

## `dim_reward_type`  ·  10 rows

Redemption catalogue; is_low_cost_catalog flags the Flash additions; -1 = unknown.

| column | dtype | non-null | distinct | example |
|---|---|---|---|---|
| `reward_type_key` | object | 100.0% | 10 | -1 |
| `reward_name` | object | 100.0% | 10 | unknown |
| `reward_category` | object | 100.0% | 7 | unknown |
| `points_price` | object | 90.0% | 9 | 8000.0 |
| `value_per_point_brl` | object | 90.0% | 9 | 0.024 |
| `is_low_cost_catalog` | object | 100.0% | 2 | False |
| `available_from_date_key` | object | 90.0% | 2 | 20240901.0 |
| `available_from` | object | 90.0% | 2 | 2024-09-01 00:00:00 |

## `dim_route`  ·  290 rows

Distinct flown routes with a haul band; -1 = unknown.

| column | dtype | non-null | distinct | example |
|---|---|---|---|---|
| `route_key` | object | 100.0% | 290 | -1 |
| `origin` | object | 100.0% | 18 | ? |
| `dest` | object | 100.0% | 18 | ? |
| `haul_band` | object | 100.0% | 3 | unknown |
| `region_pair` | object | 100.0% | 290 | ? |

## `dim_tier`  ·  4 rows

The four tiers (Blue/Silver/Gold/Platinum) with earn multipliers and thresholds.

| column | dtype | non-null | distinct | example |
|---|---|---|---|---|
| `tier_key` | object | 100.0% | 4 | 1 |
| `tier_name` | object | 100.0% | 4 | Blue |
| `tier_rank` | object | 100.0% | 4 | 1 |
| `earn_multiplier` | object | 100.0% | 4 | 1.0 |
| `tp_threshold` | object | 100.0% | 4 | 0 |
| `segment_threshold` | object | 100.0% | 4 | 0 |
| `is_elite` | object | 100.0% | 2 | False |

## `fact_card_spend_month`  ·  670,216 rows

Member x month co-brand card spend and card SkyPoints earned.

| column | dtype | non-null | distinct | example |
|---|---|---|---|---|
| `member_key` | object | 100.0% | 46,881 | 1 |
| `month_key` | object | 100.0% | 24 | 202507 |
| `card_spend_brl` | object | 100.0% | 281,654 | 1780.85 |
| `skypoints_earned` | object | 100.0% | 4,469 | 712 |
| `is_card_active` | object | 100.0% | 1 | True |

## `fact_experiment_assignment`  ·  15,000 rows

One row per assigned subject (eligible only; late corrections reconciled out). Frozen pre-period covariates.

| column | dtype | non-null | distinct | example |
|---|---|---|---|---|
| `member_key` | object | 100.0% | 15,000 | 16 |
| `member_id` | object | 100.0% | 15,000 | SKP100015 |
| `arm_key` | object | 100.0% | 2 | treatment |
| `stratum` | object | 100.0% | 4 | Gold |
| `assigned_ts` | object | 100.0% | 13,749 | 2026-03-01 09:21:14+00:00 |
| `pre_earn_12m_pts` | object | 100.0% | 10,408 | 35061 |
| `pre_flights_12m` | object | 100.0% | 71 | 20 |
| `pre_redemptions_12m` | object | 100.0% | 8 | 0 |
| `pre_balance_pts` | object | 100.0% | 11,078 | 36260 |
| `prior_redeemer_flag` | object | 100.0% | 2 | False |
| `pre_tenure_months` | object | 100.0% | 18 | 14 |

## `fact_experiment_member_week`  ·  180,000 rows

Assigned subject x experiment week — the weekly redemption series for the novelty diagnostic.

| column | dtype | non-null | distinct | example |
|---|---|---|---|---|
| `member_key` | object | 100.0% | 15,000 | 16 |
| `member_id` | object | 100.0% | 15,000 | SKP100015 |
| `arm_key` | object | 100.0% | 2 | treatment |
| `stratum` | object | 100.0% | 4 | Gold |
| `week` | object | 100.0% | 12 | 1 |
| `redeemed_w` | object | 100.0% | 2 | False |
| `redemptions_w` | object | 100.0% | 2 | 0 |
| `points_redeemed_w` | object | 100.0% | 534 | 0 |
| `redemption_value_brl_w` | object | 100.0% | 571 | 0.0 |
| `low_cost_only_w` | object | 100.0% | 2 | False |

## `fact_experiment_outcome`  ·  15,000 rows

One row per subject with the full window + post-window outcomes: primary metric, guardrails, diagnostics.

| column | dtype | non-null | distinct | example |
|---|---|---|---|---|
| `member_key` | object | 100.0% | 15,000 | 16 |
| `member_id` | object | 100.0% | 15,000 | SKP100015 |
| `arm_key` | object | 100.0% | 2 | treatment |
| `stratum` | object | 100.0% | 4 | Gold |
| `redeemed_in_window` | object | 100.0% | 2 | False |
| `redemptions_in_window` | object | 100.0% | 4 | 0 |
| `redemption_value_brl` | object | 100.0% | 688 | 0.0 |
| `points_redeemed_in_window` | object | 100.0% | 588 | 0 |
| `low_cost_only` | object | 100.0% | 2 | False |
| `revenue_brl_window_plus8w` | object | 100.0% | 9,329 | 4890.93 |
| `liability_drawdown_brl` | object | 100.0% | 588 | 0.0 |
| `reward_cash_cost_brl` | object | 100.0% | 566 | 0.0 |
| `net_liability_cost_brl` | object | 100.0% | 633 | 0.0 |
| `disengaged_90d_post` | object | 100.0% | 2 | False |
| `earn_in_window` | object | 100.0% | 2 | True |
| `flights_in_window` | object | 100.0% | 24 | 8 |
| `active_post_quarter` | object | 100.0% | 2 | True |

## `fact_flight_segment`  ·  672,320 rows

One flown segment. member_key -1 = non-member booking, -2 = orphan. skypoints_earned recomputed with the month's tier multiplier.

| column | dtype | non-null | distinct | example |
|---|---|---|---|---|
| `member_key` | object | 100.0% | 89,251 | 16657 |
| `loyalty_member_id` | object | 100.0% | 101,543 | SKP116656 |
| `flight_date_key` | object | 100.0% | 672 | 20250513 |
| `month_key` | object | 100.0% | 24 | 202505 |
| `route_key` | object | 100.0% | 289 | 1 |
| `fare_family` | object | 100.0% | 3 | PROMO |
| `base_fare_brl` | object | 91.5% | 96,536 | 802.48 |
| `taxes_brl` | object | 100.0% | 36,027 | 224.69 |
| `booking_channel` | object | 100.0% | 5 | web |
| `is_award_redemption` | object | 100.0% | 2 | False |
| `points_redeemed` | object | 8.5% | 4,612 | 11100 |
| `skypoints_earned` | object | 100.0% | 3,821 | 1605 |
| `tier_points_earned` | object | 100.0% | 2,274 | 902 |

## `fact_liability_month`  ·  24 rows

Monthly point-liability roll-forward from the transaction ledger, with the finance sub-ledger figures alongside for tie-out.

| column | dtype | non-null | distinct | example |
|---|---|---|---|---|
| `month_key` | object | 100.0% | 24 | 202409 |
| `points_issued_m` | object | 100.0% | 24 | 257562484 |
| `points_expired_m` | object | 100.0% | 8 | 0 |
| `points_redeemed_m` | object | 100.0% | 24 | 5066662 |
| `adjust` | object | 100.0% | 1 | 0 |
| `points_outstanding_eop` | object | 100.0% | 24 | 252495822 |
| `liability_brl_gross` | object | 100.0% | 24 | 5302412.26 |
| `liability_brl_breakage_adj` | object | 100.0% | 24 | 3181447.36 |
| `points_issued_m_ledger` | object | 100.0% | 24 | 257562484 |
| `points_redeemed_m_ledger` | object | 100.0% | 24 | 5066662 |
| `points_expired_m_ledger` | object | 100.0% | 8 | 0 |
| `breakage_provision_brl` | object | 100.0% | 24 | 2120964.9 |
| `reward_cash_cost_brl` | object | 100.0% | 24 | 42559.96 |

## `fact_member_month`  ·  1,897,349 rows

Member x month panel — the retention / program-health workhorse. balance, earn/burn/expiry, tier, activity, and lapse (null until the 12-month rule is evaluable).

| column | dtype | non-null | distinct | example |
|---|---|---|---|---|
| `member_key` | object | 100.0% | 120,000 | 1 |
| `member_id` | object | 100.0% | 120,000 | SKP100000 |
| `month_key` | object | 100.0% | 24 | 202507 |
| `ym` | object | 100.0% | 24 | 2025-07 |
| `tier_key` | object | 100.0% | 4 | 1 |
| `experiment_arm` | object | 100.0% | 3 | not_enrolled |
| `points_earned_m` | object | 100.0% | 20,457 | 16243 |
| `points_redeemed_m` | object | 100.0% | 4,687 | 0 |
| `points_expired_m` | object | 100.0% | 735 | 0 |
| `redemptions_m` | object | 100.0% | 2 | 0.0 |
| `balance_pts_eom` | object | 100.0% | 63,231 | 16243 |
| `has_redeemed_ever_eom` | object | 100.0% | 2 | False |
| `flights_m` | object | 100.0% | 23 | 0 |
| `flight_revenue_brl_m` | object | 100.0% | 147,521 | 0.0 |
| `card_spend_brl_m` | object | 100.0% | 281,655 | 1780.85 |
| `tenure_months` | object | 100.0% | 24 | 0 |
| `is_new_enrollment` | object | 100.0% | 2 | True |
| `months_since_last_activity` | object | 100.0% | 25 | 0 |
| `is_active_eom` | object | 100.0% | 2 | True |
| `is_lapsed_eom` | object | 35.2% | 2 | 0.0 |
| `became_lapsed_this_month` | object | 100.0% | 2 | False |
| `is_reactivation` | object | 100.0% | 2 | False |

## `fact_point_transaction`  ·  1,593,188 rows

One SkyPoints ledger entry (earn / redeem / expire / adjust). Signed points; points_value_brl in BRL; earn_month_key on earn rows.

| column | dtype | non-null | distinct | example |
|---|---|---|---|---|
| `member_key` | object | 100.0% | 111,624 | 86972 |
| `member_id` | object | 100.0% | 111,624 | SKP186971 |
| `txn_date_key` | object | 100.0% | 672 | 20241003 |
| `month_key` | object | 100.0% | 24 | 202410 |
| `txn_type` | object | 100.0% | 3 | earn |
| `earn_source_key` | object | 94.7% | 8 | 5.0 |
| `reward_type_key` | object | 3.6% | 4 | 3.0 |
| `points` | object | 100.0% | 15,709 | 127 |
| `points_value_brl` | object | 100.0% | 14,653 | 2.67 |
| `earn_month_key` | object | 94.7% | 24 | 202410 |
| `txn_id` | object | 100.0% | 1,593,188 | PTX001340948 |

## `fact_targets_month`  ·  120 rows

Plan / target values per month per KPI (doc 01 section 12).

| column | dtype | non-null | distinct | example |
|---|---|---|---|---|
| `month_key` | object | 100.0% | 24 | 202409 |
| `kpi` | object | 100.0% | 5 | active_members |
| `target_value` | object | 100.0% | 120 | 45000.0 |

## `fact_tier_change`  ·  46,476 rows

Tier-change events (the movement source of truth).

| column | dtype | non-null | distinct | example |
|---|---|---|---|---|
| `member_key` | object | 100.0% | 42,117 | 159 |
| `member_id` | object | 100.0% | 42,117 | SKP100158 |
| `change_date_key` | object | 100.0% | 120 | 20240901 |
| `change_month_key` | object | 100.0% | 24 | 202409 |
| `from_tier` | object | 100.0% | 4 | Blue |
| `to_tier` | object | 100.0% | 4 | Gold |
| `from_tier_key` | object | 100.0% | 4 | 1 |
| `to_tier_key` | object | 100.0% | 4 | 3 |
| `direction` | object | 100.0% | 2 | upgrade |
| `trigger` | object | 100.0% | 2 | qualification |