# Voxa+ — Data Dictionary (curated layer)

_Auto-generated from `data/curated/` on 2026-09-02 by `etl/gen_data_dictionary.py`. Do not edit by hand._

All monetary columns are stored `*_local` (transaction currency) and `*_usd` (month-average FX). Surrogate keys are `*_key` (integer); business keys keep their source form as `*_id`. Sentinel keys: `-1` unknown, `0` unresolved.

---
### `dim_app_version`

*one row per observed app version string* · **15 rows**

| column | dtype | sample values |
|---|---|---|
| `app_version_key` | int64 | 1, 2, 3 |
| `app_version` | str | 2.0.4, 2.1.4, 2.2.4 |
| `major` | int64 | 2, 3 |
| `is_v3` | bool | False, True |
| `device_class_hint` | str | all |


### `dim_channel`

*one row per acquisition channel* · **7 rows**

| column | dtype | sample values |
|---|---|---|
| `channel_key` | int64 | 1, 2, 3 |
| `channel` | str | direct, organic, paid_search |
| `channel_group` | str | owned, performance, partner |
| `is_low_quality` | bool | False, True |


### `dim_content`

*one row per catalogue title* · **3,500 rows**

| column | dtype | sample values |
|---|---|---|
| `content_key` | int64 | 1, 2, 3 |
| `content_id` | str | T50000, T50001, T50002 |
| `title` | str | Días de Sol 2, Marea Alta, Maré 5 |
| `content_type` | str | series, movie |
| `primary_genre` | str | Comedy, Crime, Unknown |
| `language` | str | es, pt, en |
| `is_original` | bool | False, True |
| `runtime_min` | int64 | 501, 124, 390 |
| `release_date_key` | int64 | 20231201, 20220101, 20220501 |


### `dim_date`

*one row per calendar day* · **1,826 rows**

| column | dtype | sample values |
|---|---|---|
| `date` | datetime64[ms] | 2023-01-01 00:00:00, 2023-01-02 00:00:00, 2023-01-03 00:00:00 |
| `date_key` | int32 | 20230101, 20230102, 20230103 |
| `year` | int32 | 2023, 2024, 2025 |
| `quarter` | int32 | 1, 2, 3 |
| `month_num` | int32 | 1, 2, 3 |
| `month_name` | str | Jan, Feb, Mar |
| `year_month` | str | 2023-01, 2023-02, 2023-03 |
| `month_sort` | int32 | 202301, 202302, 202303 |
| `abs_month` | int32 | 24277, 24278, 24279 |
| `day_of_month` | int32 | 1, 2, 3 |
| `is_month_end` | bool | False, True |
| `iso_week` | int64 | 52, 1, 2 |
| `window_month_idx` | int32 | -8, -7, -6 |
| `in_analysis_window` | bool | False, True |
| `is_holiday_br` | bool | False, True |
| `is_holiday_mx` | bool | False, True |
| `is_holiday_us` | bool | False, True |
| `season_tag` | str | year_end_peak, carnaval, regular |
| `is_partial_period` | bool | False, True |


### `dim_device`

*one row per device family* · **7 rows**

| column | dtype | sample values |
|---|---|---|
| `device_key` | int64 | 1, 2, 3 |
| `device_family` | str | mobile_ios, mobile_android, web |
| `device_class` | str | mobile, web, ctv |
| `is_ctv` | bool | False, True |


### `dim_market`

*one row per market* · **3 rows**

| column | dtype | sample values |
|---|---|---|
| `market_key` | int64 | 1, 2, 3 |
| `market_id` | str | BR, MX, US |
| `currency_code` | str | BRL, MXN, USD |
| `market_active_from_date_key` | int64 | 20230901, 20240601, 20241201 |
| `timezone` | str | America/Sao_Paulo, America/Mexico_City, America/New_York |
| `is_comparable_base` | bool | True, False |


### `dim_payment_method`

*one row per payment method* · **5 rows**

| column | dtype | sample values |
|---|---|---|
| `method_key` | int64 | 1, 2, 3 |
| `method` | str | card, pix, boleto |
| `is_prepaid` | bool | False, True |
| `settlement_lag_days_typical` | int64 | 2, 0, 3 |


### `dim_plan`

*one row per tier x billing period x market* · **18 rows**

| column | dtype | sample values |
|---|---|---|
| `plan_key` | int64 | 1, 2, 3 |
| `plan_id` | str | Basico-monthly-BR, Basico-monthly-MX, Basico-monthly-US |
| `tier` | str | Basico, Standard, Premium |
| `billing_period` | str | monthly, annual |
| `market_id` | str | BR, MX, US |
| `market_key` | int64 | 1, 2, 3 |
| `has_ads` | bool | True, False |
| `max_streams` | int64 | 1, 2, 4 |
| `max_resolution` | str | 1080p, 4K |
| `has_downloads` | bool | False, True |


