"""
gen_report_visuals.py — emit powerbi/_report_layout.json, the layout manifest that
_drive_pbir.py turns into `pbir` calls.

7 pages, one business question each. Every page: a page-background PNG, a
Currency + Market + Analysis-Period slicer row, a white KPI frame with six value
cards + delta cards, then two content rows on the 3-30-300 gradient.

Roles (from `pbir schema roles`): charts use Category / Y / Series;
pivotTable uses Rows / Columns / Values; card + slicer + tableEx use Values.
"""
from __future__ import annotations
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "assets"))
import brand as B  # noqa

PBI = Path(__file__).resolve().parent
M = "_Measures."
GOOD_HIGH, GOOD_LOW = "high", "low"

W = B.CANVAS_W
MARGIN = 24
GUT = 12
KPI_Y = 172            # top of the KPI value cards
                       # (was 138 -> FRAME_Y=128 sat on top of the header wallpaper's
                       # own subtitle/divider, which ends at y=152; see assets/gen_logo.py
                       # _page_bg: ty=band_h+22=82, divider at ty+70=152)
KPI_H = 58             # value-card height
KPI_DELTA_H = 22       # delta-card height, sits just under the value card
KPI_GAP = 2            # value -> delta gap
FRAME_Y = KPI_Y - 10
FRAME_H = 10 + KPI_H + KPI_GAP + KPI_DELTA_H + 12    # -> frame bottom = FRAME_Y + FRAME_H
SLICER_Y = FRAME_Y + FRAME_H + 6                     # slicer row lives *below* the KPI frame
SLICER_H = 28
CONTENT_Y = 310        # was 276; shifted +34 to match KPI_Y, keeping the same
                       # gap to the (now lower) slicer row
R2 = CONTENT_Y
R3 = CONTENT_Y + 250 + 16

YM = "dim_date.year_month"
SORT_YM = {"by": "dim_date.year_month", "dir": "asc"}   # year_month sorts by month_sort in the model
MKT = "dim_subscriber.market"


def col(n, span, cols=12, x0=MARGIN, total=W):
    inner = total - 2 * x0 - (cols - 1) * GUT
    cw = inner / cols
    return round(x0 + n * (cw + GUT)), round(span * cw + (span - 1) * GUT)


def kpi(title, value, delta=None, good=GOOD_HIGH):
    return {"title": title, "value": M + value,
            "delta": (M + delta) if delta else None, "good": good}


def kpi_row(items):
    out = []
    for i, it in enumerate(items):
        x, w = col(i * 2, 2)
        out.append({**it, "x": x, "y": KPI_Y, "w": w, "val_h": KPI_H,
                    "delta_y": KPI_Y + KPI_H + KPI_GAP, "delta_h": KPI_DELTA_H})
    return out


DISPLAY = {
    "01_executive": "Executive Summary",
    "02_retention": "Retention & Cohorts",
    "03_engagement": "Content & Engagement",
    "04_pricing": "Pricing & Plans",
    "05_acquisition": "Acquisition Quality",
    "06_experience": "CX, Billing & App",
    "07_market": "Market Context",
}


def V(name, type_, gx, gspan, y, h, roles, title, sort=None):
    x, w = col(gx, gspan)
    v = {"name": name, "type": type_, "x": x, "y": y, "w": w, "h": h,
         "roles": roles, "title": title}
    if sort:
        v["sort"] = sort
    return v


def line(name, gx, gspan, y, h, measures, title, category=YM, series=None, sort=SORT_YM):
    # lineChart has no Series role in the core catalogue; a series -> clustered columns
    roles = {"Category": category, "Y": [M + m for m in measures]}
    if series:
        roles["Series"] = series
        return V(name, "clusteredColumnChart", gx, gspan, y, h, roles, title, sort)
    return V(name, "lineChart", gx, gspan, y, h, roles, title, sort)


def cols_(name, gx, gspan, y, h, measures, title, category=YM, series=None, sort=SORT_YM,
          stacked=False):
    roles = {"Category": category, "Y": [M + m for m in measures]}
    if series:
        roles["Series"] = series
    t = "stackedColumnChart" if stacked else "clusteredColumnChart"
    return V(name, t, gx, gspan, y, h, roles, title, sort)


def bars(name, gx, gspan, y, h, category, measure, title):
    return V(name, "clusteredBarChart", gx, gspan, y, h,
             {"Category": category, "Y": [M + measure]}, title)


