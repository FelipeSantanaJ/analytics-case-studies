# SwiftBite Delivery — Data Dictionary

_Auto-generated from `data/curated/` on 2026-09-10 · SEED=20260910. Do not edit by hand — run `python etl/gen_data_dictionary.py`._

15 curated tables.

## `dim_courier`  ·  1,400 rows

One row per courier. Signup cohort, vehicle, acquisition channel, modal home zone. courier_key -1 = no courier assigned, -2 = orphan.

| column | dtype | non-null | distinct | example |
|---|---|---|---|---|
| `courier_key` | int64 | 100.0% | 1,400 | 1 |
| `courier_id` | str | 100.0% | 1,400 | C100000 |
| `signup_date_key` | int32 | 100.0% | 590 | 20250420 |
| `signup_cohort_month` | str | 100.0% | 23 | 2025-04 |
| `vehicle_type` | str | 100.0% | 3 | bike |
| `acquisition_channel` | str | 100.0% | 4 | referral |
| `home_zone_key` | int64 | 100.0% | 12 | 1 |
| `is_test_account` | bool | 100.0% | 1 | False |

## `dim_customer`  ·  9,000 rows

One row per ordering customer, with a coarse activity segment.

| column | dtype | non-null | distinct | example |
|---|---|---|---|---|
| `customer_key` | int64 | 100.0% | 9,000 | 1 |
| `customer_id` | str | 100.0% | 9,000 | U200000 |
| `customer_segment` | str | 100.0% | 4 | new |
| `home_zone_key` | int64 | 100.0% | 12 | 8 |

## `dim_date`  ·  1,125 rows

Calendar spine (2024-06 → 2027-06). Carries experiment_phase / experiment_week, BR holidays, rainy-season flag.

| column | dtype | non-null | distinct | example |
|---|---|---|---|---|
| `date` | datetime64[ms] | 100.0% | 1,125 | 2024-06-01 00:00:00 |
| `date_key` | int32 | 100.0% | 1,125 | 20240601 |
| `year` | int32 | 100.0% | 4 | 2024 |
| `quarter` | int32 | 100.0% | 4 | 2 |
| `month` | int32 | 100.0% | 12 | 6 |
| `month_name` | str | 100.0% | 12 | Jun |
| `iso_week` | UInt32 | 100.0% | 53 | 22 |
| `day_of_week` | int32 | 100.0% | 7 | 5 |
| `is_weekend` | bool | 100.0% | 2 | True |
| `is_holiday_br` | bool | 100.0% | 2 | False |
| `is_rainy_season` | bool | 100.0% | 2 | False |
| `experiment_phase` | str | 100.0% | 3 | pre |
| `experiment_week` | float64 | 6.2% | 10 | 1.0 |

## `dim_incentive_campaign`  ·  840 rows

One row per peak-eligible zone-day in the 10-week experiment window: arm, bonus, stratum (zone × stress tier), day-of-week.

| column | dtype | non-null | distinct | example |
|---|---|---|---|---|
| `campaign_key` | int64 | 100.0% | 840 | 1 |
| `zone_key` | int64 | 100.0% | 12 | 1 |
| `date_key` | int64 | 100.0% | 70 | 20260406 |
| `arm` | str | 100.0% | 2 | control |
| `bonus_brl_per_delivery` | float64 | 100.0% | 2 | 0.0 |
| `push_radius_m` | int64 | 100.0% | 1 | 2000 |
| `peak_block_start_hour` | int64 | 100.0% | 1 | 18 |
| `peak_block_end_hour` | int64 | 100.0% | 1 | 22 |
| `stratum` | str | 100.0% | 12 | Z01|long |
| `day_of_week` | int32 | 100.0% | 7 | 0 |

## `dim_restaurant`  ·  1,200 rows

One row per restaurant, its zone, cuisine and price band.

| column | dtype | non-null | distinct | example |
|---|---|---|---|---|
| `restaurant_key` | int64 | 100.0% | 1,200 | 1 |
| `restaurant_id` | str | 100.0% | 1,200 | R300000 |
| `zone_key` | int64 | 100.0% | 12 | 9 |
| `cuisine` | str | 100.0% | 7 | burger |
| `price_band` | str | 100.0% | 3 | R$ |

## `dim_time_block`  ·  24 rows

