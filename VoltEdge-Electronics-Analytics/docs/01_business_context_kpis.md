# 01 — Business Context & KPI Framework

This document defines *the business* the analytics are built for: who VoltEdge Electronics
is, how it makes money, who consumes the report, and the exact definition of every metric.
Everything downstream (data model, DAX, report pages) traces back to this document.

---

## 1. Company profile

| Attribute | Value |
|---|---|
| Name | VoltEdge Electronics |
| Type | Pure-play online retailer (direct-to-consumer), no physical stores |
| Category | Consumer electronics |
| Founded | 2022 (US); trading history predates the analytics extract |
| HQ | Austin, TX, USA |
| Reporting currency | USD |
| Fulfillment | Company-operated fulfillment centers + regional 3PL partners |
| **Analytics extract window** | **2024-07-01 → 2026-06-30 (24 months)** |

### Why 24 months

Two complete trailing years lets every metric be shown **year-over-year against the same
period last year**:

| Period | Range |
|---|---|
| **Current year (CY)** | 2025-07-01 → 2026-06-30 |
| **Prior year (PY)** | 2024-07-01 → 2025-06-30 |

### Market expansion timeline

VoltEdge scaled from one market to four *during the extract window*. The report must make
this legible — total revenue "steps up" as markets go live, and blended metrics (CAC, AOV,
margin, delivery time) shift as the market mix changes.

| Market | Currency | Live since | In the extract | Fulfillment centers | Primary carriers |
|---|---|---|---|---|---|
| United States | USD | 2022 | full 24 months | Dallas TX, Reno NV | UPS, FedEx, USPS |
| United Kingdom | GBP | **2025-01-01** | 18 months | Birmingham | Royal Mail, DPD, Evri |
| Germany | EUR | **2025-01-01** | 18 months | Leipzig | DHL, Hermes, DPD |
| Brazil | BRL | **2025-07-01** | 12 months | São Paulo (Cajamar) | Correios, Jadlog, Loggi |

### Product catalog

~300 active SKUs organized as **Category → Subcategory → Brand → Product**.

| Category | Example subcategories | Typical gross margin |
|---|---|---|
| Smartphones | Flagship, Mid-range, Budget | 8–14% |
| Laptops & Tablets | Ultrabooks, Gaming laptops, Tablets | 10–16% |
| Audio | Headphones, Earbuds, Speakers, Soundbars | 22–35% |
| Gaming | Consoles, Controllers, VR, Games | 6–18% |
| Smart Home | Hubs, Cameras, Lighting, Thermostats | 20–30% |
| Wearables | Smartwatches, Fitness bands | 18–28% |
| Accessories | Cables, Chargers, Cases, Storage, Power banks | 35–55% |

> **Why this matters analytically:** electronics is a **thin-margin** business. Flagship
> phones and consoles drive revenue but barely any profit; accessories and audio carry the
> margin. A recurring executive question is *"are we growing revenue or growing profit?"* —
> the answer depends on **category mix**, which is why price–volume–mix analysis is a
> first-class citizen in this report.

---

## 2. Business model & economics

### Revenue streams
1. **Product sales** — the vast majority of revenue.
2. **Shipping fees** — charged on orders below a free-shipping threshold (varies by market).
3. **Extended warranty / protection plans** — attach-rate add-on, high margin, modeled as a
   separate line item (`line_type = 'warranty'`) on a share of eligible orders.

### Cost structure (modeled)
- **COGS** — unit cost × quantity (per SKU, sourced from the purchase price of the stock actually sold).
- **Discounts** — promotional and coupon reductions (campaign-driven and site-wide sales).
- **Returns** — refunded merchandise value (electronics return rates are high: 8–14%).
- **Marketing spend** — paid media across Paid Search, Paid Social, Display, Affiliate, plus email tooling.
- **Shipping cost** — what VoltEdge pays carriers (distinct from shipping *fees* charged to customers).
- **Payment processing** — merchant fees per transaction + financing cost of merchant-funded installments (§3).
- **Inventory purchases** — cash paid to suppliers for stock, on supplier payment terms (§4).

