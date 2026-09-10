# Voxa+ — DAX Measure Library

_Auto-generated from `etl/pbi_measures.py` on 2026-09-02 by `etl/gen_dax_doc.py`. Do not edit by hand._

**113 measures** in the `_Measures` table, injected into the semantic model by `powerbi/gen_semantic_model.py`.

**Conventions**

- Monetary measures are computed in USD from the curated `*_usd` columns, then multiplied by `[FX Rate to Reporting]` so the **Reporting Currency** slicer re-expresses them. `[Currency Symbol]` is available for labels and the narrative.
- Time intelligence uses `dim_date[abs_month]` (a linear `year*12 + month` index), so it needs **no marked date table** and never calls `SAMEPERIODLASTYEAR`. Prior year = `abs_month - 12`.
- **Comparable Base** = Brazil (`dim_subscriber[is_comparable_base]`); **Expansion** = Mexico + US.
- Churn, CAC and payback are **lower-is-better**: their `vs Target` measures are good when negative, and the KPI cards invert the delta colour.

---

## 00 Currency

### FX Rate to Reporting  
<sub>format `0.0000` · hidden</sub>

USD-to-selected-reporting-currency factor for the current date context.

```dax
VAR cur = SELECTEDVALUE ( 'Reporting Currency'[Currency], "USD" )
RETURN
    IF (
        cur = "USD",
        1,
        CALCULATE (
            AVERAGE ( fact_fx_rate[avg_rate] ),
            REMOVEFILTERS ( 'Reporting Currency' ),
            fact_fx_rate[currency] = cur
        )
    )
```

### Currency Symbol

Symbol of the selected reporting currency, for labels and the narrative.

```dax
SELECTEDVALUE ( 'Reporting Currency'[Symbol], "$" )
```

## 01 Subscribers

### Paid Active Subscribers  
<sub>format `#,##0`</sub>

Mean monthly count of subscribers with an in-force paid subscription. North Star.

```dax
AVERAGEX (
    VALUES ( dim_date[window_month_idx] ),
    CALCULATE (
        DISTINCTCOUNT ( fact_subscription_month[subscriber_key] ),
        fact_subscription_month[status] = "active"
    )
)
```

### Paid Active Subscribers (EoP)  
<sub>format `#,##0`</sub>

Active subscribers in the last month of the analysis window (end of period).

```dax
VAR lastm =
    CALCULATE ( MAX ( dim_date[window_month_idx] ),
        REMOVEFILTERS ( dim_date ), dim_date[in_analysis_window] = TRUE )
RETURN
    CALCULATE ( [Paid Active Subscribers],
        FILTER ( ALL ( dim_date ), dim_date[window_month_idx] = lastm ) )
```

### Active at Start of Month  
<sub>format `#,##0` · hidden</sub>

```dax
CALCULATE (
    DISTINCTCOUNT ( fact_subscription_month[subscriber_key] ),
    fact_subscription_month[status] = "active",
    FILTER ( ALL ( dim_date ), dim_date[window_month_idx] = MAX ( dim_date[window_month_idx] ) - 1 )
)
```

### New Subscribers  
<sub>format `#,##0`</sub>

First paid billing in the period.

```dax
CALCULATE ( COUNTROWS ( fact_subscription_month ), fact_subscription_month[is_new] = TRUE )
```

### Reactivations  
<sub>format `#,##0`</sub>

```dax
CALCULATE ( COUNTROWS ( fact_subscription_month ), fact_subscription_month[is_reactivation] = TRUE )
```

### Voluntary Churned Subscribers  
<sub>format `#,##0`</sub>

```dax
CALCULATE ( COUNTROWS ( fact_subscription_month ), fact_subscription_month[is_voluntary_churn] = TRUE )
```

### Involuntary Churned Subscribers  
<sub>format `#,##0`</sub>

```dax
CALCULATE ( COUNTROWS ( fact_subscription_month ), fact_subscription_month[is_involuntary_churn] = TRUE )
```

### Gross Churned Subscribers  
<sub>format `#,##0`</sub>

```dax
[Voluntary Churned Subscribers] + [Involuntary Churned Subscribers]
```

### Net Adds  
<sub>format `#,##0`</sub>

```dax
[New Subscribers] + [Reactivations] - [Gross Churned Subscribers]
```