One row per hour of day (0–23) with daypart and is_peak_block (18:00–21:59, the experiment's block).

| column | dtype | non-null | distinct | example |
|---|---|---|---|---|
| `time_block_key` | int64 | 100.0% | 24 | 0 |
| `hour` | int64 | 100.0% | 24 | 0 |
| `daypart` | str | 100.0% | 6 | early |
| `is_peak_block` | bool | 100.0% | 2 | False |
| `block_label` | str | 100.0% | 24 | 00:00–01:00 |

## `dim_zone`  ·  12 rows

The 12 delivery zones. baseline_supply_stress_tier (short/balanced/long) is derived from months 1–15 liquidity; is_boundary_redrawn flags the two zones re-cut at window-month 9.

| column | dtype | non-null | distinct | example |
|---|---|---|---|---|
| `zone_key` | int64 | 100.0% | 12 | 1 |
| `zone_id` | str | 100.0% | 12 | Z01 |
| `zone_name` | str | 100.0% | 12 | Centro |
| `macro_area` | str | 100.0% | 3 | centre |
| `area_km2` | float64 | 100.0% | 12 | 7.5 |
| `centroid_lat` | float64 | 100.0% | 6 | -19.92 |
| `centroid_lon` | float64 | 100.0% | 5 | -43.96 |
| `n_neighbours` | int64 | 100.0% | 4 | 5 |
| `baseline_supply_stress_tier` | str | 100.0% | 3 | long |
| `avg_trip_km_baseline` | float64 | 100.0% | 3 | 2.4 |
| `is_boundary_redrawn` | bool | 100.0% | 2 | False |

## `dim_zone_adjacency`  ·  42 rows

Undirected zone adjacency as a bridge table — the basis for the neighbour-zone cannibalisation analysis.

| column | dtype | non-null | distinct | example |
|---|---|---|---|---|
| `zone_key` | int64 | 100.0% | 12 | 1 |
| `neighbour_zone_key` | int64 | 100.0% | 12 | 2 |

## `fact_courier_shift_block`  ·  204,123 rows

Courier × zone × date × hour: logged-in / active / idle / cooldown minutes, deliveries, earnings. The supply side of liquidity.

| column | dtype | non-null | distinct | example |
|---|---|---|---|---|
| `courier_key` | int64 | 100.0% | 1,400 | 830 |
| `zone_key` | int64 | 100.0% | 12 | 2 |
| `date_key` | int64 | 100.0% | 608 | 20250101 |
| `time_block_key` | int64 | 100.0% | 22 | 0 |
| `logged_in_min` | int64 | 100.0% | 45 | 44 |
| `active_min` | int64 | 100.0% | 46 | 0 |
| `idle_min` | int64 | 100.0% | 57 | 38 |
| `cooldown_min` | int64 | 100.0% | 4 | 3 |
| `deliveries` | int64 | 100.0% | 16 | 0 |
| `base_payout_brl` | Float64 | 100.0% | 7,654 | 0.0 |
| `tip_brl` | float64 | 100.0% | 1 | 0.0 |
| `bonus_brl` | float64 | 100.0% | 10 | 0.0 |
| `earnings_brl` | Float64 | 100.0% | 7,907 | 0.0 |
| `is_peak_block` | bool | 100.0% | 2 | False |

## `fact_delivery`  ·  351,577 rows

One row per delivered order: courier, trip, payout split (base / tip / incentive bonus / total).

| column | dtype | non-null | distinct | example |
|---|---|---|---|---|
| `delivery_key` | int64 | 100.0% | 351,577 | 1 |
| `order_key` | int64 | 100.0% | 351,577 | 1 |
| `courier_key` | int64 | 100.0% | 1,400 | 859 |
| `zone_key` | int64 | 100.0% | 12 | 2 |
| `date_key` | int32 | 100.0% | 608 | 20250101 |
| `time_block_key` | int32 | 100.0% | 24 | 0 |
| `dropoff_ts` | datetime64[ns, UTC] | 100.0% | 328,188 | 2025-01-01 03:31:00+00:00 |
| `trip_min` | float64 | 100.0% | 1,647 | 29.975 |
| `trip_distance_km` | float64 | 100.0% | 954 | 1.7 |
| `courier_base_payout_brl` | float64 | 100.0% | 954 | 8.36 |
| `tip_brl` | float64 | 100.0% | 1,191 | 0.0 |
| `incentive_bonus_brl` | float64 | 100.0% | 2 | 0.0 |
| `total_payout_brl` | float64 | 100.0% | 1,913 | 8.36 |
| `is_peak_block` | bool | 100.0% | 2 | False |
| `experiment_phase` | str | 100.0% | 3 | pre |
| `on_treated_zone_day` | bool | 100.0% | 2 | False |

## `fact_experiment_zone_block_week`  ·  480 rows

Zone × experiment week × peak hour-block — the weekly series for the novelty / decay diagnostic.

| column | dtype | non-null | distinct | example |
|---|---|---|---|---|
| `zone_key` | int64 | 100.0% | 12 | 1 |
| `experiment_week` | float64 | 100.0% | 10 | 1.0 |
| `time_block_key` | int32 | 100.0% | 4 | 18 |
| `orders_placed` | int64 | 100.0% | 58 | 44 |
| `orders_delivered` | int64 | 100.0% | 57 | 44 |
| `eta_p90_min` | float64 | 100.0% | 475 | 30.976 |
| `available_courier_hours` | float64 | 100.0% | 409 | 21.017 |
| `fulfillment_rate` | float64 | 100.0% | 95 | 1.0 |
| `date_key` | int64 | 100.0% | 1 | 20260406 |
| `arm` | str | 100.0% | 2 | control |

## `fact_experiment_zone_day`  ·  840 rows

One tidy row per unit of randomization (~840): fulfillment_rate (primary), ETA p50/p90, cancel & no-courier rate, courier earnings/active-hr, incentive spend and cost per delivered order, adjacency-to-treated.

| column | dtype | non-null | distinct | example |
|---|---|---|---|---|
| `zone_key` | int64 | 100.0% | 12 | 1 |
| `date_key` | int32 | 100.0% | 70 | 20260406 |
| `orders_placed` | int64 | 100.0% | 45 | 21 |
| `orders_delivered` | int64 | 100.0% | 42 | 21 |
| `eta_p50_min` | float64 | 100.0% | 724 | 26.838 |
| `eta_p90_min` | float64 | 100.0% | 824 | 30.25 |
| `cancelled_no_courier` | int64 | 100.0% | 4 | 0 |
| `available_courier_hours` | float64 | 100.0% | 519 | 9.717 |
| `active_couriers` | float64 | 100.0% | 8 | 4.0 |
| `fulfillment_rate` | float64 | 100.0% | 65 | 1.0 |
| `cancel_rate` | float64 | 100.0% | 65 | 0.0 |
| `cancel_no_courier_rate` | float64 | 100.0% | 39 | 0.0 |
| `arm` | str | 100.0% | 2 | control |
| `stratum` | str | 100.0% | 12 | Z01|long |
| `courier_earnings_per_active_hour_brl` | float64 | 100.0% | 838 | 31.16 |
| `incentive_spend_brl` | float64 | 100.0% | 49 | 0.0 |
| `deliveries` | int64 | 100.0% | 42 | 21 |
| `incentive_cost_per_delivered_order_brl` | float64 | 100.0% | 192 | 0.0 |
| `n_adjacent_zones_treated` | int64 | 100.0% | 6 | 1 |
| `is_adjacent_to_treated` | bool | 100.0% | 2 | True |

## `fact_incentive_assignment`  ·  840 rows

One row per experiment zone-day (~840). Arm, bonus, stratum, adjacency-to-treated flags, and pre-period (months 1–15) covariates frozen for the balance checks.

| column | dtype | non-null | distinct | example |
|---|---|---|---|---|
| `campaign_key` | int64 | 100.0% | 840 | 1 |
| `zone_key` | int64 | 100.0% | 12 | 1 |
| `date_key` | int64 | 100.0% | 70 | 20260406 |
| `arm` | str | 100.0% | 2 | control |
| `bonus_brl_per_delivery` | float64 | 100.0% | 2 | 0.0 |
| `push_radius_m` | int64 | 100.0% | 1 | 2000 |
| `peak_block_start_hour` | int64 | 100.0% | 1 | 18 |
| `peak_block_end_hour` | int64 | 100.0% | 1 | 22 |
| `stratum` | str | 100.0% | 12 | Z01|long |
| `day_of_week` | int32 | 100.0% | 7 | 0 |
| `pre_fulfillment_rate` | float64 | 100.0% | 12 | 0.981 |
| `pre_eta_p90_min` | float64 | 100.0% | 12 | 33.201 |
| `pre_orders_placed_mean` | float64 | 100.0% | 12 | 6.56 |
| `pre_liquidity_ratio` | float64 | 100.0% | 12 | 1.281 |
| `pre_idle_courier_ratio` | float64 | 100.0% | 12 | 0.329 |
| `n_adjacent_zones_treated` | int64 | 100.0% | 6 | 1 |
| `is_adjacent_to_treated` | bool | 100.0% | 2 | True |

## `fact_order`  ·  368,658 rows

One row per placed order. Dual zone resolution (dropoff_zone_key_asbooked vs _current); outcome, ETA, assignment latency; experiment flags (on_treated_zone_day, is_adjacent_to_treated_zone_day). courier_key filled for delivered orders.

| column | dtype | non-null | distinct | example |
|---|---|---|---|---|
| `order_key` | int64 | 100.0% | 368,658 | 1 |
| `order_id` | str | 100.0% | 368,658 | O5000001 |
| `customer_key` | int64 | 100.0% | 9,000 | 8760 |
| `restaurant_key` | int64 | 100.0% | 1,200 | 159 |
| `pickup_zone_key` | int64 | 100.0% | 12 | 2 |
| `dropoff_zone_key_asbooked` | int64 | 100.0% | 12 | 2 |
| `dropoff_zone_key_current` | int64 | 100.0% | 12 | 2 |
| `placed_date_key` | int32 | 100.0% | 608 | 20250101 |
| `placed_ts` | datetime64[ns, UTC] | 100.0% | 343,196 | 2025-01-01 03:31:00+00:00 |
| `placed_hour` | int32 | 100.0% | 24 | 0 |
| `time_block_key` | int32 | 100.0% | 24 | 0 |
| `is_peak_block` | bool | 100.0% | 2 | False |
| `basket_value_brl` | Float64 | 100.0% | 23,132 | 38.89 |
| `delivery_fee_brl` | Float64 | 100.0% | 1,381 | 8.25 |
| `outcome` | str | 100.0% | 5 | delivered |
| `eta_min` | float64 | 95.4% | 1,647 | 54.5 |
| `assignment_latency_s` | Float64 | 100.0% | 581 | 258.0 |
| `trip_distance_km` | float64 | 100.0% | 958 | 1.7 |
| `experiment_phase` | str | 100.0% | 3 | pre |
| `on_treated_zone_day` | bool | 100.0% | 2 | False |
| `is_adjacent_to_treated_zone_day` | bool | 100.0% | 2 | False |
| `courier_key` | int64 | 100.0% | 1,401 | 859 |

## `fact_zone_hour`  ·  117,997 rows

Zone × date × hour — the liquidity spine. Orders placed/delivered/cancelled by cause, fulfillment_rate, ETA p50/p90, available vs demanded courier-hours, liquidity_ratio, idle_courier_ratio, unmet_demand, rain / event flags, experiment_arm.

| column | dtype | non-null | distinct | example |
|---|---|---|---|---|
| `zone_key` | int64 | 100.0% | 12 | 1 |
| `date_key` | int32 | 100.0% | 608 | 20250101 |
| `hour` | int32 | 100.0% | 24 | 1 |
| `orders_placed` | int64 | 100.0% | 23 | 1 |
| `orders_delivered` | int64 | 100.0% | 23 | 1 |
| `cancelled_customer` | int64 | 100.0% | 5 | 0 |
| `cancelled_courier` | int64 | 100.0% | 4 | 0 |
| `cancelled_no_courier` | int64 | 100.0% | 4 | 0 |
| `cancelled_restaurant` | int64 | 100.0% | 3 | 0 |
| `assignment_latency_p90_s` | Float64 | 100.0% | 6,805 | 231.0 |
| `eta_p50_min` | float64 | 98.9% | 2,575 | 38.6 |
| `eta_p90_min` | float64 | 98.9% | 14,585 | 38.6 |
| `time_block_key` | int32 | 100.0% | 24 | 1 |
| `is_peak_block` | bool | 100.0% | 2 | False |
| `fulfillment_rate` | float64 | 100.0% | 56 | 1.0 |
| `unmet_demand` | int64 | 100.0% | 6 | 0 |
| `demanded_delivery_hours` | float64 | 100.0% | 54 | 0.433 |
| `available_courier_hours` | float64 | 100.0% | 530 | 0.617 |
| `idle_courier_hours` | float64 | 100.0% | 446 | 0.0 |
| `active_couriers` | float64 | 100.0% | 10 | 1.0 |
| `liquidity_ratio` | float64 | 100.0% | 5,297 | 1.423 |
| `idle_courier_ratio` | float64 | 95.6% | 9,831 | 0.0 |
| `is_rainy` | bool | 100.0% | 2 | False |
| `has_local_event` | bool | 100.0% | 2 | False |
| `experiment_arm` | str | 100.0% | 3 |  |
| `on_treated_zone_day` | bool | 100.0% | 2 | False |
| `is_adjacent_to_treated_zone_day` | bool | 100.0% | 2 | False |
