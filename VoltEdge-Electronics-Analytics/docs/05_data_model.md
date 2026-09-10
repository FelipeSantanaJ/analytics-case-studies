# 05 — Data Model (Curated Star Schema)

The curated layer is a Kimball-style star: one row per business event in the fact tables,
conformed dimensions with integer surrogate keys, a real date dimension, and every
monetary value available in both local currency and USD.

Power BI connects to `data/curated/*.parquet` through a single parameter (`pDataFolder`).

---

## 1. Bus matrix — which dimension touches which fact

| Dimension ▸ / Fact ▾ | date | market | customer | product | supplier | channel | campaign | payment_method | carrier | warehouse | currency |
|---|:--:|:--:|:--:|:--:|:--:|:--:|:--:|:--:|:--:|:--:|:--:|
| **fact_order_lines** | ● (order/ship/deliver) | ● | ● | ● | | ● | | ● | | ● | ● |
| **fact_orders** | ● (order/ship/deliver) | ● | ● | | | ● | | ● | ● | ● | ● |
| **fact_payment_schedule** | ● (order/due) | ● | | | | | | | | | ● |
| **fact_returns** | ● (return) | ● | ● | ● | | | | | | | ● |
| **fact_purchase_orders** | ● (order/receipt/due/paid) | ● | | ● | ● | | | | | ● | |
| **fact_inventory_movement** | ● (movement) | ● | | ● | | | | | | ● | |
| **fact_inventory_snapshot** | ● (month-end) | ● | | ● | | | | | | ● | |
| **fact_marketing_spend** | ● | ● | | | | ● | ● | | | | |
| **fact_web_traffic_daily** | ● | ● | | | | ● | | | | | |
| **fact_support_tickets** | ● (created/resolved) | ● | ● | | | | | | | | |
| **fact_exchange_rate** | ● | | | | | | | | | | ● |
| **fact_target** | ● (month) | ● | | | | | | | | | |

All date roles join to the **single** `dim_date` (Power BI: one active relationship on
`order_date_key`; `ship_date_key`, `delivery_date_key`, etc. are inactive relationships
activated with `USERELATIONSHIP` inside specific measures).

---

## 2. Fact tables — grain & measures

### fact_order_lines  *(centre of the model)*
**Grain:** one row per order line — an order × product, or a `warranty` add-on line.
**Keys:** `order_date_key`, `ship_date_key`, `delivery_date_key`, `product_key`,
`customer_key`, `market_key`, `currency_key`, `channel_key`, `warehouse_key`,
`payment_method_key`; degenerate `order_id`, `order_line_id`, `line_type`, `order_status`.
**Measures:** `quantity`, `unit_price_local`, `gross_amount_(local|usd)`,
`discount_amount_(local|usd)`, `net_amount_(local|usd)`, `cogs_usd` (moving-average),
`gross_profit_usd`, `returned_qty`, `is_returned`, `refund_amount_(local|usd)`.

### fact_orders
**Grain:** one row per order header. **Keys:** order/ship/delivery date, `customer_key`,
`market_key`, `currency_key`, `channel_key`, `warehouse_key`, `carrier_key`,
`payment_method_key`; degenerate `order_id`, `order_status`, `device`,
`installments`, `installment_plan`.
**Measures:** `units`, `gross/discount/net/tax/shipping_fee/payment_fee` in `_local` and
`_usd`, `shipping_cost_usd`, `ship_days`, `delivery_days`; flags `is_late`, `is_on_time`,
`is_delivered`, `is_cancelled`, `has_return`, `is_perfect_order`.

### fact_payment_schedule
**Grain:** one row per settlement tranche (`order_id` × `installment_number`).
**Keys:** `order_date_key`, `due_date_key`, `market_key`, `currency_key`.
**Measures:** `n_installments`, `installment_plan`, `settlement_lag_days`,
`gross/fee/financing_cost/net` amount in `_local` and `_usd`.
Cash **received** in a period = SUM(`net_amount_usd`) filtered by `due_date_key`;
revenue **booked** = `fact_order_lines` filtered by `order_date_key`. The gap is the DSO story.