## 02 Churn

### Gross Monthly Churn %  
<sub>format `0.0%`</sub>

Mean of the monthly (gross churned / start-of-month active) ratios in the period. Watch metric.

```dax
AVERAGEX (
    FILTER ( VALUES ( dim_date[window_month_idx] ),
        dim_date[window_month_idx] >= 0 && dim_date[window_month_idx] <= 35 ),
    DIVIDE ( CALCULATE ( [Gross Churned Subscribers] ), CALCULATE ( [Active at Start of Month] ) )
)
```

### Voluntary Churn %  
<sub>format `0.0%`</sub>

```dax
AVERAGEX (
    FILTER ( VALUES ( dim_date[window_month_idx] ),
        dim_date[window_month_idx] >= 0 && dim_date[window_month_idx] <= 35 ),
    DIVIDE ( CALCULATE ( [Voluntary Churned Subscribers] ), CALCULATE ( [Active at Start of Month] ) )
)
```

### Involuntary Churn %  
<sub>format `0.0%`</sub>

```dax
AVERAGEX (
    FILTER ( VALUES ( dim_date[window_month_idx] ),
        dim_date[window_month_idx] >= 0 && dim_date[window_month_idx] <= 35 ),
    DIVIDE ( CALCULATE ( [Involuntary Churned Subscribers] ), CALCULATE ( [Active at Start of Month] ) )
)
```

### Pre-Shift Baseline Churn %  
<sub>format `0.0%`</sub>

Blended gross monthly churn over window-months 25-33 (the stable pre-shift band).

```dax
CALCULATE (
    [Gross Monthly Churn %],
    REMOVEFILTERS ( dim_date ),
    dim_date[window_month_idx] >= 24 && dim_date[window_month_idx] <= 32
)
```

### Churn vs Baseline (pp)  
<sub>format `+0.0%;-0.0%;0.0%`</sub>

Percentage points above (or below) the pre-shift baseline. Higher is worse.

```dax
[Gross Monthly Churn %] - [Pre-Shift Baseline Churn %]
```

### Churn vs Baseline (x)  
<sub>format `0.00"x"`</sub>

```dax
DIVIDE ( [Gross Monthly Churn %], [Pre-Shift Baseline Churn %] )
```

### Net MRR Retention %  
<sub>format `0.0%`</sub>

MRR from the cohort active 12 months ago, now vs then (incl. up/downgrades and churn).

```dax
VAR wlast =
    CALCULATE ( MAX ( dim_date[abs_month] ),
        REMOVEFILTERS ( dim_date ), dim_date[in_analysis_window] = TRUE )
VAR c = MIN ( MAX ( dim_date[abs_month] ), wlast )
VAR baseSubs =
    CALCULATETABLE (
        VALUES ( fact_subscription_month[subscriber_key] ),
        FILTER ( ALL ( dim_date ), dim_date[abs_month] = c - 12 ),
        fact_subscription_month[status] = "active"
    )
VAR startMRR =
    CALCULATE ( SUM ( fact_subscription_month[mrr_usd] ),
        FILTER ( ALL ( dim_date ), dim_date[abs_month] = c - 12 ), baseSubs )
VAR endMRR =
    CALCULATE ( SUM ( fact_subscription_month[mrr_usd] ),
        FILTER ( ALL ( dim_date ), dim_date[abs_month] = c ), baseSubs )
RETURN DIVIDE ( endMRR, startMRR )
```

## 03 Cohorts

### Cohort Size  
<sub>format `#,##0`</sub>

Subscribers at tenure month 0 in the current filter context (use with a cohort slicer).

```dax
CALCULATE ( DISTINCTCOUNT ( fact_subscription_month[subscriber_key] ), fact_subscription_month[tenure_months] = 0 )
```

### Active Subscribers at Tenure  
<sub>format `#,##0` · hidden</sub>

```dax
CALCULATE ( DISTINCTCOUNT ( fact_subscription_month[subscriber_key] ), fact_subscription_month[status] = "active" )
```

### Retention %  
<sub>format `0.0%`</sub>

Share of a cohort still active — put cohort_month on rows and tenure_months on columns.

```dax
DIVIDE (
    [Active Subscribers at Tenure],
    CALCULATE ( [Cohort Size], REMOVEFILTERS ( fact_subscription_month[tenure_months] ) )
)
```

