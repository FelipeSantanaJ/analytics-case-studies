# AeroVanti SkyPoints — DAX Measure Library

_Auto-generated from `etl/pbi_measures.py` on 2026-09-02 by `etl/gen_dax_doc.py`. Do not edit by hand._

**62 measures** in the `_Measures` table, injected into the semantic model by `powerbi/gen_semantic_model.py`.

**Conventions**

- All money is **BRL** — no currency slicer.
- "Latest month" = `MAX(dim_month[month_key])` in the current filter context.
- Time intelligence uses `dim_month[month_sort]` (a linear `year*12 + month` index): PY = `month_sort - 12`. No marked date table, no `SAMEPERIODLASTYEAR`.
- Experiment measures read `fact_experiment_outcome` / `fact_experiment_member_week` and respect the Experiment Arm / Stratum slicers; arm-specific measures pin the arm with `CALCULATE(..., arm_key = "...")`.
- **Breakage rate, lapse rate and liability per member are lower-is-better** — their `vs Target` measures are good when negative.

---

## 01 Program

### Members  
<sub>format `#,0`</sub>

Enrolled members, excluding the two sentinel rows.

```dax
CALCULATE ( DISTINCTCOUNT ( dim_member[member_key] ), dim_member[member_key] > 0 )
```

### Active Members  
<sub>format `#,0`</sub>

Members with an earn or flight in the trailing 12 months, at the latest month in context.

```dax
VAR mk = MAX ( dim_month[month_key] )
RETURN
CALCULATE (
    DISTINCTCOUNT ( fact_member_month[member_key] ),
    fact_member_month[is_active_eom] = TRUE (),
    fact_member_month[month_key] = mk
)
```

### Active Rate %  
<sub>format `0.0%`</sub>

```dax
DIVIDE ( [Active Members], [Members] )
```

### New Enrolments  
<sub>format `#,0`</sub>

First enrolment month for a member.

```dax
CALCULATE ( COUNTROWS ( fact_member_month ), fact_member_month[is_new_enrollment] = TRUE () )
```

### Co-brand Card Penetration %  
<sub>format `0.0%`</sub>

```dax
DIVIDE (
    CALCULATE ( DISTINCTCOUNT ( dim_member[member_key] ),
                dim_member[has_cobrand_card] = TRUE (), dim_member[member_key] > 0 ),
    [Members]
)
```

## 02 Earn & Burn

### SkyPoints Issued  
<sub>format `#,0`</sub>

```dax
CALCULATE ( SUM ( fact_point_transaction[points] ), fact_point_transaction[txn_type] = "earn" )
```

### SkyPoints Redeemed  
<sub>format `#,0`</sub>

```dax
- CALCULATE ( SUM ( fact_point_transaction[points] ), fact_point_transaction[txn_type] = "redeem" )
```

### SkyPoints Expired  
<sub>format `#,0`</sub>

```dax
- CALCULATE ( SUM ( fact_point_transaction[points] ), fact_point_transaction[txn_type] = "expire" )
```

### Burn Earn Ratio  
<sub>format `0.0%`</sub>

Points redeemed as a share of points issued over the period in context.

```dax
DIVIDE ( [SkyPoints Redeemed], [SkyPoints Issued] )
```

### Redemptions  
<sub>format `#,0`</sub>

```dax
CALCULATE ( COUNTROWS ( fact_point_transaction ), fact_point_transaction[txn_type] = "redeem" )
```

### Redeeming Members  
<sub>format `#,0`</sub>

```dax
CALCULATE ( DISTINCTCOUNT ( fact_point_transaction[member_key] ), fact_point_transaction[txn_type] = "redeem" )
```

### Quarterly Redemption Rate %  
<sub>format `0.0%`</sub>

Share of active members with >= 1 redemption in the trailing quarter.

```dax
VAR mk = MAX ( dim_month[month_key] )
VAR q  = FILTER ( ALL ( dim_month ),
                  dim_month[month_sort] > MAXX ( FILTER ( ALL ( dim_month ), dim_month[month_key] = mk ), dim_month[month_sort] ) - 3
               && dim_month[month_key] <= mk )
VAR redeemers =
    CALCULATE ( DISTINCTCOUNT ( fact_member_month[member_key] ),
                fact_member_month[redemptions_m] > 0, q )
VAR active =
    CALCULATE ( DISTINCTCOUNT ( fact_member_month[member_key] ),
                fact_member_month[is_active_eom] = TRUE (), fact_member_month[month_key] = mk )
RETURN DIVIDE ( redeemers, active )
```