### fact_returns
**Grain:** one return line. `return_date_key`, `product_key`, `customer_key`,
`market_key`, `currency_key`; `returned_qty`, `refund_amount_(local|usd)`, `reason`,
`restocked`, `condition`.

### fact_purchase_orders
**Grain:** one PO line (`po_number` × SKU). `order_date_key`,
`expected/actual_receipt_date_key`, `payment_due_date_key`, `supplier_paid_date_key`,
`supplier_key`, `product_key`, `warehouse_key`, `market_key`.
**Measures:** `qty_ordered`, `unit_cost_usd`, `po_value_usd`, `payment_terms_days`,
`late_receipt_days`, `days_to_pay`.
Accounts payable open at a date = POs with `actual_receipt ≤ date < supplier_paid`.

### fact_inventory_movement
**Grain:** one stock movement. `movement_date_key`, `product_key`, `warehouse_key`,
`market_key`; `movement_type` (`adjustment`/`receipt`/`sale`), signed `quantity`,
`unit_cost_usd` (moving-average at the date), `value_usd`.

### fact_inventory_snapshot  *(derived from the ledger)*
**Grain:** month-end × SKU × warehouse. `snapshot_date_key`, `month_year`,
`product_key`, `warehouse_key`, `market_key`.
**Measures:** `units_on_hand`, `moving_avg_cost_usd`, `inventory_value_usd`,
`units_in_transit`, `avg_weekly_units_sold`, `weeks_of_cover`, plus `raw_snapshot_units`
and `snapshot_variance_units` for the DQ narrative.

### fact_marketing_spend
**Grain:** date × market × channel × campaign. `impressions`, `clicks`,
`cost_local`, `cost_usd`.

### fact_web_traffic_daily
**Grain:** date × market × channel × device. `sessions`, `users`, `pageviews`,
`bounces`, `add_to_carts`, `carts_created`, `transactions`, `had_data_anomaly`.

### fact_support_tickets
**Grain:** one ticket. `created_date_key`, `resolved_date_key`, `market_key`,
`customer_key`, `category`, `priority`, `resolution_hours`,
`first_contact_resolution`, `csat`.

### fact_exchange_rate
**Grain:** date × currency. `rate_to_usd`, `rate_from_usd`. Used by currency-aware
measures and the reporting-currency selector.

### fact_target
**Grain:** month × market × metric. `target_value`. `metric` ∈ {Net Revenue, Orders,
New Customers, Blended CAC, Gross Margin %}.

---

## 3. Dimensions — notable attributes

| Dimension | Key | Attributes used in the report |
|---|---|---|
| **dim_date** | `date_key` (yyyymmdd) | `date`, `month_year`, `quarter_name`, `year`, `day_name`, `is_weekend`, `fiscal_year`/`fiscal_quarter`/`fiscal_period` (FY starts 1 Jul), `is_promo_period`, `promo_name`, `is_black_friday_week`, `in_extract_window`, `yoy_period` (CY/PY) |
| **dim_market** | `market_key` | `market_id`, `market_name`, `region`, `currency_code`, `live_date`, `is_comparable_base` |
| **dim_currency** | `currency_key` | `currency_code`, `currency_name`, `currency_symbol`, `is_reporting_currency` |
| **dim_customer** | `customer_key` (`-1` = Unknown) | `market_id`, `acquisition_channel`, `acquisition_month`, `acquired_before_window`, `segment`, `age_band`, `loyalty_tier`, `marketing_consent`, `has_email`, `country`, `state_region`, `city`, `first_order_date`, `last_order_date`, `lifetime_orders`, `lifetime_net_revenue_usd`, `is_repeat_customer`, `customer_status` (Prospect/Active/Lapsed/Churned) |
| **dim_product** | `product_key` (`-1` = Unknown/late-arriving) | `sku_id`, `product_name`, `category`, `subcategory`, `brand`, `list_price_usd`, `price_tier`, `launch_date`, `discontinue_date`, `is_active_at_window_end`, `is_warranty_eligible`, `warranty_months`, `weight_kg`, `supplier_key` |
| **dim_supplier** | `supplier_key` | `supplier_name`, `country`, `payment_terms_days`, `payment_terms_band` (Net 30/45/60), `lead_time_days`, `on_time_rate`, `reliability_band` |
| **dim_channel** | `channel_key` | `channel_name`, `channel_group` (Paid/Owned/Earned), `is_paid` |
| **dim_campaign** | `campaign_key` | `campaign` name, `market_id`, `channel`, `campaign_theme` |
| **dim_payment_method** | `payment_method_key` (`-1`) | `method_name`, `method_group`, `card_scheme`, `mdr_pct`, `fixed_fee_local_nominal`, `settlement_days`, `installment_eligible`, `max_installments`, `available_markets` |
| **dim_carrier** | `carrier_key` | `carrier_name`, `market_id`, `baseline_transit_days`, `baseline_on_time_rate` |
| **dim_warehouse** | `warehouse_key` | `warehouse_id`, `warehouse_name`, `market_id`, `region` |
| small dims | | `dim_device`, `dim_return_reason`, `dim_ticket_category`, `dim_order_status`, `dim_metric` |

