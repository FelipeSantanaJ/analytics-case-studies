"""
pbi_measures.py — the DAX measure library for the SwiftBite Delivery semantic model.

`MEASURE_LIBRARY` = list of (display_folder, [measure, ...]). Each measure is a dict
{name, dax, format, folder, description}.

`powerbi/gen_semantic_model.py` injects these into `_Measures.tmdl`.
`etl/gen_dax_doc.py` renders `docs/06_dax_measures.md` from the same list.

Conventions
-----------
- All money is BRL — no currency slicer.
- The report's date grain is the day; `dim_date[date_key]` is the calendar key on every
  fact. Time-of-day comes from `dim_time_block` (`is_peak_block` = 18:00–21:59).
- ETA percentiles are stored per zone-hour; measures aggregate them as an
  order-weighted mean of the per-zone-hour p50 / p90 (a close approximation — the exact
  distribution-level percentile is a Phase-10 artifact, not a live measure).
- Experiment measures read `fact_experiment_zone_day` (one row per randomised zone-day)
  and `fact_incentive_assignment` (design + frozen pre-period covariates); `arm` and
  `stratum` are text columns filtered directly.
- The live experiment CI is a two-sample normal interval on the zone-day means. The
  **cluster-robust (by zone) SE, randomization-inference p-value and the formal arm×tier
  interaction test are Phase-10 deliverables**, not measures.
- ETA, cancellation rate, no-courier rate, idle-courier ratio and incentive cost per
  incremental order are **lower-is-better**.
"""
from __future__ import annotations

import textwrap


def M(name, dax, format="", folder="", description=""):
    return {"name": name, "dax": textwrap.dedent(dax).strip(),
            "format": format, "folder": folder, "description": description}


def all_measures():
    for _f, group in MEASURE_LIBRARY:
        yield from group


F1 = "01 Marketplace Health"
F2 = "02 Liquidity"
F3 = "03 Courier Economics"
F4 = "04 Experiment"
F5 = "05 Targets & Context"
F6 = "06 Exec Insight"

# --------------------------------------------------------------------------- #
MARKETPLACE = [
    M("Orders Placed", "SUM ( fact_zone_hour[orders_placed] )", "#,0", F1),
    M("Orders Delivered", "SUM ( fact_zone_hour[orders_delivered] )", "#,0", F1),
    M("Fulfillment Rate %", "DIVIDE ( [Orders Delivered], [Orders Placed] )", "0.0%", F1,
      "Delivered orders as a share of placed orders in the current filter context."),
    M("Cancellations", "[Orders Placed] - [Orders Delivered]", "#,0", F1),
    M("Cancellation Rate %", "DIVIDE ( [Cancellations], [Orders Placed] )", "0.0%", F1),
    M("No-Courier Cancels", "SUM ( fact_zone_hour[cancelled_no_courier] )", "#,0", F1),
    M("No-Courier Rate %", "DIVIDE ( [No-Courier Cancels], [Orders Placed] )", "0.00%", F1,
      "Orders cancelled because no courier could be assigned — the sharpest liquidity signal."),
    M("Customer Cancels", "SUM ( fact_zone_hour[cancelled_customer] )", "#,0", F1),
    M("ETA p50 (min)",
      "DIVIDE ( SUMX ( fact_zone_hour, fact_zone_hour[eta_p50_min] * fact_zone_hour[orders_delivered] ), [Orders Delivered] )",
      "0.0", F1, "Order-weighted mean of the per-zone-hour median ETA."),
    M("ETA p90 (min)",
      "DIVIDE ( SUMX ( fact_zone_hour, fact_zone_hour[eta_p90_min] * fact_zone_hour[orders_delivered] ), [Orders Delivered] )",
      "0.0", F1, "Order-weighted mean of the per-zone-hour 90th-percentile ETA — the customer-pain metric."),
    M("Assignment Latency p90 (s)",
      "DIVIDE ( SUMX ( fact_zone_hour, fact_zone_hour[assignment_latency_p90_s] * fact_zone_hour[orders_placed] ), [Orders Placed] )",
      "0", F1),
    M("Peak Fulfillment Rate %",
      "CALCULATE ( [Fulfillment Rate %], dim_time_block[is_peak_block] = TRUE () )", "0.0%", F1,
      "Fulfillment restricted to the 18:00–21:59 dinner peak."),
    M("Peak ETA p90 (min)",
      "CALCULATE ( [ETA p90 (min)], dim_time_block[is_peak_block] = TRUE () )", "0.0", F1),
]

