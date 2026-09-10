# 04 — ETL Pipeline

The pipeline turns one seed into a full messy-source dataset and a clean star schema.
Four stages, each a standalone script, chained by `run_pipeline.py`.

```
config.py ─► 01_generate_raw.py ─► 02_clean_stage.py ─► 03_build_curated.py ─► dq_checks.py
              data/raw/               data/staging/         data/curated/         data/quality/dq_report.md
```

Run it all:

```bash
cd etl
python -m pip install -r requirements.txt
python run_pipeline.py                 # 01 → 02 → 03 → 04, stops on first failure
python run_pipeline.py --from 3        # re-run from a later stage
```

Deterministic: one `SEED` in `config.py` drives every random draw, so a re-run reproduces
byte-identical output.

---

## `config.py` — the single control panel

Everything tunable lives here: the 24-month window and YoY split, the four markets and
their go-live dates, the product taxonomy with per-category price ranges / margins /
return rates, order-volume ramps, seasonality and promo calendar, customer and
returning-buyer behaviour, channel economics, the full payment-method rate card,
supplier terms, logistics SLAs, and the catalogue of data-quality noise to inject (`DQ`).

---

## Stage 01 — `01_generate_raw.py` (bronze)

Generates 12 "source system" extracts into `data/raw/`. Build order and the dependencies
between them:

| # | Output | Notes |
|---|---|---|
| 1 | `fx_rates.csv` | Daily USD-per-unit for EUR/GBP/BRL as a mean-reverting random walk around anchors. Written `d/m/Y`, USD row omitted. |
| 2 | `suppliers.csv` | 15 suppliers: country, `payment_terms_days` (Net 30/45/60), `lead_time_days`, `on_time_rate`. |
| 3 | `erp_products.xlsx` | 300 SKUs across 3 sheets (`products`, `cost_history`, `price_history`). Prices skewed to the low end of each band; unit cost = price × (1 − margin) then a **mean-reverting monthly walk**. Injected mess: category spelled 3 ways on ~30% of rows, lowercased brands, `"$ 1,234.56"` strings, `m/d/Y` dates, and **~6 SKUs omitted from the master** (they still sell → late-arriving dimension). |
| 4 | Orders | The core generator. Month-by-month per market: derive order count from the ramp × seasonality × promo/Black-Friday day weights; split into **new vs returning** customers (returning sampled with a recency×frequency weight); build each basket (popularity-weighted SKU pick ~ 1/price, correlated accessory add-on, warranty attach on eligible items); attach channel, device, warehouse, carrier, ship/promise/deliver dates, payment method and instalment plan. Emits `oms_orders.csv`, `oms_order_lines.csv` and seeds every downstream table. Injected mess: 5 date formats incl. Excel serials, money strings, ~0.5% duplicate lines, ~0.3% blank customer id, ~0.2% negative quantities. |
| 5 | CRM | `crm_customers.csv` (utf-8) + `crm_customers_br.csv` (**Latin-1**, to be detected). ~2% null e-mail, ~1.5% duplicate rows, mixed casing, trailing spaces. |
| 6 | `psp_transactions.csv` | One auth per order + ~1% unmatched junk + ~0.4% of orders missing. Fee column is deliberately **mislabelled** `mdr_pct` while holding a currency amount. |
| 7 | `procurement_purchase_orders.csv` | Reorder loop per SKU×market with real movement: when projected on-hand drops below `TARGET_WEEKS_OF_COVER`, raise a PO (rounded to a case pack) dated back by the supplier lead time; late receipts for unreliable suppliers; `payment_due = receipt + terms`; `supplier_paid ≈ due ± few days`. |
| 8 | WMS | `wms_inventory_movements.csv` — a ledger of `adjustment` (opening), `receipt` (from POs) and `sale` (from order lines). `wms_inventory_snapshots.csv` — month-end balances taken from that ledger, then **~3% of rows perturbed** so the snapshot and the ledger disagree. |
| 9 | `returns.csv` | ~1 line per return with reason, restock flag, `d/m/Y` dates. |
| 10 | `web_analytics_daily.csv` | Sessions reverse-engineered from orders and a channel×device conversion rate; funnel columns; ~1.5% of dates dropped; a few negative-session rows. |
| 11 | Marketing | `google_ads_report.csv` (Search + Display), `meta_ads_export.csv` (Social, different column names & date format), `other_marketing_spend.csv` (affiliate commission + email tooling, monthly). Budget sized to hit a target MER, then split by channel. |
| 12 | `support_tickets.csv` | ~14% of orders raise a ticket: category, priority, created/resolved timestamps, FCR flag, CSAT. |
| — | `carrier_tracking.json` | Nested `{shipments:[{events:[…]}]}` for a ~9% sample; status vocabulary inconsistent on purpose (`delivered` / `DELIVERED` / `Delivery complete`). |
| — | `finance_targets.csv` | Monthly plan per market for 5 metrics, set so actuals land ~90–110% of plan. |

---

## Stage 02 — `02_clean_stage.py` (silver)

Reads `data/raw/*`, writes typed Parquet to `data/staging/` (`stg_*`), and records every
fix as a Markdown fragment in `data/quality/_fragments/`.