### Ever-Redeemed Share %  
<sub>format `0.0%`</sub>

```dax
VAR mk = MAX ( dim_month[month_key] )
RETURN
DIVIDE (
    CALCULATE ( DISTINCTCOUNT ( fact_member_month[member_key] ),
                fact_member_month[has_redeemed_ever_eom] = TRUE (),
                fact_member_month[month_key] = mk ),
    [Active Members]
)
```

### Avg Points Balance  
<sub>format `#,0`</sub>

```dax
VAR mk = MAX ( dim_month[month_key] )
RETURN
CALCULATE ( AVERAGE ( fact_member_month[balance_pts_eom] ),
            fact_member_month[month_key] = mk, fact_member_month[is_active_eom] = TRUE () )
```

## 03 Breakage & Liability

### Point Liability BRL  
<sub>format `"R$"#,0`</sub>

```dax
VAR mk = MAX ( dim_month[month_key] )
RETURN CALCULATE ( SUM ( fact_liability_month[liability_brl_gross] ),
                   fact_liability_month[month_key] = mk )
```

### Point Liability BRL (breakage-adj)  
<sub>format `"R$"#,0`</sub>

```dax
VAR mk = MAX ( dim_month[month_key] )
RETURN CALCULATE ( SUM ( fact_liability_month[liability_brl_breakage_adj] ),
                   fact_liability_month[month_key] = mk )
```

### Breakage Rate %  
<sub>format `0.0%`</sub>

Points expired as a share of points issued over the period in context (realised).

```dax
DIVIDE ( [SkyPoints Expired], [SkyPoints Issued] )
```

### Points Expiring BRL  
<sub>format `"R$"#,0`</sub>

```dax
SUM ( fact_liability_month[points_expired_m] ) * 0.021
```

### Liability per Active Member  
<sub>format `"R$"#,0.0`</sub>

```dax
DIVIDE ( [Point Liability BRL], [Active Members] )
```

## 04 Tiers / 05 Commercial

### Members in Tier  
<sub>format `#,0`</sub>

```dax
VAR mk = MAX ( dim_month[month_key] )
RETURN CALCULATE ( DISTINCTCOUNT ( fact_member_month[member_key] ),
                   fact_member_month[month_key] = mk, fact_member_month[is_active_eom] = TRUE () )
```

### Elite Share %  
<sub>format `0.0%`</sub>

```dax
DIVIDE (
    CALCULATE ( [Members in Tier], dim_tier[is_elite] = TRUE () ),
    CALCULATE ( [Members in Tier], REMOVEFILTERS ( dim_tier ) )
)
```

### Tier Upgrades  
<sub>format `#,0`</sub>

```dax
CALCULATE ( COUNTROWS ( fact_tier_change ), fact_tier_change[direction] = "upgrade" )
```

### Tier Downgrades  
<sub>format `#,0`</sub>

```dax
CALCULATE ( COUNTROWS ( fact_tier_change ), fact_tier_change[direction] IN { "downgrade", "retain_drop" } )
```

### Flight Revenue BRL  
<sub>format `"R$"#,0`</sub>

```dax
CALCULATE ( SUM ( fact_flight_segment[base_fare_brl] ), fact_flight_segment[is_award_redemption] = FALSE () )
```

### Revenue per Active Member  
<sub>format `"R$"#,0`</sub>

```dax
DIVIDE ( [Flight Revenue BRL], [Active Members] )
```

### Award Seat Share %  
<sub>format `0.0%`</sub>

```dax
DIVIDE (
    CALCULATE ( COUNTROWS ( fact_flight_segment ), fact_flight_segment[is_award_redemption] = TRUE () ),
    COUNTROWS ( fact_flight_segment )
)
```

### Card Spend BRL  
<sub>format `"R$"#,0`</sub>

```dax
SUM ( fact_card_spend_month[card_spend_brl] )
```

## 06 Retention & Lapse

### Account-Lapsed Members  
<sub>format `#,0`</sub>

Members in account-lapse (no earn and no redemption for 12 months) at the latest month.

```dax
VAR mk = MAX ( dim_month[month_key] )
RETURN CALCULATE ( DISTINCTCOUNT ( fact_member_month[member_key] ),
                   fact_member_month[is_lapsed_eom] = 1, fact_member_month[month_key] = mk )
```

### Account Lapse Rate %  
<sub>format `0.0%`</sub>