### M1 Retention %  
<sub>format `0.0%`</sub>

```dax
VAR c0 = [Cohort Size]
VAR c1 = CALCULATE ( DISTINCTCOUNT ( fact_subscription_month[subscriber_key] ),
             fact_subscription_month[tenure_months] = 1, fact_subscription_month[status] = "active",
             REMOVEFILTERS ( fact_subscription_month[tenure_months] ) )
RETURN DIVIDE ( c1, c0 )
```

### M3 Retention %  
<sub>format `0.0%`</sub>

```dax
VAR c0 = [Cohort Size]
VAR c3 = CALCULATE ( DISTINCTCOUNT ( fact_subscription_month[subscriber_key] ),
             fact_subscription_month[tenure_months] = 3, fact_subscription_month[status] = "active",
             REMOVEFILTERS ( fact_subscription_month[tenure_months] ) )
RETURN DIVIDE ( c3, c0 )
```

### M6 Retention %  
<sub>format `0.0%`</sub>

```dax
VAR c0 = [Cohort Size]
VAR c6 = CALCULATE ( DISTINCTCOUNT ( fact_subscription_month[subscriber_key] ),
             fact_subscription_month[tenure_months] = 6, fact_subscription_month[status] = "active",
             REMOVEFILTERS ( fact_subscription_month[tenure_months] ) )
RETURN DIVIDE ( c6, c0 )
```

### M12 Retention %  
<sub>format `0.0%`</sub>

```dax
VAR c0 = [Cohort Size]
VAR c12 = CALCULATE ( DISTINCTCOUNT ( fact_subscription_month[subscriber_key] ),
             fact_subscription_month[tenure_months] = 12, fact_subscription_month[status] = "active",
             REMOVEFILTERS ( fact_subscription_month[tenure_months] ) )
RETURN DIVIDE ( c12, c0 )
```

## 04 Engagement

### Streamed Hours  
<sub>format `#,##0`</sub>

```dax
SUM ( fact_engagement_month[streamed_hours] )
```

### Streaming Subscribers  
<sub>format `#,##0` · hidden</sub>

```dax
DISTINCTCOUNT ( fact_engagement_month[subscriber_key] )
```

### Monthly Active Rate %  
<sub>format `0.0%`</sub>

Share of paid subscribers who streamed at least once in the month.

```dax
DIVIDE ( [Streaming Subscribers], [Paid Active Subscribers] )
```

### Viewing Hours per Active Sub  
<sub>format `0.0`</sub>

```dax
DIVIDE ( [Streamed Hours], [Streaming Subscribers] )
```

### % Subs Below Healthy Engagement  
<sub>format `0.0%`</sub>

Streaming subscribers with < 5 hours this month — a leading indicator of churn.

```dax
DIVIDE (
    CALCULATE ( DISTINCTCOUNT ( fact_engagement_month[subscriber_key] ),
        fact_engagement_month[below_healthy_engagement] = TRUE ),
    [Streaming Subscribers]
)
```

### Titles Started per Active Sub  
<sub>format `0.0`</sub>

```dax
DIVIDE ( SUM ( fact_engagement_month[distinct_titles] ), [Streaming Subscribers] )
```

### Avg % Days on Connected TV  
<sub>format `0.0%`</sub>

```dax
AVERAGE ( fact_engagement_month[pct_days_ctv] )
```

### Streamed Hours (by Device)  
<sub>format `#,##0`</sub>

```dax
SUM ( fact_engagement_device_month[streamed_hours] )
```

### Video Start Failure Rate  
<sub>format `0.00%`</sub>

Play attempts that never start, by device family / market.

```dax
DIVIDE ( SUM ( fact_engagement_device_month[video_start_failures] ), SUM ( fact_engagement_device_month[play_starts] ) )
```

### Playback Error Rate  
<sub>format `0.00%`</sub>

```dax
DIVIDE ( SUM ( fact_engagement_device_month[playback_errors] ), SUM ( fact_engagement_device_month[play_starts] ) )
```

### Rebuffer Ratio  
<sub>format `0.00%`</sub>

```dax
AVERAGE ( fact_engagement_device_month[rebuffer_ratio] )
```

## 05 App Quality

