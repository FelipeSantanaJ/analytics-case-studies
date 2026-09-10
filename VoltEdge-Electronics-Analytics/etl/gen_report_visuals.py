"""
Per-page visual layouts for the VoltEdge report, emitted as pbir `--from-json` bundles
(one JSON file per page under powerbi/_visuals/).

Design identity (corporate tone, deep-blue palette):
  * every page: a header image (navy bar: bolt + VOLTEDGE + page title), a slicer row
    (analysis period / currency / market), a 6-tile KPI row (kpi visual with a Goal where
    a plan target exists, card otherwise), then two content rows on the detail gradient.
  * blue = current period, amber = prior year / comparison, rest neutral. 16px gutters.

Canvas 1280 x 860.  Rebuild with `powerbi/build_report.sh`.
"""

from __future__ import annotations

import json
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "powerbi" / "_visuals"
OUT.mkdir(parents=True, exist_ok=True)

W, M, G = 1280, 24, 16
COLW = (W - 2 * M - 11 * G) / 12          # = 88
# the executive page is taller (it carries the insight band + 4 bridge charts); every
# other page uses the standard canvas. build_report.sh / gen_logo mirror these.
PAGE_H_EXEC, PAGE_H_STD = 1240, 1000
H = PAGE_H_STD

# header band (page background) occupies y 0-60; everything else sits below it
# slicers carry only their custom title (the field-name header is switched off in the
# build), so the row does not need to be tall
SLICER_Y, SLICER_H = 72, 76
# KPI tile: a white rounded background shape with two transparent cards on it -- the
# metric value, then a small green/red "vs Target %" -- so they read as one object.
ROW_KPI, KPI_TILE_H = 152, 148
KPI_VAL_DY, KPI_VAL_H = 4, 88
KPI_DELTA_DY, KPI_DELTA_H = 90, 56
# default two-row layout (pages without the insight card) -- standard bodies
ROW_A, ROW_B, BODY_H = 314, 656, 318
# executive layout: taller insight band, a wide CM trend, then a 4-up bridge row
EXE_NARR_Y, EXE_NARR_H = 314, 122
EXE_A, EXE_B, EXE_C, EXE_BODY = 452, 704, 956, 244


def x(col: int) -> int:
    return round(M + col * (COLW + G))


def span(cols: int) -> int:
    return round(cols * COLW + (cols - 1) * G)


def M_(name: str) -> str:
    return f"_Measures.{name}"


_SMALL = {"a", "an", "and", "as", "at", "but", "by", "for", "from", "in", "into",
          "nor", "of", "on", "onto", "or", "over", "per", "the", "to", "vs", "via", "with"}


def tc(s: str) -> str:
    """Title Case: capitalise each word except lowercase connectors (never the first);
    leave words that already carry caps or digits alone (YoY, DIO, CM%, 12M, ...)."""
    words = s.split()
    out = []
    for i, w in enumerate(words):
        lw = w.lower()
        if i and lw in _SMALL:
            out.append(lw)
        elif any(c.isupper() for c in w) or (any(c.isdigit() for c in w) and not any(c.islower() for c in w)):
            out.append(w)                                  # YoY, DIO, CCC, 12M, %, ...
        else:
            out.append(w[:1].upper() + w[1:])
    return " ".join(out)


# metric -> "vs plan %" companion measure shown under the KPI value (value + % only)
VS_TARGET = {
    "Net Revenue (USD)": "Net Revenue vs Target %",
    "Orders": "Orders vs Target %",
    "Gross Margin %": "Gross Margin % vs Target (pp)",
    "New Customers": "New Customers vs Target %",
    "Blended CAC (USD)": "Blended CAC vs Target %",
}


