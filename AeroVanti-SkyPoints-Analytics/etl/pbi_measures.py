"""
pbi_measures.py — the DAX measure library for the AeroVanti SkyPoints semantic model.

`MEASURE_LIBRARY` = list of (display_folder, [measure, ...]). Each measure:
    {name, dax, format, folder, description}

`powerbi/gen_semantic_model.py` injects these into `_Measures.tmdl`.
`etl/gen_dax_doc.py` renders `docs/06_dax_measures.md` from the same list.

Conventions
- All money is BRL (no currency slicer).
- "Latest month" = MAX(dim_month[month_key]) in the current filter context.
- Time intelligence uses dim_month[month_sort] (a linear year*12+month index); PY =
  month_sort - 12. No marked date table, no SAMEPERIODLASTYEAR.
- Experiment measures read fact_experiment_outcome / fact_experiment_member_week and
  respect the Experiment Arm / Experiment Stratum slicers (disconnected dims read with
  SELECTEDVALUE where an explicit arm is needed).
- Breakage / lapse / liability-per-member are lower-is-better.
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
PROGRAM = [
    M("Members",
      "CALCULATE ( DISTINCTCOUNT ( dim_member[member_key] ), dim_member[member_key] > 0 )",
      "#,0", "01 Program", "Enrolled members, excluding the two sentinel rows."),
    M("Active Members",
      """
      VAR mk = MAX ( dim_month[month_key] )
      RETURN
      CALCULATE (
          DISTINCTCOUNT ( fact_member_month[member_key] ),
          fact_member_month[is_active_eom] = TRUE (),
          fact_member_month[month_key] = mk
      )
      """, "#,0", "01 Program",
      "Members with an earn or flight in the trailing 12 months, at the latest month in context."),
    M("Active Rate %",
      "DIVIDE ( [Active Members], [Members] )", "0.0%", "01 Program"),
    M("New Enrolments",
      "CALCULATE ( COUNTROWS ( fact_member_month ), fact_member_month[is_new_enrollment] = TRUE () )",
      "#,0", "01 Program", "First enrolment month for a member."),
    M("Co-brand Card Penetration %",
      """
      DIVIDE (
          CALCULATE ( DISTINCTCOUNT ( dim_member[member_key] ),
                      dim_member[has_cobrand_card] = TRUE (), dim_member[member_key] > 0 ),
          [Members]
      )
      """, "0.0%", "01 Program"),
]

EARN_BURN = [
    M("SkyPoints Issued",
      'CALCULATE ( SUM ( fact_point_transaction[points] ), fact_point_transaction[txn_type] = "earn" )',
      "#,0", "02 Earn & Burn"),
    M("SkyPoints Redeemed",
      '- CALCULATE ( SUM ( fact_point_transaction[points] ), fact_point_transaction[txn_type] = "redeem" )',
      "#,0", "02 Earn & Burn"),
    M("SkyPoints Expired",
      '- CALCULATE ( SUM ( fact_point_transaction[points] ), fact_point_transaction[txn_type] = "expire" )',
      "#,0", "02 Earn & Burn"),
    M("Burn Earn Ratio",
      "DIVIDE ( [SkyPoints Redeemed], [SkyPoints Issued] )", "0.0%", "02 Earn & Burn",
      "Points redeemed as a share of points issued over the period in context."),
    M("Redemptions",
      'CALCULATE ( COUNTROWS ( fact_point_transaction ), fact_point_transaction[txn_type] = "redeem" )',
      "#,0", "02 Earn & Burn"),
    M("Redeeming Members",
      'CALCULATE ( DISTINCTCOUNT ( fact_point_transaction[member_key] ), fact_point_transaction[txn_type] = "redeem" )',
      "#,0", "02 Earn & Burn"),
    M("Quarterly Redemption Rate %",
      """
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
      """, "0.0%", "02 Earn & Burn",
      "Share of active members with >= 1 redemption in the trailing quarter."),
    M("Ever-Redeemed Share %",
      """
      VAR mk = MAX ( dim_month[month_key] )
      RETURN
      DIVIDE (
          CALCULATE ( DISTINCTCOUNT ( fact_member_month[member_key] ),
                      fact_member_month[has_redeemed_ever_eom] = TRUE (),
                      fact_member_month[month_key] = mk ),
          [Active Members]
      )
      """, "0.0%", "02 Earn & Burn"),
    M("Avg Points Balance",
      """
      VAR mk = MAX ( dim_month[month_key] )
      RETURN
      CALCULATE ( AVERAGE ( fact_member_month[balance_pts_eom] ),
                  fact_member_month[month_key] = mk, fact_member_month[is_active_eom] = TRUE () )
      """, "#,0", "02 Earn & Burn"),
]

BREAKAGE = [
    M("Point Liability BRL",
      """
      VAR mk = MAX ( dim_month[month_key] )
      RETURN CALCULATE ( SUM ( fact_liability_month[liability_brl_gross] ),
                         fact_liability_month[month_key] = mk )
      """, '"R$"#,0', "03 Breakage & Liability"),
    M("Point Liability BRL (breakage-adj)",
      """
      VAR mk = MAX ( dim_month[month_key] )
      RETURN CALCULATE ( SUM ( fact_liability_month[liability_brl_breakage_adj] ),
                         fact_liability_month[month_key] = mk )
      """, '"R$"#,0', "03 Breakage & Liability"),
    M("Breakage Rate %",
      "DIVIDE ( [SkyPoints Expired], [SkyPoints Issued] )", "0.0%", "03 Breakage & Liability",
      "Points expired as a share of points issued over the period in context (realised)."),
    M("Points Expiring BRL",
      "SUM ( fact_liability_month[points_expired_m] ) * 0.021", '"R$"#,0', "03 Breakage & Liability"),
    M("Liability per Active Member",
      "DIVIDE ( [Point Liability BRL], [Active Members] )", '"R$"#,0.0', "03 Breakage & Liability"),
]

TIERS = [
    M("Members in Tier",
      """
      VAR mk = MAX ( dim_month[month_key] )
      RETURN CALCULATE ( DISTINCTCOUNT ( fact_member_month[member_key] ),
                         fact_member_month[month_key] = mk, fact_member_month[is_active_eom] = TRUE () )
      """, "#,0", "04 Tiers"),
    M("Elite Share %",
      """
      DIVIDE (
          CALCULATE ( [Members in Tier], dim_tier[is_elite] = TRUE () ),
          CALCULATE ( [Members in Tier], REMOVEFILTERS ( dim_tier ) )
      )
      """, "0.0%", "04 Tiers"),
    M("Tier Upgrades",
      'CALCULATE ( COUNTROWS ( fact_tier_change ), fact_tier_change[direction] = "upgrade" )',
      "#,0", "04 Tiers"),
    M("Tier Downgrades",
      'CALCULATE ( COUNTROWS ( fact_tier_change ), fact_tier_change[direction] IN { "downgrade", "retain_drop" } )',
      "#,0", "04 Tiers"),
    M("Flight Revenue BRL",
      "CALCULATE ( SUM ( fact_flight_segment[base_fare_brl] ), fact_flight_segment[is_award_redemption] = FALSE () )",
      '"R$"#,0', "05 Commercial"),
    M("Revenue per Active Member",
      "DIVIDE ( [Flight Revenue BRL], [Active Members] )", '"R$"#,0', "05 Commercial"),
    M("Award Seat Share %",
      """
      DIVIDE (
          CALCULATE ( COUNTROWS ( fact_flight_segment ), fact_flight_segment[is_award_redemption] = TRUE () ),
          COUNTROWS ( fact_flight_segment )
      )
      """, "0.0%", "05 Commercial"),
    M("Card Spend BRL",
      "SUM ( fact_card_spend_month[card_spend_brl] )", '"R$"#,0', "05 Commercial"),
]

LAPSE = [
    M("Account-Lapsed Members",
      """
      VAR mk = MAX ( dim_month[month_key] )
      RETURN CALCULATE ( DISTINCTCOUNT ( fact_member_month[member_key] ),
                         fact_member_month[is_lapsed_eom] = 1, fact_member_month[month_key] = mk )
      """, "#,0", "06 Retention & Lapse",
      "Members in account-lapse (no earn and no redemption for 12 months) at the latest month."),
    M("Account Lapse Rate %",
      "DIVIDE ( [Account-Lapsed Members], [Active Members] + [Account-Lapsed Members] )",
      "0.0%", "06 Retention & Lapse"),
    M("Engagement-Lapsed Members",
      """
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
      """, "#,0", "06 Retention & Lapse",
      "Members with no flight and no redemption for 12 months (card-only earn does not count)."),
    M("Engagement Lapse Rate %",
      "DIVIDE ( [Engagement-Lapsed Members], [Active Members] )", "0.0%", "06 Retention & Lapse"),
    M("Reactivations",
      "CALCULATE ( COUNTROWS ( fact_member_month ), fact_member_month[is_reactivation] = TRUE () )",
      "#,0", "06 Retention & Lapse"),
]

EXPERIMENT = [
    M("Exp Subjects",
      "DISTINCTCOUNT ( fact_experiment_outcome[member_key] )", "#,0", "07 A/B Test"),
    M("Exp Redemption Rate",
      """
      DIVIDE (
          CALCULATE ( COUNTROWS ( fact_experiment_outcome ),
                      fact_experiment_outcome[redeemed_in_window] = TRUE () ),
          COUNTROWS ( fact_experiment_outcome )
      )
      """, "0.0%", "07 A/B Test",
      "Share of subjects (in the current arm/stratum filter) with >= 1 redemption in the 12-week window."),
    M("Exp Control Rate",
      'CALCULATE ( [Exp Redemption Rate], fact_experiment_outcome[arm_key] = "control" )',
      "0.0%", "07 A/B Test"),
    M("Exp Treatment Rate",
      'CALCULATE ( [Exp Redemption Rate], fact_experiment_outcome[arm_key] = "treatment" )',
      "0.0%", "07 A/B Test"),
    M("Exp Lift pp",
      "( [Exp Treatment Rate] - [Exp Control Rate] ) * 100", "+0.00;-0.00;0.00", "07 A/B Test",
      "Absolute treatment - control difference in the redemption rate, in percentage points."),
    M("Exp Lift Rel %",
      "DIVIDE ( [Exp Treatment Rate] - [Exp Control Rate], [Exp Control Rate] )", "+0.0%;-0.0%;0.0%", "07 A/B Test"),
    M("Exp Lift CI Low pp",
      """
      VAR p1 = [Exp Control Rate]   VAR p2 = [Exp Treatment Rate]
      VAR n1 = CALCULATE ( [Exp Subjects], fact_experiment_outcome[arm_key] = "control" )
      VAR n2 = CALCULATE ( [Exp Subjects], fact_experiment_outcome[arm_key] = "treatment" )
      VAR se = SQRT ( DIVIDE ( p1 * ( 1 - p1 ), n1 ) + DIVIDE ( p2 * ( 1 - p2 ), n2 ) )
      RETURN ( ( p2 - p1 ) - 1.959964 * se ) * 100
      """, "+0.00;-0.00;0.00", "07 A/B Test"),
    M("Exp Lift CI High pp",
      """
      VAR p1 = [Exp Control Rate]   VAR p2 = [Exp Treatment Rate]
      VAR n1 = CALCULATE ( [Exp Subjects], fact_experiment_outcome[arm_key] = "control" )
      VAR n2 = CALCULATE ( [Exp Subjects], fact_experiment_outcome[arm_key] = "treatment" )
      VAR se = SQRT ( DIVIDE ( p1 * ( 1 - p1 ), n1 ) + DIVIDE ( p2 * ( 1 - p2 ), n2 ) )
      RETURN ( ( p2 - p1 ) + 1.959964 * se ) * 100
      """, "+0.00;-0.00;0.00", "07 A/B Test"),
    M("Exp Z Stat",
      """
      VAR p1 = [Exp Control Rate]   VAR p2 = [Exp Treatment Rate]
      VAR n1 = CALCULATE ( [Exp Subjects], fact_experiment_outcome[arm_key] = "control" )
      VAR n2 = CALCULATE ( [Exp Subjects], fact_experiment_outcome[arm_key] = "treatment" )
      VAR pp = DIVIDE ( p1 * n1 + p2 * n2, n1 + n2 )
      VAR se = SQRT ( pp * ( 1 - pp ) * ( DIVIDE ( 1, n1 ) + DIVIDE ( 1, n2 ) ) )
      RETURN DIVIDE ( p2 - p1, se )
      """, "0.00", "07 A/B Test", "Two-proportion pooled z-statistic."),
    M("Exp Significant 95%",
      'IF ( ABS ( [Exp Z Stat] ) > 1.959964, "Significant", "Not significant" )',
      "", "07 A/B Test"),
    M("Exp SRM Ratio",
      """
      DIVIDE (
          CALCULATE ( [Exp Subjects], fact_experiment_outcome[arm_key] = "treatment" ),
          [Exp Subjects]
      )
      """, "0.0%", "07 A/B Test", "Treatment share of subjects; expect 50% (sample-ratio-mismatch check)."),
    M("Exp Revenue per Member",
      "AVERAGE ( fact_experiment_outcome[revenue_brl_window_plus8w] )", '"R$"#,0', "07 A/B Test"),
    M("Exp Revenue per Member Delta %",
      """
      DIVIDE (
          CALCULATE ( [Exp Revenue per Member], fact_experiment_outcome[arm_key] = "treatment" )
        - CALCULATE ( [Exp Revenue per Member], fact_experiment_outcome[arm_key] = "control" ),
          CALCULATE ( [Exp Revenue per Member], fact_experiment_outcome[arm_key] = "control" )
      )
      """, "+0.0%;-0.0%;0.0%", "07 A/B Test", "Guardrail: non-inferiority margin is -3%."),
    M("Exp Net Liability Cost per Member",
      "AVERAGE ( fact_experiment_outcome[net_liability_cost_brl] )", '"R$"#,0.00', "07 A/B Test"),
    M("Exp Disengaged 90d %",
      """
      DIVIDE (
          CALCULATE ( COUNTROWS ( fact_experiment_outcome ),
                      fact_experiment_outcome[disengaged_90d_post] = TRUE () ),
          COUNTROWS ( fact_experiment_outcome )
      )
      """, "0.0%", "07 A/B Test",
      "Guardrail: share with no earn and no redemption in the 90 days after the window."),
    M("Exp Redemption Value per Redeemer",
      """
      DIVIDE (
          SUM ( fact_experiment_outcome[redemption_value_brl] ),
          CALCULATE ( COUNTROWS ( fact_experiment_outcome ),
                      fact_experiment_outcome[redeemed_in_window] = TRUE () )
      )
      """, '"R$"#,0', "07 A/B Test", "Guardrail: depth of redemptions (Flash makes them shallower)."),
    M("Exp Weekly Redeemers %",
      "DIVIDE ( CALCULATE ( COUNTROWS ( fact_experiment_member_week ), fact_experiment_member_week[redeemed_w] = TRUE () ), [Exp Subjects] )",
      "0.00%", "07 A/B Test", "Redeemers in the week / subjects — plot by week and arm for the novelty check."),
    M("Exp Effect by Tier pp",
      "[Exp Lift pp]", "+0.00;-0.00;0.00", "07 A/B Test",
      "Same as Exp Lift pp; place on a bar by Experiment Stratum for the heterogeneity cut."),
]

TIME_TGT = [
    M("SkyPoints Redeemed PY",
      """
      CALCULATE (
          [SkyPoints Redeemed],
          FILTER ( ALL ( dim_month ),
                   dim_month[month_sort] = MAX ( dim_month[month_sort] ) - 12 )
      )
      """, "#,0", "08 Time & Targets"),
    M("SkyPoints Redeemed YoY %",
      "DIVIDE ( [SkyPoints Redeemed] - [SkyPoints Redeemed PY], [SkyPoints Redeemed PY] )",
      "+0.0%;-0.0%;0.0%", "08 Time & Targets"),
    M("Breakage Rate Target",
      """
      VAR mk = MAX ( dim_month[month_key] )
      RETURN CALCULATE ( AVERAGE ( fact_targets_month[target_value] ),
                         fact_targets_month[kpi] = "breakage_rate", fact_targets_month[month_key] = mk )
      """, "0.0%", "08 Time & Targets"),
    M("Redemption Rate Target",
      """
      VAR mk = MAX ( dim_month[month_key] )
      RETURN CALCULATE ( AVERAGE ( fact_targets_month[target_value] ),
                         fact_targets_month[kpi] = "redemption_rate_quarterly", fact_targets_month[month_key] = mk )
      """, "0.0%", "08 Time & Targets"),
    M("Quarterly Redemption Rate vs Target",
      "[Quarterly Redemption Rate %] - [Redemption Rate Target]", "+0.0%;-0.0%;0.0%", "08 Time & Targets"),
    M("Breakage Rate vs Target",
      "[Breakage Rate %] - [Breakage Rate Target]", "+0.0%;-0.0%;0.0%", "08 Time & Targets",
      "Lower is better — negative is good."),
]

NARRATIVE = [
    M("Exec Insight",
      '''
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
      ''', "", "09 Narrative",
      "Dynamic summary sentence for the Executive Summary page; updates with the slicers."),
]

FUNNEL = [
    M("Members with Redeemable Balance",
      """
      VAR mk = MAX ( dim_month[month_key] )
      RETURN CALCULATE ( DISTINCTCOUNT ( fact_member_month[member_key] ),
                         fact_member_month[month_key] = mk,
                         fact_member_month[is_active_eom] = TRUE (),
                         fact_member_month[balance_pts_eom] >= 3500 )
      """, "#,0", "10 Funnel",
      "Active members whose balance clears the Flash minimum redemption threshold."),
    M("Redeemers in Last 12m",
      """
      VAR mk = MAX ( dim_month[month_key] )
      VAR startsort = MAXX ( FILTER ( ALL ( dim_month ), dim_month[month_key] = mk ), dim_month[month_sort] ) - 11
      RETURN
      CALCULATE ( DISTINCTCOUNT ( fact_member_month[member_key] ),
                  fact_member_month[redemptions_m] > 0,
                  FILTER ( ALL ( dim_month ), dim_month[month_sort] >= startsort && dim_month[month_key] <= mk ) )
      """, "#,0", "10 Funnel"),
    M("Redeemers in Last Quarter",
      """
      VAR mk = MAX ( dim_month[month_key] )
      VAR startsort = MAXX ( FILTER ( ALL ( dim_month ), dim_month[month_key] = mk ), dim_month[month_sort] ) - 2
      RETURN
      CALCULATE ( DISTINCTCOUNT ( fact_member_month[member_key] ),
                  fact_member_month[redemptions_m] > 0,
                  FILTER ( ALL ( dim_month ), dim_month[month_sort] >= startsort && dim_month[month_key] <= mk ) )
      """, "#,0", "10 Funnel"),
    M("Ever-Redeemed Members",
      """
      VAR mk = MAX ( dim_month[month_key] )
      RETURN CALCULATE ( DISTINCTCOUNT ( fact_member_month[member_key] ),
                         fact_member_month[has_redeemed_ever_eom] = TRUE (), fact_member_month[month_key] = mk )
      """, "#,0", "10 Funnel"),
    M("Funnel Value",
      '''
      VAR s = SELECTEDVALUE ( 'Funnel Stage'[stage] )
      RETURN
      SWITCH ( s,
          "Active members", [Active Members],
          "Have points >= Flash threshold", [Members with Redeemable Balance],
          "Ever redeemed", [Ever-Redeemed Members],
          "Redeemed in last 12m", [Redeemers in Last 12m],
          "Redeemed in last quarter", [Redeemers in Last Quarter],
          BLANK () )
      ''', "#,0", "10 Funnel",
      "Member count at the selected redemption-funnel stage (place 'Funnel Stage'[stage] on Category)."),
]

MEASURE_LIBRARY = [
    ("01 Program", PROGRAM),
    ("02 Earn & Burn", EARN_BURN),
    ("03 Breakage & Liability", BREAKAGE),
    ("04 Tiers / 05 Commercial", TIERS),
    ("06 Retention & Lapse", LAPSE),
    ("07 A/B Test", EXPERIMENT),
    ("08 Time & Targets", TIME_TGT),
    ("09 Narrative", NARRATIVE),
    ("10 Funnel", FUNNEL),
]
