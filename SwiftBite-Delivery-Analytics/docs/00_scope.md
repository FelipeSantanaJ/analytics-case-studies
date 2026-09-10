# 00 — Scope & Scaffold (Phase 0)

**Project:** SwiftBite Delivery — Marketplace Liquidity & the Zone-Hour Incentive Experiment
**Fictional company:** SwiftBite Delivery — a Brazilian food-delivery marketplace, single metro.
**Two-sided marketplace:** couriers = supply · orders = demand.
**Date locked:** 2026-09-10

> **PT — resumo.** Projeto de portfólio nº 4. Marketplace fictício de delivery de comida
> ("SwiftBite"), operando em **uma** cidade brasileira dividida em **12 zonas**, moeda
> **BRL apenas**. Em horários de pico e em zonas específicas, a oferta de entregadores não
> acompanha a demanda → ETA alto, cancelamento e entregadores ociosos na zona errada
> (liquidez ruim). Operações testou um **incentivo dinâmico por zona-horário** (bônus
> temporário pago ao entregador para entrar numa zona/janela) como **experimento
> randomizado por zona-dia**. A pergunta: o incentivo melhora a liquidez o suficiente para
> pagar o próprio custo, funciona só nas zonas carentes, e há canibalização das zonas
> vizinhas?

---

## 1. Premise

SwiftBite runs a food-delivery marketplace in one large Brazilian metro. It does not employ
couriers; they log into the courier app and choose when and where to work. On a normal
weekday afternoon the marketplace clears fine. But at **dinner peak on Friday and Saturday**,
and in a handful of **structurally supply-short zones**, demand outruns the couriers
available: order-to-courier assignment slows, **ETA climbs**, a wave of orders is
**cancelled** (by the customer while waiting, or by SwiftBite when no courier can be
assigned), and — the marketplace-liquidity signature — **couriers sit idle in other zones**
at the same moment, logged in but without a run.

The Operations team piloted a **dynamic zone-hour incentive**: a temporary per-delivery
bonus, announced in-app, paid to couriers who complete deliveries in a **named zone during
a named peak block**. It was run as a **randomized experiment with the zone-day as the unit**
(not the user, not the order): on a treated zone-day the incentive is armed for that zone's
peak blocks; on a control zone-day it is not.

This project reads out that experiment — **did the incentive buy
enough liquidity to justify the bonus spend, is the effect concentrated in the
supply-short zones, and does it cannibalise supply from neighbouring zones** — plus a
Power BI report on marketplace health and courier economics.

---

## 2. Locked scope decisions

| Dimension | Decision |
|---|---|
| Deliverable language | **English** (all docs, code, reports). Every deliverable also carries a short **PT** explanation of each step. Working chat in Portuguese. |
| Priority | **Phase 10 (data analysis + the zone-hour incentive experiment) is the primary deliverable.** Power BI track is secondary, scoped to 4 pages. |
| Geography / currency | **One Brazilian metro** (modelled on Belo Horizonte), **12 delivery zones**, **BRL only**. No second city, no multi-currency — that ground is already covered by VoltEdge. |
| Data window | **20 months: 2025-01-01 → 2026-08-31.** Baseline period = months 1–15; experiment sits in months 16–18; post-window observation to month 20. |
| Experiment window | **10 weeks: 2026-04-06 → 2026-06-14** (window-months 16–18) — a shoulder stretch, no major holiday inside it. Post-window Jun 15 – Aug 31 reserved for persistence / courizer-supply after-effects. |
| **Unit of randomization** | **Zone-day** (a zone × a calendar date). Secondary cut: **zone × hour-block**. **Not** user, order or courier. |
| ETL / data-quality depth | **Balanced** (matches the other three): ~6 simulated source systems, ~8 data-quality issue classes (§5). |
| Marketplace scale | ~**12 zones**; ~**3,500** couriers ever active, ~**900** active in a typical week; ~**14–16k orders/day** metro-wide (~**7.5M** orders over the window). |
| Experiment scale | Peak-eligible zone-days only (dinner blocks, all days): **12 zones × ~70 window-days ≈ 840 zone-days**, **50/50** treated/control, **stratified by zone and by baseline supply-stress tier**. |
| Power BI track | Semantic model as code (TMDL) + PBIR + `theme.json` + build script; **4 pages**, one business question per page. |
| Visual identity | **New palette, designed in Phase 5** — must not reuse AeroVanti (navy/amber), VoltEdge (navy) or Voxa+ (violet). |

---

## 3. Phase-1 report pages (4 pages, one question each)

