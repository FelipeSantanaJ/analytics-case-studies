-- 07_marketing_efficiency.sql  (DuckDB dialect)
-- Finding 07 - marketing efficiency (docs/06 section 08).
--   Marketing Spend (USD) = SUM(fact_marketing_spend.cost_usd)
--   New Customers          = customers whose first-ever non-cancelled order falls in the window
--   New Customer Revenue   = Net Revenue from those customers, within the window
-- The Python side runs each query once per window: full (1 .. 99999999),
-- CY (20250701 .. 20260630), PY (20240701 .. 20250630). Bounds bind as $lo / $hi.
-- Bare table names resolve to the per-parquet views created by utils.duck().

-- name: first_order_view
-- Each customer's first-ever non-cancelled order date.
CREATE OR REPLACE VIEW first_order AS
SELECT customer_key, MIN(order_date_key) AS first_key
FROM fact_orders
WHERE NOT is_cancelled
GROUP BY 1;

-- name: spend
SELECT SUM(cost_usd)
FROM fact_marketing_spend
WHERE date_key BETWEEN $lo AND $hi;

-- name: new_customers
SELECT COUNT(DISTINCT o.customer_key)
FROM fact_orders o
JOIN first_order f USING (customer_key)
WHERE NOT o.is_cancelled
  AND o.order_date_key BETWEEN $lo AND $hi
  AND f.first_key      BETWEEN $lo AND $hi;

-- name: net_revenue
SELECT SUM(net_amount_usd - refund_amount_usd)
FROM fact_order_lines
WHERE order_status <> 'cancelled' AND order_date_key BETWEEN $lo AND $hi;

-- name: new_revenue
SELECT SUM(ol.net_amount_usd - ol.refund_amount_usd)
FROM fact_order_lines ol
JOIN first_order f USING (customer_key)
WHERE ol.order_status <> 'cancelled'
  AND ol.order_date_key BETWEEN $lo AND $hi
  AND f.first_key       BETWEEN $lo AND $hi;