LIQUIDITY = [
    M("Available Courier-Hours", "SUM ( fact_zone_hour[available_courier_hours] )", "#,0.0", F2),
    M("Demanded Courier-Hours", "SUM ( fact_zone_hour[demanded_delivery_hours] )", "#,0.0", F2,
      "Orders placed × the period's average service time (pickup + drive + drop)."),
    M("Liquidity Ratio", "DIVIDE ( [Available Courier-Hours], [Demanded Courier-Hours] )", "0.00", F2,
      "Available ÷ demanded courier-hours. < 1 = supply-short."),
    M("Idle Courier-Hours", "SUM ( fact_zone_hour[idle_courier_hours] )", "#,0.0", F2),
    M("Idle Courier Ratio %", "DIVIDE ( [Idle Courier-Hours], [Available Courier-Hours] )", "0.0%", F2,
      "Logged-in courier-hours not on a run — supply present but unproductive."),
    M("Unmet Demand", "SUM ( fact_zone_hour[unmet_demand] )", "#,0", F2,
      "Placed − delivered, the volume a liquidity fix would recover."),
    M("Active Couriers",
      "CALCULATE ( DISTINCTCOUNT ( fact_courier_shift_block[courier_key] ), fact_courier_shift_block[courier_key] > 0 )",
      "#,0", F2),
    M("Supply-Short Peak Zone-Hours %",
      """
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
      """, "0.0%", F2, "Share of peak zone-hours where available < demanded courier-hours."),
    M("Deliveries per Active Hour",
      "DIVIDE ( SUM ( fact_courier_shift_block[deliveries] ), DIVIDE ( SUM ( fact_courier_shift_block[active_min] ), 60 ) )",
      "0.00", F2),
]

COURIER = [
    M("Courier Earnings (BRL)", "SUM ( fact_courier_shift_block[earnings_brl] )", "#,0", F3),
    M("Active Hours", "DIVIDE ( SUM ( fact_courier_shift_block[active_min] ), 60 )", "#,0.0", F3),
    M("Logged-in Hours", "DIVIDE ( SUM ( fact_courier_shift_block[logged_in_min] ), 60 )", "#,0.0", F3),
    M("Earnings per Active Hour (BRL)", "DIVIDE ( [Courier Earnings (BRL)], [Active Hours] )", "#,0.00", F3),
    M("Utilisation %",
      "DIVIDE ( SUM ( fact_courier_shift_block[active_min] ), SUM ( fact_courier_shift_block[logged_in_min] ) )",
      "0.0%", F3, "Active ÷ logged-in minutes."),
    M("Payout per Delivery (BRL)",
      "DIVIDE ( [Courier Earnings (BRL)], SUM ( fact_courier_shift_block[deliveries] ) )", "#,0.00", F3),
    M("Incentive Spend (BRL)", "SUM ( fact_courier_shift_block[bonus_brl] )", "#,0", F3),
    M("Incentive Spend as % of Payout",
      "DIVIDE ( [Incentive Spend (BRL)], [Courier Earnings (BRL)] )", "0.0%", F3),
    M("Contribution Margin per Delivered Order (BRL)",
      """
      VAR delivered = [Orders Delivered]
      VAR take =
          0.22 * CALCULATE ( SUM ( fact_order[basket_value_brl] ), fact_order[outcome] = "delivered" )
          + CALCULATE ( SUM ( fact_order[delivery_fee_brl] ), fact_order[outcome] = "delivered" )
      VAR payout =
          SUM ( fact_delivery[courier_base_payout_brl] ) + SUM ( fact_delivery[tip_brl] )
      VAR support = 1.1 * delivered
      RETURN
      DIVIDE ( take - payout - support, delivered )
      """, "#,0.00", F3,
      "SwiftBite take (22% of basket + fee) − courier base+tip payout − payment/support cost, per delivered order. Excludes the experiment bonus."),
]

