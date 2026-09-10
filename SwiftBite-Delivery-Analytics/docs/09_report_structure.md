# SwiftBite Delivery — Report Structure

**Document status:** Phase 8 deliverable. The report is built from code:
`powerbi/gen_report_visuals.py` writes `powerbi/_report_layout.json`,
`powerbi/_drive_pbir.py` drives the `pbir` CLI to produce
`powerbi/SwiftBiteDelivery.Report/**`. `powerbi/build_report.sh` orchestrates the
whole chain. `pbir validate --all` passes.

> **PT.** 4 páginas, uma pergunta de negócio por página. Cada página: banda verde
> com o wordmark, hairline tangerina, título + a pergunta, uma linha de 6 KPI cards
> numa moldura branca, e 4 visuais de conteúdo. 3 slicers globais (período / zona /
> tier de estresse de oferta).

---

## Every page

- **Header band** (green-deep, 58 px) with the *SwiftBite* wordmark, a tangerine
  hairline, and a right-aligned "Marketplace Analytics" label — carried by the
  page-background PNG (`assets/gen_logo.py`).
- **Title + business question** on the light body.
- **Slicer row:** Analysis period (`dim_date[date]`) · Zone (`dim_zone[zone_name]`) ·
  Supply-stress tier (`dim_zone[baseline_supply_stress_tier]`).
- **KPI frame:** a white rounded shape holding **6 value cards**.
- **Two content rows** on the 3-30-300 gradient (4 visuals).

All numbers come from the 69 explicit DAX measures in `_Measures`
(`discourageImplicitMeasures` is on); see `06_dax_measures.md`.

---

## 1 · Executive Overview

**Question — Is the marketplace healthy, and did the zone-hour incentive earn its cost?**

| KPIs | Visuals |
|---|---|
| Fulfillment Rate · Peak ETA p90 · No-Courier Rate · Idle Courier Ratio · Incentive Lift (pp) · Cost / Incremental Order | fulfillment-rate trend (line) · **Exec Insight** dynamic narrative card · fulfillment lift by supply-stress tier (bar) · weekly fulfillment treated vs control (line) |

## 2 · Marketplace Health

**Question — Where and when does liquidity break?**

| KPIs | Visuals |
|---|---|
| Orders Placed · Fulfillment Rate · ETA p90 · No-Courier Rate · Liquidity Ratio · Idle Courier Ratio | fulfillment rate by zone (bar) · **liquidity ratio by zone × daypart** (matrix) · ETA p90 by hour of day (line) · cancellations by cause and zone (column) |

## 3 · Pricing & Incentive Experiment

**Question — Is the incentive real, safe on the guardrails, and not just cannibalising neighbour zones?**

| KPIs | Visuals |
|---|---|
| Fulfillment Lift (pp) · ETA p90 Lift (min) · No-Courier Lift (pp) · Cost / Incremental Order · Neighbour-Zone Gap (pp) · Adjusted Net Lift (pp) | fulfillment lift by tier — heterogeneity (bar) · fulfillment by arm (column) · weekly fulfillment treated vs control — launch bump vs settled (line) · **guardrails by arm** (table) |

## 4 · Courier Economics

**Question — What do couriers earn, how utilised is supply, and how elastic is it to the bonus?**

| KPIs | Visuals |
|---|---|
| Active Couriers · Earnings / Active Hr · Utilisation · Deliveries / Active Hr · Contribution Margin · Incentive % of Payout | earnings per active hour by daypart (column) · utilisation by zone (bar) · available vs demanded courier-hours by hour (line) · incentive cost per delivered order by tier (column) |

---

*Layout warnings from `pbir validate` (`VISUAL_OVERLAP` / `VISUAL_UNDERSIZED`) are
expected — the KPI value cards sit inside the frame shape by design; final pixel
spacing is a Power BI Desktop polish pass.*

*End of Phase 8 deliverable (Report Structure).*
