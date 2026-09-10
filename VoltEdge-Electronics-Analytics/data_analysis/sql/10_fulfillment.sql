-- 10_fulfillment.sql  (DuckDB dialect)
-- Finding 10 - fulfilment KPIs (docs/06 section 10):
--   On-Time Delivery %       = distinct on-time delivered orders / distinct delivered orders
--   Avg Delivery Days        = AVG(delivery_days) where is_delivered
--   Perfect Order Rate %     = distinct perfect orders / distinct orders
--   Shipping Cost Recovery % = SUM(shipping_fee_usd) / SUM(shipping_cost_usd)
-- Non-cancelled orders only. CY/PY, carrier and Q4 cuts stay pandas-only.
-- Bare table names resolve to the per-parquet views created by utils.duck().

-- name: o_view
CREATE OR REPLACE VIEW o AS
SELECT * FROM fact_orders WHERE NOT is_cancelled;

-- name: kpis
SELECT
    COUNT(DISTINCT order_id) AS orders,
    AVG(CASE WHEN is_delivered THEN delivery_days END) AS avg_delivery_days,
    COUNT(DISTINCT CASE WHEN is_delivered AND is_on_time THEN order_id END)::DOUBLE
        / COUNT(DISTINCT CASE WHEN is_delivered THEN order_id END) AS on_time_pct,
    COUNT(DISTINCT CASE WHEN is_perfect_order THEN order_id END)::DOUBLE
        / COUNT(DISTINCT order_id) AS perfect_order_pct,
    SUM(shipping_cost_usd) AS ship_cost,
    SUM(shipping_cost_usd) / COUNT(DISTINCT order_id) AS ship_cost_per_order,
    SUM(shipping_fee_usd) / SUM(shipping_cost_usd) AS ship_recovery_pct
FROM o;

-- name: by_market
SELECT m.market_name,
       SUM(o.shipping_cost_usd) / COUNT(DISTINCT o.order_id) AS ship_cost_per_order,
       SUM(o.shipping_fee_usd)  / SUM(o.shipping_cost_usd)   AS ship_recovery_pct,
       COUNT(DISTINCT CASE WHEN o.is_delivered AND o.is_on_time THEN o.order_id END)::DOUBLE
           / COUNT(DISTINCT CASE WHEN o.is_delivered THEN o.order_id END) AS on_time_pct
FROM o
JOIN dim_market m USING (market_key)
GROUP BY 1
ORDER BY 1;