### App Sessions  
<sub>format `#,##0`</sub>

```dax
SUM ( fact_app_performance_daily[sessions] )
```

### Crashes  
<sub>format `#,##0`</sub>

```dax
SUM ( fact_app_performance_daily[crashes] )
```

### Crash-Free Session Rate %  
<sub>format `0.00%`</sub>

```dax
DIVIDE ( [App Sessions] - [Crashes], [App Sessions] )
```

### % Sessions on App v3  
<sub>format `0.0%`</sub>

```dax
DIVIDE (
    CALCULATE ( [App Sessions], dim_app_version[is_v3] = TRUE ),
    [App Sessions]
)
```

## 06 Payments

### Billing Attempts  
<sub>format `#,##0`</sub>

```dax
COUNTROWS ( fact_billing_attempt )
```

### Approved Attempts  
<sub>format `#,##0`</sub>

```dax
CALCULATE ( [Billing Attempts], fact_billing_attempt[status] = "approved" )
```

### Failed Attempts  
<sub>format `#,##0`</sub>

```dax
CALCULATE ( [Billing Attempts], fact_billing_attempt[status] = "failed" )
```

### Payment Failure Rate %  
<sub>format `0.0%`</sub>

First-attempt billing failures (excludes dunning retries).

```dax
DIVIDE (
    CALCULATE ( [Failed Attempts], fact_billing_attempt[is_dunning] = FALSE ),
    CALCULATE ( [Billing Attempts], fact_billing_attempt[is_dunning] = FALSE )
)
```

### Authorization Rate %  
<sub>format `0.0%`</sub>

Approved / attempted — slice by payment method.

```dax
DIVIDE ( [Approved Attempts], [Billing Attempts] )
```

### Dunning Recovery Rate %  
<sub>format `0.0%`</sub>

```dax
DIVIDE (
    CALCULATE ( [Approved Attempts], fact_billing_attempt[is_dunning] = TRUE ),
    CALCULATE ( [Billing Attempts], fact_billing_attempt[is_dunning] = TRUE )
)
```

### Processing Cost  
<sub>format `#,##0`</sub>

```dax
SUM ( fact_billing_attempt[processing_cost_usd] ) * [FX Rate to Reporting]
```

## 07 Revenue

### MRR  
<sub>format `#,##0`</sub>

```dax
CALCULATE ( SUM ( fact_subscription_month[mrr_usd] ), fact_subscription_month[status] = "active" ) * [FX Rate to Reporting]
```

### ARPU  
<sub>format `#,##0.00`</sub>

```dax
DIVIDE ( [MRR], [Paid Active Subscribers] )
```

### Subscription Revenue  
<sub>format `#,##0`</sub>

```dax
CALCULATE ( SUM ( fact_finance_month[amount_usd] ), fact_finance_month[pnl_line] = "subscription_revenue" ) * [FX Rate to Reporting]
```

### Advertising Revenue  
<sub>format `#,##0`</sub>

```dax
CALCULATE ( SUM ( fact_finance_month[amount_usd] ), fact_finance_month[pnl_line] = "advertising_revenue" ) * [FX Rate to Reporting]
```

### Partner Revenue  
<sub>format `#,##0`</sub>

```dax
CALCULATE ( SUM ( fact_finance_month[amount_usd] ), fact_finance_month[pnl_line] = "partner_revenue" ) * [FX Rate to Reporting]
```

### Total Revenue  
<sub>format `#,##0`</sub>

```dax
[Subscription Revenue] + [Advertising Revenue] + [Partner Revenue]
```

### Content Amortisation  
<sub>format `#,##0`</sub>

```dax
-1 * CALCULATE ( SUM ( fact_finance_month[amount_usd] ), fact_finance_month[pnl_line] = "content_amortization" ) * [FX Rate to Reporting]
```

### CDN Cost  
<sub>format `#,##0`</sub>

```dax
-1 * CALCULATE ( SUM ( fact_finance_month[amount_usd] ), fact_finance_month[pnl_line] = "streaming_delivery" ) * [FX Rate to Reporting]
```

### Payment Cost  
<sub>format `#,##0`</sub>

```dax
-1 * CALCULATE ( SUM ( fact_finance_month[amount_usd] ), fact_finance_month[pnl_line] = "payment_processing" ) * [FX Rate to Reporting]
```