PAGES = [
    # ================================================================= 01
    {"key": "01_executive", "name": "01_executive", "height": B.PAGE_H_EXEC,
     "kpis": kpi_row([
         kpi("Paid Subscribers (EoP)", "Paid Active Subscribers (EoP)", "Paid Active Subscribers vs Target %", GOOD_HIGH),
         kpi("Gross Monthly Churn", "Gross Monthly Churn % (Latest)", "Gross Churn vs Target (pp)", GOOD_LOW),
         kpi("Churn vs Baseline", "Churn vs Baseline (x) (Latest)", None, GOOD_LOW),
         kpi("Net Adds (last month)", "Net Adds (Latest)", None, GOOD_HIGH),
         kpi("MRR (last month)", "MRR (Latest)", "MRR vs Target %", GOOD_HIGH),
         kpi("LTV : CAC", "LTV to CAC (Latest)", None, GOOD_HIGH),
     ]),
     "visuals": [
         line("churn_vs_baseline", 0, 7, R2, 250,
              ["Gross Monthly Churn %", "Pre-Shift Baseline Churn %"],
              "Gross monthly churn vs the pre-shift baseline"),
         V("exec_insight", "card", 7, 5, R2, 250, {"Values": [M + "Exec Insight"]}, "Read this"),
         line("churn_by_market", 0, 6, R3, 250, ["Gross Monthly Churn %"],
              "Gross monthly churn by market", series=MKT),
         cols_("vol_invol", 6, 6, R3, 250,
               ["Voluntary Churned Subscribers", "Involuntary Churned Subscribers"],
               "Voluntary vs involuntary churned subscribers"),
         cols_("net_adds", 0, 12, R3 + 256, 92, ["Net Adds"], "Net subscriber adds by month"),
     ]},

    # ================================================================= 02
    {"key": "02_retention", "name": "02_retention", "height": B.PAGE_H_STANDARD,
     "kpis": kpi_row([
         kpi("Gross Monthly Churn", "Gross Monthly Churn %", "Gross Churn vs Target (pp)", GOOD_LOW),
         kpi("Voluntary Churn", "Voluntary Churn %", None, GOOD_LOW),
         kpi("Involuntary Churn", "Involuntary Churn %", None, GOOD_LOW),
         kpi("M1 Retention", "M1 Retention %", None, GOOD_HIGH),
         kpi("M6 Retention", "M6 Retention %", None, GOOD_HIGH),
         kpi("Net MRR Retention", "Net MRR Retention %", None, GOOD_HIGH),
     ]),
     "visuals": [
         V("cohort_triangle", "pivotTable", 0, 7, R2, 250,
           {"Rows": "dim_subscriber.cohort_month",
            "Columns": "fact_subscription_month.tenure_months",
            "Values": [M + "Retention %"]}, "Cohort retention triangle (share still active)"),
         bars("churn_by_tier", 7, 5, R2, 250, "dim_subscriber.current_tier",
              "Gross Monthly Churn %", "Gross monthly churn by plan tier"),
         line("churn_by_tenure", 0, 6, R3, 250, ["Gross Monthly Churn %"],
              "Gross monthly churn by tenure (months)",
              category="fact_subscription_month.tenure_months",
              sort={"by": "fact_subscription_month.tenure_months", "dir": "asc"}),
         cols_("churn_by_channel", 6, 6, R3, 250, ["Gross Churned Subscribers"],
               "Churned subscribers by acquisition channel",
               category="dim_subscriber.acquisition_channel", sort=None),
     ]},

    # ================================================================= 03
    {"key": "03_engagement", "name": "03_engagement", "height": B.PAGE_H_STANDARD,
     "kpis": kpi_row([
         kpi("Monthly Active Rate", "Monthly Active Rate %", None, GOOD_HIGH),
         kpi("Hours / Active Sub", "Viewing Hours per Active Sub", None, GOOD_HIGH),
         kpi("% Below Healthy Eng.", "% Subs Below Healthy Engagement", None, GOOD_LOW),
         kpi("Titles / Active Sub", "Titles Started per Active Sub", None, GOOD_HIGH),
         kpi("% Days on CTV", "Avg % Days on Connected TV", None, GOOD_HIGH),
         kpi("Streamed Hours", "Streamed Hours", None, GOOD_HIGH),
     ]),
     "visuals": [
         line("hours_trend", 0, 6, R2, 250, ["Viewing Hours per Active Sub"],
              "Viewing hours per active subscriber"),
         line("vsf_by_device", 6, 6, R2, 250, ["Video Start Failure Rate"],
              "Video-start-failure rate by device class", series="dim_device.device_class"),
         line("below_healthy_trend", 0, 6, R3, 250, ["% Subs Below Healthy Engagement"],
              "Share of subscribers below healthy engagement"),
         cols_("hours_by_device", 6, 6, R3, 250, ["Streamed Hours (by Device)"],
               "Streamed hours by device family",
               category="dim_device.device_family", sort=None),
     ]},

    # ================================================================= 04
    {"key": "04_pricing", "name": "04_pricing", "height": B.PAGE_H_STANDARD,
     "kpis": kpi_row([
         kpi("ARPU", "ARPU", None, GOOD_HIGH),
         kpi("Gross Margin", "Gross Margin %", None, GOOD_HIGH),
         kpi("Gross Monthly Churn", "Gross Monthly Churn %", "Gross Churn vs Target (pp)", GOOD_LOW),
         kpi("% Below Healthy Eng.", "% Subs Below Healthy Engagement", None, GOOD_LOW),
         kpi("MRR (last month)", "MRR (Latest)", "MRR vs Target %", GOOD_HIGH),
         kpi("Net MRR Retention", "Net MRR Retention %", None, GOOD_HIGH),
     ]),
     "visuals": [
         line("churn_by_tier_time", 0, 7, R2, 250, ["Gross Monthly Churn %"],
              "Gross monthly churn by tier over time", series="dim_subscriber.current_tier"),
         V("price_history", "tableEx", 7, 5, R2, 250,
           {"Values": ["dim_price_history.tier", "dim_price_history.market_id",
                       "dim_price_history.list_price_local"]}, "Plan list-price history"),
         line("arpu_by_market", 0, 6, R3, 250, ["ARPU"], "ARPU by market", series=MKT),
         cols_("churned_by_tier_month", 6, 6, R3, 250, ["Gross Churned Subscribers"],
               "Churned subscribers by tier and month (filter market = BR)",
               series="dim_subscriber.current_tier"),
     ]},

    # ================================================================= 05
    {"key": "05_acquisition", "name": "05_acquisition", "height": B.PAGE_H_STANDARD,
     "kpis": kpi_row([
         kpi("New Subscribers", "New Subscribers", None, GOOD_HIGH),
         kpi("% via Low-Q Channels", "% New via Low-Quality Channels", None, GOOD_LOW),
         kpi("% Incentivised", "% New Incentivised", None, GOOD_LOW),
         kpi("M1 Retention", "M1 Retention %", None, GOOD_HIGH),
         kpi("M3 Retention", "M3 Retention %", None, GOOD_HIGH),
         kpi("Blended CAC", "Blended CAC", "Blended CAC vs Target %", GOOD_LOW),
     ]),
     "visuals": [
         cols_("new_by_channel", 0, 7, R2, 250, ["New Subscribers"],
               "New subscribers by acquisition channel",
               series="dim_subscriber.acquisition_channel", stacked=True),
         bars("m3_by_channel", 7, 5, R2, 250, "dim_subscriber.acquisition_channel",
              "M3 Retention %", "M3 retention by acquisition channel"),
         line("lowq_trend", 0, 6, R3, 250, ["% New via Low-Quality Channels"],
              "Share of new subscribers via low-quality channels"),
         line("lowq_by_market", 6, 6, R3, 250, ["% New via Low-Quality Channels"],
              "Low-quality-channel share by market", series=MKT),
     ]},

    # ================================================================= 06
    {"key": "06_experience", "name": "06_experience", "height": B.PAGE_H_STANDARD,
     "kpis": kpi_row([
         kpi("Payment Failure Rate", "Payment Failure Rate %", None, GOOD_LOW),
         kpi("Dunning Recovery", "Dunning Recovery Rate %", None, GOOD_HIGH),
         kpi("Involuntary Churn", "Involuntary Churn %", None, GOOD_LOW),
         kpi("Crash-Free Rate", "Crash-Free Session Rate %", None, GOOD_HIGH),
         kpi("Tickets / 1k Subs", "Tickets per 1,000 Subs", None, GOOD_LOW),
         kpi("CSAT", "CSAT", None, GOOD_HIGH),
     ]),
     "visuals": [
         line("crashfree_by_device", 0, 6, R2, 250, ["Crash-Free Session Rate %"],
              "Crash-free session rate by device class", series="dim_device.device_class"),
         line("pay_fail_recovery", 6, 6, R2, 250,
              ["Payment Failure Rate %", "Dunning Recovery Rate %"],
              "Payment failure rate and dunning recovery"),
         bars("auth_by_method", 0, 6, R3, 250, "dim_payment_method.method",
              "Authorization Rate %", "Authorization rate by payment method"),
         line("tickets_by_reason", 6, 6, R3, 250, ["Tickets per 1,000 Subs"],
              "Support contacts per 1,000 subscribers by reason",
              series="dim_support_reason.reason_group"),
     ]},

    # ================================================================= 07
    {"key": "07_market", "name": "07_market", "height": B.PAGE_H_STANDARD,
     "kpis": kpi_row([
         kpi("Gross Churn (Total)", "Gross Monthly Churn % (Latest)", None, GOOD_LOW),
         kpi("Churn (Comp. Base)", "Gross Monthly Churn % (Comparable Base)", None, GOOD_LOW),
         kpi("Churn (Expansion)", "Gross Monthly Churn % (Expansion)", None, GOOD_LOW),
         kpi("Net Adds (last month)", "Net Adds (Latest)", None, GOOD_HIGH),
         kpi("MRR (last month)", "MRR (Latest)", None, GOOD_HIGH),
         kpi("Lost vs Plan", "Subscribers Lost vs Plan (since shift)", None, GOOD_LOW),
     ]),
     "visuals": [
         line("churn_by_market_7", 0, 6, R2, 250, ["Gross Monthly Churn %"],
              "Gross monthly churn by market", series=MKT),
         line("netadds_by_market", 6, 6, R2, 250, ["Net Adds"],
              "Net adds by market", series=MKT),
         cols_("cb_vs_exp", 0, 7, R3, 250,
               ["Gross Monthly Churn % (Comparable Base)", "Gross Monthly Churn % (Expansion)"],
               "Comparable Base vs Expansion churn"),
         V("insight_7", "card", 7, 5, R3, 250, {"Values": [M + "Exec Insight"]}, "Read this"),
     ]},
]


