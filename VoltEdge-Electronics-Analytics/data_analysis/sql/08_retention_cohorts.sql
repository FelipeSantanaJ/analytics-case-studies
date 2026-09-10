-- 08_retention_cohorts.sql  (DuckDB dialect)
-- Finding 08 - retention headline rates (docs/06 section 12):
--   Repeat Purchase Rate % = customers with >1 non-cancelled order / customers with >=1
--   Customers with Orders  = DISTINCTCOUNT(fact_orders.customer_key), is_cancelled = FALSE
-- CY window = 20250701 .. 20260630. (Cohort curves + new/returning split stay pandas-only.)
-- Bare table names resolve to the per-parquet views created by utils.duck().

-- name: repeat_rate_full
WITH opc AS (
    SELECT customer_key, COUNT(DISTINCT order_id) AS n
    FROM fact_orders
    WHERE NOT is_cancelled
    GROUP BY 1
)
SELECT SUM(CASE WHEN n > 1 THEN 1 ELSE 0 END)::DOUBLE / COUNT(*)
FROM opc;

-- name: repeat_rate_cy
WITH opc AS (
    SELECT customer_key, COUNT(DISTINCT order_id) AS n
    FROM fact_orders
    WHERE NOT is_cancelled AND order_date_key BETWEEN 20250701 AND 20260630
    GROUP BY 1
)
SELECT SUM(CASE WHEN n > 1 THEN 1 ELSE 0 END)::DOUBLE / COUNT(*)
FROM opc;

-- name: customers_with_orders
SELECT COUNT(DISTINCT customer_key)
FROM fact_orders
WHERE NOT is_cancelled;
