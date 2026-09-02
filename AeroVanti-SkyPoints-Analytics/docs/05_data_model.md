# AeroVanti SkyPoints — Data Model

**Document status:** Phase 4 deliverable. **Depends on:** `02_data_architecture.md`,
`03_data_dictionary.md` (auto-generated). Describes the curated star as it will be imported
into the Power BI semantic model (Phase 6).

---

## 1. Bus matrix (facts × dimensions)

| Fact ↓ / Dim → | date | member | tier | earn_source | reward_type | route | experiment_arm | experiment_stratum |
|---|:--:|:--:|:--:|:--:|:--:|:--:|:--:|:--:|
| `fact_point_transaction` | ● | ● | (via member) | ● | ● | | (via member) | |
| `fact_member_month` | ● (month) | ● | ● | | | | ● | (via member) |
| `fact_flight_segment` | ● | ● | ● | | | ● | (via member) | |
| `fact_card_spend_month` | ● (month) | ● | | | | | | |
| `fact_tier_change` | ● | ● | ● (from/to) | | | | | |
| `fact_liability_month` | ● (month) | | | | | | | |
| `fact_experiment_assignment` | ● (assigned_ts) | ● | | | | | ● | ● |
| `fact_experiment_member_week` | ● (exp. week) | ● | | | | | ● | ● |
| `fact_experiment_outcome` | | ● | | | | | ● | ● |
| `fact_targets_month` | ● (month) | | | | | | | |

`●` = direct relationship; `(via …)` = reachable through another dimension, not a physical
relationship.

---

## 2. Fact tables — grain & measures

| Fact | Grain | Additive measures | Non-additive / semi-additive |
|---|---|---|---|
| `fact_point_transaction` | one ledger entry | `points` (signed), `points_value_brl` | — |
| `fact_member_month` | member × calendar month | `points_earned_m`, `points_redeemed_m`, `points_expired_m`, `redemptions_m`, `flights_m`, `flight_revenue_brl_m`, `card_spend_brl_m` | `balance_pts_eom` (semi-additive, last), `is_active_eom`, `is_lapsed_eom` (nullable), `has_redeemed_ever_eom`, `tier_key`, `months_since_last_activity` |
| `fact_flight_segment` | one flown segment | `base_fare_brl`, `taxes_brl`, `skypoints_earned`, `tier_points_earned`, `points_redeemed` | `is_award_redemption` |
| `fact_card_spend_month` | member × month | `card_spend_brl`, `skypoints_earned` | `is_card_active` |
| `fact_tier_change` | one tier-change event | count of events | `direction`, `trigger`, `from_tier_key`, `to_tier_key` |
| `fact_liability_month` | calendar month | `points_issued_m`, `points_redeemed_m`, `points_expired_m`, `breakage_provision_brl`, `reward_cash_cost_brl` | `points_outstanding_eop`, `liability_brl_gross`, `liability_brl_breakage_adj` (all semi-additive, last) + `*_ledger` tie-out columns |
| `fact_experiment_assignment` | subject (member) | count of subjects | `pre_earn_12m_pts`, `pre_flights_12m`, `pre_redemptions_12m`, `pre_balance_pts`, `prior_redeemer_flag`, `pre_tenure_months` |
| `fact_experiment_member_week` | subject × experiment week (1–12) | `redemptions_w`, `points_redeemed_w`, `redemption_value_brl_w` | `redeemed_w`, `low_cost_only_w` |
| `fact_experiment_outcome` | subject (member) | `redemptions_in_window`, `redemption_value_brl`, `points_redeemed_in_window`, `revenue_brl_window_plus8w`, `liability_drawdown_brl`, `reward_cash_cost_brl`, `net_liability_cost_brl`, `flights_in_window` | `redeemed_in_window` (**primary metric**), `low_cost_only`, `disengaged_90d_post`, `earn_in_window`, `active_post_quarter` |
| `fact_targets_month` | month × KPI | `target_value` | `kpi` |

---

## 3. Dimensions — key attributes

