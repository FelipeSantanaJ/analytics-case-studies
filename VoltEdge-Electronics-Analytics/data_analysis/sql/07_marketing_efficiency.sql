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

-- name: monthly_panel
-- One row per month in the 24-month extract window ($py_lo..$py_hi = PY, ($py_hi+1)..$cy_hi
-- = CY): spend and new-customer count (customer attributed to the calendar month of their
-- first-ever order). dim_date.yoy_period is not used here -- it is flagged for a calendar
-- that extends past the extract window, which would double-count calendar months when
-- paired below. Feeds the paired PY-vs-CY CAC test and the spend -> new-customer elasticity.
WITH months AS (
  SELECT DISTINCT month_year, month,
         CASE WHEN date_key <= $py_hi THEN 'PY' ELSE 'CY' END AS yoy_period
  FROM dim_date
  WHERE date_key BETWEEN $py_lo AND $cy_hi
),
spend_m AS (
  SELECT d.month_year, SUM(ms.cost_usd) AS spend
  FROM fact_marketing_spend ms
  JOIN dim_date d ON d.date_key = ms.date_key
  WHERE d.date_key BETWEEN $py_lo AND $cy_hi
  GROUP BY 1
),
newc_m AS (
  SELECT d.month_year, COUNT(DISTINCT f.customer_key) AS new_customers
  FROM first_order f
  JOIN dim_date d ON d.date_key = f.first_key
  WHERE d.date_key BETWEEN $py_lo AND $cy_hi
  GROUP BY 1
)
SELECT m.month_year, m.month, m.yoy_period,
       COALESCE(s.spend, 0) AS spend, COALESCE(n.new_customers, 0) AS new_customers
FROM months m
LEFT JOIN spend_m s ON s.month_year = m.month_year
LEFT JOIN newc_m n ON n.month_year = m.month_year
ORDER BY m.month_year;
