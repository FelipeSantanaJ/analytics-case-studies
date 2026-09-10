"""
pbi_measures.py — the DAX measure library for the Voxa+ semantic model.

`MEASURE_LIBRARY` is a list of (display_folder, [measure, ...]). Each measure is a dict:
    {name, dax, format, folder, description, hidden}

`powerbi/gen_semantic_model.py` injects these into `_Measures.tmdl`.
`etl/gen_dax_doc.py` renders `docs/06_dax_measures.md` from the same list.

Time intelligence uses `dim_date[abs_month]` (a linear year*12+month index) so it needs
**no marked date table** and never calls SAMEPERIODLASTYEAR. PY = abs_month - 12.

Monetary measures are computed in USD from the curated `*_usd` columns and multiplied by
`[FX Rate to Reporting]` so the Reporting Currency slicer re-expresses them; `[Currency
Symbol]` is available for labels and the narrative.
"""
from __future__ import annotations
import textwrap


def M(name, dax, format="", folder="", description="", hidden=False):
    return {"name": name, "dax": textwrap.dedent(dax).strip(),
            "format": format, "folder": folder, "description": description, "hidden": hidden}


# ---------------------------------------------------------------------------
# 00 — Reporting currency plumbing
# ---------------------------------------------------------------------------
CURRENCY = [
    M("FX Rate to Reporting",
      """
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
      """, "0.0000", "00 Currency", hidden=True,
      description="USD-to-selected-reporting-currency factor for the current date context."),
    M("Currency Symbol",
      'SELECTEDVALUE ( \'Reporting Currency\'[Symbol], "$" )',
      "", "00 Currency",
      description="Symbol of the selected reporting currency, for labels and the narrative."),
]

# ---------------------------------------------------------------------------
# 01 — Subscribers & churn
# ---------------------------------------------------------------------------
SUBS = [
    M("Paid Active Subscribers",
      """
      AVERAGEX (
          VALUES ( dim_date[window_month_idx] ),
          CALCULATE (
              DISTINCTCOUNT ( fact_subscription_month[subscriber_key] ),
              fact_subscription_month[status] = "active"
          )
      )
      """, "#,##0", "01 Subscribers",
      description="Mean monthly count of subscribers with an in-force paid subscription. North Star."),
    M("Paid Active Subscribers (EoP)",
      """
      VAR lastm =
          CALCULATE ( MAX ( dim_date[window_month_idx] ),
              REMOVEFILTERS ( dim_date ), dim_date[in_analysis_window] = TRUE )
      RETURN
          CALCULATE ( [Paid Active Subscribers],
              FILTER ( ALL ( dim_date ), dim_date[window_month_idx] = lastm ) )
      """, "#,##0", "01 Subscribers",
      description="Active subscribers in the last month of the analysis window (end of period)."),
    M("Active at Start of Month",
      """
      CALCULATE (
          DISTINCTCOUNT ( fact_subscription_month[subscriber_key] ),
          fact_subscription_month[status] = "active",
          FILTER ( ALL ( dim_date ), dim_date[window_month_idx] = MAX ( dim_date[window_month_idx] ) - 1 )
      )
      """, "#,##0", "01 Subscribers", hidden=True),
    M("New Subscribers",
      'CALCULATE ( COUNTROWS ( fact_subscription_month ), fact_subscription_month[is_new] = TRUE )',
      "#,##0", "01 Subscribers", description="First paid billing in the period."),
    M("Reactivations",
      'CALCULATE ( COUNTROWS ( fact_subscription_month ), fact_subscription_month[is_reactivation] = TRUE )',
      "#,##0", "01 Subscribers"),
    M("Voluntary Churned Subscribers",
      'CALCULATE ( COUNTROWS ( fact_subscription_month ), fact_subscription_month[is_voluntary_churn] = TRUE )',
      "#,##0", "01 Subscribers"),
    M("Involuntary Churned Subscribers",
      'CALCULATE ( COUNTROWS ( fact_subscription_month ), fact_subscription_month[is_involuntary_churn] = TRUE )',
      "#,##0", "01 Subscribers"),
    M("Gross Churned Subscribers",
      "[Voluntary Churned Subscribers] + [Involuntary Churned Subscribers]",
      "#,##0", "01 Subscribers"),
    M("Net Adds",
      "[New Subscribers] + [Reactivations] - [Gross Churned Subscribers]",
      "#,##0", "01 Subscribers"),
]