EXPERIMENT = [
    M("Treated Zone-Days",
      'CALCULATE ( COUNTROWS ( fact_experiment_zone_day ), fact_experiment_zone_day[arm] = "treatment" )',
      "#,0", F4),
    M("Control Zone-Days",
      'CALCULATE ( COUNTROWS ( fact_experiment_zone_day ), fact_experiment_zone_day[arm] = "control" )',
      "#,0", F4),
    M("Fulfillment (Treated) %",
      'CALCULATE ( AVERAGE ( fact_experiment_zone_day[fulfillment_rate] ), fact_experiment_zone_day[arm] = "treatment" )',
      "0.0%", F4, "Mean fulfillment rate across treated zone-days (peak block)."),
    M("Fulfillment (Control) %",
      'CALCULATE ( AVERAGE ( fact_experiment_zone_day[fulfillment_rate] ), fact_experiment_zone_day[arm] = "control" )',
      "0.0%", F4),
    M("Fulfillment Lift (pp)",
      "( [Fulfillment (Treated) %] - [Fulfillment (Control) %] ) * 100", "+0.00;-0.00;0.00", F4,
      "Primary metric: treated − control mean fulfillment, in percentage points."),
    M("Fulfillment Lift SE (pp)",
      """
      VAR nt = [Treated Zone-Days]
      VAR nc = [Control Zone-Days]
      VAR vt = CALCULATE ( VAR.S ( fact_experiment_zone_day[fulfillment_rate] ), fact_experiment_zone_day[arm] = "treatment" )
      VAR vc = CALCULATE ( VAR.S ( fact_experiment_zone_day[fulfillment_rate] ), fact_experiment_zone_day[arm] = "control" )
      RETURN
      SQRT ( DIVIDE ( vt, nt ) + DIVIDE ( vc, nc ) ) * 100
      """, "0.00", F4,
      "Two-sample normal SE on the zone-day means. The cluster-robust (by zone) SE is a Phase-10 artifact."),
    M("Fulfillment Lift CI Low (pp)", "[Fulfillment Lift (pp)] - 1.96 * [Fulfillment Lift SE (pp)]", "+0.00;-0.00;0.00", F4),
    M("Fulfillment Lift CI High (pp)", "[Fulfillment Lift (pp)] + 1.96 * [Fulfillment Lift SE (pp)]", "+0.00;-0.00;0.00", F4),
    M("Fulfillment Lift Significant?",
      'IF ( [Fulfillment Lift CI Low (pp)] > 0, "Yes (95%)", "No" )', "", F4),
    M("ETA p90 (Treated) min",
      'CALCULATE ( AVERAGE ( fact_experiment_zone_day[eta_p90_min] ), fact_experiment_zone_day[arm] = "treatment" )',
      "0.0", F4),
    M("ETA p90 (Control) min",
      'CALCULATE ( AVERAGE ( fact_experiment_zone_day[eta_p90_min] ), fact_experiment_zone_day[arm] = "control" )',
      "0.0", F4),
    M("ETA p90 Lift (min)", "[ETA p90 (Treated) min] - [ETA p90 (Control) min]", "+0.0;-0.0;0.0", F4,
      "Co-primary evidence (lower is better)."),
    M("No-Courier Rate (Treated) %",
      'CALCULATE ( AVERAGE ( fact_experiment_zone_day[cancel_no_courier_rate] ), fact_experiment_zone_day[arm] = "treatment" )',
      "0.00%", F4),
    M("No-Courier Rate (Control) %",
      'CALCULATE ( AVERAGE ( fact_experiment_zone_day[cancel_no_courier_rate] ), fact_experiment_zone_day[arm] = "control" )',
      "0.00%", F4),
    M("No-Courier Rate Lift (pp)",
      "( [No-Courier Rate (Treated) %] - [No-Courier Rate (Control) %] ) * 100", "+0.00;-0.00;0.00", F4,
      "Co-primary evidence (lower is better)."),
    M("Incentive Spend - Experiment (BRL)",
      "SUM ( fact_experiment_zone_day[incentive_spend_brl] )", "#,0", F4),
    M("Incremental Delivered Orders",
      """
      VAR lift = [Fulfillment (Treated) %] - [Fulfillment (Control) %]
      VAR treated_placed =
          CALCULATE ( SUM ( fact_experiment_zone_day[orders_placed] ), fact_experiment_zone_day[arm] = "treatment" )
      RETURN
      lift * treated_placed
      """, "#,0", F4,
      "Treated orders delivered above the control fulfillment rate."),
    M("G1 Incentive Cost per Incremental Order (BRL)",
      "DIVIDE ( [Incentive Spend - Experiment (BRL)], [Incremental Delivered Orders] )", "#,0.00", F4,
      "The go/no-go economics: bonus spend ÷ incremental delivered orders."),
    M("G1 Verdict",
      """
      IF (
          [G1 Incentive Cost per Incremental Order (BRL)] < [Contribution Margin per Delivered Order (BRL)],
          "Pays for itself",
          "Costs more than it saves"
      )
      """, "", F4),
    M("Fulfillment Lift - Short tier (pp)",
      """
      VAR t = CALCULATE ( AVERAGE ( fact_experiment_zone_day[fulfillment_rate] ),
                          fact_experiment_zone_day[arm] = "treatment", dim_zone[baseline_supply_stress_tier] = "short" )
      VAR c = CALCULATE ( AVERAGE ( fact_experiment_zone_day[fulfillment_rate] ),
                          fact_experiment_zone_day[arm] = "control", dim_zone[baseline_supply_stress_tier] = "short" )
      RETURN ( t - c ) * 100
      """, "+0.00;-0.00;0.00", F4),
    M("Fulfillment Lift - Balanced tier (pp)",
      """
      VAR t = CALCULATE ( AVERAGE ( fact_experiment_zone_day[fulfillment_rate] ),
                          fact_experiment_zone_day[arm] = "treatment", dim_zone[baseline_supply_stress_tier] = "balanced" )
      VAR c = CALCULATE ( AVERAGE ( fact_experiment_zone_day[fulfillment_rate] ),
                          fact_experiment_zone_day[arm] = "control", dim_zone[baseline_supply_stress_tier] = "balanced" )
      RETURN ( t - c ) * 100
      """, "+0.00;-0.00;0.00", F4),
    M("Fulfillment Lift - Long tier (pp)",
      """
      VAR t = CALCULATE ( AVERAGE ( fact_experiment_zone_day[fulfillment_rate] ),
                          fact_experiment_zone_day[arm] = "treatment", dim_zone[baseline_supply_stress_tier] = "long" )
      VAR c = CALCULATE ( AVERAGE ( fact_experiment_zone_day[fulfillment_rate] ),
                          fact_experiment_zone_day[arm] = "control", dim_zone[baseline_supply_stress_tier] = "long" )
      RETURN ( t - c ) * 100
      """, "+0.00;-0.00;0.00", F4),
    M("Arm x Tier Contrast (Short minus Long, pp)",
      "[Fulfillment Lift - Short tier (pp)] - [Fulfillment Lift - Long tier (pp)]", "+0.00;-0.00;0.00", F4,
      "Descriptive heterogeneity contrast. The formal LR interaction test is Phase 10."),
    M("Cannibalisation - Adjacent-Control Gap (pp)",
      """
      VAR adj =
          CALCULATE ( AVERAGE ( fact_experiment_zone_day[fulfillment_rate] ),
              fact_experiment_zone_day[arm] = "control", fact_experiment_zone_day[is_adjacent_to_treated] = TRUE () )
      VAR noadj =
          CALCULATE ( AVERAGE ( fact_experiment_zone_day[fulfillment_rate] ),
              fact_experiment_zone_day[arm] = "control", fact_experiment_zone_day[is_adjacent_to_treated] = FALSE () )
      RETURN ( adj - noadj ) * 100
      """, "+0.00;-0.00;0.00", F4,
      "Fulfillment on control zone-days next to a treated zone minus control zone-days that are not. Negative = neighbours are being drained (cannibalisation)."),
    M("Cannibalisation-Adjusted Net Lift (pp)",
      "[Fulfillment Lift (pp)] + [Cannibalisation - Adjacent-Control Gap (pp)]", "+0.00;-0.00;0.00", F4,
      "Rough metro-level net of the local lift and the neighbour-zone drag. Phase 10 does the full spatial model."),
    M("Balance - Pre-period Fulfillment Gap (pp)",
      """
      VAR t = CALCULATE ( AVERAGE ( fact_incentive_assignment[pre_fulfillment_rate] ), fact_incentive_assignment[arm] = "treatment" )
      VAR c = CALCULATE ( AVERAGE ( fact_incentive_assignment[pre_fulfillment_rate] ), fact_incentive_assignment[arm] = "control" )
      RETURN ( t - c ) * 100
      """, "+0.00;-0.00;0.00", F4,
      "Should be ≈ 0 — a smoke test that randomisation balanced the arms on the 15-month baseline."),
    M("Settled Lift (weeks 8-10, pp)",
      """
      VAR t = CALCULATE ( AVERAGE ( fact_experiment_zone_block_week[fulfillment_rate] ),
                          fact_experiment_zone_block_week[arm] = "treatment", fact_experiment_zone_block_week[experiment_week] >= 8 )
      VAR c = CALCULATE ( AVERAGE ( fact_experiment_zone_block_week[fulfillment_rate] ),
                          fact_experiment_zone_block_week[arm] = "control", fact_experiment_zone_block_week[experiment_week] >= 8 )
      RETURN ( t - c ) * 100
      """, "+0.00;-0.00;0.00", F4,
      "Lift over the last three weeks — after any launch-novelty bump has decayed."),
    # --- unpinned helpers for by-arm / by-week visuals -----------------------
    M("Weekly Fulfillment %", "AVERAGE ( fact_experiment_zone_block_week[fulfillment_rate] )", "0.0%", F4,
      "Mean zone-block fulfillment per experiment week."),
    M("Weekly Fulfillment (Treated) %",
      'CALCULATE ( AVERAGE ( fact_experiment_zone_block_week[fulfillment_rate] ), fact_experiment_zone_block_week[arm] = "treatment" )',
      "0.0%", F4),
    M("Weekly Fulfillment (Control) %",
      'CALCULATE ( AVERAGE ( fact_experiment_zone_block_week[fulfillment_rate] ), fact_experiment_zone_block_week[arm] = "control" )',
      "0.0%", F4),
    M("Zone-Day Fulfillment %", "AVERAGE ( fact_experiment_zone_day[fulfillment_rate] )", "0.0%", F4,
      "Mean fulfillment across the zone-days in context — split by `arm` for the guardrail table."),
    M("Zone-Day ETA p90 (min)", "AVERAGE ( fact_experiment_zone_day[eta_p90_min] )", "0.0", F4),
    M("Zone-Day No-Courier Rate %", "AVERAGE ( fact_experiment_zone_day[cancel_no_courier_rate] )", "0.00%", F4),
    M("Zone-Day Earnings per Active Hour (BRL)",
      "AVERAGE ( fact_experiment_zone_day[courier_earnings_per_active_hour_brl] )", "#,0.00", F4),
    M("Zone-Day Incentive Cost per Order (BRL)",
      "AVERAGE ( fact_experiment_zone_day[incentive_cost_per_delivered_order_brl] )", "#,0.00", F4),
]