| # | Page | The question it answers |
|---|---|---|
| 1 | **Executive Overview** | Is the marketplace healthy overall, and did the zone-hour incentive work well enough to keep? |
| 2 | **Marketplace Health** | *Where and when* does liquidity break — fulfillment rate, ETA, idle couriers vs unmet demand, by zone × hour? |
| 3 | **Pricing & Incentive Experiment** | Is the incentive effect real, significant and safe on the guardrails — including neighbour-zone cannibalisation — or is one zone carrying it? |
| 4 | **Courier Economics** | What do couriers earn, how utilised are they, and how elastic is courier supply to the incentive (R$ of bonus per incremental delivered order)? |

---

## 4. Experiment design (locked at Phase 0, detailed in Phase 1)

| Element | Decision |
|---|---|
| Unit of randomization | **Zone-day.** On a treated zone-day, the dynamic incentive is armed for that zone's **peak blocks** (18:00–22:00). Secondary analysis at **zone × hour-block**. |
| Eligible units | **Peak-eligible zone-days**: every zone, every date in the 10-week window, restricted to the dinner peak (the only time the incentive is offered). ~840 zone-days. |
| Assignment | **Stratified randomization**: within each zone and each **baseline supply-stress tier** (short / balanced / long, fixed from months 1–15), zone-days are split **50/50** treated/control. No day is switched mid-day; no re-randomization. |
| Treatment | A per-delivery bonus (a flat R$ amount, set in `etl/config.py`) for deliveries **completed in the treated zone during the peak block**, plus an in-app "surge zone" push to nearby couriers. |
| Control | No bonus, no push — normal marketplace. |
| Primary metric | **Fulfillment rate** = orders delivered ÷ orders placed, at the **zone-day (peak-block)** grain. |
| Guardrail metrics | (1) **Incentive cost per incremental delivered order** (BRL); (2) **ETA** p50 and p90; (3) **cancellation rate** (customer-, courier- and no-courier-initiated); (4) **courier earnings per active hour**; (5) **neighbour-zone spillover** — fulfillment rate and idle-courier ratio in *adjacent, control* zones on treated zone-days (the cannibalisation check). |
| Analyses required | Balance / sample-ratio check at zone-day grain; stated hypothesis + **MDE / power computed for the zone-day unit** (small N, intra-zone correlation → cluster-robust SEs and a randomization-inference check); primary effect with a 95% CI; **heterogeneity by baseline supply-stress tier and by zone**, with a formal **arm × tier interaction test**; spatial-spillover / cannibalisation estimate with a stated sign and bound; persistence in the post-window weeks. |

**Underlying true effect:** decided during Phase 3 (ETL) and baked into the generated data
with plausible noise, a modest **neighbour-zone cannibalisation** term, and heterogeneity
by supply-stress tier. The true values live only in `etl/config.py`; Phase 10 must detect
and quantify them as if blind.

---

## 5. Data-quality issues to inject (balanced set)

1. **Multiple date/time formats** across source exports — `DD/MM/YYYY`, ISO, and Unix-epoch
   milliseconds in the GPS ping log.
2. **Timezone drift** — one source (payments) logs in UTC while everything else is
   `America/Sao_Paulo`; no offset column.
3. **Money as strings** — `"R$ 12,90"`, `"12.90"`, `"1.234,56"` mixed in payout and
   basket-value fields.
4. **GPS noise & out-of-area pings** — lat/long jitter, a tail of pings hundreds of km away
   (device cold-start), and (0, 0) nulls.
5. **Duplicate rows** — the consumer app retries on flaky mobile connections, so a slice of
   `orders` and `order_status_events` rows are exact or near-exact duplicates.
6. **Missing master rows** — some `courier_id`s in the trip log have no row in the courier
   dimension export (referential gap).
7. **Zone boundary redraw** — SwiftBite re-cut two zone polygons at window-month 9; a
   **current** zone-assignment table disagrees with the **as-booked** zone on older orders.
8. **Mojibake / mixed encoding** in customer names, address strings and restaurant names.

---

## 6. Simulated source systems

| System | Feeds | Grain |
|---|---|---|
| **Consumer order app** | `orders`, `order_status_events`, basket value, address → zone | order / status event |
| **Courier app** | `courier_sessions` (login/logout), `shift_zone_blocks`, offer → accept/reject/timeout | session / offer |
| **GPS / location service** | `location_pings` (courier position over time), used to derive idle vs en-route minutes | ping (~30–60 s) |
| **Dispatch / assignment engine** | offer→assignment→pickup→dropoff timestamps, assignment latency, "no courier found" events | assignment |
| **Payments & payouts** | order payment, courier payout, incentive bonus payout | transaction |
| **Incentive / campaign system** | `incentive_campaigns`, per zone-day arm + bonus params + spend | zone-day |
| **Zone / geo reference** | zone polygons, adjacency graph, area, baseline supply-stress tier | zone (+ history) |

