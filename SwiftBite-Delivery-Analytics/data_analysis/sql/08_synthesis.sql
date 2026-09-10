-- 08 — Synthesis: the numbers the recommendation rests on (see findings/08).
SELECT
  100*(AVG(fulfillment_rate) FILTER (WHERE treat=1)
     - AVG(fulfillment_rate) FILTER (WHERE treat=0))            fulfillment_lift_pp,
  AVG(eta_p90_min) FILTER (WHERE treat=1)
    - AVG(eta_p90_min) FILTER (WHERE treat=0)                   eta_p90_lift_min,
  100*(AVG(cancel_no_courier_rate) FILTER (WHERE treat=1)
     - AVG(cancel_no_courier_rate) FILTER (WHERE treat=0))      no_courier_lift_pp,
  SUM(incentive_spend_brl) FILTER (WHERE treat=1)               incentive_spend
FROM zd;