Key routines:

- **`parse_money`** — locale-tolerant: `$ 1,299.00`, `1.299,00`, `R$ 1.299,00`, blanks, floats.
- **`parse_dt`** — tries 8 explicit formats then Excel serial numbers then a loose fallback.
- **Products** — map the 27 observed category spellings to 7 canonical values via a lookup
  built from `config.CATEGORY_TYPOS`; title-case brands; parse price/dates; drop duplicate SKUs.
- **Customers** — probe the regional file's encoding (`utf-8`? else `latin-1`), concat,
  drop exact-duplicate rows, then de-dup on `customer_id`; normalise strings; flag missing e-mail.
- **Orders / order lines** — parse, type, drop duplicate lines, move non-positive-qty
  lines to `stg_order_line_rejects`, flag orphan orders/lines and SKUs missing from the master.
- **PSP** — rename the mislabelled column to `reported_fee_local`; reconcile `order_ref`
  against orders (matched / unmatched both reported).
- **Inventory** — reconcile the raw month-end snapshot against a running balance rebuilt
  from the movement ledger; report the variance.
- **Marketing** — union the three sources into one long `stg_marketing_spend`
  (date · market · channel · campaign · impressions · clicks · cost_local · currency · source_system);
  the monthly `other` rows are spread evenly across their days.
- **Carrier JSON** — flatten to `stg_carrier_events` (one row per event) and
  `stg_shipments` (one row per order with created/in-transit/out-for-delivery/delivered
  timestamps); collapse the status vocabulary.
- **FX** — parse, add `USD = 1.0` for every calendar day, forward/back-fill to the full
  `dim_date` span.

---

## Stage 03 — `03_build_curated.py` (gold)

Builds the Kimball star schema in `data/curated/` (Parquet **and** CSV per table).

### Dimensions
`dim_date` (fiscal year starts 1 July; promo & Black-Friday flags; `yoy_period` = CY/PY),
`dim_market` (`live_date`, `is_comparable_base`), `dim_currency`, `dim_customer`
(two-pass: attributes first, then lifetime orders / revenue / status / loyalty tier from
the facts), `dim_product` (price tier by in-category quantile, `+` an `Unknown` stub with
`product_key = -1`), `dim_supplier`, `dim_channel`, `dim_campaign`, `dim_payment_method`,
`dim_carrier`, `dim_warehouse`, and small dims for device / return reason / ticket
category / order status / target metric.

### Techniques worth calling out

- **Currency conversion** — `FX` helper holds a `{(date, ccy): rate}` map; every `*_local`
  money column gets a materialised `*_usd` sibling at the transaction-date rate.
- **Moving-average COGS** — `build_cost_curves` walks each SKU's receipts (opening
  adjustment valued at first known cost, then every PO receipt at its PO unit cost) and
  keeps a running weighted-average. `cost_asof(sku, date)` is a binary search on that step
  function. Sale lines take `qty × cost_asof`; warranty lines take a cost ratio.
- **`fact_payment_schedule`** — each non-cancelled order is exploded into one row per
  settlement tranche: à-vista = a single row at `order_date + settlement_days`;
  instalments = *N* monthly rows. Fees are pro-rated; interest-free (merchant-funded)
  plans also accrue a monthly financing cost on the declining balance.
- **`fact_inventory_snapshot`** — **derived from the movement ledger**, not copied from
  the raw snapshot: month-end running balance per SKU×warehouse, valued at the
  moving-average cost, plus units in transit (open POs) and weeks-of-cover from trailing
  8-week sales. The raw snapshot value and its variance are carried alongside for the DQ story.
- **Comparable base** — `dim_market.is_comparable_base` flags markets live for the whole
  CY+PY span (US). The report also recomputes this dynamically in DAX.

### Facts
`fact_order_lines` (line grain — the centre of the model), `fact_orders` (header grain,
with delivery / perfect-order flags), `fact_payment_schedule`, `fact_returns`,
`fact_purchase_orders`, `fact_inventory_movement`, `fact_inventory_snapshot`,
`fact_marketing_spend`, `fact_web_traffic_daily`, `fact_support_tickets`,
`fact_exchange_rate`, `fact_target`.

Grain, columns and relationships are catalogued in
[`05_data_model.md`](05_data_model.md) and [`03_data_dictionary.md`](03_data_dictionary.md).

---

## Stage 04 — `dq_checks.py` (gate)

Structural and business assertions over the curated layer, split **HARD** (fails the
build) vs **SOFT** (reported):

- no null surrogate keys in the fact tables;
- referential integrity — every fact FK resolves to a dimension key (or the `-1` stub);
- every fact date is present in `dim_date`;
- accounting identities — `net = gross − discount` on every line; order lines roll up to
  the order header; payment schedule sums back to the order total;
- `comparable base = US only`; FX `USD = 1.0`; no non-positive rates;
- sanity bands — order count, AOV, blended gross margin, share of below-cost lines.

Output: `data/quality/dq_report.md` (this gate's table + the stage-02 cleaning fragments).
Non-zero exit on any HARD failure, which also halts `run_pipeline.py`.