### Support Cost  
<sub>format `#,##0`</sub>

```dax
-1 * CALCULATE ( SUM ( fact_finance_month[amount_usd] ), fact_finance_month[pnl_line] = "customer_support" ) * [FX Rate to Reporting]
```

### Marketing Spend  
<sub>format `#,##0`</sub>

```dax
SUM ( fact_marketing_spend[spend_usd] ) * [FX Rate to Reporting]
```

### Gross Profit  
<sub>format `#,##0`</sub>

```dax
[Total Revenue] - [Content Amortisation] - [CDN Cost] - [Payment Cost] - [Support Cost]
```

### Gross Margin %  
<sub>format `0.0%`</sub>

```dax
DIVIDE ( [Gross Profit], [Total Revenue] )
```

### Contribution Margin  
<sub>format `#,##0`</sub>

```dax
[Gross Profit] - [Marketing Spend]
```

### Contribution Margin % (T12M)  
<sub>format `0.0%`</sub>

```dax
VAR c = MAX ( dim_date[abs_month] )
VAR flt = FILTER ( ALL ( dim_date ), dim_date[abs_month] > c - 12 && dim_date[abs_month] <= c )
RETURN DIVIDE ( CALCULATE ( [Contribution Margin], flt ), CALCULATE ( [Total Revenue], flt ) )
```

## 08 Unit Economics

### Blended CAC  
<sub>format `#,##0.00`</sub>

```dax
DIVIDE ( [Marketing Spend], [New Subscribers] )
```

### Expected Lifetime (months)  
<sub>format `0.0`</sub>

```dax
DIVIDE ( 1, [Gross Monthly Churn %] )
```

### LTV  
<sub>format `#,##0.00`</sub>

```dax
MAX ( 0, [ARPU] * [Gross Margin %] * [Expected Lifetime (months)] )
```

### LTV to CAC  
<sub>format `0.00`</sub>

```dax
DIVIDE ( [LTV], [Blended CAC] )
```

### CAC Payback (months)  
<sub>format `0.0`</sub>

```dax
DIVIDE ( [Blended CAC], [ARPU] * [Gross Margin %] )
```

## 09 Time Intelligence

### Paid Active Subscribers PY  
<sub>format `#,##0` · hidden</sub>

```dax
CALCULATE ( [Paid Active Subscribers], TREATAS ( SELECTCOLUMNS ( VALUES ( dim_date[abs_month] ), "abs_month", dim_date[abs_month] - 12 ), dim_date[abs_month] ) )
```

### Paid Active Subscribers YoY %  
<sub>format `+0.0%;-0.0%;0.0%`</sub>

```dax
DIVIDE ( [Paid Active Subscribers] - [Paid Active Subscribers PY], ABS ( [Paid Active Subscribers PY] ) )
```

### MRR PY  
<sub>format `#,##0` · hidden</sub>

```dax
CALCULATE ( [MRR], TREATAS ( SELECTCOLUMNS ( VALUES ( dim_date[abs_month] ), "abs_month", dim_date[abs_month] - 12 ), dim_date[abs_month] ) )
```

### MRR YoY %  
<sub>format `+0.0%;-0.0%;0.0%`</sub>

```dax
DIVIDE ( [MRR] - [MRR PY], ABS ( [MRR PY] ) )
```

### Total Revenue PY  
<sub>format `#,##0` · hidden</sub>

```dax
CALCULATE ( [Total Revenue], TREATAS ( SELECTCOLUMNS ( VALUES ( dim_date[abs_month] ), "abs_month", dim_date[abs_month] - 12 ), dim_date[abs_month] ) )
```

### Total Revenue YoY %  
<sub>format `+0.0%;-0.0%;0.0%`</sub>

```dax
DIVIDE ( [Total Revenue] - [Total Revenue PY], ABS ( [Total Revenue PY] ) )
```

### Net Adds PY  
<sub>format `#,##0` · hidden</sub>

```dax
CALCULATE ( [Net Adds], TREATAS ( SELECTCOLUMNS ( VALUES ( dim_date[abs_month] ), "abs_month", dim_date[abs_month] - 12 ), dim_date[abs_month] ) )
```

### Net Adds YoY %  
<sub>format `+0.0%;-0.0%;0.0%`</sub>

