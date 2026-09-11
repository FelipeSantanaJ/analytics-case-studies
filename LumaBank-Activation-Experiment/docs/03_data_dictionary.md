# LumaBank — Data Dictionary

_Auto-generated from `data/curated/` on 2026-09-11 · SEED=20260910. Do not edit by hand — run `python etl/gen_data_dictionary.py`._

17 curated tables.


## `dim_acquisition_channel`  ·  6 rows

paid_social / organic / app_store_search / referral / influencer / unknown.

| column | dtype | non-null | distinct | example |
|---|---|---|---|---|
| `channel_key` | object | 100.0% | 6 | 1 |
| `channel_name` | object | 100.0% | 6 | paid_social |
| `channel_group` | object | 100.0% | 4 | paid |
| `is_paid` | object | 100.0% | 2 | True |

## `dim_app_release`  ·  144 rows

Mobile + backend releases. is_cache_reset_release flags the 2026-07-16 release; a 2026-07-22 hotfix row follows; -1 = unknown.

| column | dtype | non-null | distinct | example |
|---|---|---|---|---|
| `app_release_key` | object | 100.0% | 144 | -1 |
| `version` | object | 100.0% | 141 | unknown |
| `platform` | object | 100.0% | 3 | unknown |
| `released_at` | object | 99.3% | 122 | 2025-01-01 00:00:00 |
| `released_date_key` | object | 99.3% | 122 | 20250101.0 |
| `rollout_pct` | object | 99.3% | 4 | 90.0 |
| `release_type` | object | 100.0% | 3 | unknown |
| `notes` | object | 100.0% | 9 |  |
| `is_cache_reset_release` | object | 100.0% | 2 | False |

## `dim_date`  ·  1,309 rows

Calendar spine, 2024-06-01 to 2027-12-31. Carries experiment_phase (pre / original / washout / rerun / post), experiment_day, is_post_deploy, and BR holiday / season attributes.

| column | dtype | non-null | distinct | example |
|---|---|---|---|---|
| `date` | object | 100.0% | 1,309 | 2024-06-01 00:00:00 |
| `date_key` | object | 100.0% | 1,309 | 20240601 |
| `year` | object | 100.0% | 4 | 2024 |
| `quarter` | object | 100.0% | 4 | 2 |
| `month` | object | 100.0% | 12 | 6 |
| `month_key` | object | 100.0% | 43 | 202406 |
| `month_name` | object | 100.0% | 43 | Jun 2024 |
| `month_sort` | object | 100.0% | 43 | 24294 |
| `iso_week` | object | 100.0% | 53 | 22 |
| `day_of_week` | object | 100.0% | 7 | 5 |
| `is_month_end` | object | 100.0% | 2 | False |
| `is_weekend` | object | 100.0% | 2 | True |
| `is_school_break` | object | 100.0% | 2 | False |
| `is_holiday_br` | object | 100.0% | 2 | False |
| `season_tag` | object | 100.0% | 4 | Winter |
| `experiment_phase` | object | 100.0% | 6 | out_of_window |
| `is_post_deploy` | object | 100.0% | 2 | False |
| `experiment_day` | object | 3.6% | 28 | 1 |

## `dim_experiment_arm`  ·  3 rows

Slicer helper: control / treatment / ambiguous.

| column | dtype | non-null | distinct | example |
|---|---|---|---|---|
| `arm_key` | object | 100.0% | 3 | control |

## `dim_kyc_outcome`  ·  9 rows

Distinct (outcome, reason_code, reason_group); is_rejection; -1 = none.

| column | dtype | non-null | distinct | example |
|---|---|---|---|---|
| `kyc_outcome_key` | object | 100.0% | 9 | -1 |
| `outcome` | object | 100.0% | 4 | none |
| `reason_code` | object | 100.0% | 7 | none |
| `reason_group` | object | 100.0% | 5 | n/a |
| `is_rejection` | object | 100.0% | 2 | False |

## `dim_onboarding_step`  ·  6 rows

The six funnel steps in order.

