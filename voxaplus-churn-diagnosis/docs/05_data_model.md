# Voxa+ — Data Model

**Document status:** Phase 4 deliverable · the curated star as built in `data/curated/`.
**Companion:** `docs/03_data_dictionary.md` (every column + samples), `docs/06_dax_measures.md`
(Phase 7). The Power BI semantic model (Phase 6) is generated from these schemas.

Grain of the mart: **the subscriber-month** for retention and revenue, with event-,
attempt-, and day-grain facts beneath it for the diagnostic pages.

---

## 1. Bus matrix (facts × conformed dimensions)

| Fact ↓ / Dimension → | date | market | subscriber | plan | channel | device | payment method | content | support reason | app version |
|---|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|
| **fact_subscription_month** | ● | ● | ● | ○(tier) | ○(via sub) | ○(via sub) | | | | |
| **fact_subscription_event** | ● | ○(via sub) | ● | ○(from/to tier) | | | | | | |
| **fact_billing_attempt** | ● | ● | ● | ○(tier) | | | ● | | | |
| **fact_viewing_daily** | ● | ○(via sub) | ● | | | ● | | ○(content_key) | | |
| **fact_engagement_month** | ● | ○(via sub) | ● | | | ○(pct_days_ctv) | | | | |
| **fact_app_performance_daily** | ● | ● | | | | ● | | | | ● |
| **fact_support_ticket** | ● | ● | ● | | | | | | ● | |
| **fact_marketing_spend** | ● (week) | ● | | | ● | | | | | |
| **fact_ad_revenue** | ● | ● | | | | | | | | |
| **fact_content_cost** | ● (month) | ○(alloc) | | | | | | ● | | |
| **fact_fx_rate** | ● (month) | ○(currency) | | | | | | | | |
| **fact_finance_month** | ● (month) | ● | | ○(pnl_line) | | | | | | |
| **fact_targets_month** | ● (month) | ● | | | | | | | | |

● direct relationship · ○ derived / attribute-level / bridged in DAX.

---

## 2. Facts — grain, measures, degenerate columns

| Fact | Grain | Rows (full run) | Additive measures | Non-additive / flags | Degenerate dims |
|---|---|--:|---|---|---|
| `fact_subscription_month` | subscriber × window-month while subscribed | 1,216,330 | `mrr_local`, `mrr_usd` | `status`, `tenure_months`, `is_new`, `is_reactivation`, `is_voluntary_churn`, `is_involuntary_churn` | `tier`, `billing_period`, `market` |
| `fact_subscription_event` | one lifecycle event | 265,110 | count | `event_type`, `from_tier`, `to_tier`, `reason_code` | `event_id`, `subject` |
| `fact_billing_attempt` | one billing attempt | 1,141,115 | `amount_local/usd`, `processing_cost_local/usd` | `status`, `type`, `attempt_number`, `is_dunning`, `failure_reason` | `txn_id`, `method` |
| `fact_viewing_daily` | subscriber × local date × device family | 13,485,904 | `streamed_minutes`, `play_starts`, `distinct_titles`, `video_start_failures`, `playback_errors`, `cdn_gb` | `rebuffer_ratio` (avg) | — |
| `fact_engagement_month` | subscriber × window-month with streaming | 1,146,571 | `streamed_hours`, `active_days`, `distinct_titles`, `playback_errors`, `video_start_failures`, `ctv_days` | `pct_days_ctv`, `below_healthy_engagement` | — |
| `fact_app_performance_daily` | market × date × device family × app version | 15,342 | `sessions`, `crashes`, `screen_views` | `crash_free_rate` | `app_version` |
| `fact_support_ticket` | one ticket | 79,215 | count, `resolution_hours` | `csat_score`, `is` flags, `source_version` | `ticket_id`, `contact_channel` |
| `fact_marketing_spend` | ISO week × market × channel × campaign | 2,016 | `spend_usd`, `spend_local`, `impressions`, `clicks`, `signups_attributed` | — | `campaign_id` |
| `fact_ad_revenue` | market × day | 2,557 | `impressions_served`, `ad_revenue_usd` | `fill_rate`, `ecpm_usd` | — |
| `fact_content_cost` | title × window-month | 123,876 | `amort_usd`, `cash_spend_usd` | — | — |
| `fact_fx_rate` | window-month × currency | 108 | — | `avg_rate`, `eop_rate` | `currency` |
| `fact_finance_month` | window-month × market × P&L line | 780 | `amount_usd` | — | `pnl_line` |
| `fact_targets_month` | market × window-month × KPI | 432 | `target_value` | — | `kpi` |

`month_idx` (0-based window month) and `date_key` (`YYYYMMDD` int, month-end for
monthly-grain facts) appear on every fact for the relationship to `dim_date`.

---

## 3. Dimensions — key attributes