```dax
DIVIDE ( [Account-Lapsed Members], [Active Members] + [Account-Lapsed Members] )
```

### Engagement-Lapsed Members  
<sub>format `#,0`</sub>

Members with no flight and no redemption for 12 months (card-only earn does not count).

```dax
VAR mk = MAX ( dim_month[month_key] )
VAR startsort = MAXX ( FILTER ( ALL ( dim_month ), dim_month[month_key] = mk ), dim_month[month_sort] ) - 11
RETURN
COUNTROWS (
    FILTER (
        VALUES ( fact_member_month[member_key] ),
        CALCULATE (
            SUM ( fact_member_month[flights_m] ) + SUM ( fact_member_month[redemptions_m] ),
            FILTER ( ALL ( dim_month ),
                     dim_month[month_sort] >= startsort
                  && dim_month[month_key] <= mk )
        ) = 0
    )
)
```

### Engagement Lapse Rate %  
<sub>format `0.0%`</sub>

```dax
DIVIDE ( [Engagement-Lapsed Members], [Active Members] )
```

### Reactivations  
<sub>format `#,0`</sub>

```dax
CALCULATE ( COUNTROWS ( fact_member_month ), fact_member_month[is_reactivation] = TRUE () )
```

## 07 A/B Test

### Exp Subjects  
<sub>format `#,0`</sub>

```dax
DISTINCTCOUNT ( fact_experiment_outcome[member_key] )
```

### Exp Redemption Rate  
<sub>format `0.0%`</sub>

Share of subjects (in the current arm/stratum filter) with >= 1 redemption in the 12-week window.

```dax
DIVIDE (
    CALCULATE ( COUNTROWS ( fact_experiment_outcome ),
                fact_experiment_outcome[redeemed_in_window] = TRUE () ),
    COUNTROWS ( fact_experiment_outcome )
)
```

### Exp Control Rate  
<sub>format `0.0%`</sub>

```dax
CALCULATE ( [Exp Redemption Rate], fact_experiment_outcome[arm_key] = "control" )
```

### Exp Treatment Rate  
<sub>format `0.0%`</sub>

```dax
CALCULATE ( [Exp Redemption Rate], fact_experiment_outcome[arm_key] = "treatment" )
```

### Exp Lift pp  
<sub>format `+0.00;-0.00;0.00`</sub>

Absolute treatment - control difference in the redemption rate, in percentage points.

```dax
( [Exp Treatment Rate] - [Exp Control Rate] ) * 100
```

### Exp Lift Rel %  
<sub>format `+0.0%;-0.0%;0.0%`</sub>

```dax
DIVIDE ( [Exp Treatment Rate] - [Exp Control Rate], [Exp Control Rate] )
```

### Exp Lift CI Low pp  
<sub>format `+0.00;-0.00;0.00`</sub>

```dax
VAR p1 = [Exp Control Rate]   VAR p2 = [Exp Treatment Rate]
VAR n1 = CALCULATE ( [Exp Subjects], fact_experiment_outcome[arm_key] = "control" )
VAR n2 = CALCULATE ( [Exp Subjects], fact_experiment_outcome[arm_key] = "treatment" )
VAR se = SQRT ( DIVIDE ( p1 * ( 1 - p1 ), n1 ) + DIVIDE ( p2 * ( 1 - p2 ), n2 ) )
RETURN ( ( p2 - p1 ) - 1.959964 * se ) * 100
```

### Exp Lift CI High pp  
<sub>format `+0.00;-0.00;0.00`</sub>

```dax
VAR p1 = [Exp Control Rate]   VAR p2 = [Exp Treatment Rate]
VAR n1 = CALCULATE ( [Exp Subjects], fact_experiment_outcome[arm_key] = "control" )
VAR n2 = CALCULATE ( [Exp Subjects], fact_experiment_outcome[arm_key] = "treatment" )
VAR se = SQRT ( DIVIDE ( p1 * ( 1 - p1 ), n1 ) + DIVIDE ( p2 * ( 1 - p2 ), n2 ) )
RETURN ( ( p2 - p1 ) + 1.959964 * se ) * 100
```

### Exp Z Stat  
<sub>format `0.00`</sub>

Two-proportion pooled z-statistic.

