-- 09_returns.sql  (DuckDB dialect)
-- Finding 09 - returns (docs/06 section 13):
--   Return Rate %  = SUM(fact_order_lines.returned_qty) / SUM(quantity), product lines only
--   Return Value   = SUM(fact_returns.refund_amount_usd)
--   Restock Rate % = SUM(returned_qty where restocked) / SUM(returned_qty)
-- All cuts here are full-window; CY/PY splits and reason buckets stay pandas-only.
-- Bare table names resolve to the per-parquet views created by utils.duck().

-- name: return_rate_full
SELECT SUM(returned_qty)::DOUBLE / SUM(quantity)
FROM fact_order_lines
WHERE order_status <> 'cancelled' AND line_type = 'product';

-- name: return_value
SELECT SUM(refund_amount_usd)      AS refund,
       SUM(cogs_recovered_usd)     AS cogs_recovered
FROM fact_returns;

-- name: restock_rate
SELECT SUM(CASE WHEN restocked THEN returned_qty ELSE 0 END)::DOUBLE / SUM(returned_qty)
FROM fact_returns;

-- name: by_cat
SELECT p.category,
       SUM(ol.returned_qty)::DOUBLE / SUM(ol.quantity) AS rate
FROM fact_order_lines ol
JOIN dim_product p USING (product_key)
WHERE ol.order_status <> 'cancelled' AND ol.line_type = 'product'
GROUP BY 1
ORDER BY rate DESC;
