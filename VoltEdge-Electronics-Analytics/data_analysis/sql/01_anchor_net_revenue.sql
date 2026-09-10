-- 01_anchor_net_revenue.sql  (DuckDB dialect)
-- Decision: none yet - this is the dual-track anchor on a known number.
-- Audience: the analyst. Reproduce Net Revenue (USD) per docs/06_dax_measures.md:
--   Net Revenue (USD) = Gross Sales (USD) - Returns (USD)
--   Gross Sales (USD) = SUM(fact_order_lines.net_amount_usd)  WHERE order_status <> 'cancelled'
--   Returns (USD)     = SUM(fact_order_lines.refund_amount_usd) WHERE order_status <> 'cancelled'
-- Grain of fact_order_lines: one row per order line (order x product) or a warranty add-on line.

-- Full 24-month window --------------------------------------------------------
SELECT
    'total_window'                                        AS scope,
    COUNT(*)                                              AS order_lines,
    COUNT(DISTINCT order_id)                              AS orders,
    ROUND(SUM(net_amount_usd), 2)                         AS gross_sales_usd,
    ROUND(SUM(refund_amount_usd), 2)                      AS returns_usd,
    ROUND(SUM(net_amount_usd) - SUM(refund_amount_usd), 2) AS net_revenue_usd
FROM fact_order_lines
WHERE order_status <> 'cancelled';

-- Split by fiscal year (CY = 2025-07-01..2026-06-30, PY = 2024-07-01..2025-06-30)
SELECT
    CASE WHEN d.date >= DATE '2025-07-01' THEN 'CY' ELSE 'PY' END AS yr,
    ROUND(SUM(ol.net_amount_usd) - SUM(ol.refund_amount_usd), 2)  AS net_revenue_usd,
    COUNT(DISTINCT ol.order_id)                                   AS orders
FROM fact_order_lines ol
JOIN dim_date d ON d.date_key = ol.order_date_key
WHERE ol.order_status <> 'cancelled'
GROUP BY 1
ORDER BY 1;

-- By market -----------------------------------------------------------------
SELECT
    m.market_name,
    ROUND(SUM(ol.net_amount_usd) - SUM(ol.refund_amount_usd), 2) AS net_revenue_usd,
    COUNT(DISTINCT ol.order_id)                                  AS orders
FROM fact_order_lines ol
JOIN dim_market m ON m.market_key = ol.market_key
WHERE ol.order_status <> 'cancelled'
GROUP BY 1
ORDER BY net_revenue_usd DESC;