CHURN = [
    M("Gross Monthly Churn %",
      """
      AVERAGEX (
          FILTER ( VALUES ( dim_date[window_month_idx] ),
              dim_date[window_month_idx] >= 0 && dim_date[window_month_idx] <= 35 ),
          DIVIDE ( CALCULATE ( [Gross Churned Subscribers] ), CALCULATE ( [Active at Start of Month] ) )
      )
      """, "0.0%", "02 Churn",
      description="Mean of the monthly (gross churned / start-of-month active) ratios in the period. Watch metric."),
    M("Voluntary Churn %",
      """
      AVERAGEX (
          FILTER ( VALUES ( dim_date[window_month_idx] ),
              dim_date[window_month_idx] >= 0 && dim_date[window_month_idx] <= 35 ),
          DIVIDE ( CALCULATE ( [Voluntary Churned Subscribers] ), CALCULATE ( [Active at Start of Month] ) )
      )
      """, "0.0%", "02 Churn"),
    M("Involuntary Churn %",
      """
      AVERAGEX (
          FILTER ( VALUES ( dim_date[window_month_idx] ),
              dim_date[window_month_idx] >= 0 && dim_date[window_month_idx] <= 35 ),
          DIVIDE ( CALCULATE ( [Involuntary Churned Subscribers] ), CALCULATE ( [Active at Start of Month] ) )
      )
      """, "0.0%", "02 Churn"),
    M("Pre-Shift Baseline Churn %",
      """
      CALCULATE (
          [Gross Monthly Churn %],
          REMOVEFILTERS ( dim_date ),
          dim_date[window_month_idx] >= 24 && dim_date[window_month_idx] <= 32
      )
      """, "0.0%", "02 Churn",
      description="Blended gross monthly churn over window-months 25-33 (the stable pre-shift band)."),
    M("Churn vs Baseline (pp)",
      "[Gross Monthly Churn %] - [Pre-Shift Baseline Churn %]",
      "+0.0%;-0.0%;0.0%", "02 Churn",
      description="Percentage points above (or below) the pre-shift baseline. Higher is worse."),
    M("Churn vs Baseline (x)",
      "DIVIDE ( [Gross Monthly Churn %], [Pre-Shift Baseline Churn %] )",
      "0.00\"x\"", "02 Churn"),
    M("Net MRR Retention %",
      """
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
      """, "0.0%", "02 Churn",
      description="MRR from the cohort active 12 months ago, now vs then (incl. up/downgrades and churn)."),
]

