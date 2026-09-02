-- 06 — Heterogeneity by tier.  .read data_analysis/sql/_prelude.sql first.
SELECT stratum,
       AVG(CASE WHEN arm_key='control'   THEN CAST(redeemed_in_window AS INT) END) control_rate,
       AVG(CASE WHEN arm_key='treatment' THEN CAST(redeemed_in_window AS INT) END) treatment_rate,
       100*(AVG(CASE WHEN arm_key='treatment' THEN CAST(redeemed_in_window AS INT) END)
          - AVG(CASE WHEN arm_key='control'   THEN CAST(redeemed_in_window AS INT) END)) lift_pp,
       COUNT(*) n
FROM eo GROUP BY stratum
ORDER BY CASE stratum WHEN 'Blue' THEN 1 WHEN 'Silver' THEN 2 WHEN 'Gold' THEN 3 ELSE 4 END;
-- (the arm x tier interaction LR test is run in Python — statsmodels logit)
