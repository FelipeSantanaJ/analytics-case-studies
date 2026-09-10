# VoltEdge Electronics — Data-Quality Report

_generated 2026-08-31 20:15_  ·  seed `20240701`

## Curated-layer gate

- checks run: **28**  ·  passed: **28**  ·  hard failures: **0**  ·  soft warnings: **0**

| level | check | result | detail |
|---|---|---|---|
| HARD | fact_order_lines: no null keys | ✅ | 0 rows with a null key |
| HARD | fact_orders: no null keys | ✅ | 0 rows with a null key |
| HARD | fact_payment_schedule: no null keys | ✅ | 0 rows with a null key |
| HARD | fact_marketing_spend: no null keys | ✅ | 0 rows with a null key |
| HARD | RI fact_order_lines.product_key -> dim_product | ✅ | 0 unresolved key values |
| HARD | RI fact_order_lines.market_key -> dim_market | ✅ | 0 unresolved key values |
| HARD | RI fact_order_lines.currency_key -> dim_currency | ✅ | 0 unresolved key values |
| HARD | RI fact_order_lines.channel_key -> dim_channel | ✅ | 0 unresolved key values |
| HARD | RI fact_orders.customer_key -> dim_customer | ✅ | 0 unresolved key values |
| HARD | RI fact_orders.payment_method_key -> dim_payment_method | ✅ | 0 unresolved key values |
| HARD | RI fact_orders.carrier_key -> dim_carrier | ✅ | 0 unresolved key values |
| HARD | RI fact_purchase_orders.supplier_key -> dim_supplier | ✅ | 0 unresolved key values |
| HARD | RI fact_purchase_orders.product_key -> dim_product | ✅ | 0 unresolved key values |
| HARD | RI fact_returns.product_key -> dim_product | ✅ | 0 unresolved key values |
| HARD | RI fact_inventory_snapshot.product_key -> dim_product | ✅ | 0 unresolved key values |
| HARD | fact_order_lines: dates within dim_date | ✅ | 0 rows outside dim_date |
| HARD | fact_marketing_spend: dates within dim_date | ✅ | 0 rows outside dim_date |
| HARD | fact_web_traffic_daily: dates within dim_date | ✅ | 0 rows outside dim_date |
| HARD | fact_order_lines: net = gross - discount | ✅ | 0 lines break the identity |
| HARD | order lines roll up to order header (net local) | ✅ | 0 of 168,045 clean orders differ > 0.5 (519 reject-touched orders excluded) |
| SOFT | product lines sold below moving-avg cost (loss leaders + cost drift) | ✅ | 1.7% of product lines have negative gross profit (expected < 8%) |
| HARD | comparable base = US only | ✅ | comparable-base markets: ['US'] |
| HARD | FX: USD rate is exactly 1.0 | ✅ | 0 USD rows != 1.0 |
| HARD | FX: no non-positive rates | ✅ | 0 rows |
| SOFT | order count in 110k–200k | ✅ | 167,396 orders |
| SOFT | AOV in $120–$320 | ✅ | AOV = $208 |
| SOFT | blended gross margin 12–24% | ✅ | GM = 21.0% |
| HARD | payment schedule sums to order total | ✅ | 0 orders differ > 2% |

## Stage 02 — cleaning & conforming

_generated 2026-08-31 20:14_

| check | detail | count | severity |
|---|---|---:|---|
| fx | rows after fill to full calendar | 4,384 | info |
| products | category spellings normalized to canonical | 81 | info |
| products | category values left unmapped | 0 | info |
| products | duplicate SKU rows dropped | 0 | info |
| customers | regional file decoded as latin-1 | 12,904 | info |
| customers | exact duplicate rows dropped | 1,441 | info |
| customers | rows sharing customer_id dropped | 236 | info |
| customers | rows with no e-mail | 2,196 | warn |
| orders | unparseable order timestamps | 0 | info |
| orders | orders with blank customer_id | 484 | warn |
| orders | orders whose customer_id is not in CRM | 0 | warn |
| orders | orders outside the extract window | 0 | info |
| order_lines | exact duplicate lines dropped | 1,378 | info |
| order_lines | non-positive-qty lines moved to rejects | 519 | warn |
| order_lines | lines with no matching order | 0 | info |
| order_lines | distinct SKUs missing from ERP master (late-arriving dim) | 6 | warn |
| psp | transactions not matching any order | 1,678 | warn |
| psp | orders with no PSP transaction | 702 | warn |
| purchase_orders | PO lines received late | 1,131 | info |
| inventory | snapshot rows disagreeing with the movement ledger | 7,216 | warn |
| returns | return rows with no matching order line | 48 | warn |
| web | rows with negative sessions (abs-corrected) | 109 | warn |
| web | market-days with no web analytics rows at all | 69 | warn |
| marketing | unified spend rows (google+meta+other) | 10,935 | info |
| support | tickets with negative resolution time | 0 | info |
| carrier | distinct raw status strings collapsed to canonical vocab | 12 | info |