# ---------------------------------------------------------------------------
# 03 — Cohort retention
# ---------------------------------------------------------------------------
COHORT = [
    M("Cohort Size",
      'CALCULATE ( DISTINCTCOUNT ( fact_subscription_month[subscriber_key] ), fact_subscription_month[tenure_months] = 0 )',
      "#,##0", "03 Cohorts",
      description="Subscribers at tenure month 0 in the current filter context (use with a cohort slicer)."),
    M("Active Subscribers at Tenure",
      'CALCULATE ( DISTINCTCOUNT ( fact_subscription_month[subscriber_key] ), fact_subscription_month[status] = "active" )',
      "#,##0", "03 Cohorts", hidden=True),
    M("Retention %",
      """
      DIVIDE (
          [Active Subscribers at Tenure],
          CALCULATE ( [Cohort Size], REMOVEFILTERS ( fact_subscription_month[tenure_months] ) )
      )
      """, "0.0%", "03 Cohorts",
      description="Share of a cohort still active — put cohort_month on rows and tenure_months on columns."),
    M("M1 Retention %",
      """
      VAR c0 = [Cohort Size]
      VAR c1 = CALCULATE ( DISTINCTCOUNT ( fact_subscription_month[subscriber_key] ),
                   fact_subscription_month[tenure_months] = 1, fact_subscription_month[status] = "active",
                   REMOVEFILTERS ( fact_subscription_month[tenure_months] ) )
      RETURN DIVIDE ( c1, c0 )
      """, "0.0%", "03 Cohorts"),
    M("M3 Retention %",
      """
      VAR c0 = [Cohort Size]
      VAR c3 = CALCULATE ( DISTINCTCOUNT ( fact_subscription_month[subscriber_key] ),
                   fact_subscription_month[tenure_months] = 3, fact_subscription_month[status] = "active",
                   REMOVEFILTERS ( fact_subscription_month[tenure_months] ) )
      RETURN DIVIDE ( c3, c0 )
      """, "0.0%", "03 Cohorts"),
    M("M6 Retention %",
      """
      VAR c0 = [Cohort Size]
      VAR c6 = CALCULATE ( DISTINCTCOUNT ( fact_subscription_month[subscriber_key] ),
                   fact_subscription_month[tenure_months] = 6, fact_subscription_month[status] = "active",
                   REMOVEFILTERS ( fact_subscription_month[tenure_months] ) )
      RETURN DIVIDE ( c6, c0 )
      """, "0.0%", "03 Cohorts"),
    M("M12 Retention %",
      """
      VAR c0 = [Cohort Size]
      VAR c12 = CALCULATE ( DISTINCTCOUNT ( fact_subscription_month[subscriber_key] ),
                   fact_subscription_month[tenure_months] = 12, fact_subscription_month[status] = "active",
                   REMOVEFILTERS ( fact_subscription_month[tenure_months] ) )
      RETURN DIVIDE ( c12, c0 )
      """, "0.0%", "03 Cohorts"),
]

# ---------------------------------------------------------------------------
# 04 — Engagement
# ---------------------------------------------------------------------------
ENGAGEMENT = [
    M("Streamed Hours", 'SUM ( fact_engagement_month[streamed_hours] )', "#,##0", "04 Engagement"),
    M("Streaming Subscribers",
      'DISTINCTCOUNT ( fact_engagement_month[subscriber_key] )', "#,##0", "04 Engagement", hidden=True),
    M("Monthly Active Rate %",
      'DIVIDE ( [Streaming Subscribers], [Paid Active Subscribers] )', "0.0%", "04 Engagement",
      description="Share of paid subscribers who streamed at least once in the month."),
    M("Viewing Hours per Active Sub",
      'DIVIDE ( [Streamed Hours], [Streaming Subscribers] )', "0.0", "04 Engagement"),
    M("% Subs Below Healthy Engagement",
      """
      DIVIDE (
          CALCULATE ( DISTINCTCOUNT ( fact_engagement_month[subscriber_key] ),
              fact_engagement_month[below_healthy_engagement] = TRUE ),
          [Streaming Subscribers]
      )
      """, "0.0%", "04 Engagement",
      description="Streaming subscribers with < 5 hours this month — a leading indicator of churn."),
    M("Titles Started per Active Sub",
      'DIVIDE ( SUM ( fact_engagement_month[distinct_titles] ), [Streaming Subscribers] )',
      "0.0", "04 Engagement"),
    M("Avg % Days on Connected TV",
      'AVERAGE ( fact_engagement_month[pct_days_ctv] )', "0.0%", "04 Engagement"),
    # device-level (fact_engagement_device_month)
    M("Streamed Hours (by Device)", 'SUM ( fact_engagement_device_month[streamed_hours] )',
      "#,##0", "04 Engagement"),
    M("Video Start Failure Rate",
      'DIVIDE ( SUM ( fact_engagement_device_month[video_start_failures] ), SUM ( fact_engagement_device_month[play_starts] ) )',
      "0.00%", "04 Engagement",
      description="Play attempts that never start, by device family / market."),
    M("Playback Error Rate",
      'DIVIDE ( SUM ( fact_engagement_device_month[playback_errors] ), SUM ( fact_engagement_device_month[play_starts] ) )',
      "0.00%", "04 Engagement"),
    M("Rebuffer Ratio",
      'AVERAGE ( fact_engagement_device_month[rebuffer_ratio] )', "0.00%", "04 Engagement"),
]

