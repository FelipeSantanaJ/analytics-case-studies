# SwiftBite Delivery — DAX Measure Library

_Auto-generated from `etl/pbi_measures.py` on 2026-09-10 by `etl/gen_dax_doc.py`. Do not edit by hand._

**71 measures** in the `_Measures` table, injected into the semantic model by `powerbi/gen_semantic_model.py`.

## Conventions

- All money is **BRL** — no currency slicer.
- The report's date grain is the day; `dim_date[date_key]` is the calendar key on every fact. Time-of-day comes from `dim_time_block` (`is_peak_block` = 18:00–21:59).
- **ETA p50 / p90** are stored per zone-hour; the measures aggregate them as an order-weighted mean of the per-zone-hour percentile — a close approximation. The exact distribution-level percentile is a Phase-10 artifact, not a live measure.
- Experiment measures read `fact_experiment_zone_day` (one row per randomised zone-day) and `fact_incentive_assignment` (design + frozen pre-period covariates); `arm` / `stratum` are text columns filtered directly.
- The live experiment CI is a **two-sample normal interval on the zone-day means**. The cluster-robust (by zone) SE, the randomization-inference p-value and the formal arm×tier interaction test are **Phase-10 deliverables**, not measures.
- **ETA, cancellation rate, no-courier rate, idle-courier ratio and incentive cost per incremental order are lower-is-better** — their `vs Target` measures are good when negative.

---

## 01 Marketplace Health

### Orders Placed  
<sub>format `#,0`</sub>

```dax
SUM ( fact_zone_hour[orders_placed] )
```

### Orders Delivered  
<sub>format `#,0`</sub>

```dax
SUM ( fact_zone_hour[orders_delivered] )
```

### Fulfillment Rate %  
<sub>format `0.0%`</sub>

Delivered orders as a share of placed orders in the current filter context.

```dax
DIVIDE ( [Orders Delivered], [Orders Placed] )
```

### Cancellations  
<sub>format `#,0`</sub>

```dax
[Orders Placed] - [Orders Delivered]
```

### Cancellation Rate %  
<sub>format `0.0%`</sub>

```dax
DIVIDE ( [Cancellations], [Orders Placed] )
```

### No-Courier Cancels  
<sub>format `#,0`</sub>

```dax
SUM ( fact_zone_hour[cancelled_no_courier] )
```

### No-Courier Rate %  
<sub>format `0.00%`</sub>

Orders cancelled because no courier could be assigned — the sharpest liquidity signal.

```dax
DIVIDE ( [No-Courier Cancels], [Orders Placed] )
```

### Customer Cancels  
<sub>format `#,0`</sub>

```dax
SUM ( fact_zone_hour[cancelled_customer] )
```

### ETA p50 (min)  
<sub>format `0.0`</sub>

Order-weighted mean of the per-zone-hour median ETA.

```dax
DIVIDE ( SUMX ( fact_zone_hour, fact_zone_hour[eta_p50_min] * fact_zone_hour[orders_delivered] ), [Orders Delivered] )
```

### ETA p90 (min)  
<sub>format `0.0`</sub>

Order-weighted mean of the per-zone-hour 90th-percentile ETA — the customer-pain metric.

```dax
DIVIDE ( SUMX ( fact_zone_hour, fact_zone_hour[eta_p90_min] * fact_zone_hour[orders_delivered] ), [Orders Delivered] )
```

### Assignment Latency p90 (s)  
<sub>format `0`</sub>

```dax
DIVIDE ( SUMX ( fact_zone_hour, fact_zone_hour[assignment_latency_p90_s] * fact_zone_hour[orders_placed] ), [Orders Placed] )
```

### Peak Fulfillment Rate %  
<sub>format `0.0%`</sub>

Fulfillment restricted to the 18:00–21:59 dinner peak.

```dax
CALCULATE ( [Fulfillment Rate %], dim_time_block[is_peak_block] = TRUE () )
```

### Peak ETA p90 (min)  
<sub>format `0.0`</sub>

```dax
CALCULATE ( [ETA p90 (min)], dim_time_block[is_peak_block] = TRUE () )
```

## 02 Liquidity

### Available Courier-Hours  
<sub>format `#,0.0`</sub>

```dax
SUM ( fact_zone_hour[available_courier_hours] )
```

### Demanded Courier-Hours  
<sub>format `#,0.0`</sub>

Orders placed × the period's average service time (pickup + drive + drop).

```dax
SUM ( fact_zone_hour[demanded_delivery_hours] )
```

### Liquidity Ratio  
<sub>format `0.00`</sub>

