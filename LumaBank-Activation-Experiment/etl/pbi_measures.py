"""
pbi_measures.py — the DAX measure library for the LumaBank Activation semantic model.

`MEASURE_LIBRARY` = list of (display_folder, [measure, ...]). Each measure:
    {name, dax, format, folder, description}

`powerbi/gen_semantic_model.py` injects these into `_Measures.tmdl`.
`etl/gen_dax_doc.py` renders `docs/06_dax_measures.md` from the same list.

Conventions
- All money is BRL (none of these measures are money — LumaBank tracks activation and
  risk, not revenue, by design; see docs/00_scope.md §16).
- `fact_activation` is ONE ROW PER SIGNUP, platform-wide — most measures here read it
  with no arm filter for platform-health context, and with `in_analysis_flag` /
  `arm_key` filters for the experiment read-out. Never confuse the two: a measure with
  no `in_analysis_flag` filter answers a platform question; one with it answers an
  experiment question.
- "Latest day" = `MAX(dim_date[date])` in the current filter context. No marked date
  table, no time-intelligence functions (`__PBI_TimeIntelligenceEnabled = 0`) — trailing
  windows use explicit `dim_date[date]` arithmetic.
- The experiment scorecard filters `fact_activation[in_analysis_flag] = TRUE()` — the
  clean re-run population only. Guardrails (KYC rejection, fraud, tickets) are framed as
  non-inferiority deltas: positive = treatment worse, matching doc 01 §8.3's bounds
  (+1.5 pp KYC, +0.5 pp fraud).
- SRM measures read `fact_srm_daily` (one row per experiment × calendar day) and are
  never sliced by arm — `n_control` / `n_treatment` are columns, not a filtered value.
"""
from __future__ import annotations
import textwrap


def M(name, dax, format="", folder="", description=""):
    return {"name": name, "dax": textwrap.dedent(dax).strip(),
            "format": format, "folder": folder, "description": description}


def all_measures():
    for _f, group in MEASURE_LIBRARY:
        yield from group


# ---------------------------------------------------------------------------
PLATFORM = [
    M("Signups",
      "COUNTROWS ( fact_activation )", "#,0", "01 Platform Health",
      "One row per signup (platform-wide) — trends by dim_date via assigned_date_key."),
    M("Active Users",
      """
      VAR maxd = MAX ( dim_date[date] )
      VAR lo   = maxd - 29
      RETURN
      CALCULATE (
          DISTINCTCOUNT ( fact_transaction_day[user_key] ),
          dim_date[date] >= lo, dim_date[date] <= maxd,
          REMOVEFILTERS ( fact_activation )
      )
      """, "#,0", "01 Platform Health",
      "Users with >= 1 transaction in the trailing 30 days ending at the latest date in context."),
    M("Active Rate %",
      "DIVIDE ( [Active Users], [Signups] )", "0.0%", "01 Platform Health"),
    M("Account-Creation Rate %",
      """
      DIVIDE (
          CALCULATE ( COUNTROWS ( fact_activation ), fact_activation[account_opened_flag] = TRUE () ),
          [Signups]
      )
      """, "0.0%", "01 Platform Health", "Signups that ever reach an account, any state."),
]

FUNNEL = [
    M("Funnel Reach",
      "DISTINCTCOUNT ( fact_onboarding_step[user_key] )", "#,0", "02 Onboarding Funnel",
      "Users reaching the step selected by the Onboarding Step slicer."),
    M("Funnel Step Conversion %",
      "DIVIDE ( [Funnel Reach], [Signups] )", "0.0%", "02 Onboarding Funnel",
      "Funnel Reach as a share of all signups — plot by dim_onboarding_step[step_order]."),
    M("KYC-Submit Rate %",
      """
      DIVIDE (
          CALCULATE ( COUNTROWS ( fact_activation ), fact_activation[kyc_submitted_flag] = TRUE () ),
          [Signups]
      )
      """, "0.0%", "02 Onboarding Funnel"),
    M("Median Minutes Signup to Account",
      """
      MEDIANX (
          FILTER ( fact_activation, fact_activation[account_opened_flag] = TRUE () ),
          DATEDIFF ( fact_activation[signup_ts], fact_activation[account_opened_ts], MINUTE )
      )
      """, "#,0", "02 Onboarding Funnel"),
    M("Limited Never-Verified % (Re-run Treatment)",
      """
      VAR base =
          CALCULATE ( COUNTROWS ( fact_activation ),
              fact_activation[in_analysis_flag] = TRUE (), fact_activation[arm_key] = "treatment" )
      VAR nv =
          CALCULATE ( COUNTROWS ( fact_activation ),
              fact_activation[in_analysis_flag] = TRUE (), fact_activation[arm_key] = "treatment",
              fact_activation[account_opened_flag] = TRUE (), fact_activation[kyc_submitted_flag] = FALSE () )
      RETURN DIVIDE ( nv, base )
      """, "0.0%", "02 Onboarding Funnel",
      "Treatment subjects (clean re-run) with an account who never submitted KYC."),
]