| column | dtype | non-null | distinct | example |
|---|---|---|---|---|
| `step_key` | object | 100.0% | 6 | 1 |
| `step_name` | object | 100.0% | 6 | signup_started |
| `step_order` | object | 100.0% | 6 | 1 |
| `funnel_stage` | object | 100.0% | 5 | signup |

## `dim_region`  ·  28 rows

27 UFs + macro region + timezone + utc_offset + is_amazon_tz; -1 = unknown. The axis the post-deploy fallback bias correlates with.

| column | dtype | non-null | distinct | example |
|---|---|---|---|---|
| `region_key` | object | 100.0% | 28 | -1 |
| `uf` | object | 100.0% | 28 | ?? |
| `uf_name` | object | 100.0% | 28 | unknown |
| `macro_region` | object | 100.0% | 6 | unknown |
| `timezone` | object | 100.0% | 9 | America/Sao_Paulo |
| `utc_offset_hours` | object | 100.0% | 3 | -3 |
| `is_amazon_tz` | object | 100.0% | 2 | False |
| `pop_weight` | object | 100.0% | 26 | 0.0 |

## `dim_user`  ·  135,001 rows

One row per signup. Acquisition channel, region, device, app version at signup, and the derived experiment fields: effective arm, cohort (pre_deploy / post_deploy / rerun), contaminated_flag, in_analysis_flag.

| column | dtype | non-null | distinct | example |
|---|---|---|---|---|
| `user_key` | object | 100.0% | 135,001 | 1 |
| `user_id` | object | 100.0% | 135,001 | LB1058661 |
| `signup_date_key` | object | 100.0% | 589 | 20251219 |
| `signup_cohort_week` | object | 100.0% | 93 | 2025-12-15 |
| `channel_key` | object | 100.0% | 7 | 3 |
| `acquisition_channel` | object | 100.0% | 6 | app_store_search |
| `region_key` | object | 100.0% | 28 | 1 |
| `device_os` | object | 100.0% | 3 | Android |
| `app_version_at_signup` | object | 100.0% | 122 | 4.74.0 |
| `age_band` | object | 100.0% | 1 | unknown |
| `birth_year_valid` | object | 100.0% | 1 | False |
| `is_test_account` | object | 100.0% | 1 | False |
| `experiment_arm` | object | 100.0% | 4 | not_in_experiment |
| `experiment_cohort` | object | 100.0% | 5 | not_in_experiment |
| `is_experiment_subject` | object | 100.0% | 2 | False |
| `contaminated_flag` | object | 100.0% | 2 | False |
| `assignment_switch_flag` | object | 100.0% | 2 | False |
| `in_analysis_flag` | object | 100.0% | 2 | False |

## `fact_activation`  ·  135,000 rows

ONE ROW PER SIGNUP, platform-wide (is_experiment_subject flags the randomized ones). Effective arm, cohort, Day-1/7/30 activation, TTFT, and the guardrail flags (kyc_rejected, fraud_flag_30d, onboarding_tickets_n) pre-computed. in_analysis_flag = the clean re-run population.

| column | dtype | non-null | distinct | example |
|---|---|---|---|---|
| `user_key` | object | 100.0% | 135,000 | 1 |
| `user_id` | object | 100.0% | 135,000 | LB1058661 |
| `arm_key` | object | 100.0% | 3 | not_in_experiment |
| `assigned_date_key` | object | 100.0% | 588 | 20251219 |
| `assigned_ts` | object | 100.0% | 112,922 | 2025-12-19 18:27:00 |
| `experiment_cohort` | object | 100.0% | 4 | not_in_experiment |
| `channel_key` | object | 100.0% | 6 | 3 |
| `region_key` | object | 100.0% | 27 | 1 |
| `app_version_at_signup` | object | 100.0% | 121 | 4.74.0 |
| `account_opened_flag` | object | 100.0% | 2 | True |
| `account_opened_ts` | object | 71.6% | 95,975 | 2025-12-20 01:17:07.778368 |
| `first_txn_ts` | object | 50.2% | 67,693 | 2025-12-22 00:27:27.643000 |
| `hours_to_first_txn` | object | 50.2% | 64,331 | 54.008 |
| `day7_activated` | object | 100.0% | 2 | 1 |
| `day1_activated` | object | 100.0% | 2 | 0 |
| `day30_activated` | object | 100.0% | 2 | 1 |
| `kyc_submitted_flag` | object | 100.0% | 2 | True |
| `kyc_rejected_flag` | object | 100.0% | 2 | False |
| `fraud_flag_30d` | object | 100.0% | 2 | False |
| `onboarding_tickets_n` | object | 100.0% | 4 | 0 |
| `is_experiment_subject` | object | 100.0% | 2 | False |
| `contaminated_flag` | object | 100.0% | 2 | False |
| `assignment_switch_flag` | object | 100.0% | 2 | False |
| `in_analysis_flag` | object | 100.0% | 2 | False |

