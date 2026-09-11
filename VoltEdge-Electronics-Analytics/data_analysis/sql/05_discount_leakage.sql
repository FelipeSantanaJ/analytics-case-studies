-- 05_discount_leakage.sql  (DuckDB dialect)
-- Finding 05 - discount leakage (docs/06 section 05):
--   Discount Rate % = SUM(discount_amount_usd) / SUM(gross_amount_usd), order_status <> 'cancelled'
-- Cuts: full window, CY vs PY, promo vs non-promo days (dim_date.is_promo_period), by category.
-- CY = 20250701 .. 20260630, PY = 20240701 .. 20250630; the fiscal window is bound as $lo / $hi.
-- Bare table names resolve to the per-parquet views created by utils.duck().

-- name: base_view
-- Non-cancelled order lines with promo flag / promo name / category attached.
CREATE OR REPLACE VIEW b AS
SELECT ol.order_date_key, ol.gross_amount_usd, ol.discount_amount_usd, ol.quantity,
       d.is_promo_period,
       COALESCE(NULLIF(d.promo_name, ''), '(no promo)') AS promo_name,
       p.category
FROM fact_order_lines ol
JOIN dim_date d       ON d.date_key    = ol.order_date_key
LEFT JOIN dim_product p ON p.product_key = ol.product_key
WHERE ol.order_status <> 'cancelled';

-- name: rate_full
-- Gross revenue and discounts over the whole window.
SELECT SUM(gross_amount_usd) AS g, SUM(discount_amount_usd) AS d
FROM b;

-- name: rate_window
-- Gross revenue and discounts for one fiscal-year window.
SELECT SUM(gross_amount_usd) AS g, SUM(discount_amount_usd) AS d
FROM b
WHERE order_date_key BETWEEN $lo AND $hi;

-- name: rate_promo
-- Gross revenue and discounts on promo-period days.
SELECT SUM(gross_amount_usd) AS g, SUM(discount_amount_usd) AS d
FROM b
WHERE is_promo_period;

-- name: rate_nonpromo
-- Gross revenue and discounts on non-promo days.
SELECT SUM(gross_amount_usd) AS g, SUM(discount_amount_usd) AS d
FROM b
WHERE NOT is_promo_period;

-- name: by_cat
-- Discount rate by category, worst first.
SELECT category,
       SUM(gross_amount_usd) AS g,
       SUM(discount_amount_usd) AS d,
       SUM(discount_amount_usd) / SUM(gross_amount_usd) AS rate
FROM b
GROUP BY 1
ORDER BY rate DESC;

-- name: daily_gp
-- One row per calendar day: gross profit (net of refunds and COGS), promo flag,
-- and calendar month (1-12, pooling both fiscal years) for the seasonality control.
-- Feeds the promo-day P&L significance test and the month-adjusted regression.
SELECT ol.order_date_key AS day,
       d.is_promo_period,
       d.month,
       SUM(ol.net_amount_usd - ol.refund_amount_usd - ol.cogs_usd) AS gp
FROM fact_order_lines ol
JOIN dim_date d ON d.date_key = ol.order_date_key
WHERE ol.order_status <> 'cancelled'
GROUP BY 1, 2, 3;
