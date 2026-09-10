-- 06_cash_conversion_cycle.sql  (DuckDB dialect)
-- Finding 06 - Cash Conversion Cycle components (docs/06 section 11).
--   DSO (days) = SUM(gross_amount_usd * settlement_lag_days) / SUM(gross_amount_usd)
--   Avg Inventory Value = mean of the per-snapshot inventory_value_usd totals
--   COGS Trailing 12M   = CY COGS (window ends 2026-06-30) -> order_date_key 20250701 .. 20260630
--   AP Open (USD)       = SUM(po_value_usd) received on/before asOf, paid after asOf
--   asOf = last dim_date key in window = 20260630
-- Bare table names resolve to the per-parquet views created by utils.duck().

-- name: dso
-- Value-weighted settlement lag, all payment schedules.
SELECT SUM(gross_amount_usd * settlement_lag_days) / SUM(gross_amount_usd)
FROM fact_payment_schedule;

-- name: dso_by_market
SELECT m.market_name,
       SUM(f.gross_amount_usd * f.settlement_lag_days) / SUM(f.gross_amount_usd) AS dso
FROM fact_payment_schedule f
JOIN dim_market m ON m.market_key = f.market_key
GROUP BY 1
ORDER BY 1;

-- name: avg_inv_24
-- Mean inventory value across all snapshot dates.
SELECT AVG(x)
FROM (SELECT snapshot_date_key, SUM(inventory_value_usd) AS x
      FROM fact_inventory_snapshot
      GROUP BY 1);

-- name: avg_inv_12
-- Mean inventory value across the last 12 snapshot dates.
SELECT AVG(x)
FROM (SELECT SUM(inventory_value_usd) AS x
      FROM fact_inventory_snapshot
      GROUP BY snapshot_date_key
      ORDER BY snapshot_date_key DESC
      LIMIT 12);

-- name: cogs_12m
-- Trailing-12-month COGS (= CY COGS for the window that ends 2026-06-30).
SELECT SUM(cogs_usd)
FROM fact_order_lines
WHERE order_status <> 'cancelled' AND order_date_key BETWEEN 20250701 AND 20260630;

-- name: ap_open
-- Accounts payable open at asOf = 20260630 (received by then, not yet paid).
SELECT SUM(po_value_usd)
FROM fact_purchase_orders
WHERE actual_receipt_date_key <= 20260630 AND supplier_paid_date_key > 20260630;

-- name: wtd_pay
-- Value-weighted days past due and payment terms across all purchase orders.
SELECT SUM(days_to_pay * po_value_usd)        / SUM(po_value_usd) AS wtd_past_due,
       SUM(payment_terms_days * po_value_usd) / SUM(po_value_usd) AS wtd_terms
FROM fact_purchase_orders;