def kpi_tiles(cards: list[tuple[str, str]]) -> list[dict]:
    out = [
        {"visual_type": "slicer", "name": "slcDate",
         "x": 24, "y": SLICER_Y, "width": 552, "height": SLICER_H, "title": "Analysis Period",
         "fields": {"Values": "dim_date.date"}},
        {"visual_type": "slicer", "name": "slcCurrency",
         "x": 592, "y": SLICER_Y, "width": 300, "height": SLICER_H, "title": "Currency",
         "fields": {"Values": "Reporting Currency.Currency"}},
        {"visual_type": "slicer", "name": "slcMarket",
         "x": 908, "y": SLICER_Y, "width": 348, "height": SLICER_H, "title": "Market",
         "fields": {"Values": "dim_market.market_name"}},
    ]
    for i, (label, meas) in enumerate(cards[:6]):
        cx, w = x(i * 2), span(2)
        # 1) white rounded background shape (listed first -> lowest z -> behind the cards)
        out.append({"visual_type": "shape", "name": f"kpi_{i}_bg",
                    "x": cx, "y": ROW_KPI, "width": w, "height": KPI_TILE_H})
        # 2) value card (transparent bg via the build step)
        out.append({"visual_type": "card", "name": f"kpi_{i}",
                    "x": cx, "y": ROW_KPI + KPI_VAL_DY, "width": w, "height": KPI_VAL_H,
                    "title": label, "fields": {"Values": [M_(meas)]}})
        # 3) small green/red "vs Target %" beneath it, on the same shape
        if meas in VS_TARGET:
            out.append({"visual_type": "card", "name": f"kpi_{i}_d",
                        "x": cx, "y": ROW_KPI + KPI_DELTA_DY, "width": w, "height": KPI_DELTA_H,
                        "title": "vs Target", "fields": {"Values": [M_(VS_TARGET[meas])]}})
    return out


def viz(vtype, name, col, cols, y, h, title, roles) -> dict:
    return {"visual_type": vtype, "name": name,
            "x": x(col), "y": y, "width": span(cols), "height": h,
            "title": tc(title), "fields": roles}


def table(name, col, cols, y, h, title, fields) -> dict:
    return {"visual_type": "tableEx", "name": name,
            "x": x(col), "y": y, "width": span(cols), "height": h,
            "title": tc(title), "fields": {"Values": fields}}


# =============================== ROW helpers ========================================
def r3(y, h):    # three columns 4 / 4 / 4
    return [(0, 4, y, h), (4, 4, y, h), (8, 4, y, h)]


def r2_84(y, h):  # 8 / 4
    return [(0, 8, y, h), (8, 4, y, h)]


def r2_66(y, h):  # 6 / 6
    return [(0, 6, y, h), (6, 6, y, h)]


# ====================================================================================
def page_executive() -> list[dict]:
    v = kpi_tiles([
        ("Net Revenue", "Net Revenue (USD)"),
        ("Gross Margin %", "Gross Margin %"),
        ("Orders", "Orders"),
        ("Contribution Margin", "Contribution Margin (USD)"),
        ("New Customers", "New Customers"),
        ("Blended CAC", "Blended CAC (USD)"),
    ])
    # dynamic insight band - a card bound to a text measure (updates with every filter)
    v.append({"visual_type": "card", "name": "exec_insight",
              "x": 24, "y": EXE_NARR_Y, "width": span(12), "height": EXE_NARR_H,
              "title": tc("Key insights"), "fields": {"Values": M_("Exec Insight")}})
    v.append(viz("lineChart", "exec_trend", 0, 8, EXE_A, EXE_BODY,
                 "Net revenue by month - current vs prior year",
                 {"Category": "dim_date.month_year",
                  "Y": [M_("Net Revenue (USD)"), M_("Net Revenue PY (USD)")]}))
    # Actual + attainment % is enough; the plan value itself is implied and the 4-col slot
    # is too narrow for a fourth column
    v.append(table("exec_budget", 8, 4, EXE_A, EXE_BODY, "Budget scorecard - actual vs plan",
                   ["dim_metric.metric", M_("Budget Actual (fmt)"), M_("Budget Attainment %")]))
    # row B: the CM trend, kept wide
    v.append(viz("lineClusteredColumnComboChart", "exec_cmtrend", 0, 12, EXE_B, EXE_BODY,
                 "Contribution margin % - monthly (bars) and trailing-12-month trend (line)",
                 {"Category": "dim_date.month_year",
                  "Y": [M_("Contribution Margin %")],
                  "Y2": [M_("Contribution Margin % (Trailing 12M)")]}))
    # row C: 4 composition waterfalls -- revenue and CM, each split by product and by region
    v.append(viz("waterfallChart", "exec_rev_cat", 0, 3, EXE_C, EXE_BODY,
                 "Net revenue by product category",
                 {"Category": "dim_product.category", "Y": M_("Net Revenue (USD)")}))
    v.append(viz("waterfallChart", "exec_rev_area", 3, 3, EXE_C, EXE_BODY,
                 "Net revenue by region",
                 {"Category": "dim_market.market_name", "Y": M_("Net Revenue (USD)")}))
    v.append(viz("waterfallChart", "exec_cm_cat", 6, 3, EXE_C, EXE_BODY,
                 "Contribution margin by product category",
                 {"Category": "dim_product.category", "Y": M_("Contribution Margin (Alloc) (USD)")}))
    v.append(viz("waterfallChart", "exec_cm_area", 9, 3, EXE_C, EXE_BODY,
                 "Contribution margin by region",
                 {"Category": "dim_market.market_name", "Y": M_("Contribution Margin (Alloc) (USD)")}))
    return v


