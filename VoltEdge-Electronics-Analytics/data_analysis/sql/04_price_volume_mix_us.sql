-- 04_price_volume_mix_us.sql  (DuckDB dialect)
-- Finding 04 - Price / Volume / Mix decomposition of the US like-for-like growth (docs/06 section 07).
-- Scope: dim_market.is_comparable_base = TRUE (United States), order_status <> 'cancelled'.
-- Units come from product lines only (line_type = 'product'); revenue is gross_amount_usd.
-- The Python side aggregates by category once per window: CY (20250701 .. 20260630) and
-- PY (20240701 .. 20250630). Window bounds are bound as $lo / $hi at execution time.
-- Bare table names resolve to the per-parquet views created by utils.duck().

-- name: base_view
-- Comparable-base (US) order lines with category attached; reused by the by_cat query.
CREATE OR REPLACE VIEW base AS
SELECT p.category, ol.order_date_key, ol.line_type, ol.quantity, ol.gross_amount_usd
FROM fact_order_lines ol
JOIN dim_market m  ON m.market_key  = ol.market_key
JOIN dim_product p ON p.product_key = ol.product_key
WHERE ol.order_status <> 'cancelled' AND m.is_comparable_base;

-- name: by_cat
-- Gross revenue and product units by category, for one window.
SELECT category,
       SUM(gross_amount_usd) AS gross,
       SUM(CASE WHEN line_type = 'product' THEN quantity ELSE 0 END) AS units
FROM base
WHERE order_date_key BETWEEN $lo AND $hi
GROUP BY 1;