### `dim_price_history`

*one row per tier x market x price-effective period* · **11 rows**

| column | dtype | sample values |
|---|---|---|
| `price_key` | int64 | 1, 2, 3 |
| `tier` | str | Basico, Standard, Premium |
| `market_id` | str | BR, MX, US |
| `effective_from_date_key` | int64 | 20230901, 20260301 |
| `effective_to_date_key` | int64 | 20271231, 20260300 |
| `list_price_local` | float64 | 18.9, 89.0, 6.99 |


### `dim_subscriber`

*one row per subscriber (account with >=1 paid start)* · **115,728 rows**

| column | dtype | sample values |
|---|---|---|
| `subscriber_key` | int64 | 1, 2, 3 |
| `subscriber_id` | str | S1000000, S1000001, S1000002 |
| `market` | str | BR, MX, US |
| `market_key` | int64 | 1, 2, 3 |
| `cohort_month` | str | 2025-12, 2024-03, 2026-02 |
| `first_paid_month_idx` | int64 | 27, 6, 29 |
| `signup_date_key` | int64 | 20251220, 20240321, 20260223 |
| `acquisition_channel` | str | partner_bundle, paid_social, direct |
| `channel_key` | int64 | 6, 4, 1 |
| `first_tier` | str | Standard, Premium, Basico |
| `current_tier` | str | Standard, Premium, Basico |
| `billing_period` | str | monthly, annual |
| `primary_device_family` | str | smart_tv, mobile_ios, streaming_stick |
| `crm_lifecycle_stage` | str | new, power_user, engaged |
| `is_incentivised` | bool | False, True |
| `is_comparable_base` | bool | True, False |
| `is_l4l_cohort` | bool | False, True |


### `dim_support_reason`

*one row per unified support reason category* · **6 rows**

| column | dtype | sample values |
|---|---|---|
| `support_reason_key` | int64 | 1, 2, 3 |
| `reason_category` | str | billing_payment, app_playback, app_crash |
| `reason_group` | str | billing, app_tech, account |


### `fact_ad_revenue`

*one row per market x day* · **2,557 rows**

| column | dtype | sample values |
|---|---|---|
| `date_key` | int64 | 20230901, 20230902, 20230903 |
| `month_idx` | int64 | 0, 1, 2 |
| `market` | str | BR, MX, US |
| `market_key` | int64 | 1, 2, 3 |
| `impressions_served` | int64 | 1123, 1388, 1319 |
| `fill_rate` | float64 | 0.867, 0.765, 0.865 |
| `ecpm_usd` | float64 | 11.31, 8.58, 8.95 |
| `ad_revenue_usd` | float64 | 12.71, 11.91, 11.82 |


### `fact_app_performance_daily`

*one row per market x date x device family x app version* · **15,342 rows**

| column | dtype | sample values |
|---|---|---|
| `market` | str | BR, MX, US |
| `local_date` | datetime64[us] | 2023-09-01 00:00:00, 2023-09-02 00:00:00, 2023-09-03 00:00:00 |
| `device_family` | str | console, mobile_android, mobile_ios |
| `device_key` | int64 | 6, 2, 1 |
| `app_version` | str | 2.0.4, 2.1.4, 2.2.4 |
| `month_idx` | int64 | 0, 1, 2 |
| `sessions` | int64 | 48, 265, 168 |
| `crashes` | int64 | 0, 1, 2 |
| `screen_views` | int64 | 316, 1739, 1095 |
| `crash_free_rate` | float64 | 1.0, 0.9962264150943396, 0.9940476190476191 |
| `date_key` | int64 | 20230901, 20230902, 20230903 |


### `fact_billing_attempt`

*one row per billing attempt* · **1,141,115 rows**

| column | dtype | sample values |
|---|---|---|
| `txn_id` | str | pg_204913177311, pg_243834280277, pg_200064501858 |
| `subscriber_key` | int64 | 24, 246, 272 |
| `market` | str | BR, MX, US |
| `month_idx` | int32 | 0, 1, 2 |
| `date_key` | int64 | 20230930, 20231031, 20231130 |
| `attempt_ts_utc` | datetime64[us, UTC] | 2023-09-21 00:00:00+00:00, 2023-09-11 00:00:00+00:00, 2023-09-17 00:00:00+00:00 |
| `method` | str | carrier_billing, card, pix |
| `method_key` | int64 | 5, 1, 2 |
| `status` | str | approved, failed, refunded |
| `type` | str | charge, refund, retry |
| `attempt_number` | int64 | 1, 2, 3 |
| `is_dunning` | bool | False, True |
| `failure_reason` | str | , not_paid, expired |
| `amount_local` | float64 | 26.46, 18.9, 39.04 |
| `amount_usd` | float64 | 5.3411, 3.8151, 7.8805 |
| `processing_cost_local` | float64 | 2.3814, 1.16734, 0.9481 |
| `processing_cost_usd` | float64 | 0.4807, 0.2356, 0.1914 |