### Financial definitions used throughout

| Term | Definition |
|---|---|
| **Gross Revenue** (GMV) | Σ (unit list price × quantity), before discounts, excl. tax & shipping |
| **Discounts** | Σ discount amount applied to order lines |
| **Returns** | Σ net merchandise value of returned lines (post-discount) |
| **Net Revenue** | Gross Revenue − Discounts − Returns. *This is the North Star.* Excludes tax and shipping fees. |
| **COGS** | Σ (unit cost × net quantity sold) |
| **Gross Profit** | Net Revenue − COGS |
| **Payment Fees** | Merchant discount rate × amount + fixed fee per transaction (+ merchant-funded financing cost) |
| **Contribution Margin** | Gross Profit − Marketing Spend − Shipping Cost − Payment Fees (operating-contribution proxy; not a full P&L) |

> Net Revenue, COGS and margin are always expressed in **USD (reporting currency)**.
> Transactions are captured in **local currency** and converted using the exchange rate on
> the transaction date (see §6).

---

## 3. Payment methods, fees & customer-side cash

A deliberate CFO-grade thread. Payment choice affects **cost** (processing fees differ a
lot by scheme) and **cash timing** (settlement lag, and Brazilian installments spreading
cash over months).

### `dim_payment_method` attributes

| Attribute | Meaning |
|---|---|
| `method_group` | Card · Digital Wallet · Bank Transfer · BNPL · Pix · Boleto |
| `method_name` | Visa Credit, Mastercard Debit, Amex, Elo Credit, Hipercard, PayPal, Apple Pay, Google Pay, Klarna, Clearpay, SEPA Direct Debit, Pix, Boleto Bancário |
| `card_scheme` | Visa · Mastercard · Amex · Elo · Hipercard · *(n/a)* |
| `mdr_pct` | Merchant discount rate (% of transaction) |
| `fixed_fee_local` | Flat fee per transaction |
| `settlement_days` | Days until VoltEdge receives the cash |
| `installment_eligible` | Supports paying in instalments |
| `max_installments` | Cap (12 in BR, 3–4 for EU BNPL) |
| `available_markets` | Methods are market-specific (Pix/Boleto/Elo/Hipercard = BR only; SEPA/Klarna/Clearpay = UK/DE; Amex skewed US/UK) |

### Indicative economics (modeled, not a real rate card)

| Method | `mdr_pct` | Fixed fee | Settlement days | Notes |
|---|---|---|---|---|
| Visa / Mastercard – Debit | 1.1 % | — | 2 | cheapest card |
| Visa / Mastercard – Credit | 2.2 % | — | 2 | |
| Amex | 3.4 % | — | 3 | highest scheme fee |
| Elo / Hipercard (BR) – Credit | 2.6 % | — | 2 (à vista) | instalments settle monthly |
| PayPal | 2.9 % | 0.30 | 1 | |
| Apple Pay / Google Pay | 2.0 % | — | 2 | rides card rails |
| Klarna / Clearpay (BNPL) | 4.5 % | 0.30 | 2 | merchant paid upfront, keeps the fee |
| SEPA Direct Debit (DE) | 0.8 % | 0.25 | 3 | |
| Pix (BR) | 0.45 % | — | 0 | instant, cheapest overall |
| Boleto Bancário (BR) | — | 3.49 | 1 (after customer pays, avg +2) | ~12 % of boletos are never paid → order cancelled |

### Installments (`installment_plan`)

| Plan | Who pays financing | Cash-flow effect |
|---|---|---|
| `None` (à vista) | — | Full amount settles once, after `settlement_days` |
| `Interest-Free` (merchant-funded — BR "parcelado sem juros") | **VoltEdge** absorbs ~1.8 %/month of the deferred balance | Cash arrives in *N* monthly tranches; a financing cost is booked |
| `With Interest` (customer-funded) | Customer | Cash arrives in *N* monthly tranches; no extra merchant cost |