```dax
DIVIDE ( [Net Adds] - [Net Adds PY], ABS ( [Net Adds PY] ) )
```

### Gross Monthly Churn % PY  
<sub>format `0.0%` · hidden</sub>

```dax
CALCULATE ( [Gross Monthly Churn %], TREATAS ( SELECTCOLUMNS ( VALUES ( dim_date[abs_month] ), "abs_month", dim_date[abs_month] - 12 ), dim_date[abs_month] ) )
```

### Gross Monthly Churn % YoY %  
<sub>format `+0.0%;-0.0%;0.0%`</sub>

```dax
DIVIDE ( [Gross Monthly Churn %] - [Gross Monthly Churn % PY], ABS ( [Gross Monthly Churn % PY] ) )
```

### MRR MoM %  
<sub>format `+0.0%;-0.0%;0.0%`</sub>

```dax
DIVIDE ( [MRR] - CALCULATE ( [MRR], FILTER ( ALL ( dim_date ), dim_date[abs_month] = MAX ( dim_date[abs_month] ) - 1 ) ), CALCULATE ( [MRR], FILTER ( ALL ( dim_date ), dim_date[abs_month] = MAX ( dim_date[abs_month] ) - 1 ) ) )
```

### Total Revenue YTD  
<sub>format `#,##0`</sub>

```dax
CALCULATE (
    [Total Revenue],
    FILTER ( ALL ( dim_date ),
        dim_date[year] = MAX ( dim_date[year] )
        && dim_date[abs_month] <= MAX ( dim_date[abs_month] ) )
)
```

### Total Revenue MAT  
<sub>format `#,##0`</sub>

```dax
CALCULATE (
    [Total Revenue],
    FILTER ( ALL ( dim_date ),
        dim_date[abs_month] > MAX ( dim_date[abs_month] ) - 12
        && dim_date[abs_month] <= MAX ( dim_date[abs_month] ) )
)
```

## 10 Comparable Base

### Paid Active Subscribers (Comparable Base)  
<sub>format `#,##0`</sub>

```dax
CALCULATE ( [Paid Active Subscribers], dim_subscriber[is_comparable_base] = TRUE )
```

### Paid Active Subscribers (Expansion)  
<sub>format `#,##0`</sub>

```dax
CALCULATE ( [Paid Active Subscribers], dim_subscriber[is_comparable_base] = FALSE )
```

### Net Adds (Comparable Base)  
<sub>format `#,##0`</sub>

```dax
CALCULATE ( [Net Adds], dim_subscriber[is_comparable_base] = TRUE )
```

### Net Adds (Expansion)  
<sub>format `#,##0`</sub>

```dax
CALCULATE ( [Net Adds], dim_subscriber[is_comparable_base] = FALSE )
```

### MRR (Comparable Base)  
<sub>format `#,##0`</sub>

```dax
CALCULATE ( [MRR], dim_subscriber[is_comparable_base] = TRUE )
```

### MRR (Expansion)  
<sub>format `#,##0`</sub>

```dax
CALCULATE ( [MRR], dim_subscriber[is_comparable_base] = FALSE )
```

### Gross Monthly Churn % (Comparable Base)  
<sub>format `0.0%`</sub>

```dax
CALCULATE ( [Gross Monthly Churn %], dim_subscriber[is_comparable_base] = TRUE )
```

### Gross Monthly Churn % (Expansion)  
<sub>format `0.0%`</sub>

```dax
CALCULATE ( [Gross Monthly Churn %], dim_subscriber[is_comparable_base] = FALSE )
```

## 11 Targets

### Target Paid Active Subscribers  
<sub>format `#,##0`</sub>

```dax
CALCULATE ( SUM ( fact_targets_month[target_value] ), fact_targets_month[kpi] = "paid_active_subscribers", FILTER ( ALL ( dim_date ), dim_date[abs_month] = CALCULATE ( MAX ( dim_date[abs_month] ), REMOVEFILTERS ( dim_date ), dim_date[in_analysis_window] = TRUE ) ) )
```

### Target MRR  
<sub>format `#,##0`</sub>

