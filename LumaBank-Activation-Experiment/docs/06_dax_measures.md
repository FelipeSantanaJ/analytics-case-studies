# LumaBank — DAX Measure Library

_Auto-generated from `etl/pbi_measures.py` on 2026-09-10 by `etl/gen_dax_doc.py`. Do not edit by hand._

**46 measures** in the `_Measures` table, injected into the semantic model by `powerbi/gen_semantic_model.py`.

**Conventions**

- `fact_activation` is **one row per signup, platform-wide** — most measures here carry no arm filter (platform-health questions); the Experiment Readout group filters `in_analysis_flag = TRUE()` (the clean re-run population only).
- "Latest day" = `MAX(dim_date[date])` in the current filter context. No marked date table, no time-intelligence functions — trailing windows use explicit `dim_date[date]` arithmetic.
- SRM measures read `fact_srm_daily` (one row per experiment x calendar day) and are never sliced by arm.
- **KYC rejection rate, fraud flag rate, and onboarding tickets are lower-is-better** — guardrail delta measures are framed so positive = treatment worse, matching the non-inferiority bounds in doc 01 section 8.3 (+1.5 pp KYC, +0.5 pp fraud).

---

## 01 Platform Health

### Signups  
<sub>format `#,0`</sub>

One row per signup (platform-wide) — trends by dim_date via assigned_date_key.

```dax
COUNTROWS ( fact_activation )
```

### Active Users  
<sub>format `#,0`</sub>

Users with >= 1 transaction in the trailing 30 days ending at the latest date in context.

```dax
VAR maxd = MAX ( dim_date[date] )
VAR lo   = maxd - 29
RETURN
CALCULATE (
    DISTINCTCOUNT ( fact_transaction_day[user_key] ),
    dim_date[date] >= lo, dim_date[date] <= maxd,
    REMOVEFILTERS ( fact_activation )
)
```

### Active Rate %  
<sub>format `0.0%`</sub>

```dax
DIVIDE ( [Active Users], [Signups] )
```

### Account-Creation Rate %  
<sub>format `0.0%`</sub>

Signups that ever reach an account, any state.

```dax
DIVIDE (
    CALCULATE ( COUNTROWS ( fact_activation ), fact_activation[account_opened_flag] = TRUE () ),
    [Signups]
)
```

## 02 Onboarding Funnel

### Funnel Reach  
<sub>format `#,0`</sub>

Users reaching the step selected by the Onboarding Step slicer.

```dax
DISTINCTCOUNT ( fact_onboarding_step[user_key] )
```

### Funnel Step Conversion %  
<sub>format `0.0%`</sub>

Funnel Reach as a share of all signups — plot by dim_onboarding_step[step_order].

```dax
DIVIDE ( [Funnel Reach], [Signups] )
```

### KYC-Submit Rate %  
<sub>format `0.0%`</sub>

```dax
DIVIDE (
    CALCULATE ( COUNTROWS ( fact_activation ), fact_activation[kyc_submitted_flag] = TRUE () ),
    [Signups]
)
```

### Median Minutes Signup to Account  
<sub>format `#,0`</sub>

```dax
MEDIANX (
    FILTER ( fact_activation, fact_activation[account_opened_flag] = TRUE () ),
    DATEDIFF ( fact_activation[signup_ts], fact_activation[account_opened_ts], MINUTE )
)
```

### Limited Never-Verified % (Re-run Treatment)  
<sub>format `0.0%`</sub>

Treatment subjects (clean re-run) with an account who never submitted KYC.

```dax
VAR base =
    CALCULATE ( COUNTROWS ( fact_activation ),
        fact_activation[in_analysis_flag] = TRUE (), fact_activation[arm_key] = "treatment" )
VAR nv =
    CALCULATE ( COUNTROWS ( fact_activation ),
        fact_activation[in_analysis_flag] = TRUE (), fact_activation[arm_key] = "treatment",
        fact_activation[account_opened_flag] = TRUE (), fact_activation[kyc_submitted_flag] = FALSE () )
RETURN DIVIDE ( nv, base )
```

## 03 Activation