- `fact_orders` carries the order-grain payment attributes and total `payment_fee`.
- `fact_payment_schedule` explodes each order into **one row per settlement tranche**
  (`installment_number`, `due_date`, `gross_amount`, `fee_amount`, `financing_cost`,
  `net_amount`, currency) — the table the customer-side cash-flow visuals sit on.

---

## 4. Inventory, procurement & the cash conversion cycle

The other half of working capital: cash goes **out** to suppliers to buy stock, that stock
**sits** in a warehouse, then a sale converts it back to cash **in**. The report treats this
as a first-class CFO/COO topic.

### What is modeled

| Object | Grain | Purpose |
|---|---|---|
| `dim_supplier` | supplier | Country, `payment_terms_days` (Net 30 / 45 / 60), `lead_time_days`, on-time-supply reliability |
| `fact_purchase_orders` | PO line (PO × SKU) | Order date, supplier, qty ordered, unit cost, PO value (local + USD), expected & actual receipt date, **supplier payment due date** (receipt + terms), **supplier paid date** |
| `fact_inventory_movement` | movement | Transactional ledger: `receipt` (from a PO), `sale` (from an order line), `return_to_stock`, `adjustment`, `transfer`. Date, SKU, warehouse, qty (+/−), unit cost, value |
| `fact_inventory_snapshot` | month-end × SKU × warehouse | **Derived from the movement ledger.** Units on hand, units in transit (inbound), units reserved, unit cost, inventory value (local + USD), days of cover |

> Building the snapshot **from** the movement ledger is a deliberate data-engineering
> showcase (a running balance / window function per SKU-warehouse), documented in
> [`04_etl_pipeline.md`](04_etl_pipeline.md).

### COGS sourcing

COGS on a sale is taken from the **weighted-average purchase cost** of stock on hand for
that SKU at sale time (moving-average cost), so margin reflects what the goods actually
cost — not a static list cost. Price drift in `fact_purchase_orders` therefore flows
through to margin.

### Working-capital KPIs  *(Executive Summary tile + dedicated Phase-2 section)*

| KPI | Definition | Benchmark |
|---|---|---|
| Inventory Value (on hand) | Σ units on hand × moving-avg cost, USD | — |
| Inventory in Transit | Σ inbound units not yet received × PO cost | — |
| **DIO** — Days Inventory Outstanding | Avg Inventory Value ÷ COGS × days in period | 45–75 |
| **DSO** — Days Sales Outstanding | Amount-weighted avg days from order date to cash settlement | US/EU ~2–4; BR much higher (instalments) |
| **DPO** — Days Payables Outstanding | Avg Accounts Payable ÷ COGS (or purchases) × days in period | 30–60 |
| **CCC** — Cash Conversion Cycle | DIO + DSO − DPO | lower is better; watch the trend |
| Accounts Payable (open) | Σ received-but-unpaid PO value at a date | — |
| Accounts Receivable (open) | Σ booked-but-unsettled customer amounts at a date | — |
| Working Capital Tied Up | Inventory Value + AR − AP | — |
| Supplier Spend | Σ PO value received in period, USD | — |
| Inventory Turnover | Trailing COGS ÷ Avg Inventory Value | 5–8×/yr |
| Weeks of Cover | Inventory on hand ÷ avg weekly units sold | 4–10 |
| Stockout Rate % | SKU-days out of stock ÷ SKU-days | < 3% |
| Aged / Excess Inventory % | Value with > 90 days of cover ÷ total inventory value | < 15% |

### Company cash-flow timeline

A single view combining, per week/month:

- **Cash out** — supplier payments (PO value on `supplier_paid_date`), marketing spend, shipping cost, payment processing fees.
- **Cash in** — customer settlements from `fact_payment_schedule`.
- **Net cash flow** and **cumulative cash position**, plus the split of working capital
  between inventory and receivables. Makes the cost of BR "parcelado sem juros" and of
  slow-moving stock visible in cash terms.