Available ÷ demanded courier-hours. < 1 = supply-short.

```dax
DIVIDE ( [Available Courier-Hours], [Demanded Courier-Hours] )
```

### Idle Courier-Hours  
<sub>format `#,0.0`</sub>

```dax
SUM ( fact_zone_hour[idle_courier_hours] )
```

### Idle Courier Ratio %  
<sub>format `0.0%`</sub>

Logged-in courier-hours not on a run — supply present but unproductive.

```dax
DIVIDE ( [Idle Courier-Hours], [Available Courier-Hours] )
```

### Unmet Demand  
<sub>format `#,0`</sub>

Placed − delivered, the volume a liquidity fix would recover.

```dax
SUM ( fact_zone_hour[unmet_demand] )
```

### Active Couriers  
<sub>format `#,0`</sub>

```dax
CALCULATE ( DISTINCTCOUNT ( fact_courier_shift_block[courier_key] ), fact_courier_shift_block[courier_key] > 0 )
```

### Supply-Short Peak Zone-Hours %  
<sub>format `0.0%`</sub>

Share of peak zone-hours where available < demanded courier-hours.

```dax
VAR peak =
    FILTER (
        fact_zone_hour,
        fact_zone_hour[is_peak_block] = TRUE () && fact_zone_hour[orders_placed] > 0
    )
RETURN
DIVIDE (
    COUNTROWS ( FILTER ( peak, fact_zone_hour[liquidity_ratio] < 1 ) ),
    COUNTROWS ( peak )
)
```

### Deliveries per Active Hour  
<sub>format `0.00`</sub>

```dax
DIVIDE ( SUM ( fact_courier_shift_block[deliveries] ), DIVIDE ( SUM ( fact_courier_shift_block[active_min] ), 60 ) )
```

## 03 Courier Economics

### Courier Earnings (BRL)  
<sub>format `#,0`</sub>

```dax
SUM ( fact_courier_shift_block[earnings_brl] )
```

### Active Hours  
<sub>format `#,0.0`</sub>

```dax
DIVIDE ( SUM ( fact_courier_shift_block[active_min] ), 60 )
```

### Logged-in Hours  
<sub>format `#,0.0`</sub>

```dax
DIVIDE ( SUM ( fact_courier_shift_block[logged_in_min] ), 60 )
```

### Earnings per Active Hour (BRL)  
<sub>format `#,0.00`</sub>

```dax
DIVIDE ( [Courier Earnings (BRL)], [Active Hours] )
```

### Utilisation %  
<sub>format `0.0%`</sub>

Active ÷ logged-in minutes.

```dax
DIVIDE ( SUM ( fact_courier_shift_block[active_min] ), SUM ( fact_courier_shift_block[logged_in_min] ) )
```

### Payout per Delivery (BRL)  
<sub>format `#,0.00`</sub>

```dax
DIVIDE ( [Courier Earnings (BRL)], SUM ( fact_courier_shift_block[deliveries] ) )
```

### Incentive Spend (BRL)  
<sub>format `#,0`</sub>

```dax
SUM ( fact_courier_shift_block[bonus_brl] )
```

### Incentive Spend as % of Payout  
<sub>format `0.0%`</sub>

```dax
DIVIDE ( [Incentive Spend (BRL)], [Courier Earnings (BRL)] )
```

### Contribution Margin per Delivered Order (BRL)  
<sub>format `#,0.00`</sub>

SwiftBite take (22% of basket + fee) − courier base+tip payout − payment/support cost, per delivered order. Excludes the experiment bonus.

```dax
VAR delivered = [Orders Delivered]
VAR take =
    0.22 * CALCULATE ( SUM ( fact_order[basket_value_brl] ), fact_order[outcome] = "delivered" )
    + CALCULATE ( SUM ( fact_order[delivery_fee_brl] ), fact_order[outcome] = "delivered" )
VAR payout =
    SUM ( fact_delivery[courier_base_payout_brl] ) + SUM ( fact_delivery[tip_brl] )
VAR support = 1.1 * delivered
RETURN
DIVIDE ( take - payout - support, delivered )
```

## 04 Experiment

### Treated Zone-Days  
<sub>format `#,0`</sub>

```dax
CALCULATE ( COUNTROWS ( fact_experiment_zone_day ), fact_experiment_zone_day[arm] = "treatment" )
```

### Control Zone-Days  
<sub>format `#,0`</sub>

```dax
CALCULATE ( COUNTROWS ( fact_experiment_zone_day ), fact_experiment_zone_day[arm] = "control" )
```