### `fact_content_cost`

*one row per title x month* · **123,876 rows**

| column | dtype | sample values |
|---|---|---|
| `content_key` | int64 | 1, 2, 3 |
| `month_idx` | int32 | 0, 1, 2 |
| `amort_usd` | float64 | 0.0, 319.37, 83.72 |
| `cash_spend_usd` | float64 | 0.0, 11178.02, 1925.01 |
| `date_key` | int64 | 20230930, 20231031, 20231130 |


### `fact_engagement_device_month`

*one row per record* · **504 rows**

| column | dtype | sample values |
|---|---|---|
| `market` | str | BR, MX, US |
| `device_family` | str | console, mobile_android, mobile_ios |
| `device_key` | int64 | 6, 2, 1 |
| `month_idx` | int64 | 0, 1, 2 |
| `streamed_hours` | float64 | 1538.8311666666666, 3819.2058055555553, 6926.048250000001 |
| `play_starts` | int64 | 2229, 5600, 10100 |
| `video_start_failures` | int64 | 36, 60, 109 |
| `playback_errors` | int64 | 12, 25, 63 |
| `rebuffer_ratio` | float64 | 0.011813559322033897, 0.011583167495854063, 0.011925649350649352 |
| `cdn_gb` | float64 | 5527.191487304687, 13725.237560546875, 24991.49345410156 |
| `viewing_subs` | int64 | 197, 492, 807 |
| `market_key` | int64 | 1, 2, 3 |
| `vsf_rate` | float64 | 0.01615, 0.01071, 0.01079 |
| `playback_error_rate` | float64 | 0.00538, 0.00446, 0.00624 |
| `date_key` | int64 | 20230930, 20231031, 20231130 |


### `fact_engagement_month`

*one row per subscriber x month with streaming activity* · **1,146,571 rows**

| column | dtype | sample values |
|---|---|---|
| `subscriber_key` | int64 | -1, 24, 246 |
| `account_ref` | str | S1031759, S1037109, S1068598 |
| `month_idx` | int64 | 0, 1, 2 |
| `streamed_hours` | float64 | 74.15, 30.589999999999996, 104.0 |
| `active_days` | int64 | 19, 9, 18 |
| `distinct_titles` | int64 | 56, 33, 69 |
| `playback_errors` | int64 | 1, 0, 2 |
| `video_start_failures` | int64 | 0, 2, 3 |
| `ctv_days` | float64 | 12.0, 13.0, 14.0 |
| `pct_days_ctv` | float64 | 0.632, 1.333, 0.667 |
| `below_healthy_engagement` | bool | False, True |
| `date_key` | int64 | 20230930, 20231031, 20231130 |


### `fact_finance_month`

*one row per month x market x P&L line* · **780 rows**

| column | dtype | sample values |
|---|---|---|
| `month_idx` | int64 | 0, 1, 2 |
| `market` | str | BR, MX, US |
| `pnl_line` | str | subscription_revenue, advertising_revenue, partner_revenue |
| `amount_usd` | float64 | 2722.6, 353.73, 122.52 |
| `market_key` | int64 | 1, 2, 3 |
| `date_key` | int64 | 20230930, 20231031, 20231130 |


### `fact_fx_rate`

*one row per month x currency* · **108 rows**

| column | dtype | sample values |
|---|---|---|
| `month_idx` | int64 | 0, 1, 2 |
| `currency` | str | BRL, MXN, USD |
| `avg_rate` | float64 | 4.954, 4.8952, 4.9136 |
| `eop_rate` | float64 | 4.9761, 4.9183, 4.9177 |
| `date_key` | int64 | 20230930, 20231031, 20231130 |


### `fact_marketing_spend`

*one row per week x market x channel x campaign* · **2,016 rows**

| column | dtype | sample values |
|---|---|---|
| `week_date_key` | int64 | 20230901, 20230908, 20230915 |
| `month_idx` | int64 | 0, 1, 2 |
| `market` | str | BR, MX, US |
| `market_key` | int64 | 1, 2, 3 |
| `channel` | str | affiliate, direct, organic |
| `channel_key` | int64 | 5, 1, 2 |
| `campaign_id` | str | cmp_BR_affiliate_2023Q3, cmp_BR_direct_2023Q3, cmp_BR_organic_2023Q3 |
| `spend_usd` | float64 | 264.01, 245.15, 226.3 |
| `spend_local` | float64 | 264.01, 245.15, 226.3 |
| `impressions` | int64 | 66003, 61288, 56574 |
| `clicks` | float64 | 543.0, 504.0, 465.0 |
| `signups_attributed` | int64 | 16, 25, 23 |


