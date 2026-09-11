# VoltEdge Electronics — Report Structure

**Document status:** built to match the numbered `docs/` convention used by the other
four portfolio projects. Full design rationale, palette, and page-by-page detail already
live in [`07_report_guide.md`](07_report_guide.md) — this doc is the compact index of
that same report, table-first. One command rebuilds the report:

```
cd powerbi && bash build_report.sh
```

Pipeline: `gen_logo.py` → `gen_semantic_model.py` (+ `pbi_measures.py`) →
`gen_dax_doc.py` → `gen_report_visuals.py` → `build_report.sh` (drives `pbir`).
Output: `powerbi/VoltEdge Electronics.pbip` + `.Report` + `.SemanticModel`.
`pbir validate --all` passes (see the known polish backlog in `07_report_guide.md`).

**First open in Power BI Desktop:** Transform data → set `pDataFolder` to
`data/curated` → Close & Apply · View ▸ Themes ▸ Browse → `powerbi/theme/VoltEdge.json`.

---

## Semantic model

28 data tables (16 dims + 12 facts) + `_Measures` (167 measures in 14 folders) + two
disconnected helper tables (`Reporting Currency`, `Funnel Stage`). 65 relationships,
single-direction many-to-one fact → dimension; secondary date roles (ship, delivery,
due, receipt, paid…) are inactive, activated per-measure with `USERELATIONSHIP`. See
`docs/05_data_model.md` for the full bus matrix.

---

## The seven pages

Every page: navy logo bar + accent rule (header image) · Currency + Market slicer row ·
Analysis-period date slicer · 6 KPI tiles · two content rows on the 3-30-300 gradient.

| # | Page | Question | KPI row (6 cards) | Content |
|---|---|---|---|---|
| 1 | **Executive Summary** | Are we hitting plan, is growth real, where does the money go? | Net Revenue · Gross Margin % · Orders · Contribution Margin · New Customers · Blended CAC | Net revenue by month CY vs PY (line) · budget scorecard (table) · contribution-margin bridge (waterfall) · net revenue by market CY vs PY (column) |
| 2 | **Sales Performance** | What is driving the top line — volume, price, or mix? | Net Revenue · Orders · AOV · Gross Margin % · Discount Rate % · Units/Order | Net revenue & discount rate by month (combo) · net revenue by category (bar) · YoY revenue change by category (waterfall, price/volume/mix) · cumulative revenue booked vs cash received (line) |
| 3 | **Marketing & Acquisition** | Is paid spend efficient, and how much growth is actually paid-for? | Marketing Spend · Blended CAC · MER · New Customers · % New via Paid · ROAS | On-site funnel (sessions → cart → orders) · spend & blended CAC by month (combo) · new customers by acquisition channel (bar) · spend & ROAS by channel (combo) · campaign performance (table) |
| 4 | **Website & Digital** | Where does the on-site funnel leak? | Sessions · Conversion Rate % · Bounce Rate % · Add-to-Cart % · Cart Abandonment % · Revenue/Session | Sessions & conversion rate by month (combo) · sessions by device (donut) · revenue/session & conversion by channel (combo) · sessions & conversion by market (combo) |
| 5 | **Logistics & Fulfillment** | Are we delivering on time, and where is cash trapped? | On-Time Delivery % · Avg Delivery Days · Perfect Order % · Ship Cost/Order · Cost Recovery % · Cash Conversion Cycle | Avg delivery days & on-time % by month (combo) · carrier scorecard (combo) · working capital — DIO/DSO/DPO/CCC by month (column) · company cash flow (line) |
| 6 | **CRM & Customer** | Is the customer base retaining, and who churns? | Customers with Orders · Repeat Rate % · Avg Orders/Customer · CLV (Gross Profit) · Churned Customers · Gold-Tier Revenue % | New vs returning customer revenue by month (line) · customers by status (bar) · customers acquired by cohort month & channel (stacked column) · returns by reason (table) |
| 7 | **Product & Inventory** | Which SKUs and categories drive margin, and where does inventory sit? | Inventory Value · Inventory Turnover · Weeks of Cover · Return Rate % · In Transit · Supplier Spend | Gross margin % by category (bar) · return rate % by category (bar) · SKUs — revenue vs margin (scatter) · inventory value & weeks of cover by month (combo) · slow movers (table) |

Every "big number + ratio" pair is a combo chart — magnitude as bars, ratio as a line on
a secondary axis. Time axes are sorted oldest→newest.

---

## Known lite-scope gaps (not polished)

See `07_report_guide.md`'s known polish backlog for the full list — undersized KPI
cards/slicers (deliberately compact), two `TOO_MANY_FIELDS` warnings on the working-capital
column chart, no alt text yet, plain `card` visuals on the hero KPIs instead of `kpi` with
target + trendline, and rendering not yet verified live in Desktop.