### Day-7 Activation Rate %  
<sub>format `0.0%`</sub>

PRIMARY METRIC. Account created and first transaction within 7 days of signup.

```dax
DIVIDE ( SUM ( fact_activation[day7_activated] ), COUNTROWS ( fact_activation ) )
```

### Day-1 Activation Rate %  
<sub>format `0.0%`</sub>

```dax
DIVIDE ( SUM ( fact_activation[day1_activated] ), COUNTROWS ( fact_activation ) )
```

### Day-30 Activation Rate %  
<sub>format `0.0%`</sub>

```dax
DIVIDE ( SUM ( fact_activation[day30_activated] ), COUNTROWS ( fact_activation ) )
```

### Median Hours to First Transaction  
<sub>format `#,0`</sub>

```dax
MEDIANX (
    FILTER ( fact_activation, NOT ISBLANK ( fact_activation[first_txn_ts] ) ),
    fact_activation[hours_to_first_txn]
)
```

### P90 Hours to First Transaction  
<sub>format `#,0`</sub>

```dax
PERCENTILEX.INC (
    FILTER ( fact_activation, NOT ISBLANK ( fact_activation[first_txn_ts] ) ),
    fact_activation[hours_to_first_txn], 0.9
)
```

## 04 Risk & Guardrails

### KYC Rejection Rate %  
<sub>format `0.0%`</sub>

Rejected / KYC submissions. Non-negotiable guardrail.

```dax
DIVIDE (
    CALCULATE ( COUNTROWS ( fact_activation ), fact_activation[kyc_rejected_flag] = TRUE () ),
    CALCULATE ( COUNTROWS ( fact_activation ), fact_activation[kyc_submitted_flag] = TRUE () )
)
```

### KYC Manual-Review Rate %  
<sub>format `0.0%`</sub>

```dax
DIVIDE (
    CALCULATE ( COUNTROWS ( fact_kyc_decision ), fact_kyc_decision[is_manual_review] = TRUE () ),
    COUNTROWS ( fact_kyc_decision )
)
```

### Flagged-Fraud Rate % (30d)  
<sub>format `0.00%`</sub>

Confirmed fraud signals within 30 days / Day-7-activated accounts. Non-negotiable guardrail.

```dax
DIVIDE (
    CALCULATE ( COUNTROWS ( fact_activation ), fact_activation[fraud_flag_30d] = TRUE () ),
    CALCULATE ( COUNTROWS ( fact_activation ), fact_activation[day7_activated] = 1 )
)
```

## 05 Support & Cost

### Onboarding Tickets  
<sub>format `#,0`</sub>

```dax
SUM ( fact_activation[onboarding_tickets_n] )
```

### Onboarding Tickets per 1k Signups  
<sub>format `#,0.0`</sub>

```dax
DIVIDE ( [Onboarding Tickets], [Signups] ) * 1000
```

### Onboarding Contact Rate %  
<sub>format `0.0%`</sub>

```dax
DIVIDE (
    CALCULATE ( COUNTROWS ( fact_activation ), fact_activation[onboarding_tickets_n] > 0 ),
    [Signups]
)
```

## 06 Experiment Integrity

### SRM P-Value (Cumulative)  
<sub>format `0.0000`</sub>

Pearson chi-square goodness-of-fit vs 50/50, cumulative to the day in context.

```dax
AVERAGE ( fact_srm_daily[srm_p_cumulative] )
```

### SRM P-Value (Trailing 7d)  
<sub>format `0.0000`</sub>

The test that actually catches a mid-flight break — see docs/01 section 9.

```dax
AVERAGE ( fact_srm_daily[srm_p_trailing7] )
```

### Allocation Ratio (Treatment Share)  
<sub>format `0.0%`</sub>

Expect 50%. The daily line that shows the break.

```dax
DIVIDE (
    SUM ( fact_srm_daily[n_treatment] ),
    SUM ( fact_srm_daily[n_treatment] ) + SUM ( fact_srm_daily[n_control] )
)
```

### Fallback Share %  
<sub>format `0.0%`</sub>

