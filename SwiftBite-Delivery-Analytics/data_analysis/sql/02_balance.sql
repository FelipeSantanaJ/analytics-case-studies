-- 02 — Randomisation & balance.
-- sample-ratio: treated vs control counts (should be exactly 50/50 by design)
SELECT tier, is_weekend, SUM(treat) n_treat, COUNT(*)-SUM(treat) n_ctrl
FROM zd GROUP BY GROUPING SETS ((), (tier), (is_weekend), (tier, is_weekend))
ORDER BY tier, is_weekend;

-- covariate SMD (treatment - control) / pooled sd, on the frozen pre-period covariates
SELECT 'pre_fulfillment_rate' cov,
       (AVG(pre_fulfillment_rate) FILTER (WHERE treat=1)
      - AVG(pre_fulfillment_rate) FILTER (WHERE treat=0))
     / SQRT((VAR_SAMP(pre_fulfillment_rate) FILTER (WHERE treat=1)
           + VAR_SAMP(pre_fulfillment_rate) FILTER (WHERE treat=0))/2) smd
FROM zd;