```dax
VAR p1 = [Exp Control Rate]   VAR p2 = [Exp Treatment Rate]
VAR n1 = CALCULATE ( [Exp Subjects], fact_experiment_outcome[arm_key] = "control" )
VAR n2 = CALCULATE ( [Exp Subjects], fact_experiment_outcome[arm_key] = "treatment" )
VAR pp = DIVIDE ( p1 * n1 + p2 * n2, n1 + n2 )
VAR se = SQRT ( pp * ( 1 - pp ) * ( DIVIDE ( 1, n1 ) + DIVIDE ( 1, n2 ) ) )
RETURN DIVIDE ( p2 - p1, se )
```

### Exp Significant 95%

```dax
IF ( ABS ( [Exp Z Stat] ) > 1.959964, "Significant", "Not significant" )
```

### Exp SRM Ratio  
<sub>format `0.0%`</sub>

Treatment share of subjects; expect 50% (sample-ratio-mismatch check).

```dax
DIVIDE (
    CALCULATE ( [Exp Subjects], fact_experiment_outcome[arm_key] = "treatment" ),
    [Exp Subjects]
)
```

### Exp Revenue per Member  
<sub>format `"R$"#,0`</sub>

```dax
AVERAGE ( fact_experiment_outcome[revenue_brl_window_plus8w] )
```

### Exp Revenue per Member Delta %  
<sub>format `+0.0%;-0.0%;0.0%`</sub>

Guardrail: non-inferiority margin is -3%.

```dax
DIVIDE (
    CALCULATE ( [Exp Revenue per Member], fact_experiment_outcome[arm_key] = "treatment" )
  - CALCULATE ( [Exp Revenue per Member], fact_experiment_outcome[arm_key] = "control" ),
    CALCULATE ( [Exp Revenue per Member], fact_experiment_outcome[arm_key] = "control" )
)
```

### Exp Net Liability Cost per Member  
<sub>format `"R$"#,0.00`</sub>

```dax
AVERAGE ( fact_experiment_outcome[net_liability_cost_brl] )
```

### Exp Disengaged 90d %  
<sub>format `0.0%`</sub>

Guardrail: share with no earn and no redemption in the 90 days after the window.

```dax
DIVIDE (
    CALCULATE ( COUNTROWS ( fact_experiment_outcome ),
                fact_experiment_outcome[disengaged_90d_post] = TRUE () ),
    COUNTROWS ( fact_experiment_outcome )
)
```

### Exp Redemption Value per Redeemer  
<sub>format `"R$"#,0`</sub>

Guardrail: depth of redemptions (Flash makes them shallower).

```dax
DIVIDE (
    SUM ( fact_experiment_outcome[redemption_value_brl] ),
    CALCULATE ( COUNTROWS ( fact_experiment_outcome ),
                fact_experiment_outcome[redeemed_in_window] = TRUE () )
)
```

### Exp Weekly Redeemers %  
<sub>format `0.00%`</sub>

Redeemers in the week / subjects — plot by week and arm for the novelty check.

```dax
DIVIDE ( CALCULATE ( COUNTROWS ( fact_experiment_member_week ), fact_experiment_member_week[redeemed_w] = TRUE () ), [Exp Subjects] )
```

### Exp Effect by Tier pp  
<sub>format `+0.00;-0.00;0.00`</sub>

Same as Exp Lift pp; place on a bar by Experiment Stratum for the heterogeneity cut.

```dax
[Exp Lift pp]
```

## 08 Time & Targets

### SkyPoints Redeemed PY  
<sub>format `#,0`</sub>

```dax
CALCULATE (
    [SkyPoints Redeemed],
    FILTER ( ALL ( dim_month ),
             dim_month[month_sort] = MAX ( dim_month[month_sort] ) - 12 )
)
```

### SkyPoints Redeemed YoY %  
<sub>format `+0.0%;-0.0%;0.0%`</sub>

```dax
DIVIDE ( [SkyPoints Redeemed] - [SkyPoints Redeemed PY], [SkyPoints Redeemed PY] )
```

### Breakage Rate Target  
<sub>format `0.0%`</sub>

```dax
VAR mk = MAX ( dim_month[month_key] )
RETURN CALCULATE ( AVERAGE ( fact_targets_month[target_value] ),
                   fact_targets_month[kpi] = "breakage_rate", fact_targets_month[month_key] = mk )
```

### Redemption Rate Target  
<sub>format `0.0%`</sub>

```dax
VAR mk = MAX ( dim_month[month_key] )
RETURN CALCULATE ( AVERAGE ( fact_targets_month[target_value] ),
                   fact_targets_month[kpi] = "redemption_rate_quarterly", fact_targets_month[month_key] = mk )
```