def build():
    slicers = [
        {"name": "sl-currency", "field": "Reporting Currency.Currency",
         "x": W - MARGIN - 150, "y": SLICER_Y, "w": 150, "h": SLICER_H, "title": "Currency"},
        {"name": "sl-market", "field": "dim_subscriber.market",
         "x": W - MARGIN - 150 - GUT - 230, "y": SLICER_Y, "w": 230, "h": SLICER_H, "title": "Market"},
        {"name": "sl-period", "field": "dim_date.year_month",
         "x": MARGIN, "y": SLICER_Y, "w": 380, "h": SLICER_H, "title": "Analysis period"},
    ]
    for pg in PAGES:
        pg["display"] = DISPLAY.get(pg["key"], pg["name"])
    manifest = {
        "report_name": "VoxaChurnDiagnosis",
        "canvas_width": W,
        "kpi_frame": {"x": MARGIN - 8, "y": FRAME_Y,
                      "w": W - 2 * (MARGIN - 8), "h": FRAME_H, "radius": 20},
        "slicers": slicers,
        "pages": PAGES,
    }
    # remap the content rows to fit shorter (720px) pages
    for pg in manifest["pages"]:
        if pg["height"] >= 860:
            continue
        r2_new, r3_new, rh = CONTENT_Y, 530, 204  # r3_new was 496; +34 to keep the same
                                                   # 16px gap under the (now lower) r2 row
        for v in pg["visuals"]:
            if v["y"] >= R3:
                v["y"] = r3_new + (v["y"] - R3)
                v["h"] = min(v["h"], rh)
            elif v["y"] >= R2:
                v["y"] = r2_new
                v["h"] = min(v["h"], rh)
            if v["y"] + v["h"] > pg["height"] - 16:
                v["h"] = pg["height"] - 16 - v["y"]

    (PBI / "_report_layout.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    nvis = sum(len(p["visuals"]) + 12 + 3 for p in PAGES)
    print(f"_report_layout.json  ({len(PAGES)} pages, ~{nvis} visuals)")


if __name__ == "__main__":
    build()