### `fact_subscription_event`

*one row per subscription lifecycle event (movement ledger)* · **265,110 rows**

| column | dtype | sample values |
|---|---|---|
| `event_id` | str | ent_874752370545, ent_663015193664, ent_667510900029 |
| `subscriber_key` | int64 | 1, 2, 3 |
| `subject` | str | S1000000, S1000001, S1000002 |
| `event_type` | str | paid_start, churn, cancel_request |
| `event_ts_utc` | datetime64[us, UTC] | 2025-12-27 00:00:00+00:00, 2026-04-06 00:00:00+00:00, 2026-04-23 00:00:00+00:00 |
| `event_date_key` | int64 | 20251227, 20260406, 20260423 |
| `month_idx` | int32 | 27, 31, 6 |
| `from_tier` | str | Premium, Standard, Basico |
| `to_tier` | str | Standard, Premium, Basico |
| `reason_code` | str | voluntary, too_expensive, temporary_break |


### `fact_subscription_month`

*one row per subscriber x month while subscribed (folded from the ledger)* · **1,216,330 rows**

| column | dtype | sample values |
|---|---|---|
| `subscriber_key` | int64 | 1, 2, 3 |
| `subscriber_id` | str | S1000000, S1000001, S1000002 |
| `month_idx` | int64 | 27, 28, 29 |
| `status` | str | active, churned |
| `tier` | str | Standard, Premium, Basico |
| `billing_period` | str | monthly, annual |
| `market` | str | BR, MX, US |
| `mrr_local` | float64 | 26.46, 29.9, 0.0 |
| `tenure_months` | int64 | 0, 1, 2 |
| `is_new` | bool | True, False |
| `is_reactivation` | bool | False, True |
| `is_voluntary_churn` | bool | False, True |
| `is_involuntary_churn` | bool | False, True |
| `mrr_usd` | float64 | 4.9495, 4.9367, 5.5673 |
| `date_key` | int64 | 20251231, 20260131, 20260228 |


### `fact_support_ticket`

*one row per support ticket* · **79,215 rows**

| column | dtype | sample values |
|---|---|---|
| `ticket_id` | str | v1-0-741029, v1-0-70719851, v1-0-50785554 |
| `subscriber_key` | int64 | 31794, 8220, 7874 |
| `market` | str | BR, MX, US |
| `month_idx` | int32 | 0, 1, 2 |
| `created_date_key` | int64 | 20230918, 20230916, 20230927 |
| `contact_channel` | str | chat, phone, email |
| `reason_category` | str | account_access, app_playback, billing_payment |
| `reason_group` | str | account, app_tech, billing |
| `support_reason_key` | int64 | 4, 2, 1 |
| `csat_score` | float64 | 1.0, 0.72, 0.38 |
| `resolution_hours` | float64 | 12.76, 10.72, 0.8 |
| `source_version` | str | v1, v2 |


### `fact_targets_month`

*one row per market x month x KPI* · **432 rows**

| column | dtype | sample values |
|---|---|---|
| `market` | str | BR, MX, US |
| `market_key` | int64 | 1, 2, 3 |
| `month_idx` | int64 | 0, 1, 2 |
| `kpi` | str | paid_active_subscribers, mrr_usd, gross_monthly_churn_pct |
| `target_value` | float64 | 545.0, 2949.29, 4.0 |
| `date_key` | int64 | 20230930, 20231031, 20231130 |


### `fact_viewing_daily`

*one row per subscriber x local date x device family (partitioned by month)* · **13,485,904 rows** (across 36 monthly parts)

| column | dtype | sample values |
|---|---|---|
| `subscriber_key` | int64 | -1, 24, 246 |
| `account_ref` | str | S1031759, S1037109, S1068598 |
| `local_date` | datetime64[us] | 2023-09-01 00:00:00, 2023-09-02 00:00:00, 2023-09-05 00:00:00 |
| `device_family` | str | mobile_android, mobile_ios, web |
| `device_key` | int64 | 2, 1, 3 |
| `month_idx` | int64 | 0 |
| `streamed_minutes` | float64 | 207.51833333333335, 160.55666666666667, 487.94666666666666 |
| `play_starts` | int64 | 5, 11, 8 |
| `distinct_titles` | int64 | 3, 2, 8 |
| `video_start_failures` | int64 | 0, 1, 2 |
| `playback_errors` | int64 | 0, 1, 2 |
| `rebuffer_ratio` | float64 | 0.0084, 0.0107, 0.0069 |
| `cdn_gb` | float64 | 4.791995117187501, 3.860876953125, 9.749 |
| `date_key` | int64 | 20230901, 20230902, 20230905 |
