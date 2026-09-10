-- 04 — Guardrails.
-- G1: incentive spend vs incremental delivered orders (pooled over zones)
WITH z AS (
  SELECT zone_key,
         SUM(incentive_spend_brl) FILTER (WHERE treat=1) spend,
         SUM(orders_placed)       FILTER (WHERE treat=1) placed_t,
         AVG(fulfillment_rate)    FILTER (WHERE treat=1) ff_t,
         AVG(fulfillment_rate)    FILTER (WHERE treat=0) ff_c
  FROM zd GROUP BY zone_key)
SELECT SUM(spend) incentive_spend,
       SUM(placed_t * (ff_t - ff_c)) incremental_orders,
       SUM(spend) / SUM(placed_t * (ff_t - ff_c)) cost_per_incremental_order
FROM z;

-- G2-G4 by arm
SELECT AVG(eta_p50_min)  FILTER (WHERE treat=1) - AVG(eta_p50_min)  FILTER (WHERE treat=0) eta_p50_eff,
       AVG(eta_p90_min)  FILTER (WHERE treat=1) - AVG(eta_p90_min)  FILTER (WHERE treat=0) eta_p90_eff,
       AVG(courier_earnings_per_active_hour_brl) FILTER (WHERE treat=1)
     - AVG(courier_earnings_per_active_hour_brl) FILTER (WHERE treat=0) earn_eff
FROM zd;