```dax
DIVIDE (
    SUM ( fact_srm_daily[n_fallback] ),
    SUM ( fact_srm_daily[n_fallback] ) + SUM ( fact_srm_daily[n_primary] )
)
```

### SRM Worst State (Period)

Worst alert_state reached anywhere in the current filter — colour this with ALERT_COLORS.

```dax
VAR hasAlert = CALCULATE ( COUNTROWS ( fact_srm_daily ), fact_srm_daily[alert_state] = "alert" ) > 0
VAR hasWarn  = CALCULATE ( COUNTROWS ( fact_srm_daily ), fact_srm_daily[alert_state] = "warn" ) > 0
RETURN IF ( hasAlert, "ALERT", IF ( hasWarn, "WARN", "OK" ) )
```

### Contaminated Users  
<sub>format `#,0`</sub>

```dax
CALCULATE ( COUNTROWS ( fact_activation ), fact_activation[contaminated_flag] = TRUE () )
```

### Snapshot-Log Mismatch (Cumulative)  
<sub>format `#,0`</sub>

```dax
MAX ( fact_srm_daily[snapshot_log_mismatch_n] )
```

### Multi-Assignment Users (Cumulative)  
<sub>format `#,0`</sub>

```dax
MAX ( fact_srm_daily[multi_assignment_n] )
```

## 07 Experiment Readout

### Exp Subjects  
<sub>format `#,0`</sub>

The clean re-run population only.

```dax
CALCULATE ( COUNTROWS ( fact_activation ), fact_activation[in_analysis_flag] = TRUE () )
```

### Exp Activation Rate  
<sub>format `0.0%`</sub>

```dax
DIVIDE (
    CALCULATE ( SUM ( fact_activation[day7_activated] ), fact_activation[in_analysis_flag] = TRUE () ),
    [Exp Subjects]
)
```

### Exp Control Rate  
<sub>format `0.0%`</sub>

```dax
CALCULATE ( [Exp Activation Rate], fact_activation[arm_key] = "control" )
```

### Exp Treatment Rate  
<sub>format `0.0%`</sub>

```dax
CALCULATE ( [Exp Activation Rate], fact_activation[arm_key] = "treatment" )
```

### Exp Lift pp  
<sub>format `+0.00;-0.00;0.00`</sub>

Absolute treatment - control difference in Day-7 Activation, in percentage points.

```dax
( [Exp Treatment Rate] - [Exp Control Rate] ) * 100
```

### Exp Lift CI Low pp  
<sub>format `+0.00;-0.00;0.00`</sub>

```dax
VAR p1 = [Exp Control Rate]   VAR p2 = [Exp Treatment Rate]
VAR n1 = CALCULATE ( [Exp Subjects], fact_activation[arm_key] = "control" )
VAR n2 = CALCULATE ( [Exp Subjects], fact_activation[arm_key] = "treatment" )
VAR se = SQRT ( DIVIDE ( p1 * ( 1 - p1 ), n1 ) + DIVIDE ( p2 * ( 1 - p2 ), n2 ) )
RETURN ( ( p2 - p1 ) - 1.959964 * se ) * 100
```

### Exp Lift CI High pp  
<sub>format `+0.00;-0.00;0.00`</sub>

```dax
VAR p1 = [Exp Control Rate]   VAR p2 = [Exp Treatment Rate]
VAR n1 = CALCULATE ( [Exp Subjects], fact_activation[arm_key] = "control" )
VAR n2 = CALCULATE ( [Exp Subjects], fact_activation[arm_key] = "treatment" )
VAR se = SQRT ( DIVIDE ( p1 * ( 1 - p1 ), n1 ) + DIVIDE ( p2 * ( 1 - p2 ), n2 ) )
RETURN ( ( p2 - p1 ) + 1.959964 * se ) * 100
```

### Exp Z Stat  
<sub>format `0.00`</sub>

Two-proportion pooled z-statistic.