# ---------------------------------------------------------------------------
# 05 — App quality
# ---------------------------------------------------------------------------
APP = [
    M("App Sessions", 'SUM ( fact_app_performance_daily[sessions] )', "#,##0", "05 App Quality"),
    M("Crashes", 'SUM ( fact_app_performance_daily[crashes] )', "#,##0", "05 App Quality"),
    M("Crash-Free Session Rate %",
      'DIVIDE ( [App Sessions] - [Crashes], [App Sessions] )', "0.00%", "05 App Quality"),
    M("% Sessions on App v3",
      """
      DIVIDE (
          CALCULATE ( [App Sessions], dim_app_version[is_v3] = TRUE ),
          [App Sessions]
      )
      """, "0.0%", "05 App Quality"),
]

# ---------------------------------------------------------------------------
# 06 — Payments & dunning
# ---------------------------------------------------------------------------
PAYMENTS = [
    M("Billing Attempts", 'COUNTROWS ( fact_billing_attempt )', "#,##0", "06 Payments"),
    M("Approved Attempts",
      'CALCULATE ( [Billing Attempts], fact_billing_attempt[status] = "approved" )', "#,##0", "06 Payments"),
    M("Failed Attempts",
      'CALCULATE ( [Billing Attempts], fact_billing_attempt[status] = "failed" )', "#,##0", "06 Payments"),
    M("Payment Failure Rate %",
      """
      DIVIDE (
          CALCULATE ( [Failed Attempts], fact_billing_attempt[is_dunning] = FALSE ),
          CALCULATE ( [Billing Attempts], fact_billing_attempt[is_dunning] = FALSE )
      )
      """, "0.0%", "06 Payments",
      description="First-attempt billing failures (excludes dunning retries)."),
    M("Authorization Rate %",
      'DIVIDE ( [Approved Attempts], [Billing Attempts] )', "0.0%", "06 Payments",
      description="Approved / attempted — slice by payment method."),
    M("Dunning Recovery Rate %",
      """
      DIVIDE (
          CALCULATE ( [Approved Attempts], fact_billing_attempt[is_dunning] = TRUE ),
          CALCULATE ( [Billing Attempts], fact_billing_attempt[is_dunning] = TRUE )
      )
      """, "0.0%", "06 Payments"),
    M("Processing Cost",
      'SUM ( fact_billing_attempt[processing_cost_usd] ) * [FX Rate to Reporting]',
      "#,##0", "06 Payments"),
]

# ---------------------------------------------------------------------------
# 07 — Revenue & margin
# ---------------------------------------------------------------------------
def _pnl(line, positive=True):
    sign = "" if positive else "-1 * "
    return (f'{sign}CALCULATE ( SUM ( fact_finance_month[amount_usd] ), '
            f'fact_finance_month[pnl_line] = "{line}" ) * [FX Rate to Reporting]')

REVENUE = [
    M("MRR",
      'CALCULATE ( SUM ( fact_subscription_month[mrr_usd] ), fact_subscription_month[status] = "active" ) * [FX Rate to Reporting]',
      "#,##0", "07 Revenue"),
    M("ARPU", 'DIVIDE ( [MRR], [Paid Active Subscribers] )', "#,##0.00", "07 Revenue"),
    M("Subscription Revenue", _pnl("subscription_revenue"), "#,##0", "07 Revenue"),
    M("Advertising Revenue", _pnl("advertising_revenue"), "#,##0", "07 Revenue"),
    M("Partner Revenue", _pnl("partner_revenue"), "#,##0", "07 Revenue"),
    M("Total Revenue", "[Subscription Revenue] + [Advertising Revenue] + [Partner Revenue]",
      "#,##0", "07 Revenue"),
    M("Content Amortisation", _pnl("content_amortization", positive=False), "#,##0", "07 Revenue"),
    M("CDN Cost", _pnl("streaming_delivery", positive=False), "#,##0", "07 Revenue"),
    M("Payment Cost", _pnl("payment_processing", positive=False), "#,##0", "07 Revenue"),
    M("Support Cost", _pnl("customer_support", positive=False), "#,##0", "07 Revenue"),
    M("Marketing Spend", 'SUM ( fact_marketing_spend[spend_usd] ) * [FX Rate to Reporting]',
      "#,##0", "07 Revenue"),
    M("Gross Profit",
      "[Total Revenue] - [Content Amortisation] - [CDN Cost] - [Payment Cost] - [Support Cost]",
      "#,##0", "07 Revenue"),
    M("Gross Margin %", "DIVIDE ( [Gross Profit], [Total Revenue] )", "0.0%", "07 Revenue"),
    M("Contribution Margin", "[Gross Profit] - [Marketing Spend]", "#,##0", "07 Revenue"),
    M("Contribution Margin % (T12M)",
      """
      VAR c = MAX ( dim_date[abs_month] )
      VAR flt = FILTER ( ALL ( dim_date ), dim_date[abs_month] > c - 12 && dim_date[abs_month] <= c )
      RETURN DIVIDE ( CALCULATE ( [Contribution Margin], flt ), CALCULATE ( [Total Revenue], flt ) )
      """, "0.0%", "07 Revenue"),
]