---

## 5. Total vs Comparable Base (like-for-like)

Because markets go live mid-window, a raw YoY number mixes *organic* growth with *expansion*
growth. Every headline growth metric is shown **two ways**:

| View | Definition |
|---|---|
| **Total** | All markets, as reported. |
| **Comparable Base** | Only markets live for the **entire** CY + PY span → **United States** only. The like-for-like / "same-store" view. |
| **Expansion Contribution** | Total − Comparable Base. Revenue / orders / customers attributable to UK, DE, BR. |

Secondary cut: **Core-3 Comparable** (US + UK + DE, comparable from 2025-01) for analysis
from 2025 onward.

Implementation: `dim_market` carries `live_date`; a calculated `is_comparable_base`
(relative to PY start 2024-07-01) flags US. DAX also provides a **dynamic** comparable-base
measure that recomputes the eligible market set from the visual's date context. Both are in
[`06_dax_measures.md`](06_dax_measures.md).

---

## 6. Multi-currency handling

- Every monetary transaction is stored in its **local currency** with a `currency_code`.
- `fact_exchange_rate` holds a **daily** rate per currency → USD.
- Curated fact tables carry **both** `amount_local` and a materialized `amount_usd`
  (converted at transaction-date rate) so results are reproducible without the model.
- DAX also exposes **currency-aware measures** and a **reporting-currency selector**
  (USD / EUR / GBP / BRL). Default = USD.
- FX approach: rates fluctuate around anchors (EUR 1.08, GBP 1.26, BRL 0.19 USD per unit)
  with realistic daily drift.

---

## 7. Seasonality & patterns embedded in the data

- **Q4 peak** — Nov/Dec ~1.7–2.1× a baseline month; **Black Friday / Cyber Monday** spike within November.
- **Secondary peaks** — mid-year sale (July), back-to-school (late Aug / Sep).
- **Growth trend** — ~2–4% MoM growth on the comparable base, plus step changes at each market launch.
- **Channel mix evolution** — heavy Paid Search/Social early; Organic, Email, Direct grow as brand awareness builds; CAC rises over time.
- **Category trends** — Wearables and Smart Home grow share; Smartphones' share slowly declines.
- **Purchase-cost drift** — supplier unit costs move over time; some SKUs discontinued and replaced → margin and inventory-aging effects.
- **Promo periods** — recurring discount events with elevated discount rates and order volume.
- **Payment-mix shift** — Pix share in BR grows MoM; BNPL share in UK/DE grows; Amex share slowly falls.
- **Fulfillment stress** — delivery times and late-delivery rates worsen during Q4 and vary by carrier and destination region.
- **Returns** — higher for Smartphones/Laptops, lower for Accessories; split "defective" vs "changed mind" / "not as described".

---

## 8. Stakeholders & the questions they ask

The report is **executive-level**: each page answers the standing questions of one leader.

| Persona | Owns | Standing questions |
|---|---|---|
| **CEO** | Whole business | Are we hitting plan? Which market/category drives or drags growth? Revenue *and* margin trajectory? Total vs like-for-like? |
| **CFO** | Margin, cash & efficiency | Gross margin trend and why it moved. Discount leakage. Payment fees and the cost of "sem juros". Cash received vs revenue booked. **Cash conversion cycle** — how much cash is tied up in inventory and receivables? Contribution margin by market. Revenue vs target. |
| **CMO** | Demand & acquisition | CAC and ROAS by channel and campaign. New vs returning revenue. Which campaigns paid back? Funnel drop-off. |
| **VP E‑commerce** | Site & conversion | Traffic, conversion rate, AOV, cart abandonment, revenue per session, device performance. |
| **COO / VP Operations** | Fulfillment & inventory | On-time delivery, delivery cycle time, shipping cost per order, carrier performance, **stockouts and weeks of cover**, **aged inventory**, inventory turnover, supplier lead time & reliability. |
| **VP Customer** | Retention & service | Repeat rate, cohort retention, CLV, churn, support volume & resolution time, CSAT, return rate by reason. |