| Dimension | Key | Attributes used in the report |
|---|---|---|
| `dim_date` | `date_key` (int `YYYYMMDD`) | `year`, `quarter`, `month`, `month_key`, `month_name`, `month_sort`, `iso_week`, `is_month_end`, `is_holiday_br`, `season_tag`, `experiment_phase`, `experiment_week` |
| `dim_member` | `member_key` | `enrollment_cohort_month`, `enrollment_channel`, `home_region`, `home_city`, `has_cobrand_card`, `current_tier_name`, `crm_lifecycle_stage`, `age_band`, `is_steady_state_cohort`, `experiment_arm`, `experiment_stratum`, `is_experiment_subject` |
| `dim_tier` | `tier_key` | `tier_name`, `tier_rank`, `earn_multiplier`, `is_elite` |
| `dim_earn_source` | `earn_source_key` | `source_name`, `source_group`, `earns_tier_points` |
| `dim_reward_type` | `reward_type_key` | `reward_name`, `reward_category`, `points_price_typical`, `value_per_point_brl`, `is_low_cost_catalog` |
| `dim_route` | `route_key` | `origin`, `dest`, `haul_band`, `region_pair` |
| `dim_experiment_arm` | `arm_key` | (`control` / `treatment` / `not_enrolled`) — disconnected slicer helper |
| `dim_experiment_stratum` | `stratum` | (`Blue` … `Platinum`) — disconnected slicer helper |

Sentinel members: `member_key` `-1` (non-member booking), `-2` (orphan). Sentinel `-1`
rows also exist in `dim_earn_source`, `dim_reward_type`, `dim_route`.

---

## 4. Relationships

| From (fact) | Column | To (dim) | Column | Card. | Cross-filter | Active |
|---|---|---|---|---|---|---|
| `fact_point_transaction` | `member_key` | `dim_member` | `member_key` | * : 1 | single | yes |
| `fact_point_transaction` | `txn_date_key` | `dim_date` | `date_key` | * : 1 | single | yes |
| `fact_point_transaction` | `earn_source_key` | `dim_earn_source` | `earn_source_key` | * : 1 | single | yes |
| `fact_point_transaction` | `reward_type_key` | `dim_reward_type` | `reward_type_key` | * : 1 | single | yes |
| `fact_member_month` | `member_key` | `dim_member` | `member_key` | * : 1 | single | yes |
| `fact_member_month` | `month_key` | `dim_month` | `month_key` | * : 1 | single | yes |
| `fact_member_month` | `tier_key` | `dim_tier` | `tier_key` | * : 1 | single | yes |
| `fact_flight_segment` | `member_key` | `dim_member` | `member_key` | * : 1 | single | yes |
| `fact_flight_segment` | `flight_date_key` | `dim_date` | `date_key` | * : 1 | single | yes |
| `fact_flight_segment` | `route_key` | `dim_route` | `route_key` | * : 1 | single | yes |
| `fact_card_spend_month` | `member_key` | `dim_member` | `member_key` | * : 1 | single | yes |
| `fact_card_spend_month` | `month_key` | `dim_month` | `month_key` | * : 1 | single | yes |
| `fact_tier_change` | `member_key` | `dim_member` | `member_key` | * : 1 | single | yes |
| `fact_tier_change` | `change_date_key` | `dim_date` | `date_key` | * : 1 | single | yes |
| `fact_liability_month` | `month_key` | `dim_month` | `month_key` | * : 1 | single | yes |
| `fact_experiment_assignment` | `member_key` | `dim_member` | `member_key` | 1 : 1 | both | yes |
| `fact_experiment_member_week` | `member_key` | `dim_member` | `member_key` | * : 1 | single | yes |
| `fact_experiment_outcome` | `member_key` | `dim_member` | `member_key` | 1 : 1 | single | yes |
| `fact_targets_month` | `month_key` | `dim_month` | `month_key` | * : 1 | single | yes |

`dim_experiment_arm` / `dim_experiment_stratum` are **disconnected** — used only to drive
slicers whose selections are read by measures with `SELECTEDVALUE`. The physical arm/stratum
columns live on `dim_member` and the experiment facts.

**Date handling.** `dim_date` is at **day** grain (its `month_key` is *not* unique, so it
cannot sit on the "one" side of any relationship). A small **`dim_month`** helper table
(one row per month, unique `month_key`) is the join target for the month-grain facts
(`fact_member_month`, `fact_card_spend_month`, `fact_liability_month`, `fact_targets_month`);
day-grain facts join `dim_date[date_key]`. There is deliberately **no** `dim_month ↔ dim_date`
relationship. Time-series visuals bind to `dim_month[month_name]` (sorted by `month_sort`)
for chronological order.

---

## 5. Measure groups (Phase 7 preview)

Program Health · Earn & Burn · Breakage & Liability · Tiers & Value · Retention & Lapse ·
Commercial Value · **Experiment** (redemption rate by arm, lift + CI + p, SRM, weekly
series, guardrails, per-tier effect) · Time Intelligence (YoY, YTD, MAT, steady-state cut) ·
Targets vs Plan · a dynamic `Exec Insight` narrative measure.