## `fact_fraud_event`  ·  944 rows

One row per fraud signal (flagged_ts in BRT), days_since_activation.

| column | dtype | non-null | distinct | example |
|---|---|---|---|---|
| `user_key` | object | 100.0% | 944 | 131335 |
| `user_id` | object | 100.0% | 944 | LB1000115 |
| `flagged_ts` | object | 100.0% | 944 | 2025-01-15 05:40:02 |
| `flagged_date_key` | object | 100.0% | 495 | 20250115 |
| `signal_type` | object | 100.0% | 4 | synthetic_id |
| `score` | object | 100.0% | 397 | 0.899 |
| `is_confirmed` | object | 100.0% | 2 | True |
| `days_since_activation` | object | 99.2% | 30 | 12.0 |

## `fact_kyc_decision`  ·  107,028 rows

One row per user's final KYC decision, joined to the submission (doc_type, submitted_after_account = the treatment-flow signature).

| column | dtype | non-null | distinct | example |
|---|---|---|---|---|
| `user_key` | object | 100.0% | 105,447 | 76053 |
| `user_id` | object | 100.0% | 107,028 | LB1000002 |
| `kyc_outcome_key` | object | 100.0% | 8 | 1 |
| `submitted_ts` | object | 98.5% | 93,191 | 2025-01-01 11:30:00 |
| `decided_ts` | object | 100.0% | 84,882 | 2025-01-01 00:00:00+00:00 |
| `decision_latency_hours` | object | 98.5% | 48,179 | -11.5 |
| `is_rejection` | object | 100.0% | 2 | False |
| `is_manual_review` | object | 100.0% | 2 | False |
| `doc_type` | object | 98.5% | 2 | rg |
| `submitted_after_account` | object | 98.5% | 2 | False |

## `fact_onboarding_step`  ·  626,520 rows

One row per user x step (first occurrence) with seconds_since_signup.

| column | dtype | non-null | distinct | example |
|---|---|---|---|---|
| `user_key` | object | 100.0% | 135,000 | 71277 |
| `user_id` | object | 100.0% | 135,000 | LB1049278 |
| `step_key` | object | 100.0% | 6 | 3 |
| `step_name` | object | 100.0% | 6 | kyc_upload |
| `occurred_ts` | object | 100.0% | 491,360 | 2025-11-12 21:13:00 |
| `occurred_date_key` | object | 100.0% | 665 | 20251112 |
| `seconds_since_signup` | object | 100.0% | 247,669 | 900.0 |
| `is_reached` | object | 100.0% | 1 | True |

## `fact_srm_daily`  ·  44 rows

ONE ROW PER EXPERIMENT x CALENDAR DAY — the integrity-monitor surface. Daily arm counts, cumulative + trailing-7d chi-square SRM p-values, snapshot-vs-log mismatch count, alert_state. The 2026-07-16 break is here.