# ---------------------------------------------------------------------------
# 08 — Unit economics
# ---------------------------------------------------------------------------
UNIT = [
    M("Blended CAC", 'DIVIDE ( [Marketing Spend], [New Subscribers] )', "#,##0.00", "08 Unit Economics"),
    M("Expected Lifetime (months)", 'DIVIDE ( 1, [Gross Monthly Churn %] )', "0.0", "08 Unit Economics"),
    M("LTV", 'MAX ( 0, [ARPU] * [Gross Margin %] * [Expected Lifetime (months)] )',
      "#,##0.00", "08 Unit Economics"),
    M("LTV to CAC", 'DIVIDE ( [LTV], [Blended CAC] )', "0.00", "08 Unit Economics"),
    M("CAC Payback (months)",
      'DIVIDE ( [Blended CAC], [ARPU] * [Gross Margin %] )', "0.0", "08 Unit Economics"),
]

# ---------------------------------------------------------------------------
# 09 — Time intelligence (PY = abs_month - 12; no marked date table)
# ---------------------------------------------------------------------------
def _py(measure):
    return (f'CALCULATE ( [{measure}], '
            f'TREATAS ( SELECTCOLUMNS ( VALUES ( dim_date[abs_month] ), "abs_month", dim_date[abs_month] - 12 ), '
            f'dim_date[abs_month] ) )')

def _mom(measure):
    return (f'CALCULATE ( [{measure}], '
            f'FILTER ( ALL ( dim_date ), dim_date[abs_month] = MAX ( dim_date[abs_month] ) - 1 ) )')

TIME = []
for base in ["Paid Active Subscribers", "MRR", "Total Revenue", "Net Adds", "Gross Monthly Churn %"]:
    TIME.append(M(f"{base} PY", _py(base),
                  "#,##0" if "%" not in base else "0.0%", "09 Time Intelligence", hidden=True))
    TIME.append(M(f"{base} YoY %",
                  f'DIVIDE ( [{base}] - [{base} PY], ABS ( [{base} PY] ) )',
                  "+0.0%;-0.0%;0.0%", "09 Time Intelligence"))
TIME += [
    M("MRR MoM %",
      f'DIVIDE ( [MRR] - {_mom("MRR")}, {_mom("MRR")} )',
      "+0.0%;-0.0%;0.0%", "09 Time Intelligence"),
    M("Total Revenue YTD",
      """
      CALCULATE (
          [Total Revenue],
          FILTER ( ALL ( dim_date ),
              dim_date[year] = MAX ( dim_date[year] )
              && dim_date[abs_month] <= MAX ( dim_date[abs_month] ) )
      )
      """, "#,##0", "09 Time Intelligence"),
    M("Total Revenue MAT",
      """
      CALCULATE (
          [Total Revenue],
          FILTER ( ALL ( dim_date ),
              dim_date[abs_month] > MAX ( dim_date[abs_month] ) - 12
              && dim_date[abs_month] <= MAX ( dim_date[abs_month] ) )
      )
      """, "#,##0", "09 Time Intelligence"),
]