def page_sales() -> list[dict]:
    v = kpi_tiles([
        ("Net Revenue", "Net Revenue (USD)"),
        ("Orders", "Orders"),
        ("Avg Order Value", "Average Order Value"),
        ("Gross Margin %", "Gross Margin %"),
        ("Discount Rate %", "Discount Rate %"),
        ("Units / Order", "Units per Order"),
    ])
    a = r2_84(ROW_A, BODY_H)
    v.append(viz("lineStackedColumnComboChart", "sal_trend", *a[0][:2], *a[0][2:],
                 "Net revenue (bars) and discount rate (line) by month",
                 {"Category": "dim_date.month_year",
                  "Y": [M_("Net Revenue (USD)")], "Y2": [M_("Discount Rate %")]}))
    v.append(viz("barChart", "sal_cat", *a[1][:2], *a[1][2:], "Net revenue by category",
                 {"Category": "dim_product.category", "Y": M_("Net Revenue (USD)")}))
    # wide combo (24 monthly bars need the room) + one category waterfall beside it
    v.append(viz("clusteredColumnChart", "sal_cash", 0, 8, ROW_B, BODY_H,
                 "Revenue booked vs cash received by month",
                 {"Category": "dim_date.month_year",
                  "Y": [M_("Revenue Booked (USD)"), M_("Cash Received (USD)")]}))
    v.append(viz("waterfallChart", "sal_pvm", 8, 4, ROW_B, BODY_H,
                 "YoY revenue change by category",
                 {"Category": "dim_product.category", "Y": M_("Net Revenue YoY (USD)")}))
    return v


def page_marketing() -> list[dict]:
    v = kpi_tiles([
        ("Marketing Spend", "Marketing Spend (USD)"),
        ("Blended CAC", "Blended CAC (USD)"),
        ("MER", "MER"),
        ("New Customers", "New Customers"),
        ("% New via Paid", "% New Customers via Paid"),
        ("ROAS", "ROAS"),
    ])
    # row A: funnel (narrow) + the wide monthly combo (24 bars need the room)
    v.append(viz("funnel", "mkt_funnel", 0, 4, ROW_A, BODY_H, "On-site funnel",
                 {"Category": "Funnel Stage.Stage", "Y": M_("Funnel Value")}))
    v.append(viz("lineClusteredColumnComboChart", "mkt_trend", 4, 8, ROW_A, BODY_H,
                 "Marketing spend (bars) and blended CAC (line) by month",
                 {"Category": "dim_date.month_year",
                  "Y": [M_("Marketing Spend (USD)")], "Y2": [M_("Blended CAC (USD)")]}))
    # row B: acquisition mix + channel efficiency + campaign detail
    v.append(viz("clusteredBarChart", "mkt_acq", 0, 3, ROW_B, BODY_H,
                 "New customers by acquisition channel",
                 {"Category": "dim_customer.acquisition_channel",
                  "Y": M_("New Customers (acq month)")}))
    v.append(viz("lineClusteredColumnComboChart", "mkt_channel", 3, 3, ROW_B, BODY_H,
                 "Spend (bars) and ROAS (line) by channel",
                 {"Category": "dim_channel.channel_name",
                  "Y": [M_("Marketing Spend (USD)")], "Y2": [M_("ROAS")]}))
    v.append(table("mkt_campaign", 6, 6, ROW_B, BODY_H,
                   "Campaign media performance (orders are not campaign-attributed)",
                   ["dim_campaign.campaign", M_("Marketing Spend (USD)"), M_("Impressions"),
                    M_("Clicks"), M_("CTR %"), M_("CPC (USD)")]))
    return v