ACTIVATION = [
    M("Day-7 Activation Rate %",
      "DIVIDE ( SUM ( fact_activation[day7_activated] ), COUNTROWS ( fact_activation ) )",
      "0.0%", "03 Activation", "PRIMARY METRIC. Account created and first transaction within 7 days of signup."),
    M("Day-1 Activation Rate %",
      "DIVIDE ( SUM ( fact_activation[day1_activated] ), COUNTROWS ( fact_activation ) )",
      "0.0%", "03 Activation"),
    M("Day-30 Activation Rate %",
      "DIVIDE ( SUM ( fact_activation[day30_activated] ), COUNTROWS ( fact_activation ) )",
      "0.0%", "03 Activation"),
    M("Median Hours to First Transaction",
      """
      MEDIANX (
          FILTER ( fact_activation, NOT ISBLANK ( fact_activation[first_txn_ts] ) ),
          fact_activation[hours_to_first_txn]
      )
      """, "#,0", "03 Activation"),
    M("P90 Hours to First Transaction",
      """
      PERCENTILEX.INC (
          FILTER ( fact_activation, NOT ISBLANK ( fact_activation[first_txn_ts] ) ),
          fact_activation[hours_to_first_txn], 0.9
      )
      """, "#,0", "03 Activation"),
]

RISK = [
    M("KYC Rejection Rate %",
      """
      DIVIDE (
          CALCULATE ( COUNTROWS ( fact_activation ), fact_activation[kyc_rejected_flag] = TRUE () ),
          CALCULATE ( COUNTROWS ( fact_activation ), fact_activation[kyc_submitted_flag] = TRUE () )
      )
      """, "0.0%", "04 Risk & Guardrails", "Rejected / KYC submissions. Non-negotiable guardrail."),
    M("KYC Manual-Review Rate %",
      """
      DIVIDE (
          CALCULATE ( COUNTROWS ( fact_kyc_decision ), fact_kyc_decision[is_manual_review] = TRUE () ),
          COUNTROWS ( fact_kyc_decision )
      )
      """, "0.0%", "04 Risk & Guardrails"),
    M("Flagged-Fraud Rate % (30d)",
      """
      DIVIDE (
          CALCULATE ( COUNTROWS ( fact_activation ), fact_activation[fraud_flag_30d] = TRUE () ),
          CALCULATE ( COUNTROWS ( fact_activation ), fact_activation[day7_activated] = 1 )
      )
      """, "0.00%", "04 Risk & Guardrails",
      "Confirmed fraud signals within 30 days / Day-7-activated accounts. Non-negotiable guardrail."),
]

SUPPORT = [
    M("Onboarding Tickets",
      "SUM ( fact_activation[onboarding_tickets_n] )", "#,0", "05 Support & Cost"),
    M("Onboarding Tickets per 1k Signups",
      "DIVIDE ( [Onboarding Tickets], [Signups] ) * 1000", "#,0.0", "05 Support & Cost"),
    M("Onboarding Contact Rate %",
      """
      DIVIDE (
          CALCULATE ( COUNTROWS ( fact_activation ), fact_activation[onboarding_tickets_n] > 0 ),
          [Signups]
      )
      """, "0.0%", "05 Support & Cost"),
]