---

## 9. KPI framework

Metrics defined in business terms here; exact DAX in [`06_dax_measures.md`](06_dax_measures.md).
"Benchmark" is a plausible DTC-electronics reference range used to set report targets — not a
claim about any real company.

### 9.0 North Star

| KPI | Definition | Benchmark |
|---|---|---|
| **Net Revenue (USD)** | Gross Revenue − Discounts − Returns, converted to USD | vs monthly plan |

### 9.1 Sales & Growth  *(Executive Summary, Sales Performance)*

| KPI | Definition | Benchmark |
|---|---|---|
| Gross Revenue (GMV) | Σ (list price × qty) | — |
| Net Revenue | Gross Revenue − Discounts − Returns | vs target |
| Orders | Distinct orders, excluding fully cancelled | — |
| Units Sold | Σ net quantity | — |
| Average Order Value (AOV) | Net Revenue ÷ Orders | $170–$260 |
| Units per Order | Units ÷ Orders | 1.6–2.2 |
| Gross Profit | Net Revenue − COGS | — |
| Gross Margin % | Gross Profit ÷ Net Revenue | 12–20% blended (thin, by design — see note below) |
| Discount Rate % | Discounts ÷ Gross Revenue | 4–10% |
| Return Rate % | Returned Units ÷ Units Sold | 7–12% |
| Warranty Attach Rate % | Orders with a warranty line ÷ eligible orders | 6–12% |
| Net Revenue YoY % — **Total** | (CY − PY) ÷ PY, all markets | — |
| Net Revenue YoY % — **Comparable Base** | same, US-only like-for-like | — |
| Expansion Contribution | Total Net Revenue − Comparable-Base Net Revenue | — |
| Revenue vs Target % | Net Revenue ÷ Target − 1 | ≥ 0 |
| Price / Volume / Mix | Decomposition of Net Revenue Δ vs PY into rate, quantity, category-mix effects | — |
| Revenue by Market / Category / Channel | Net Revenue sliced by dimension | — |

> **Thin margin is the story, not a bug.** Blended gross margin sits at ~14% — flagship
> phones, laptops and consoles carry almost no margin; audio and accessories carry it all.
> After marketing (~$4M), shipping and payment fees, **contribution margin is near
> break-even** — VoltEdge is a fast-growing, not-yet-profitable business. The report is
> built to make that tension legible: *are we buying growth we can't afford, and does
> category mix / repeat revenue get us to profit?*

### 9.2 Payments & Customer Cash  *(Executive Summary, Sales Performance › Payments)*

Payment Processing Cost · Effective Fee Rate % · Fee Rate by Scheme/Method/Market ·
Merchant-Funded Financing Cost · Installment Mix % · Avg Instalments (BR) ·
Revenue Booked vs Cash Received · Accounts Receivable (open) · DSO. (Definitions in §3.)

### 9.3 Working Capital & Inventory  *(Executive Summary tile; dedicated Phase-2 section)*

DIO · DSO · DPO · **CCC** · Inventory Value · Inventory in Transit · Accounts Payable (open) ·
Accounts Receivable (open) · Working Capital Tied Up · Supplier Spend · Inventory Turnover ·
Weeks of Cover · Stockout Rate % · Aged / Excess Inventory % · Company cash-flow timeline.
(Definitions in §4.)

### 9.4 Marketing & Acquisition  *(Marketing & Acquisition)*