---

## 4. Cross-cutting model decisions

**Multi-currency.** Transactions are captured in local currency (`*_local`) with a
`currency_key`, and every one carries a materialised `*_usd` at the order-date rate.
`fact_exchange_rate` additionally lets DAX convert to any reporting currency on the fly; a
disconnected `Reporting Currency` slicer drives that. Default view is USD.

**Total vs Comparable Base.** `dim_market.is_comparable_base` (US only) gives the static
like-for-like cut. A dynamic DAX version recomputes the eligible market set from the
visual's date range, so the concept survives any filter. `Expansion Contribution =
Total − Comparable Base`.

**Moving-average COGS.** `cogs_usd` on each sale line reflects the weighted-average
purchase cost of that SKU at sale time (rebuilt from PO receipts), so margin moves with
real sourcing cost, not a static list cost.

**Inventory snapshot is derived, not trusted.** `fact_inventory_snapshot` is rebuilt from
the movement ledger; the raw WMS snapshot is kept only as `raw_snapshot_units` /
`snapshot_variance_units` to quantify system drift.

**Working-capital timing.** Three clocks: goods received → paid supplier
(`fact_purchase_orders`), stock held (`fact_inventory_snapshot`), order booked → cash
settled (`fact_payment_schedule`). Together they give DIO, DPO, DSO and the cash
conversion cycle, and a single company cash-flow timeline.

**Unknown members.** `product_key = -1` and `customer_key = -1` stubs absorb
late-arriving / missing natural keys so fact rows are never dropped and totals always tie.

---

## 5. Power BI relationships (all single-direction, many-to-one from fact to dim)

```
dim_date[date_key]            1 ─* fact_order_lines[order_date_key]      (active)
dim_date[date_key]            1 ─* fact_order_lines[ship_date_key]       (inactive)
dim_date[date_key]            1 ─* fact_order_lines[delivery_date_key]   (inactive)
dim_market[market_key]        1 ─* fact_order_lines[market_key]
dim_customer[customer_key]    1 ─* fact_order_lines[customer_key]
dim_product[product_key]      1 ─* fact_order_lines[product_key]
dim_channel[channel_key]      1 ─* fact_order_lines[channel_key]
dim_currency[currency_key]    1 ─* fact_order_lines[currency_key]
dim_payment_method[…key]      1 ─* fact_orders[payment_method_key]
dim_carrier[carrier_key]      1 ─* fact_orders[carrier_key]
dim_warehouse[warehouse_key]  1 ─* fact_orders[warehouse_key] , fact_purchase_orders , fact_inventory_*
dim_supplier[supplier_key]    1 ─* fact_purchase_orders[supplier_key]
dim_campaign[campaign_key]    1 ─* fact_marketing_spend[campaign_key]
dim_date[date_key]            1 ─* every other fact's primary date key
```

`fact_orders` and `fact_order_lines` are **not** related to each other — they are two
grains of the same process and are sliced by shared dimensions, never joined.