### Fulfillment (Treated) %  
<sub>format `0.0%`</sub>

Mean fulfillment rate across treated zone-days (peak block).

```dax
CALCULATE ( AVERAGE ( fact_experiment_zone_day[fulfillment_rate] ), fact_experiment_zone_day[arm] = "treatment" )
```

### Fulfillment (Control) %  
<sub>format `0.0%`</sub>

```dax
CALCULATE ( AVERAGE ( fact_experiment_zone_day[fulfillment_rate] ), fact_experiment_zone_day[arm] = "control" )
```

### Fulfillment Lift (pp)  
<sub>format `+0.00;-0.00;0.00`</sub>

Primary metric: treated − control mean fulfillment, in percentage points.

```dax
( [Fulfillment (Treated) %] - [Fulfillment (Control) %] ) * 100
```

### Fulfillment Lift SE (pp)  
<sub>format `0.00`</sub>

Two-sample normal SE on the zone-day means. The cluster-robust (by zone) SE is a Phase-10 artifact.

```dax
VAR nt = [Treated Zone-Days]
VAR nc = [Control Zone-Days]
VAR vt = CALCULATE ( VAR.S ( fact_experiment_zone_day[fulfillment_rate] ), fact_experiment_zone_day[arm] = "treatment" )
VAR vc = CALCULATE ( VAR.S ( fact_experiment_zone_day[fulfillment_rate] ), fact_experiment_zone_day[arm] = "control" )
RETURN
SQRT ( DIVIDE ( vt, nt ) + DIVIDE ( vc, nc ) ) * 100
```

### Fulfillment Lift CI Low (pp)  
<sub>format `+0.00;-0.00;0.00`</sub>

```dax
[Fulfillment Lift (pp)] - 1.96 * [Fulfillment Lift SE (pp)]
```

### Fulfillment Lift CI High (pp)  
<sub>format `+0.00;-0.00;0.00`</sub>

```dax
[Fulfillment Lift (pp)] + 1.96 * [Fulfillment Lift SE (pp)]
```

### Fulfillment Lift Significant?

```dax
IF ( [Fulfillment Lift CI Low (pp)] > 0, "Yes (95%)", "No" )
```

### ETA p90 (Treated) min  
<sub>format `0.0`</sub>

```dax
CALCULATE ( AVERAGE ( fact_experiment_zone_day[eta_p90_min] ), fact_experiment_zone_day[arm] = "treatment" )
```

### ETA p90 (Control) min  
<sub>format `0.0`</sub>

```dax
CALCULATE ( AVERAGE ( fact_experiment_zone_day[eta_p90_min] ), fact_experiment_zone_day[arm] = "control" )
```

### ETA p90 Lift (min)  
<sub>format `+0.0;-0.0;0.0`</sub>

Co-primary evidence (lower is better).

```dax
[ETA p90 (Treated) min] - [ETA p90 (Control) min]
```

### No-Courier Rate (Treated) %  
<sub>format `0.00%`</sub>

```dax
CALCULATE ( AVERAGE ( fact_experiment_zone_day[cancel_no_courier_rate] ), fact_experiment_zone_day[arm] = "treatment" )
```

### No-Courier Rate (Control) %  
<sub>format `0.00%`</sub>

```dax
CALCULATE ( AVERAGE ( fact_experiment_zone_day[cancel_no_courier_rate] ), fact_experiment_zone_day[arm] = "control" )
```

### No-Courier Rate Lift (pp)  
<sub>format `+0.00;-0.00;0.00`</sub>

Co-primary evidence (lower is better).

```dax
( [No-Courier Rate (Treated) %] - [No-Courier Rate (Control) %] ) * 100
```

### Incentive Spend - Experiment (BRL)  
<sub>format `#,0`</sub>

```dax
SUM ( fact_experiment_zone_day[incentive_spend_brl] )
```

### Incremental Delivered Orders  
<sub>format `#,0`</sub>

Treated orders delivered above the control fulfillment rate.

```dax
VAR lift = [Fulfillment (Treated) %] - [Fulfillment (Control) %]
VAR treated_placed =
    CALCULATE ( SUM ( fact_experiment_zone_day[orders_placed] ), fact_experiment_zone_day[arm] = "treatment" )
RETURN
lift * treated_placed
```

### G1 Incentive Cost per Incremental Order (BRL)  
<sub>format `#,0.00`</sub>

The go/no-go economics: bonus spend ÷ incremental delivered orders.

```dax
DIVIDE ( [Incentive Spend - Experiment (BRL)], [Incremental Delivered Orders] )
```

