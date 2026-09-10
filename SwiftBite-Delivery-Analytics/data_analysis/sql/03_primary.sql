-- 03 — Primary effect (point estimates; the SEs/CIs are cluster-robust / RI /
-- wild-cluster bootstrap in the Python track).
SELECT 'fulfillment_rate' metric,
       AVG(fulfillment_rate) FILTER (WHERE treat=0) control,
       AVG(fulfillment_rate) FILTER (WHERE treat=1) treatment,
       100*(AVG(fulfillment_rate) FILTER (WHERE treat=1)
          - AVG(fulfillment_rate) FILTER (WHERE treat=0)) effect_pp
FROM zd
UNION ALL SELECT 'eta_p90_min',
       AVG(eta_p90_min) FILTER (WHERE treat=0), AVG(eta_p90_min) FILTER (WHERE treat=1),
       AVG(eta_p90_min) FILTER (WHERE treat=1) - AVG(eta_p90_min) FILTER (WHERE treat=0)
FROM zd
UNION ALL SELECT 'no_courier_rate',
       AVG(cancel_no_courier_rate) FILTER (WHERE treat=0), AVG(cancel_no_courier_rate) FILTER (WHERE treat=1),
       100*(AVG(cancel_no_courier_rate) FILTER (WHERE treat=1)
          - AVG(cancel_no_courier_rate) FILTER (WHERE treat=0))
FROM zd;
