-- 03_margin_to_breakeven.sql  (DuckDB dialect)
-- Finding 03 - the Net Revenue -> Gross Profit -> Contribution Margin walk (docs/06 section 03):
--   Gross Profit (USD)        = Net Revenue - COGS + Returns COGS Recovered
--   Total Payment Cost (USD)  = Payment Fees + Financing Cost (Interest-Free installments)
--   Contribution Margin (USD) = Gross Profit - Marketing - Shipping Cost - Total Payment Cost
-- The Python side runs this once per window: full (1 .. 99999999), CY (20250701 .. 20260630),
-- PY (20240701 .. 20250630). Window bounds are bound as $lo / $hi at execution time.
-- Bare table names resolve to the per-parquet views created by utils.duck().

-- name: walk
WITH gp AS (
    SELECT SUM(net_amount_usd - refund_amount_usd) AS nr, SUM(cogs_usd) AS cogs
    FROM fact_order_lines
    WHERE order_status <> 'cancelled' AND order_date_key BETWEEN $lo AND $hi
),
rec AS (
    SELECT SUM(cogs_recovered_usd) AS cogs_rec
    FROM fact_returns
    WHERE return_date_key BETWEEN $lo AND $hi
),
mk AS (
    SELECT SUM(cost_usd) AS mktg
    FROM fact_marketing_spend
    WHERE date_key BETWEEN $lo AND $hi
),
ord AS (
    SELECT SUM(shipping_cost_usd) AS ship, SUM(payment_fee_usd) AS payfee
    FROM fact_orders
    WHERE NOT is_cancelled AND order_date_key BETWEEN $lo AND $hi
),
fin AS (
    SELECT SUM(financing_cost_usd) AS financing
    FROM fact_payment_schedule
    WHERE installment_plan = 'Interest-Free' AND order_date_key BETWEEN $lo AND $hi
)
SELECT gp.nr, gp.cogs, rec.cogs_rec, mk.mktg, ord.ship, ord.payfee, fin.financing
FROM gp, rec, mk, ord, fin;