# ---------------------------------------------------------------------------
# 10 — Comparable Base vs Expansion
# ---------------------------------------------------------------------------
CB = []
for base in ["Paid Active Subscribers", "Net Adds", "MRR", "Gross Monthly Churn %"]:
    CB.append(M(f"{base} (Comparable Base)",
                f'CALCULATE ( [{base}], dim_subscriber[is_comparable_base] = TRUE )',
                "#,##0" if "%" not in base else "0.0%", "10 Comparable Base"))
    CB.append(M(f"{base} (Expansion)",
                f'CALCULATE ( [{base}], dim_subscriber[is_comparable_base] = FALSE )',
                "#,##0" if "%" not in base else "0.0%", "10 Comparable Base"))

# ---------------------------------------------------------------------------
# 11 — Targets vs plan  (churn & CAC scored lower-is-better)
# ---------------------------------------------------------------------------
def _target(kpi):
    # pin to the last month *inside the analysis window* — an unbounded MAX(abs_month)
    # lands on the padded end of dim_date (Dec 2027), where fact_targets_month has no row
    # and the measure collapses to BLANK.
    return (f'CALCULATE ( SUM ( fact_targets_month[target_value] ), fact_targets_month[kpi] = "{kpi}", '
            f'FILTER ( ALL ( dim_date ), dim_date[abs_month] = '
            f'CALCULATE ( MAX ( dim_date[abs_month] ), REMOVEFILTERS ( dim_date ), '
            f'dim_date[in_analysis_window] = TRUE ) ) )')

TARGETS = [
    M("Target Paid Active Subscribers", _target("paid_active_subscribers"), "#,##0", "11 Targets"),
    M("Target MRR",
      f'{_target("mrr_usd")} * [FX Rate to Reporting]', "#,##0", "11 Targets"),
    M("Target Gross Churn %",
      'DIVIDE ( CALCULATE ( AVERAGE ( fact_targets_month[target_value] ), fact_targets_month[kpi] = "gross_monthly_churn_pct" ), 100 )',
      "0.0%", "11 Targets"),
    M("Paid Active Subscribers vs Target %",
      'DIVIDE ( [Paid Active Subscribers (EoP)] - [Target Paid Active Subscribers], [Target Paid Active Subscribers] )',
      "+0.0%;-0.0%;0.0%", "11 Targets",
      description="Higher is better."),
    M("MRR vs Target %",
      'DIVIDE ( [MRR (Latest)] - [Target MRR], [Target MRR] )', "+0.0%;-0.0%;0.0%", "11 Targets",
      description="Higher is better."),
    M("Gross Churn vs Target (pp)",
      '[Gross Monthly Churn %] - [Target Gross Churn %]', "+0.0%;-0.0%;0.0%", "11 Targets",
      description="LOWER is better — a negative value is good (below target)."),
    M("Blended CAC vs Target %",
      'DIVIDE ( [Blended CAC] - 22, 22 )', "+0.0%;-0.0%;0.0%", "11 Targets",
      description="Target CAC US$22. LOWER is better."),
    M("Subscribers Lost vs Plan (since shift)",
      """
      CALCULATE (
          [Target Paid Active Subscribers] - [Paid Active Subscribers (EoP)],
          REMOVEFILTERS ( dim_date ),
          dim_date[window_month_idx] >= 33
      )
      """, "#,##0", "11 Targets",
      description="Cumulative gap to plan from window-month 34 onward — the board scoreboard."),
]

# ---------------------------------------------------------------------------
# 12 — Acquisition quality
# ---------------------------------------------------------------------------
ACQ = [
    M("% New via Low-Quality Channels",
      """
      DIVIDE (
          CALCULATE ( [New Subscribers],
              dim_subscriber[acquisition_channel] IN { "affiliate", "partner_bundle" } ),
          [New Subscribers]
      )
      """, "0.0%", "12 Acquisition",
      description="Affiliate + partner-bundle share of new subscribers."),
    M("% New Incentivised",
      'DIVIDE ( CALCULATE ( [New Subscribers], dim_subscriber[is_incentivised] = TRUE ), [New Subscribers] )',
      "0.0%", "12 Acquisition"),
    M("Marketing Impressions", 'SUM ( fact_marketing_spend[impressions] )', "#,##0", "12 Acquisition"),
    M("Signups Attributed", 'SUM ( fact_marketing_spend[signups_attributed] )', "#,##0", "12 Acquisition"),
    M("Cohort M3 Retention (context)",
      "[M3 Retention %]", "0.0%", "12 Acquisition",
      description="Alias of M3 Retention % — put acquisition_channel on the axis for channel quality."),
]