### G1 Verdict

```dax
IF (
    [G1 Incentive Cost per Incremental Order (BRL)] < [Contribution Margin per Delivered Order (BRL)],
    "Pays for itself",
    "Costs more than it saves"
)
```

### Fulfillment Lift - Short tier (pp)  
<sub>format `+0.00;-0.00;0.00`</sub>

```dax
VAR t = CALCULATE ( AVERAGE ( fact_experiment_zone_day[fulfillment_rate] ),
                    fact_experiment_zone_day[arm] = "treatment", dim_zone[baseline_supply_stress_tier] = "short" )
VAR c = CALCULATE ( AVERAGE ( fact_experiment_zone_day[fulfillment_rate] ),
                    fact_experiment_zone_day[arm] = "control", dim_zone[baseline_supply_stress_tier] = "short" )
RETURN ( t - c ) * 100
```

### Fulfillment Lift - Balanced tier (pp)  
<sub>format `+0.00;-0.00;0.00`</sub>

```dax
VAR t = CALCULATE ( AVERAGE ( fact_experiment_zone_day[fulfillment_rate] ),
                    fact_experiment_zone_day[arm] = "treatment", dim_zone[baseline_supply_stress_tier] = "balanced" )
VAR c = CALCULATE ( AVERAGE ( fact_experiment_zone_day[fulfillment_rate] ),
                    fact_experiment_zone_day[arm] = "control", dim_zone[baseline_supply_stress_tier] = "balanced" )
RETURN ( t - c ) * 100
```

### Fulfillment Lift - Long tier (pp)  
<sub>format `+0.00;-0.00;0.00`</sub>

```dax
VAR t = CALCULATE ( AVERAGE ( fact_experiment_zone_day[fulfillment_rate] ),
                    fact_experiment_zone_day[arm] = "treatment", dim_zone[baseline_supply_stress_tier] = "long" )
VAR c = CALCULATE ( AVERAGE ( fact_experiment_zone_day[fulfillment_rate] ),
                    fact_experiment_zone_day[arm] = "control", dim_zone[baseline_supply_stress_tier] = "long" )
RETURN ( t - c ) * 100
```

### Arm x Tier Contrast (Short minus Long, pp)  
<sub>format `+0.00;-0.00;0.00`</sub>

Descriptive heterogeneity contrast. The formal LR interaction test is Phase 10.

```dax
[Fulfillment Lift - Short tier (pp)] - [Fulfillment Lift - Long tier (pp)]
```

### Cannibalisation - Adjacent-Control Gap (pp)  
<sub>format `+0.00;-0.00;0.00`</sub>

Fulfillment on control zone-days next to a treated zone minus control zone-days that are not. Negative = neighbours are being drained (cannibalisation).

```dax
VAR adj =
    CALCULATE ( AVERAGE ( fact_experiment_zone_day[fulfillment_rate] ),
        fact_experiment_zone_day[arm] = "control", fact_experiment_zone_day[is_adjacent_to_treated] = TRUE () )
VAR noadj =
    CALCULATE ( AVERAGE ( fact_experiment_zone_day[fulfillment_rate] ),
        fact_experiment_zone_day[arm] = "control", fact_experiment_zone_day[is_adjacent_to_treated] = FALSE () )
RETURN ( adj - noadj ) * 100
```

### Cannibalisation-Adjusted Net Lift (pp)  
<sub>format `+0.00;-0.00;0.00`</sub>

Rough metro-level net of the local lift and the neighbour-zone drag. Phase 10 does the full spatial model.

```dax
[Fulfillment Lift (pp)] + [Cannibalisation - Adjacent-Control Gap (pp)]
```

### Balance - Pre-period Fulfillment Gap (pp)  
<sub>format `+0.00;-0.00;0.00`</sub>

Should be ≈ 0 — a smoke test that randomisation balanced the arms on the 15-month baseline.

```dax
VAR t = CALCULATE ( AVERAGE ( fact_incentive_assignment[pre_fulfillment_rate] ), fact_incentive_assignment[arm] = "treatment" )
VAR c = CALCULATE ( AVERAGE ( fact_incentive_assignment[pre_fulfillment_rate] ), fact_incentive_assignment[arm] = "control" )
RETURN ( t - c ) * 100
```

### Settled Lift (weeks 8-10, pp)  
<sub>format `+0.00;-0.00;0.00`</sub>

Lift over the last three weeks — after any launch-novelty bump has decayed.

