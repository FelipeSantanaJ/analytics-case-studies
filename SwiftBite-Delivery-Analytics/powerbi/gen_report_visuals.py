"""
gen_report_visuals.py — write powerbi/_report_layout.json, the layout manifest that
_drive_pbir.py turns into the 4-page SwiftBiteDelivery.Report via the `pbir` CLI.

    python powerbi/gen_report_visuals.py

One business question per page (see docs/00_scope.md §3 / assets/brand.py PAGE_TITLES).
"""
from __future__ import annotations

import json
from pathlib import Path

PBI = Path(__file__).resolve().parent
CANVAS_W = 1280
KPI_X = [24, 231, 439, 646, 853, 1061]
KPI_W = 195


def kpis(page_key, items):
    """items: list of (title, value_measure, good) — up to 6."""
    out = []
    for i, (title, value, good) in enumerate(items):
        out.append({"title": title, "value": f"_Measures.{value}", "delta": None,
                    "good": good, "x": KPI_X[i], "y": 132, "w": KPI_W,
                    "delta_y": 208, "delta_h": 22})
    return out


def V(name, vtype, x, y, w, h, title, roles, sort=None):
    d = {"name": name, "type": vtype, "x": x, "y": y, "w": w, "h": h,
         "title": title, "roles": roles}
    if sort:
        d["sort"] = sort
    return d


def m(*names):
    return [f"_Measures.{n}" for n in names]