# ---------------------------------------------------------------------------
# 13 — CX & support
# ---------------------------------------------------------------------------
SUPPORT = [
    M("Support Tickets", 'COUNTROWS ( fact_support_ticket )', "#,##0", "13 Support"),
    M("Tickets per 1,000 Subs",
      'DIVIDE ( [Support Tickets], [Paid Active Subscribers] ) * 1000', "#,##0", "13 Support"),
    M("CSAT", 'AVERAGE ( fact_support_ticket[csat_score] ) * 5', "0.00", "13 Support",
      description="Mean post-contact satisfaction rescaled to 1-5."),
    M("% Tickets App/Tech",
      'DIVIDE ( CALCULATE ( [Support Tickets], fact_support_ticket[reason_group] = "app_tech" ), [Support Tickets] )',
      "0.0%", "13 Support"),
    M("% Tickets Billing",
      'DIVIDE ( CALCULATE ( [Support Tickets], fact_support_ticket[reason_group] = "billing" ), [Support Tickets] )',
      "0.0%", "13 Support"),
]

# ---------------------------------------------------------------------------
# 14 — Narrative
# ---------------------------------------------------------------------------
NARRATIVE = [
    M("Exec Insight",
      """
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
      """, "", "14 Narrative",
      description="Dynamic narrative that updates with the slicers; ships in the file (replaces the Smart Narrative visual)."),
]

# ---------------------------------------------------------------------------
# 15 — "Latest month" wrappers for summary-page KPI cards
# ---------------------------------------------------------------------------
def _latest(measure):
    return (
        "VAR lastm =\n"
        "    CALCULATE ( MAX ( dim_date[window_month_idx] ),\n"
        "        REMOVEFILTERS ( dim_date ), dim_date[in_analysis_window] = TRUE )\n"
        f"RETURN CALCULATE ( [{measure}],\n"
        "    FILTER ( ALL ( dim_date ), dim_date[window_month_idx] = lastm ) )")

LATEST = [
    M(f"{b} (Latest)", _latest(b),
      "0.0%" if "%" in b and "x)" not in b else ("0.00\"x\"" if "(x)" in b else
       ("0.00" if b == "LTV to CAC" else "#,##0")),
      "15 Latest Month",
      description="Value for the last month in the current filter context — for summary KPI cards.")
    for b in ["Gross Monthly Churn %", "Churn vs Baseline (x)", "Net Adds", "MRR",
              "LTV to CAC", "Net MRR Retention %"]
]

MEASURE_LIBRARY = [
    ("00 Currency", CURRENCY),
    ("01 Subscribers", SUBS),
    ("02 Churn", CHURN),
    ("03 Cohorts", COHORT),
    ("04 Engagement", ENGAGEMENT),
    ("05 App Quality", APP),
    ("06 Payments", PAYMENTS),
    ("07 Revenue", REVENUE),
    ("08 Unit Economics", UNIT),
    ("09 Time Intelligence", TIME),
    ("10 Comparable Base", CB),
    ("11 Targets", TARGETS),
    ("12 Acquisition", ACQ),
    ("13 Support", SUPPORT),
    ("14 Narrative", NARRATIVE),
    ("15 Latest Month", LATEST),
]


def all_measures():
    for _, group in MEASURE_LIBRARY:
        for m in group:
            yield m


if __name__ == "__main__":
    n = sum(1 for _ in all_measures())
    print(f"{n} measures in {len(MEASURE_LIBRARY)} folders")
    for folder, group in MEASURE_LIBRARY:
        print(f"  {folder}: {len(group)}")
