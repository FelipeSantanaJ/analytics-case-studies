-- 06 — Heterogeneity by baseline supply-stress tier.
SELECT tier,
       COUNT(DISTINCT zone_key) n_zone, COUNT(*) n_zone_day,
       100*AVG(fulfillment_rate) FILTER (WHERE treat=0) control_pct,
       100*AVG(fulfillment_rate) FILTER (WHERE treat=1) treatment_pct,
       100*(AVG(fulfillment_rate) FILTER (WHERE treat=1)
          - AVG(fulfillment_rate) FILTER (WHERE treat=0)) effect_pp
FROM zd GROUP BY tier ORDER BY tier;
-- (the arm x tier interaction Wald / nested-F test is in the Python track)
