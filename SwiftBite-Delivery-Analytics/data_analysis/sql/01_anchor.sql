-- 01 — Anchor.  .read data_analysis/sql/_prelude.sql first.
SELECT arm, COUNT(*) n,
       AVG(fulfillment_rate)          fulfillment,
       AVG(eta_p50_min)               eta_p50,
       AVG(eta_p90_min)               eta_p90,
       AVG(cancel_no_courier_rate)    no_courier_rate,
       AVG(cancel_rate)               cancel_rate,
       AVG(courier_earnings_per_active_hour_brl) earn_per_active_hr,
       SUM(orders_placed) orders_placed, SUM(orders_delivered) orders_delivered,
       SUM(incentive_spend_brl) incentive_spend
FROM ezd GROUP BY arm ORDER BY arm;

-- naive lift by baseline supply-stress tier
SELECT tier,
       100*(AVG(fulfillment_rate) FILTER (WHERE treat=1)
          - AVG(fulfillment_rate) FILTER (WHERE treat=0)) lift_pp
FROM zd GROUP BY tier ORDER BY tier;