INTEGRITY = [
    M("SRM P-Value (Cumulative)",
      "AVERAGE ( fact_srm_daily[srm_p_cumulative] )", "0.0000", "06 Experiment Integrity",
      "Pearson chi-square goodness-of-fit vs 50/50, cumulative to the day in context."),
    M("SRM P-Value (Trailing 7d)",
      "AVERAGE ( fact_srm_daily[srm_p_trailing7] )", "0.0000", "06 Experiment Integrity",
      "The test that actually catches a mid-flight break — see docs/01 section 9."),
    M("Allocation Ratio (Treatment Share)",
      """
      DIVIDE (
          SUM ( fact_srm_daily[n_treatment] ),
          SUM ( fact_srm_daily[n_treatment] ) + SUM ( fact_srm_daily[n_control] )
      )
      """, "0.0%", "06 Experiment Integrity", "Expect 50%. The daily line that shows the break."),
    M("Fallback Share %",
      """
      DIVIDE (
          SUM ( fact_srm_daily[n_fallback] ),
          SUM ( fact_srm_daily[n_fallback] ) + SUM ( fact_srm_daily[n_primary] )
      )
      """, "0.0%", "06 Experiment Integrity"),
    M("SRM Worst State (Period)",
      """
      VAR hasAlert = CALCULATE ( COUNTROWS ( fact_srm_daily ), fact_srm_daily[alert_state] = "alert" ) > 0
      VAR hasWarn  = CALCULATE ( COUNTROWS ( fact_srm_daily ), fact_srm_daily[alert_state] = "warn" ) > 0
      RETURN IF ( hasAlert, "ALERT", IF ( hasWarn, "WARN", "OK" ) )
      """, "", "06 Experiment Integrity",
      "Worst alert_state reached anywhere in the current filter — colour this with ALERT_COLORS."),
    M("Contaminated Users",
      "CALCULATE ( COUNTROWS ( fact_activation ), fact_activation[contaminated_flag] = TRUE () )",
      "#,0", "06 Experiment Integrity"),
    M("Snapshot-Log Mismatch (Cumulative)",
      "MAX ( fact_srm_daily[snapshot_log_mismatch_n] )", "#,0", "06 Experiment Integrity"),
    M("Multi-Assignment Users (Cumulative)",
      "MAX ( fact_srm_daily[multi_assignment_n] )", "#,0", "06 Experiment Integrity"),
]

READOUT = [
    M("Exp Subjects",
      "CALCULATE ( COUNTROWS ( fact_activation ), fact_activation[in_analysis_flag] = TRUE () )",
      "#,0", "07 Experiment Readout", "The clean re-run population only."),
    M("Exp Activation Rate",
      """
      DIVIDE (
          CALCULATE ( SUM ( fact_activation[day7_activated] ), fact_activation[in_analysis_flag] = TRUE () ),
          [Exp Subjects]
      )
      """, "0.0%", "07 Experiment Readout"),
    M("Exp Control Rate",
      'CALCULATE ( [Exp Activation Rate], fact_activation[arm_key] = "control" )',
      "0.0%", "07 Experiment Readout"),
    M("Exp Treatment Rate",
      'CALCULATE ( [Exp Activation Rate], fact_activation[arm_key] = "treatment" )',
      "0.0%", "07 Experiment Readout"),
    M("Exp Lift pp",
      "( [Exp Treatment Rate] - [Exp Control Rate] ) * 100", "+0.00;-0.00;0.00", "07 Experiment Readout",
      "Absolute treatment - control difference in Day-7 Activation, in percentage points."),
    M("Exp Lift CI Low pp",
      """
      VAR p1 = [Exp Control Rate]   VAR p2 = [Exp Treatment Rate]
      VAR n1 = CALCULATE ( [Exp Subjects], fact_activation[arm_key] = "control" )
      VAR n2 = CALCULATE ( [Exp Subjects], fact_activation[arm_key] = "treatment" )
      VAR se = SQRT ( DIVIDE ( p1 * ( 1 - p1 ), n1 ) + DIVIDE ( p2 * ( 1 - p2 ), n2 ) )
      RETURN ( ( p2 - p1 ) - 1.959964 * se ) * 100
      """, "+0.00;-0.00;0.00", "07 Experiment Readout"),
    M("Exp Lift CI High pp",
      """
      VAR p1 = [Exp Control Rate]   VAR p2 = [Exp Treatment Rate]
      VAR n1 = CALCULATE ( [Exp Subjects], fact_activation[arm_key] = "control" )
      VAR n2 = CALCULATE ( [Exp Subjects], fact_activation[arm_key] = "treatment" )
      VAR se = SQRT ( DIVIDE ( p1 * ( 1 - p1 ), n1 ) + DIVIDE ( p2 * ( 1 - p2 ), n2 ) )
      RETURN ( ( p2 - p1 ) + 1.959964 * se ) * 100
      """, "+0.00;-0.00;0.00", "07 Experiment Readout"),
    M("Exp Z Stat",
      """
      VAR p1 = [Exp Control Rate]   VAR p2 = [Exp Treatment Rate]
      VAR n1 = CALCULATE ( [Exp Subjects], fact_activation[arm_key] = "control" )
      VAR n2 = CALCULATE ( [Exp Subjects], fact_activation[arm_key] = "treatment" )
      VAR pp = DIVIDE ( p1 * n1 + p2 * n2, n1 + n2 )
      VAR se = SQRT ( pp * ( 1 - pp ) * ( DIVIDE ( 1, n1 ) + DIVIDE ( 1, n2 ) ) )
      RETURN DIVIDE ( p2 - p1, se )
      """, "0.00", "07 Experiment Readout", "Two-proportion pooled z-statistic."),
    M("Exp Significant 95%",
      'IF ( ABS ( [Exp Z Stat] ) > 1.959964, "Significant", "Not significant" )',
      "", "07 Experiment Readout"),
    M("Exp KYC Rejection Delta pp",
      """
      VAR r1 = CALCULATE ( [KYC Rejection Rate %], fact_activation[in_analysis_flag] = TRUE (), fact_activation[arm_key] = "control" )
      VAR r2 = CALCULATE ( [KYC Rejection Rate %], fact_activation[in_analysis_flag] = TRUE (), fact_activation[arm_key] = "treatment" )
      RETURN ( r2 - r1 ) * 100
      """, "+0.00;-0.00;0.00", "07 Experiment Readout",
      "Guardrail: non-inferiority margin is +1.5 pp (doc 01 section 8.3)."),
    M("Exp Fraud Delta pp",
      """
      VAR r1 = CALCULATE ( [Flagged-Fraud Rate % (30d)], fact_activation[in_analysis_flag] = TRUE (), fact_activation[arm_key] = "control" )
      VAR r2 = CALCULATE ( [Flagged-Fraud Rate % (30d)], fact_activation[in_analysis_flag] = TRUE (), fact_activation[arm_key] = "treatment" )
      RETURN ( r2 - r1 ) * 100
      """, "+0.00;-0.00;0.00", "07 Experiment Readout",
      "Guardrail: non-inferiority margin is +0.5 pp (doc 01 section 8.3)."),
    M("Exp Tickets per 1k Delta",
      """
      VAR t1 = CALCULATE ( [Onboarding Tickets per 1k Signups], fact_activation[in_analysis_flag] = TRUE (), fact_activation[arm_key] = "control" )
      VAR t2 = CALCULATE ( [Onboarding Tickets per 1k Signups], fact_activation[in_analysis_flag] = TRUE (), fact_activation[arm_key] = "treatment" )
      RETURN t2 - t1
      """, "+0.0;-0.0;0.0", "07 Experiment Readout", "Guardrail (secondary, directional)."),
    M("Exp Effect by Channel pp",
      "[Exp Lift pp]", "+0.00;-0.00;0.00", "07 Experiment Readout",
      "Same as Exp Lift pp; place on a bar by Acquisition Channel for the heterogeneity cut."),
]

