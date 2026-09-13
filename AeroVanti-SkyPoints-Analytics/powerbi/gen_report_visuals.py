"""
gen_report_visuals.py — emit powerbi/_report_layout.json, the layout manifest that
_drive_pbir.py turns into `pbir` calls.

4 pages (lite), one business question each. Every page: a page-background PNG, a
slicer row (Analysis period + Experiment arm + Experiment stratum), a white KPI
frame with 6 value cards, then two content rows on the 3-30-300 gradient.
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
# Was KPI_Y=132 with slicers at KPI_Y-6=126 and the frame at KPI_Y-12=120 --
# both sat on top of the header wallpaper's own subtitle/divider (divider at
# y=144, see assets/gen_logo.py _page_bg: ty=bh+20=78, divider at ty+66=144),
# and the slicer row (34px tall) overlapped the top of the KPI cards below it
# (only a 6px gap). Redesigned as three independent rows: frame -> slicer ->
# cards, each clearing the one above it.
FRAME_Y, FRAME_H = 148, 146   # -> frame bottom = 294
SLICER_Y = 152                # clears the header divider (144) by 8px
KPI_Y = 190                   # clears the slicer row (152-186) by 4px
KPI_H = 74
KPI_DELTA_H = 22
CONTENT_R1 = 300               # was 232/236 (inconsistent, and 232 overlapped
                                # the old frame by 4px on the exec page) --
                                # clears the new frame bottom (294) by 6px
R2 = 250
R3 = 500
MONTH = "dim_month.month_name"
SORT_MONTH = {"by": "dim_month.month_name", "dir": "asc"}
TIER = "dim_tier.tier_name"
STRAT = "dim_experiment_stratum.stratum"
ARM = "dim_experiment_arm.arm_key"


def col(n, span, cols=12, x0=MARGIN, total=W):
    inner = total - 2 * x0 - (cols - 1) * GUT
    cw = inner / cols
    return round(x0 + n * (cw + GUT)), round(span * cw + (span - 1) * GUT)


def kpi(title, value, delta=None, good=GOOD_HIGH):
    return {"title": title, "value": M + value, "delta": (M + delta) if delta else None, "good": good}


def kpi_row(items):
    out = []
    for i, it in enumerate(items):
        x, w = col(i * 2, 2)
        out.append({**it, "x": x, "y": KPI_Y, "w": w,
                    "delta_y": KPI_Y + KPI_H + 2, "delta_h": KPI_DELTA_H})
    return out


def V(name, type_, gx, gspan, y, h, roles, title, sort=None):
    x, w = col(gx, gspan)
    v = {"name": name, "type": type_, "x": x, "y": y, "w": w, "h": h, "roles": roles, "title": title}
    if sort:
        v["sort"] = sort
    return v


def line(name, gx, gspan, y, h, measures, title, category=MONTH, series=None, sort=SORT_MONTH):
    roles = {"Category": category, "Y": [M + m for m in measures]}
    if series:
        roles["Series"] = series
        return V(name, "clusteredColumnChart", gx, gspan, y, h, roles, title, sort)
    return V(name, "lineChart", gx, gspan, y, h, roles, title, sort)


def cols_(name, gx, gspan, y, h, measures, title, category=MONTH, series=None, sort=SORT_MONTH,
          stacked=False):
    roles = {"Category": category, "Y": [M + m for m in measures]}
    if series:
        roles["Series"] = series
    return V(name, "stackedColumnChart" if stacked else "clusteredColumnChart",
             gx, gspan, y, h, roles, title, sort)


def bars(name, gx, gspan, y, h, category, measure, title, sort=None):
    return V(name, "clusteredBarChart", gx, gspan, y, h,
             {"Category": category, "Y": [M + measure]}, title, sort)


PAGES = [
    # ================================================================= 01
    {"key": "01_executive", "name": "01_executive", "display": "Executive Summary",
     "height": B.PAGE_H_EXEC,
     "kpis": kpi_row([
         kpi("Active Members", "Active Members"),
         kpi("Quarterly Redemption Rate", "Quarterly Redemption Rate %",
             "Quarterly Redemption Rate vs Target", GOOD_HIGH),
         kpi("Burn / Earn Ratio", "Burn Earn Ratio"),
         kpi("Point Liability (adj)", "Point Liability BRL (breakage-adj)", None, GOOD_LOW),
         kpi("Flash Redemption Lift", "Exp Lift pp"),
         kpi("Engagement Lapse Rate", "Engagement Lapse Rate %", None, GOOD_LOW),
     ]),
     "visuals": [
         line("earn_burn_trend", 0, 7, CONTENT_R1, 244,
              ["SkyPoints Issued", "SkyPoints Redeemed"], "SkyPoints issued vs redeemed by month"),
         V("exec_insight", "card", 7, 5, CONTENT_R1, 244, {"Values": [M + "Exec Insight"]}, "Read this"),
         bars("effect_by_tier_exec", 0, 5, 558, 236, STRAT, "Exp Effect by Tier pp",
              "Flash Redemption effect by member tier (pp)"),
         line("liability_trend", 5, 7, 558, 236,
              ["Point Liability BRL", "Point Liability BRL (breakage-adj)"],
              "Point-liability trajectory (BRL)"),
     ]},

    # ================================================================= 02
    {"key": "02_tiers", "name": "02_tiers", "display": "Member Tiers & Value",
     "height": B.PAGE_H_STANDARD,
     "kpis": kpi_row([
         kpi("Members", "Members"),
         kpi("Active Rate", "Active Rate %"),
         kpi("Elite Share", "Elite Share %"),
         kpi("Revenue / Active Member", "Revenue per Active Member"),
         kpi("Card Penetration", "Co-brand Card Penetration %"),
         kpi("Avg Points Balance", "Avg Points Balance", None, GOOD_LOW),
     ]),
     "visuals": [
         cols_("members_by_tier", 0, 4, CONTENT_R1, 230, ["Members in Tier"], "Active members by tier",
               category=TIER, sort={"by": TIER, "dir": "asc"}),
         bars("rev_by_tier", 4, 4, CONTENT_R1, 230, TIER, "Revenue per Active Member",
              "Flight revenue per member by tier", sort={"by": TIER, "dir": "asc"}),
         cols_("issued_by_source", 8, 4, CONTENT_R1, 230, ["SkyPoints Issued"],
               "SkyPoints issued by source", category="dim_earn_source.source_name", sort=None),
         line("tier_movement", 0, 6, 544, 224, ["Tier Upgrades", "Tier Downgrades"],
              "Tier upgrades vs downgrades by month"),
         line("liability_tiers", 6, 6, 544, 224,
              ["Point Liability BRL", "Point Liability BRL (breakage-adj)"],
              "Point liability, gross vs breakage-adjusted"),
     ]},

    # ================================================================= 03
    {"key": "03_experiment", "name": "03_experiment", "display": "A/B Test Results",
     "height": B.PAGE_H_STANDARD,
     "kpis": kpi_row([
         kpi("Subjects", "Exp Subjects"),
         kpi("Control Rate", "Exp Control Rate"),
         kpi("Treatment Rate", "Exp Treatment Rate"),
         kpi("Lift (pp)", "Exp Lift pp"),
         kpi("Significance", "Exp Significant 95%"),
         kpi("SRM (treat. share)", "Exp SRM Ratio"),
     ]),
     "visuals": [
         cols_("rate_by_arm_tier", 0, 6, CONTENT_R1, 232, ["Exp Control Rate", "Exp Treatment Rate"],
               "Redemption rate by arm and tier", category=STRAT, sort={"by": STRAT, "dir": "asc"}),
         bars("effect_by_tier", 6, 6, CONTENT_R1, 232, STRAT, "Exp Effect by Tier pp",
              "Treatment effect by tier (pp) - heterogeneity cut", sort={"by": STRAT, "dir": "asc"}),
         line("novelty_curve", 0, 7, 546, 224, ["Exp Weekly Redeemers %"],
              "Weekly redeemers by arm - novelty-effect check",
              category="fact_experiment_member_week.week", series=ARM,
              sort={"by": "fact_experiment_member_week.week", "dir": "asc"}),
         V("guardrails", "tableEx", 7, 5, 546, 224,
           {"Values": ["dim_experiment_arm.arm_key", M + "Exp Revenue per Member",
                       M + "Exp Net Liability Cost per Member", M + "Exp Disengaged 90d %",
                       M + "Exp Redemption Value per Redeemer"]},
           "Guardrail metrics by arm"),
     ]},

    # ================================================================= 04
    {"key": "04_funnel", "name": "04_funnel", "display": "Redemption & Engagement Funnel",
     "height": B.PAGE_H_STANDARD,
     "kpis": kpi_row([
         kpi("Ever-Redeemed Share", "Ever-Redeemed Share %"),
         kpi("Quarterly Redemption Rate", "Quarterly Redemption Rate %",
             "Quarterly Redemption Rate vs Target", GOOD_HIGH),
         kpi("Redeeming Members", "Redeeming Members"),
         kpi("Account Lapse Rate", "Account Lapse Rate %", None, GOOD_LOW),
         kpi("Engagement Lapse Rate", "Engagement Lapse Rate %", None, GOOD_LOW),
         kpi("Reactivations", "Reactivations"),
     ]),
     "visuals": [
         V("redeem_funnel", "funnel", 0, 5, CONTENT_R1, 232,
           {"Category": "Funnel Stage.stage", "Y": [M + "Funnel Value"]},
           "Redemption funnel (members)"),
         cols_("redeemed_by_category", 5, 7, CONTENT_R1, 232, ["SkyPoints Redeemed"],
               "SkyPoints redeemed by reward category",
               category="dim_reward_type.reward_category", sort=None),
         line("redemption_vs_target", 0, 6, 546, 224,
              ["Quarterly Redemption Rate %", "Redemption Rate Target"],
              "Quarterly redemption rate vs plan"),
         bars("eng_lapse_by_tier", 6, 6, 546, 224, TIER, "Engagement Lapse Rate %",
              "Engagement lapse rate by tier", sort={"by": TIER, "dir": "asc"}),
     ]},
]


def build():
    slicers = [
        {"name": "sl-period", "field": "dim_month.month_name",
         "x": MARGIN, "y": SLICER_Y, "w": 300, "h": 34, "title": "Analysis period"},
        {"name": "sl-arm", "field": ARM,
         "x": W - MARGIN - 170 - GUT - 200, "y": SLICER_Y, "w": 200, "h": 34, "title": "Experiment arm"},
        {"name": "sl-stratum", "field": STRAT,
         "x": W - MARGIN - 170, "y": SLICER_Y, "w": 170, "h": 34, "title": "Tier stratum"},
    ]
    manifest = {
        "report_name": "AeroVantiSkyPoints",
        "canvas_width": W,
        "kpi_frame": {"x": MARGIN - 8, "y": FRAME_Y,
                      "w": W - 2 * (MARGIN - 8), "h": FRAME_H, "radius": 18},
        "slicers": slicers,
        "pages": PAGES,
    }
    (PBI / "_report_layout.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    nvis = sum(len(p["visuals"]) + 6 + 3 for p in PAGES)
    print(f"_report_layout.json  ({len(PAGES)} pages, ~{nvis} visuals)")


if __name__ == "__main__":
    build()