### Quarterly Redemption Rate vs Target  
<sub>format `+0.0%;-0.0%;0.0%`</sub>

```dax
[Quarterly Redemption Rate %] - [Redemption Rate Target]
```

### Breakage Rate vs Target  
<sub>format `+0.0%;-0.0%;0.0%`</sub>

Lower is better — negative is good.

```dax
[Breakage Rate %] - [Breakage Rate Target]
```

## 09 Narrative

### Exec Insight

Dynamic summary sentence for the Executive Summary page; updates with the slicers.

```dax
VAR lift = [Exp Lift pp]
VAR sig = [Exp Significant 95%]
VAR br = [Breakage Rate %]
VAR rr = [Quarterly Redemption Rate %]
RETURN
"Flash Redemption lifted the 12-week redemption rate by "
  & FORMAT ( lift, "+0.0;-0.0" ) & " pp (" & sig & " at 95%; control "
  & FORMAT ( [Exp Control Rate], "0.0%" ) & " vs treatment "
  & FORMAT ( [Exp Treatment Rate], "0.0%" ) & "). "
  & "Program-wide, the quarterly redemption rate is " & FORMAT ( rr, "0.0%" )
  & " and realised breakage is " & FORMAT ( br, "0.0%" )
  & " of points issued, against a ~40% lifetime expectation. "
  & "Guardrails: revenue per member " & FORMAT ( [Exp Revenue per Member Delta %], "+0.0%;-0.0%" )
  & ", 90-day disengagement "
  & FORMAT ( CALCULATE ( [Exp Disengaged 90d %], fact_experiment_outcome[arm_key] = "treatment" )
           - CALCULATE ( [Exp Disengaged 90d %], fact_experiment_outcome[arm_key] = "control" ), "+0.0%;-0.0%" )
  & "."
```

## 10 Funnel

### Members with Redeemable Balance  
<sub>format `#,0`</sub>

Active members whose balance clears the Flash minimum redemption threshold.

```dax
VAR mk = MAX ( dim_month[month_key] )
RETURN CALCULATE ( DISTINCTCOUNT ( fact_member_month[member_key] ),
                   fact_member_month[month_key] = mk,
                   fact_member_month[is_active_eom] = TRUE (),
                   fact_member_month[balance_pts_eom] >= 3500 )
```

### Redeemers in Last 12m  
<sub>format `#,0`</sub>

```dax
VAR mk = MAX ( dim_month[month_key] )
VAR startsort = MAXX ( FILTER ( ALL ( dim_month ), dim_month[month_key] = mk ), dim_month[month_sort] ) - 11
RETURN
CALCULATE ( DISTINCTCOUNT ( fact_member_month[member_key] ),
            fact_member_month[redemptions_m] > 0,
            FILTER ( ALL ( dim_month ), dim_month[month_sort] >= startsort && dim_month[month_key] <= mk ) )
```

### Redeemers in Last Quarter  
<sub>format `#,0`</sub>

```dax
VAR mk = MAX ( dim_month[month_key] )
VAR startsort = MAXX ( FILTER ( ALL ( dim_month ), dim_month[month_key] = mk ), dim_month[month_sort] ) - 2
RETURN
CALCULATE ( DISTINCTCOUNT ( fact_member_month[member_key] ),
            fact_member_month[redemptions_m] > 0,
            FILTER ( ALL ( dim_month ), dim_month[month_sort] >= startsort && dim_month[month_key] <= mk ) )
```

### Ever-Redeemed Members  
<sub>format `#,0`</sub>

```dax
VAR mk = MAX ( dim_month[month_key] )
RETURN CALCULATE ( DISTINCTCOUNT ( fact_member_month[member_key] ),
                   fact_member_month[has_redeemed_ever_eom] = TRUE (), fact_member_month[month_key] = mk )
```

### Funnel Value  
<sub>format `#,0`</sub>

Member count at the selected redemption-funnel stage (place 'Funnel Stage'[stage] on Category).

```dax
VAR s = SELECTEDVALUE ( 'Funnel Stage'[stage] )
RETURN
SWITCH ( s,
    "Active members", [Active Members],
    "Have points >= Flash threshold", [Members with Redeemable Balance],
    "Ever redeemed", [Ever-Redeemed Members],
    "Redeemed in last 12m", [Redeemers in Last 12m],
    "Redeemed in last quarter", [Redeemers in Last Quarter],
    BLANK () )
```