TIME_TGT = [
    M("Day-7 Activation Target %",
      'CALCULATE ( SUM ( fact_targets_month[target_value] ), fact_targets_month[kpi] = "day7_activation_rate" )',
      "0.0%", "08 Time & Targets"),
    M("Day-7 Activation vs Target pp",
      "( [Day-7 Activation Rate %] - [Day-7 Activation Target %] ) * 100", "+0.00;-0.00;0.00", "08 Time & Targets"),
    M("Active Users Target",
      'CALCULATE ( SUM ( fact_targets_month[target_value] ), fact_targets_month[kpi] = "active_users" )',
      "#,0", "08 Time & Targets"),
    M("KYC Rejection Target %",
      'CALCULATE ( SUM ( fact_targets_month[target_value] ), fact_targets_month[kpi] = "kyc_rejection_rate" )',
      "0.0%", "08 Time & Targets", "A ceiling, not a target to beat — lower is not automatically better (doc 01 section 15)."),
]

NARRATIVE = [
    M("Exec Insight",
      """
      VAR d7    = [Day-7 Activation Rate %]
      VAR kyc   = [KYC Rejection Rate %]
      VAR fraud = [Flagged-Fraud Rate % (30d)]
      VAR srm   = [SRM Worst State (Period)]
      RETURN
          "Day-7 Activation is " & FORMAT ( d7, "0.0%" ) &
          ". KYC rejection " & FORMAT ( kyc, "0.0%" ) & ", flagged fraud " & FORMAT ( fraud, "0.00%" ) &
          ". Experiment integrity: " & srm & "."
      """, "", "09 Narrative", "A dynamic one-line summary for the Executive Overview page."),
]

MEASURE_LIBRARY = [
    ("01 Platform Health", PLATFORM),
    ("02 Onboarding Funnel", FUNNEL),
    ("03 Activation", ACTIVATION),
    ("04 Risk & Guardrails", RISK),
    ("05 Support & Cost", SUPPORT),
    ("06 Experiment Integrity", INTEGRITY),
    ("07 Experiment Readout", READOUT),
    ("08 Time & Targets", TIME_TGT),
    ("09 Narrative", NARRATIVE),
]