```dax
VAR p1 = [Exp Control Rate]   VAR p2 = [Exp Treatment Rate]
VAR n1 = CALCULATE ( [Exp Subjects], fact_activation[arm_key] = "control" )
VAR n2 = CALCULATE ( [Exp Subjects], fact_activation[arm_key] = "treatment" )
VAR pp = DIVIDE ( p1 * n1 + p2 * n2, n1 + n2 )
VAR se = SQRT ( pp * ( 1 - pp ) * ( DIVIDE ( 1, n1 ) + DIVIDE ( 1, n2 ) ) )
RETURN DIVIDE ( p2 - p1, se )
```

### Exp Significant 95%

```dax
IF ( ABS ( [Exp Z Stat] ) > 1.959964, "Significant", "Not significant" )
```

### Exp KYC Rejection Delta pp  
<sub>format `+0.00;-0.00;0.00`</sub>

Guardrail: non-inferiority margin is +1.5 pp (doc 01 section 8.3).

```dax
VAR r1 = CALCULATE ( [KYC Rejection Rate %], fact_activation[in_analysis_flag] = TRUE (), fact_activation[arm_key] = "control" )
VAR r2 = CALCULATE ( [KYC Rejection Rate %], fact_activation[in_analysis_flag] = TRUE (), fact_activation[arm_key] = "treatment" )
RETURN ( r2 - r1 ) * 100
```

### Exp Fraud Delta pp  
<sub>format `+0.00;-0.00;0.00`</sub>

Guardrail: non-inferiority margin is +0.5 pp (doc 01 section 8.3).

```dax
VAR r1 = CALCULATE ( [Flagged-Fraud Rate % (30d)], fact_activation[in_analysis_flag] = TRUE (), fact_activation[arm_key] = "control" )
VAR r2 = CALCULATE ( [Flagged-Fraud Rate % (30d)], fact_activation[in_analysis_flag] = TRUE (), fact_activation[arm_key] = "treatment" )
RETURN ( r2 - r1 ) * 100
```

### Exp Tickets per 1k Delta  
<sub>format `+0.0;-0.0;0.0`</sub>

Guardrail (secondary, directional).

```dax
VAR t1 = CALCULATE ( [Onboarding Tickets per 1k Signups], fact_activation[in_analysis_flag] = TRUE (), fact_activation[arm_key] = "control" )
VAR t2 = CALCULATE ( [Onboarding Tickets per 1k Signups], fact_activation[in_analysis_flag] = TRUE (), fact_activation[arm_key] = "treatment" )
RETURN t2 - t1
```

### Exp Effect by Channel pp  
<sub>format `+0.00;-0.00;0.00`</sub>

Same as Exp Lift pp; place on a bar by Acquisition Channel for the heterogeneity cut.

```dax
[Exp Lift pp]
```

## 08 Time & Targets

### Day-7 Activation Target %  
<sub>format `0.0%`</sub>

```dax
CALCULATE ( SUM ( fact_targets_month[target_value] ), fact_targets_month[kpi] = "day7_activation_rate" )
```

### Day-7 Activation vs Target pp  
<sub>format `+0.00;-0.00;0.00`</sub>

```dax
( [Day-7 Activation Rate %] - [Day-7 Activation Target %] ) * 100
```

### Active Users Target  
<sub>format `#,0`</sub>

```dax
CALCULATE ( SUM ( fact_targets_month[target_value] ), fact_targets_month[kpi] = "active_users" )
```

### KYC Rejection Target %  
<sub>format `0.0%`</sub>

A ceiling, not a target to beat — lower is not automatically better (doc 01 section 15).

```dax
CALCULATE ( SUM ( fact_targets_month[target_value] ), fact_targets_month[kpi] = "kyc_rejection_rate" )
```

## 09 Narrative

### Exec Insight

A dynamic one-line summary for the Executive Overview page.

```dax
VAR d7    = [Day-7 Activation Rate %]
VAR kyc   = [KYC Rejection Rate %]
VAR fraud = [Flagged-Fraud Rate % (30d)]
VAR srm   = [SRM Worst State (Period)]
RETURN
    "Day-7 Activation is " & FORMAT ( d7, "0.0%" ) &
    ". KYC rejection " & FORMAT ( kyc, "0.0%" ) & ", flagged fraud " & FORMAT ( fraud, "0.00%" ) &
    ". Experiment integrity: " & srm & "."
```