| Dimension | Key | Rows | Attributes used on the report |
|---|---|--:|---|
| `dim_date` | `date_key` | 1,826 | `year_month`, `month_sort` (sort), `window_month_idx`, `in_analysis_window`, `season_tag`, `is_holiday_{br,mx,us}`, `is_partial_period` |
| `dim_market` | `market_key` | 3 | `market_id` (BR/MX/US), `currency_code`, `market_active_from_date_key`, **`is_comparable_base`** |
| `dim_subscriber` | `subscriber_key` | 115,728 | `market`, `cohort_month`, `first_paid_month_idx`, `acquisition_channel`, `first_tier`, `current_tier`, `billing_period`, `primary_device_family`, `crm_lifecycle_stage`, `is_comparable_base`, `is_l4l_cohort` |
| `dim_plan` | `plan_key` | 18 | `tier`, `billing_period`, `market_id`, `has_ads`, `max_streams`, `max_resolution`, `has_downloads` |
| `dim_price_history` | `price_key` | 11 | `tier`, `market_id`, `effective_from/to_date_key`, `list_price_local` — **range table, used in DAX, not a relationship** |
| `dim_channel` | `channel_key` | 7 | `channel`, `channel_group`, **`is_low_quality`** |
| `dim_device` | `device_key` | 7 | `device_family`, `device_class` (mobile/web/ctv), **`is_ctv`** |
| `dim_payment_method` | `method_key` | 5 | `method`, `is_prepaid`, `settlement_lag_days_typical` |
| `dim_content` | `content_key` | 3,500 | `title`, `content_type`, `primary_genre`, `language`, `is_original`, `release_date_key`, `runtime_min` |
| `dim_support_reason` | `support_reason_key` | 6 | `reason_category`, `reason_group` (billing / app_tech / content / account / other) |
| `dim_app_version` | `app_version_key` | 15 | `app_version`, `major`, **`is_v3`** |

`dim_reporting_currency` (a disconnected BR L/MXN/USD slicer table) and the P&L-line and
funnel helper tables are added in **Phase 6** with the semantic model, not in the curated
files.

---

## 4. Relationships

All single-direction (`dim 1 → * fact`), single cross-filter, unless noted.

| From (dim) | To (fact) | Key | Notes |
|---|---|---|---|
| `dim_date[date_key]` | every fact `[date_key]` | `date_key` | monthly facts join on month-end key |
| `dim_market[market_key]` | `fact_subscription_month`, `fact_billing_attempt`, `fact_support_ticket`, `fact_app_performance_daily`, `fact_marketing_spend`, `fact_ad_revenue`, `fact_finance_month`, `fact_targets_month` | `market_key` | facts that only carry the `market` string get `market_key` added in Phase 6 |
| `dim_subscriber[subscriber_key]` | `fact_subscription_month`, `fact_subscription_event`, `fact_billing_attempt`, `fact_engagement_month`, `fact_viewing_daily`, `fact_support_ticket` | `subscriber_key` | the hub of the model; market/channel/tier/device slice through here |
| `dim_device[device_key]` | `fact_viewing_daily`, `fact_app_performance_daily` | `device_key` | |
| `dim_content[content_key]` | `fact_viewing_daily`, `fact_content_cost` | `content_key` | orphan beacons/rows carry `content_key = -1` |
| `dim_payment_method[method_key]` | `fact_billing_attempt` | `method_key` | |
| `dim_channel[channel_key]` | `fact_marketing_spend` | `channel_key` | subscriber-level channel is an attribute of `dim_subscriber` |
| `dim_support_reason[support_reason_key]` | `fact_support_ticket` | `support_reason_key` | |
| `dim_app_version[app_version_key]` | `fact_app_performance_daily` | `app_version` → key in Phase 6 | |

**Role-playing dates.** Only one active `dim_date` relationship per fact (the event/period
date). Secondary dates (`release_date_key`, `market_active_from_date_key`,
`effective_from_date_key`) are attributes, resolved in DAX with `USERELATIONSHIP` only if a
visual needs them — kept **inactive** to avoid ambiguous filter paths.

**Deliberately not related.** `dim_price_history` (a from/to range — DAX looks up the price
in effect for a `tier`/`market`/`month`), and `fact_fx_rate` (joined in measures on
`month_idx` + `currency`, or pre-applied as the `_usd` columns).

---

## 5. Comparable Base vs Expansion in the model

`is_comparable_base` lives on `dim_market` **and** `dim_subscriber` (= Brazil). Measures
provide three cuts:

- **Total** — no filter.
- **Comparable Base** — `CALCULATE(…, dim_subscriber[is_comparable_base] = TRUE)`.
- **Expansion** — `Total − Comparable Base` for additive measures; computed within the
  filter for rates.

`is_l4l_cohort` (first-paid month ≤ PY end) supports a 12-month like-for-like cohort cut
that sits entirely inside the pre-shift baseline.

---

## 6. Known modelling caveats (see also `docs/08_data_quality.md`)

- Subscriber **acquisition channel** is a sampled attribute (the attribution source has no
  account key) — channel-level retention is directionally correct, not row-exact.
- **Billing amount** comes from the plan-price schedule, not the gateway `amount` column.
- The **last window month** is flagged `is_partial_period` (partner settlement lag) — trend
  visuals should annotate or exclude it.
- `fact_finance_month` is a modelled roll-up; it ties to operational MRR within ~4 % but is
  not a general ledger.