LAYOUT = {
    "report_name": "SwiftBiteDelivery",
    "canvas_width": CANVAS_W,
    "kpi_frame": {"x": 16, "y": 120, "w": 1248, "h": 116, "radius": 18},
    "slicers": [
        {"name": "sl-period", "field": "dim_date.date", "x": 24, "y": 126, "w": 320, "h": 34,
         "title": "Analysis period"},
        {"name": "sl-zone", "field": "dim_zone.zone_name", "x": 856, "y": 126, "w": 210, "h": 34,
         "title": "Zone"},
        {"name": "sl-tier", "field": "dim_zone.baseline_supply_stress_tier", "x": 1078, "y": 126,
         "w": 178, "h": 34, "title": "Supply-stress tier"},
    ],
    "pages": [
        {
            "key": "01_executive", "name": "01_executive", "display": "Executive Overview",
            "height": 860,
            "kpis": kpis("01_executive", [
                ("Fulfillment Rate", "Fulfillment Rate %", "high"),
                ("Peak ETA p90 (min)", "Peak ETA p90 (min)", "low"),
                ("No-Courier Rate", "No-Courier Rate %", "low"),
                ("Idle Courier Ratio", "Idle Courier Ratio %", "low"),
                ("Incentive Lift (pp)", "Fulfillment Lift (pp)", "high"),
                ("Cost / Incremental Order", "G1 Incentive Cost per Incremental Order (BRL)", "low"),
            ]),
            "visuals": [
                V("fulfillment_trend", "lineChart", 24, 236, 730, 250,
                  "Fulfillment rate over the window",
                  {"Category": "dim_date.date", "Y": m("Fulfillment Rate %")}),
                V("exec_insight", "card", 766, 236, 490, 250, "Read this",
                  {"Values": m("Exec Insight")}),
                V("lift_by_tier_exec", "clusteredBarChart", 24, 500, 490, 232,
                  "Fulfillment lift by baseline supply-stress tier (pp)",
                  {"Category": "dim_zone.baseline_supply_stress_tier", "Y": m("Fulfillment Lift (pp)")},
                  {"by": "dim_zone.baseline_supply_stress_tier", "dir": "asc"}),
                V("novelty_exec", "lineChart", 530, 500, 726, 232,
                  "Weekly fulfillment, treated vs control — novelty check",
                  {"Category": "fact_experiment_zone_block_week.experiment_week",
                   "Y": m("Weekly Fulfillment (Treated) %", "Weekly Fulfillment (Control) %")},
                  {"by": "fact_experiment_zone_block_week.experiment_week", "dir": "asc"}),
            ],
        },
        {
            "key": "02_health", "name": "02_health", "display": "Marketplace Health",
            "height": 720,
            "kpis": kpis("02_health", [
                ("Orders Placed", "Orders Placed", "high"),
                ("Fulfillment Rate", "Fulfillment Rate %", "high"),
                ("ETA p90 (min)", "ETA p90 (min)", "low"),
                ("No-Courier Rate", "No-Courier Rate %", "low"),
                ("Liquidity Ratio", "Liquidity Ratio", "high"),
                ("Idle Courier Ratio", "Idle Courier Ratio %", "low"),
            ]),
            "visuals": [
                V("fulfillment_by_zone", "clusteredBarChart", 24, 236, 610, 230,
                  "Fulfillment rate by zone",
                  {"Category": "dim_zone.zone_name", "Y": m("Fulfillment Rate %")},
                  {"by": "_Measures.Fulfillment Rate %", "dir": "asc"}),
                V("liquidity_matrix", "matrix", 646, 236, 610, 230,
                  "Liquidity ratio by zone x daypart",
                  {"Rows": "dim_zone.zone_name", "Columns": "dim_time_block.daypart",
                   "Values": m("Liquidity Ratio")}),
                V("eta_by_hour", "lineChart", 24, 480, 610, 224,
                  "ETA p90 by hour of day",
                  {"Category": "dim_time_block.hour", "Y": m("ETA p90 (min)")},
                  {"by": "dim_time_block.hour", "dir": "asc"}),
                V("cancels_by_cause", "clusteredColumnChart", 646, 480, 610, 224,
                  "Cancellations by cause and zone",
                  {"Category": "dim_zone.zone_name",
                   "Y": m("No-Courier Cancels", "Customer Cancels")}),
            ],
        },
        {
            "key": "03_experiment", "name": "03_experiment", "display": "Pricing & Incentive Experiment",
            "height": 720,
            "kpis": kpis("03_experiment", [
                ("Fulfillment Lift (pp)", "Fulfillment Lift (pp)", "high"),
                ("ETA p90 Lift (min)", "ETA p90 Lift (min)", "low"),
                ("No-Courier Lift (pp)", "No-Courier Rate Lift (pp)", "low"),
                ("Cost / Incremental Order", "G1 Incentive Cost per Incremental Order (BRL)", "low"),
                ("Neighbour-Zone Gap (pp)", "Cannibalisation - Adjacent-Control Gap (pp)", "high"),
                ("Adjusted Net Lift (pp)", "Cannibalisation-Adjusted Net Lift (pp)", "high"),
            ]),
            "visuals": [
                V("lift_by_tier", "clusteredBarChart", 24, 236, 610, 232,
                  "Fulfillment lift by tier (pp) — heterogeneity",
                  {"Category": "dim_zone.baseline_supply_stress_tier", "Y": m("Fulfillment Lift (pp)")},
                  {"by": "dim_zone.baseline_supply_stress_tier", "dir": "asc"}),
                V("fulfillment_by_arm", "clusteredColumnChart", 646, 236, 610, 232,
                  "Fulfillment by arm (zone-day mean)",
                  {"Category": "fact_experiment_zone_day.arm", "Y": m("Zone-Day Fulfillment %")}),
                V("novelty_curve", "lineChart", 24, 482, 726, 224,
                  "Weekly fulfillment, treated vs control — launch bump vs settled",
                  {"Category": "fact_experiment_zone_block_week.experiment_week",
                   "Y": m("Weekly Fulfillment (Treated) %", "Weekly Fulfillment (Control) %")},
                  {"by": "fact_experiment_zone_block_week.experiment_week", "dir": "asc"}),
                V("guardrails", "tableEx", 762, 482, 494, 224, "Guardrails by arm",
                  {"Values": ["fact_experiment_zone_day.arm"] + m(
                      "Zone-Day Fulfillment %", "Zone-Day ETA p90 (min)", "Zone-Day No-Courier Rate %",
                      "Zone-Day Earnings per Active Hour (BRL)", "Zone-Day Incentive Cost per Order (BRL)")}),
            ],
        },
        {
            "key": "04_courier", "name": "04_courier", "display": "Courier Economics",
            "height": 720,
            "kpis": kpis("04_courier", [
                ("Active Couriers", "Active Couriers", "high"),
                ("Earnings / Active Hr", "Earnings per Active Hour (BRL)", "high"),
                ("Utilisation", "Utilisation %", "high"),
                ("Deliveries / Active Hr", "Deliveries per Active Hour", "high"),
                ("Contribution Margin", "Contribution Margin per Delivered Order (BRL)", "high"),
                ("Incentive % of Payout", "Incentive Spend as % of Payout", "low"),
            ]),
            "visuals": [
                V("earnings_by_daypart", "clusteredColumnChart", 24, 236, 610, 230,
                  "Courier earnings per active hour by daypart",
                  {"Category": "dim_time_block.daypart", "Y": m("Earnings per Active Hour (BRL)")},
                  {"by": "dim_time_block.daypart", "dir": "asc"}),
                V("utilisation_by_zone", "clusteredBarChart", 646, 236, 610, 230,
                  "Utilisation by zone",
                  {"Category": "dim_zone.zone_name", "Y": m("Utilisation %")},
                  {"by": "_Measures.Utilisation %", "dir": "asc"}),
                V("supply_vs_demand", "lineChart", 24, 480, 610, 224,
                  "Available vs demanded courier-hours by hour",
                  {"Category": "dim_time_block.hour",
                   "Y": m("Available Courier-Hours", "Demanded Courier-Hours")},
                  {"by": "dim_time_block.hour", "dir": "asc"}),
                V("incentive_cost_by_tier", "clusteredColumnChart", 646, 480, 610, 224,
                  "Incentive cost per delivered order by tier (treated zone-days)",
                  {"Category": "dim_zone.baseline_supply_stress_tier",
                   "Y": m("Zone-Day Incentive Cost per Order (BRL)")},
                  {"by": "dim_zone.baseline_supply_stress_tier", "dir": "asc"}),
            ],
        },
    ],
}


def main():
    (PBI / "_report_layout.json").write_text(json.dumps(LAYOUT, indent=2), encoding="utf-8")
    n_v = sum(len(p["visuals"]) + len(p["kpis"]) for p in LAYOUT["pages"])
    print(f"wrote powerbi/_report_layout.json  ({len(LAYOUT['pages'])} pages, ~{n_v} visuals + KPIs)")


if __name__ == "__main__":
    main()