```dax
CALCULATE ( SUM ( fact_targets_month[target_value] ), fact_targets_month[kpi] = "mrr_usd", FILTER ( ALL ( dim_date ), dim_date[abs_month] = CALCULATE ( MAX ( dim_date[abs_month] ), REMOVEFILTERS ( dim_date ), dim_date[in_analysis_window] = TRUE ) ) ) * [FX Rate to Reporting]
```

### Target Gross Churn %  
<sub>format `0.0%`</sub>

```dax
DIVIDE ( CALCULATE ( AVERAGE ( fact_targets_month[target_value] ), fact_targets_month[kpi] = "gross_monthly_churn_pct" ), 100 )
```

### Paid Active Subscribers vs Target %  
<sub>format `+0.0%;-0.0%;0.0%`</sub>

Higher is better.

```dax
DIVIDE ( [Paid Active Subscribers (EoP)] - [Target Paid Active Subscribers], [Target Paid Active Subscribers] )
```

### MRR vs Target %  
<sub>format `+0.0%;-0.0%;0.0%`</sub>

Higher is better.

```dax
DIVIDE ( [MRR (Latest)] - [Target MRR], [Target MRR] )
```

### Gross Churn vs Target (pp)  
<sub>format `+0.0%;-0.0%;0.0%`</sub>

LOWER is better — a negative value is good (below target).

```dax
[Gross Monthly Churn %] - [Target Gross Churn %]
```

### Blended CAC vs Target %  
<sub>format `+0.0%;-0.0%;0.0%`</sub>

Target CAC US$22. LOWER is better.

```dax
DIVIDE ( [Blended CAC] - 22, 22 )
```

### Subscribers Lost vs Plan (since shift)  
<sub>format `#,##0`</sub>

Cumulative gap to plan from window-month 34 onward — the board scoreboard.

```dax
CALCULATE (
    [Target Paid Active Subscribers] - [Paid Active Subscribers (EoP)],
    REMOVEFILTERS ( dim_date ),
    dim_date[window_month_idx] >= 33
)
```

## 12 Acquisition

### % New via Low-Quality Channels  
<sub>format `0.0%`</sub>

Affiliate + partner-bundle share of new subscribers.

```dax
DIVIDE (
    CALCULATE ( [New Subscribers],
        dim_subscriber[acquisition_channel] IN { "affiliate", "partner_bundle" } ),
    [New Subscribers]
)
```

### % New Incentivised  
<sub>format `0.0%`</sub>

```dax
DIVIDE ( CALCULATE ( [New Subscribers], dim_subscriber[is_incentivised] = TRUE ), [New Subscribers] )
```

### Marketing Impressions  
<sub>format `#,##0`</sub>

```dax
SUM ( fact_marketing_spend[impressions] )
```

### Signups Attributed  
<sub>format `#,##0`</sub>

```dax
SUM ( fact_marketing_spend[signups_attributed] )
```

### Cohort M3 Retention (context)  
<sub>format `0.0%`</sub>

Alias of M3 Retention % — put acquisition_channel on the axis for channel quality.

```dax
[M3 Retention %]
```

## 13 Support

### Support Tickets  
<sub>format `#,##0`</sub>

```dax
COUNTROWS ( fact_support_ticket )
```

### Tickets per 1,000 Subs  
<sub>format `#,##0`</sub>

```dax
DIVIDE ( [Support Tickets], [Paid Active Subscribers] ) * 1000
```

### CSAT  
<sub>format `0.00`</sub>

Mean post-contact satisfaction rescaled to 1-5.

```dax
AVERAGE ( fact_support_ticket[csat_score] ) * 5
```

### % Tickets App/Tech  
<sub>format `0.0%`</sub>

```dax
DIVIDE ( CALCULATE ( [Support Tickets], fact_support_ticket[reason_group] = "app_tech" ), [Support Tickets] )
```

### % Tickets Billing  
<sub>format `0.0%`</sub>

```dax
DIVIDE ( CALCULATE ( [Support Tickets], fact_support_ticket[reason_group] = "billing" ), [Support Tickets] )
```

## 14 Narrative

### Exec Insight

Dynamic narrative that updates with the slicers; ships in the file (replaces the Smart Narrative visual).

