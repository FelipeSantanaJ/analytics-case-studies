-- 02_growth_decomposition.sql  (DuckDB dialect)
-- Finding 02 - organic vs expansion growth. Comparable base = US (dim_market.is_comparable_base,
-- the only market live for the whole PY+CY span); expansion = UK + DE + BR.
-- Net Revenue (USD) = SUM(net_amount_usd) - SUM(refund_amount_usd), order_status <> 'cancelled'.
-- Fiscal windows (docs/01 section 1), as order_date_key / month_date_key integers (yyyymmdd):
--   PY = 2024-07-01 .. 2025-06-30   ->  20240701 .. 20250630
--   CY = 2025-07-01 .. 2026-06-30   ->  20250701 .. 20260630
-- Bare table names resolve to the per-parquet views created by utils.duck().

-- name: piv
-- Net Revenue by market, PY vs CY.
WITH ol AS (
    SELECT m.market_name, m.is_comparable_base,
           CASE WHEN ol.order_date_key BETWEEN 20240701 AND 20250630 THEN 'PY'
                WHEN ol.order_date_key BETWEEN 20250701 AND 20260630 THEN 'CY' END AS period,
           ol.net_amount_usd - ol.refund_amount_usd AS nr
    FROM fact_order_lines ol
    JOIN dim_market m ON m.market_key = ol.market_key
    WHERE ol.order_status <> 'cancelled'
)
SELECT market_name,
       SUM(nr) FILTER (WHERE period = 'PY') AS py,
       SUM(nr) FILTER (WHERE period = 'CY') AS cy
FROM ol
GROUP BY 1
ORDER BY 1;

-- name: comp
-- Comparable-base vs total Net Revenue, PY and CY.
WITH ol AS (
    SELECT m.is_comparable_base,
           CASE WHEN ol.order_date_key BETWEEN 20240701 AND 20250630 THEN 'PY'
                WHEN ol.order_date_key BETWEEN 20250701 AND 20260630 THEN 'CY' END AS period,
           ol.net_amount_usd - ol.refund_amount_usd AS nr
    FROM fact_order_lines ol
    JOIN dim_market m ON m.market_key = ol.market_key
    WHERE ol.order_status <> 'cancelled'
)
SELECT
    SUM(nr) FILTER (WHERE is_comparable_base AND period = 'CY') AS comp_cy,
    SUM(nr) FILTER (WHERE is_comparable_base AND period = 'PY') AS comp_py,
    SUM(nr) FILTER (WHERE period = 'CY')                        AS total_cy,
    SUM(nr) FILTER (WHERE period = 'PY')                        AS total_py
FROM ol;

-- name: plan_total
-- CY plan total for Net Revenue (fact_target, metric = 'Net Revenue').
SELECT SUM(target_value)
FROM fact_target
WHERE metric = 'Net Revenue'
  AND month_date_key BETWEEN 20250701 AND 20260630;

-- name: us_monthly
-- US actual vs plan Net Revenue, one row per CY month. Feeds the test of whether the
-- -2.4% annual US-vs-plan gap is a consistent monthly shortfall or a couple of bad months.
WITH actual_m AS (
    SELECT d.month_year, SUM(ol.net_amount_usd - ol.refund_amount_usd) AS actual
    FROM fact_order_lines ol
    JOIN dim_market m ON m.market_key = ol.market_key
    JOIN dim_date d   ON d.date_key   = ol.order_date_key
    WHERE ol.order_status <> 'cancelled' AND m.market_id = 'US'
      AND ol.order_date_key BETWEEN 20250701 AND 20260630
    GROUP BY 1
),
plan_m AS (
    SELECT d.month_year, SUM(t.target_value) AS plan
    FROM fact_target t
    JOIN dim_market m ON m.market_key = t.market_key
    JOIN dim_date d   ON d.date_key   = t.month_date_key
    WHERE t.metric = 'Net Revenue' AND m.market_id = 'US'
      AND t.month_date_key BETWEEN 20250701 AND 20260630
    GROUP BY 1
)
SELECT a.month_year, a.actual, p.plan, a.actual / p.plan - 1 AS attain_pct
FROM actual_m a
JOIN plan_m p USING (month_year)
ORDER BY a.month_year;