def page_website() -> list[dict]:
    v = kpi_tiles([
        ("Sessions", "Sessions"),
        ("Conversion Rate %", "Conversion Rate %"),
        ("Bounce Rate %", "Bounce Rate %"),
        ("Add-to-Cart %", "Add-to-Cart Rate %"),
        ("Cart Abandon %", "Cart Abandonment Rate %"),
        ("Rev / Session", "Revenue per Session (USD)"),
    ])
    a = r2_84(ROW_A, BODY_H)
    v.append(viz("lineClusteredColumnComboChart", "web_trend", *a[0][:2], *a[0][2:],
                 "Sessions (bars) and conversion rate (line) by month",
                 {"Category": "dim_date.month_year",
                  "Y": [M_("Sessions")], "Y2": [M_("Conversion Rate %")]}))
    v.append(viz("donutChart", "web_device", *a[1][:2], *a[1][2:], "Sessions by device",
                 {"Category": "dim_device.device", "Y": M_("Sessions")}))
    b = r2_66(ROW_B, BODY_H)
    v.append(viz("lineClusteredColumnComboChart", "web_channel", *b[0][:2], *b[0][2:],
                 "Revenue / session (bars) and conversion rate (line) by channel",
                 {"Category": "dim_channel.channel_name",
                  "Y": [M_("Revenue per Session (USD)")], "Y2": [M_("Conversion Rate %")]}))
    v.append(viz("lineClusteredColumnComboChart", "web_market", *b[1][:2], *b[1][2:],
                 "Sessions (bars) and conversion rate (line) by market",
                 {"Category": "dim_market.market_name",
                  "Y": [M_("Sessions")], "Y2": [M_("Conversion Rate %")]}))
    return v


def page_logistics() -> list[dict]:
    v = kpi_tiles([
        ("On-Time Delivery %", "On-Time Delivery %"),
        ("Avg Delivery Days", "Avg Delivery Days"),
        ("Perfect Order %", "Perfect Order Rate %"),
        ("Ship Cost / Order", "Shipping Cost per Order (USD)"),
        ("Cost Recovery %", "Shipping Cost Recovery %"),
        ("Cash Conv. Cycle", "Cash Conversion Cycle (days)"),
    ])
    a = r2_84(ROW_A, BODY_H)
    v.append(viz("lineClusteredColumnComboChart", "log_trend", *a[0][:2], *a[0][2:],
                 "Avg delivery days (bars) and on-time delivery % (line) by month",
                 {"Category": "dim_date.month_year",
                  "Y": [M_("Avg Delivery Days")], "Y2": [M_("On-Time Delivery %")]}))
    v.append(viz("lineClusteredColumnComboChart", "log_carrier", *a[1][:2], *a[1][2:],
                 "Carrier scorecard - days (bars), on-time % (line)",
                 {"Category": "dim_carrier.carrier_name",
                  "Y": [M_("Avg Delivery Days")], "Y2": [M_("On-Time Delivery %")]}))
    b = r2_66(ROW_B, BODY_H)
    v.append(viz("clusteredColumnChart", "log_wc", *b[0][:2], *b[0][2:],
                 "Working capital - DIO / DSO / DPO / CCC by month",
                 {"Category": "dim_date.month_year",
                  "Y": [M_("DIO (days)"), M_("DSO (days)"), M_("DPO (days)"),
                        M_("Cash Conversion Cycle (days)")]}))
    v.append(viz("lineChart", "log_cash", *b[1][:2], *b[1][2:],
                 "Company cash flow - inflow vs supplier & marketing outflow by month",
                 {"Category": "dim_date.month_year",
                  "Y": [M_("Cash Received (USD)"), M_("Supplier Spend (USD)"),
                        M_("Marketing Spend (USD)")]}))
    return v