| column | dtype | non-null | distinct | example |
|---|---|---|---|---|
| `experiment_phase` | object | 100.0% | 2 | original |
| `assign_date` | object | 100.0% | 44 | 2026-07-06 |
| `assign_date_key` | object | 100.0% | 44 | 20260706 |
| `n_control` | object | 100.0% | 35 | 138 |
| `n_treatment` | object | 100.0% | 35 | 126 |
| `n_fallback` | object | 100.0% | 7 | 0 |
| `n_primary` | object | 100.0% | 41 | 264 |
| `srm_chisq_cumulative` | object | 100.0% | 41 | 0.545 |
| `srm_p_cumulative` | object | 100.0% | 41 | 0.46 |
| `srm_chisq_trailing7` | object | 100.0% | 41 | 0.545 |
| `srm_p_trailing7` | object | 100.0% | 42 | 0.46 |
| `snapshot_log_mismatch_n` | object | 100.0% | 11 | 3 |
| `multi_assignment_n` | object | 100.0% | 11 | 12 |
| `alert_state` | object | 100.0% | 2 | ok |

## `fact_support_ticket`  ·  20,324 rows

One row per ticket; is_onboarding drives the support-cost guardrail.

| column | dtype | non-null | distinct | example |
|---|---|---|---|---|
| `user_key` | object | 100.0% | 17,722 | 54428 |
| `user_id` | object | 100.0% | 17,722 | LB1000003 |
| `opened_ts` | object | 100.0% | 20,324 | 2025-01-01 13:50:32.778499600 |
| `opened_date_key` | object | 100.0% | 656 | 20250101 |
| `category` | object | 100.0% | 5 | onboarding |
| `channel` | object | 100.0% | 3 | email |
| `cidade` | object | 100.0% | 4,333 | Cirino De Goiás |
| `is_onboarding` | object | 100.0% | 2 | True |

## `fact_targets_month`  ·  105 rows

Plan / target values per month per KPI (doc 01 section 15).

| column | dtype | non-null | distinct | example |
|---|---|---|---|---|
| `month_key` | object | 100.0% | 21 | 202501 |
| `kpi` | object | 100.0% | 5 | day7_activation_rate |
| `target_value` | object | 100.0% | 45 | 0.44 |

## `fact_transaction_day`  ·  2,002,414 rows

User x local day: transaction count, BRL, per-type counts, is_first_txn_day.

| column | dtype | non-null | distinct | example |
|---|---|---|---|---|
| `user_key` | object | 100.0% | 67,705 | 89499 |
| `user_id` | object | 100.0% | 67,705 | LB1004300 |
| `date_key` | object | 100.0% | 638 | 20250203 |
| `txn_count` | object | 100.0% | 8 | 1 |
| `txn_amount_brl` | object | 100.0% | 110,781 | 65.67 |
| `pix_count` | object | 100.0% | 7 | 1 |
| `card_count` | object | 100.0% | 6 | 0 |
| `boleto_count` | object | 100.0% | 5 | 0 |
| `transfer_count` | object | 100.0% | 6 | 0 |
| `is_first_txn_day` | object | 100.0% | 2 | True |

## `fact_variant_assignment`  ·  13,709 rows

One row per assignment EVENT (contaminated users have >=2). assignment_source (primary / fallback), cache_reset_flag, is_first_assignment, is_effective_assignment (the auditable rule).

| column | dtype | non-null | distinct | example |
|---|---|---|---|---|
| `user_key` | object | 100.0% | 13,577 | 46613 |
| `user_id` | object | 100.0% | 13,577 | LB1108431 |
| `arm_key` | object | 100.0% | 2 | control |
| `assigned_ts_brt` | object | 100.0% | 10,657 | 2026-07-06 03:09:00 |
| `assigned_date_key` | object | 100.0% | 41 | 20260706 |
| `assignment_seq` | object | 100.0% | 2 | 1 |
| `assignment_source` | object | 100.0% | 2 | primary |
| `cache_reset_flag` | object | 100.0% | 2 | False |
| `app_release_key` | object | 100.0% | 14 | 113 |
| `is_first_assignment` | object | 100.0% | 2 | True |
| `is_effective_assignment` | object | 100.0% | 2 | True |