```dax
VAR t = CALCULATE ( AVERAGE ( fact_experiment_zone_block_week[fulfillment_rate] ),
                    fact_experiment_zone_block_week[arm] = "treatment", fact_experiment_zone_block_week[experiment_week] >= 8 )
VAR c = CALCULATE ( AVERAGE ( fact_experiment_zone_block_week[fulfillment_rate] ),
                    fact_experiment_zone_block_week[arm] = "control", fact_experiment_zone_block_week[experiment_week] >= 8 )
RETURN ( t - c ) * 100
```

### Weekly Fulfillment %  
<sub>format `0.0%`</sub>

Mean zone-block fulfillment per experiment week.

```dax
AVERAGE ( fact_experiment_zone_block_week[fulfillment_rate] )
```

### Weekly Fulfillment (Treated) %  
<sub>format `0.0%`</sub>

```dax
CALCULATE ( AVERAGE ( fact_experiment_zone_block_week[fulfillment_rate] ), fact_experiment_zone_block_week[arm] = "treatment" )
```

### Weekly Fulfillment (Control) %  
<sub>format `0.0%`</sub>

```dax
CALCULATE ( AVERAGE ( fact_experiment_zone_block_week[fulfillment_rate] ), fact_experiment_zone_block_week[arm] = "control" )
```

### Zone-Day Fulfillment %  
<sub>format `0.0%`</sub>

Mean fulfillment across the zone-days in context — split by `arm` for the guardrail table.

```dax
AVERAGE ( fact_experiment_zone_day[fulfillment_rate] )
```

### Zone-Day ETA p90 (min)  
<sub>format `0.0`</sub>

```dax
AVERAGE ( fact_experiment_zone_day[eta_p90_min] )
```

### Zone-Day No-Courier Rate %  
<sub>format `0.00%`</sub>

```dax
AVERAGE ( fact_experiment_zone_day[cancel_no_courier_rate] )
```

### Zone-Day Earnings per Active Hour (BRL)  
<sub>format `#,0.00`</sub>

```dax
AVERAGE ( fact_experiment_zone_day[courier_earnings_per_active_hour_brl] )
```

### Zone-Day Incentive Cost per Order (BRL)  
<sub>format `#,0.00`</sub>

```dax
AVERAGE ( fact_experiment_zone_day[incentive_cost_per_delivered_order_brl] )
```

## 05 Targets & Context

### Fulfillment vs Target (pp)  
<sub>format `+0.0;-0.0;0.0`</sub>

Plan: ≥ 98% metro-wide (doc 01 §10).

```dax
( [Fulfillment Rate %] - 0.98 ) * 100
```

### Peak ETA p90 vs Target (min)  
<sub>format `+0.0;-0.0;0.0`</sub>

Plan: ≤ 55 min at peak. Lower is better — good when negative.

```dax
[Peak ETA p90 (min)] - 55
```

### No-Courier Rate vs Target (pp)  
<sub>format `+0.00;-0.00;0.00`</sub>

Plan: ≤ 0.5%. Lower is better.

```dax
( [No-Courier Rate %] - 0.005 ) * 100
```

### Idle Courier Ratio vs Target (pp)  
<sub>format `+0.0;-0.0;0.0`</sub>

Plan: ≤ 25%. Lower is better.

```dax
( [Idle Courier Ratio %] - 0.25 ) * 100
```

## 06 Exec Insight

### Exec Insight

One-line dynamic read of the experiment for the Executive Overview page.

```dax
VAR lift = [Fulfillment Lift (pp)]
VAR sig = [Fulfillment Lift CI Low (pp)] > 0
VAR g1 = [G1 Incentive Cost per Incremental Order (BRL)]
VAR cm = [Contribution Margin per Delivered Order (BRL)]
VAR eta = [ETA p90 Lift (min)]
VAR cann = [Cannibalisation - Adjacent-Control Gap (pp)]
RETURN
"Zone-hour incentive: fulfillment " &
    IF ( lift >= 0, "+", "" ) & FORMAT ( lift, "0.0" ) & " pp" &
    IF ( sig, " (significant at 95%)", " (not significant)" ) &
    ", ETA p90 " & FORMAT ( eta, "+0.0;-0.0" ) & " min. " &
    "Cost per incremental order R$ " & FORMAT ( g1, "0.00" ) &
    IF ( g1 < cm, " — below", " — above" ) & " the R$ " & FORMAT ( cm, "0.00" ) &
    " contribution margin. Neighbour zones " &
    IF ( cann < -0.3, "show a drag of " & FORMAT ( cann, "0.0" ) & " pp (cannibalisation).",
         "show no material drag." )
```