def page_crm() -> list[dict]:
    v = kpi_tiles([
        ("Customers w/ Orders", "Customers with Orders"),
        ("Repeat Rate %", "Repeat Purchase Rate %"),
        ("Avg Orders / Cust", "Avg Orders per Customer"),
        ("CLV (Gross Profit)", "CLV Gross Profit (USD)"),
        ("Churned Customers", "Churned Customers"),
        ("Gold Tier Rev %", "Gold Tier Revenue %"),
    ])
    a = r2_84(ROW_A, BODY_H)
    v.append(viz("lineChart", "crm_new", *a[0][:2], *a[0][2:],
                 "New vs returning customer revenue by month",
                 {"Category": "dim_date.month_year",
                  "Y": [M_("New Customer Revenue (USD)"),
                        M_("Returning Customer Revenue (USD)")]}))
    v.append(viz("clusteredBarChart", "crm_seg", *a[1][:2], *a[1][2:],
                 "Customers by status",
                 {"Category": "dim_customer.customer_status",
                  "Y": M_("New Customers (acq month)")}))
    b = r2_84(ROW_B, BODY_H)
    v.append(viz("clusteredColumnChart", "crm_cohort", *b[0][:2], *b[0][2:],
                 "Customers acquired by cohort month and channel",
                 {"Category": "dim_customer.acquisition_month",
                  "Y": M_("New Customers (acq month)"),
                  "Series": "dim_customer.acquisition_channel"}))
    v.append(table("crm_returns", *b[1][:2], *b[1][2:], "Returns by reason",
                   ["dim_return_reason.reason", M_("Returned Units"),
                    M_("Return Value (USD)"), M_("Restock Rate %")]))
    return v


def page_product() -> list[dict]:
    v = kpi_tiles([
        ("Inventory Value", "Inventory Value (USD)"),
        ("Inventory Turnover", "Inventory Turnover"),
        ("Weeks of Cover", "Weeks of Cover"),
        ("Return Rate %", "Return Rate %"),
        ("In Transit", "Inventory in Transit (USD)"),
        ("Supplier Spend", "Supplier Spend (USD)"),
    ])
    a = r3(ROW_A, BODY_H)
    v.append(viz("barChart", "prd_margin", *a[0][:2], *a[0][2:],
                 "Gross margin % by category",
                 {"Category": "dim_product.category", "Y": M_("Gross Margin %")}))
    v.append(viz("barChart", "prd_return", *a[1][:2], *a[1][2:],
                 "Return rate % by category",
                 {"Category": "dim_product.category", "Y": M_("Return Rate %")}))
    v.append(viz("scatterChart", "prd_scatter", *a[2][:2], *a[2][2:],
                 "SKUs - revenue vs margin",
                 {"Category": "dim_product.product_name",
                  "X": M_("Net Revenue (USD)"), "Y": M_("Gross Margin %")}))
    b = r2_84(ROW_B, BODY_H)
    v.append(viz("lineClusteredColumnComboChart", "prd_inv", *b[0][:2], *b[0][2:],
                 "Inventory value (bars) and weeks of cover (line) by month",
                 {"Category": "dim_date.month_year",
                  "Y": [M_("Inventory Value (Month-End) (USD)")],
                  "Y2": [M_("Weeks of Cover (Month-End)")]}))
    v.append(table("prd_slow", *b[1][:2], *b[1][2:], "Slow movers - high cover, low sales",
                   ["dim_product.product_name", M_("Weeks of Cover"),
                    M_("Units Sold"), M_("Inventory Value (USD)")]))
    return v


PAGES = {
    "executive-summary": ("Executive Summary", page_executive),
    "sales-performance": ("Sales Performance", page_sales),
    "marketing-acquisition": ("Marketing & Acquisition", page_marketing),
    "website-digital": ("Website & Digital", page_website),
    "logistics-fulfillment": ("Logistics & Fulfillment", page_logistics),
    "crm-customer": ("CRM & Customer", page_crm),
    "product-inventory": ("Product & Inventory", page_product),
}


PAGE_HEIGHTS = {slug: (PAGE_H_EXEC if slug == "executive-summary" else PAGE_H_STD)
                for slug in PAGES}


def main() -> None:
    for slug, (_title, fn) in PAGES.items():
        visuals = fn()
        (OUT / f"{slug}.json").write_text(json.dumps(visuals, indent=2), encoding="utf-8")
        print(f"{slug}: {len(visuals)} visuals")
    (OUT / "_page_heights.json").write_text(json.dumps(PAGE_HEIGHTS), encoding="utf-8")


if __name__ == "__main__":
    main()