| KPI | Definition | Benchmark |
|---|---|---|
| Marketing Spend | Σ paid media spend (+ email tooling) | — |
| Impressions / Clicks | From ad-platform exports | — |
| CTR % | Clicks ÷ Impressions | 0.7–2.5% |
| CPC | Spend ÷ Clicks | $0.40–$1.60 |
| New Customers | Customers whose first-ever order falls in the period | — |
| CAC (paid) | Paid Marketing Spend ÷ New Customers via paid channels | $45–$110 |
| Blended CAC | Total Marketing Spend ÷ Total New Customers | $30–$70 |
| ROAS | Attributed Net Revenue ÷ Ad Spend (last-touch, channel-level) | 3.0–6.0× |
| MER | Total Net Revenue ÷ Total Marketing Spend | 6–10× |
| New vs Returning Revenue | Net Revenue split by customer order sequence | — |
| Campaign Performance | Spend, Orders, Net Revenue, ROAS per campaign | ROAS ≥ 3× to pay back |
| Acquisition Funnel | Impressions → Clicks → Sessions → Add-to-Cart → Orders | — |

### 9.5 Website / Digital  *(Phase 2)*

Sessions / Users · Conversion Rate % (Orders ÷ Sessions, 1.3–2.6%) · Bounce Rate % ·
Pages per Session · Add-to-Cart Rate % · Cart Abandonment Rate % · Revenue per Session ·
Device / Browser mix.

### 9.6 Logistics & Fulfillment  *(Phase 2)*

Avg Delivery Time (days, 3–6) · On-Time Delivery % (92–96%) · Perfect Order Rate % (88–93%) ·
Ship Time (days) · Shipping Cost per Order ($6–$14) · Shipping Cost Recovery % ·
Carrier Scorecard · Supplier Lead Time & On-Time-Supply % · (inventory metrics in §9.3).

### 9.7 CRM / Customer  *(Phase 3)*

Active Customers · New / Returning · Repeat Purchase Rate % (25–35%) · Cohort Retention % ·
Churn Rate % · CLV · RFM Segment · Loyalty Tier Mix · Support Tickets · Avg Resolution Time
(h, <24) · First Contact Resolution % (70–80%) · CSAT (≥4.3) · Return Rate by Reason.

---

## 10. Targets / plan

`fact_target` holds a **monthly plan by market** for: Net Revenue, Orders, New Customers,
Blended CAC, Gross Margin %. Targets are "ambitious but plausible" (actuals land ~90–110% of
plan). Targets exist only for months a market is live.

---

## 11. Out of scope (explicit)

- Full P&L / GAAP accounting, tax filing detail, statutory cash-flow statement.
- Real ad-platform attribution modeling (simple last-touch at channel level).
- Employee, payroll, or fixed-cost data.
- Real personal data — all customers synthetic (`Faker`, seeded).
- Real-time / streaming — batch pipeline, one historical load.

---

## 12. Resolved assumptions

| # | Assumption | Decision |
|---|---|---|
| 1 | North Star = **Net Revenue** (excl. tax & shipping fees), USD; Gross Profit secondary | ✅ |
| 2 | Return rate ~8%, blended gross margin ~14% (thin by design; growth-stage, near break-even after marketing) | ✅ |
| 3 | Extract window **24 months**: 2024-07-01 → 2026-06-30 | ✅ |
| 4 | Expansion inside window: US always-on · UK+DE 2025-01-01 · BR 2025-07-01 | ✅ |
| 5 | Every growth metric shown **Total** and **Comparable Base (US like-for-like)** + Expansion Contribution | ✅ |
| 6 | Warranty / protection-plan revenue modeled as an add-on line | ✅ |
| 7 | Reporting-currency selector (USD/EUR/GBP/BRL) in the model | ✅ |
| 8 | Payment model: MDR by scheme, fixed fees, settlement lag, instalments (merchant- vs customer-funded), `fact_payment_schedule` | ✅ |
| 9 | Procurement & inventory modeled: `dim_supplier` (Net 30/45/60), `fact_purchase_orders`, `fact_inventory_movement` ledger → derived `fact_inventory_snapshot`; moving-average COGS; DIO/DSO/DPO/CCC and a company cash-flow timeline | ✅ |
| 10 | Realised scale: 294 SKUs · ~103k customers · ~158k non-cancelled orders · ~262k order lines · ~14k PO lines · 24 months. AOV ~$208, ~1.7 lifetime orders/customer, repeat rate ~40%. | ✅ |