TARGETS = [
    M("Fulfillment vs Target (pp)", "( [Fulfillment Rate %] - 0.98 ) * 100", "+0.0;-0.0;0.0", F5,
      "Plan: ≥ 98% metro-wide (doc 01 §10)."),
    M("Peak ETA p90 vs Target (min)", "[Peak ETA p90 (min)] - 55", "+0.0;-0.0;0.0", F5,
      "Plan: ≤ 55 min at peak. Lower is better — good when negative."),
    M("No-Courier Rate vs Target (pp)", "( [No-Courier Rate %] - 0.005 ) * 100", "+0.00;-0.00;0.00", F5,
      "Plan: ≤ 0.5%. Lower is better."),
    M("Idle Courier Ratio vs Target (pp)", "( [Idle Courier Ratio %] - 0.25 ) * 100", "+0.0;-0.0;0.0", F5,
      "Plan: ≤ 25%. Lower is better."),
]

EXEC = [
    M("Exec Insight",
      """
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
      """, "", F6,
      "One-line dynamic read of the experiment for the Executive Overview page."),
]

MEASURE_LIBRARY = [
    (F1, MARKETPLACE),
    (F2, LIQUIDITY),
    (F3, COURIER),
    (F4, EXPERIMENT),
    (F5, TARGETS),
    (F6, EXEC),
]