---

## 7. Out of scope (explicit)

- A second city, region expansion, multi-currency / FX (covered by VoltEdge).
- Restaurant-side economics (menu pricing, commission take-rate optimisation), except as an
  input to demand.
- Consumer-side pricing / promo experiments (delivery fee, discount coupons) — the
  intervention studied here is **supply-side**.
- Real-time dispatch-algorithm design; routing optimisation.
- A courier-churn *prediction* model — Phase 10 quantifies supply elasticity and the
  experiment effect; it does not ship a scorecard.
- Fraud (GPS spoofing, incentive gaming) beyond a noted data-quality tail.
- Real personal data — every courier, customer, order, ping and payout is synthetic and
  seed-generated.
- The **true incentive effect size and cannibalisation term** — decided in Phase 3, not here.

---

## 8. Resolved-assumptions log

| # | Assumption | Resolution |
|---|---|---|
| A1 | City & geography | One metro (modelled on Belo Horizonte), **12 zones**, adjacency graph fixed in the geo reference (with one mid-window redraw as a DQ issue). |
| A2 | Window & anchor | 20 months, 2025-01-01 → 2026-08-31; data-gen date 2026-09-10. |
| A3 | Baseline supply-stress tier | Each zone tagged **short / balanced / long** on supply, fixed from months 1–15 behaviour; used for stratification and heterogeneity. |
| A4 | "Active courier" | ≥ 1 completed delivery in the trailing 7 days (weekly) / trailing 28 days (monthly cut). |
| A5 | Liquidity metric | Available courier-hours ÷ demanded delivery-hours, by zone × hour; < 1 = supply-short. |
| A6 | Fulfillment rate | Orders delivered ÷ orders placed, same zone-hour; the experiment's primary metric. |
| A7 | ETA | Order-placed → delivered wall-clock minutes; report p50 and p90 (p90 is the customer-pain metric). |
| A8 | Cancellation taxonomy | customer-initiated · courier-initiated (after accept) · no-courier-found (system). |
| A9 | Experiment unit / split | **Zone-day**, 50/50, stratified by zone × baseline supply-stress tier; peak block 18:00–22:00. |
| A10 | Experiment window | 10 weeks, 2026-04-06 → 2026-06-14 (window-months 16–18); post-window to 2026-08-31. |
| A11 | Primary metric & decision rule | Fulfillment rate; ship if lift is positive, significant at α = 0.05 (cluster-robust), ≥ MDE, **and** incentive cost per incremental delivered order is below the stated threshold. |
| A12 | Guardrails | Incentive cost / incremental order; ETA p50 & p90; cancellation rate; courier earnings / active hour; **neighbour-zone spillover**. |
| A13 | MDE / power | Computed for the **zone-day** unit (N ≈ 420/arm), with intra-zone ICC; randomization-inference cross-check. Planning values finalized in Phase 1. |
| A14 | Cannibalisation | A real, modest negative spillover to adjacent control zones is baked into the data in Phase 3; Phase 10 must estimate its sign and size. |
| A15 | Currency | BRL only; no FX. |
| A16 | True effect | **Not** decided here; set in ETL (Phase 3), detected blind in Phase 10. |

---

## 9. Folder scaffold (created)

```
SwiftBite-Delivery-Analytics/
  docs/            00 scope · 01 business context & KPIs · 02 architecture · 03 data dict ·
                   04 ETL · 05 model · 06 DAX · 07 visual identity · 08 data quality ·
                   09 report structure · walkthrough.md · docs bundle
  etl/             config (one SEED) · gen/ · 01 generate raw · 02 clean/stage ·
                   03 build curated · dq_checks · doc + DAX generators · run_pipeline
  data/
    raw/           source-faithful messy exports        (git-ignored, regenerated)
    staging/       typed stg_* tables                   (git-ignored, regenerated)
    curated/       Kimball star, CSV + Parquet          (git-ignored, regenerated)
    quality/       dq_report.md
  powerbi/         semantic model as code (TMDL) · PBIR report · theme · build script
  assets/          brand.py · logo / page-background generators
  data_analysis/   sql/ python/ findings/ parity/ deliverables/ outputs/   ← PRIMARY
  portfolio/       5 gallery images only
  README.md
```

---

*End of Phase 0 deliverable. Next gate: Phase 1 (`docs/01_business_context_kpis.md`) — drafted alongside this; review both before Phase 2.*