```dax
VAR churn = [Gross Monthly Churn % (Latest)]
VAR base = [Pre-Shift Baseline Churn %]
VAR ratio = DIVIDE ( churn, base )
VAR adds = [Net Adds (Latest)]
VAR br = CALCULATE ( [Gross Monthly Churn % (Latest)], dim_subscriber[market] = "BR" )
VAR mx = CALCULATE ( [Gross Monthly Churn % (Latest)], dim_subscriber[market] = "MX" )
VAR us = CALCULATE ( [Gross Monthly Churn % (Latest)], dim_subscriber[market] = "US" )
VAR worst =
    SWITCH ( TRUE (),
        br >= mx && br >= us, "Brazil",
        mx >= br && mx >= us, "Mexico",
        "the United States" )
RETURN
    "Gross monthly churn is " & FORMAT ( churn, "0.0%" ) & ". "
    & IF (
        ratio >= 1.35,
        "That is about " & FORMAT ( ratio, "0.0" ) & "x the pre-shift baseline of "
            & FORMAT ( base, "0.0%" ) & " and the highest of the three markets is "
            & worst & " (" & FORMAT ( MAX ( MAX ( br, mx ), us ), "0.0%" ) & "). ",
        "That is close to the pre-shift baseline of " & FORMAT ( base, "0.0%" ) & ". " )
    & "Net adds in the latest month: " & FORMAT ( adds, "#,##0" ) & ". "
    & "Reporting currency: " & [Currency Symbol] & "."
```

## 15 Latest Month

### Gross Monthly Churn % (Latest)  
<sub>format `0.0%`</sub>

Value for the last month in the current filter context — for summary KPI cards.

```dax
VAR lastm =
    CALCULATE ( MAX ( dim_date[window_month_idx] ),
        REMOVEFILTERS ( dim_date ), dim_date[in_analysis_window] = TRUE )
RETURN CALCULATE ( [Gross Monthly Churn %],
    FILTER ( ALL ( dim_date ), dim_date[window_month_idx] = lastm ) )
```

### Churn vs Baseline (x) (Latest)  
<sub>format `0.00"x"`</sub>

Value for the last month in the current filter context — for summary KPI cards.

```dax
VAR lastm =
    CALCULATE ( MAX ( dim_date[window_month_idx] ),
        REMOVEFILTERS ( dim_date ), dim_date[in_analysis_window] = TRUE )
RETURN CALCULATE ( [Churn vs Baseline (x)],
    FILTER ( ALL ( dim_date ), dim_date[window_month_idx] = lastm ) )
```

### Net Adds (Latest)  
<sub>format `#,##0`</sub>

Value for the last month in the current filter context — for summary KPI cards.

```dax
VAR lastm =
    CALCULATE ( MAX ( dim_date[window_month_idx] ),
        REMOVEFILTERS ( dim_date ), dim_date[in_analysis_window] = TRUE )
RETURN CALCULATE ( [Net Adds],
    FILTER ( ALL ( dim_date ), dim_date[window_month_idx] = lastm ) )
```

### MRR (Latest)  
<sub>format `#,##0`</sub>

Value for the last month in the current filter context — for summary KPI cards.

```dax
VAR lastm =
    CALCULATE ( MAX ( dim_date[window_month_idx] ),
        REMOVEFILTERS ( dim_date ), dim_date[in_analysis_window] = TRUE )
RETURN CALCULATE ( [MRR],
    FILTER ( ALL ( dim_date ), dim_date[window_month_idx] = lastm ) )
```

### LTV to CAC (Latest)  
<sub>format `0.00`</sub>

Value for the last month in the current filter context — for summary KPI cards.

```dax
VAR lastm =
    CALCULATE ( MAX ( dim_date[window_month_idx] ),
        REMOVEFILTERS ( dim_date ), dim_date[in_analysis_window] = TRUE )
RETURN CALCULATE ( [LTV to CAC],
    FILTER ( ALL ( dim_date ), dim_date[window_month_idx] = lastm ) )
```

### Net MRR Retention % (Latest)  
<sub>format `0.0%`</sub>

Value for the last month in the current filter context — for summary KPI cards.

```dax
VAR lastm =
    CALCULATE ( MAX ( dim_date[window_month_idx] ),
        REMOVEFILTERS ( dim_date ), dim_date[in_analysis_window] = TRUE )
RETURN CALCULATE ( [Net MRR Retention %],
    FILTER ( ALL ( dim_date ), dim_date[window_month_idx] = lastm ) )
```
