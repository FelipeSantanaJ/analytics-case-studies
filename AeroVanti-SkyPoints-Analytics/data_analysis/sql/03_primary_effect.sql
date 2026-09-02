-- 03 — Primary metric.  .read data_analysis/sql/_prelude.sql first.

-- pooled redemptions / n by arm (feed the two-proportion z-test)
SELECT SUM(CASE WHEN arm_key='control'   THEN CAST(redeemed_in_window AS INT) END) x1,
       SUM(CASE WHEN arm_key='control'   THEN 1 END)                                n1,
       SUM(CASE WHEN arm_key='treatment' THEN CAST(redeemed_in_window AS INT) END) x2,
       SUM(CASE WHEN arm_key='treatment' THEN 1 END)                                n2
FROM eo;

-- per-stratum control / treatment rate, lift and Wald SE
SELECT stratum,
       AVG(CASE WHEN arm_key='control'   THEN CAST(redeemed_in_window AS INT) END) p1,
       AVG(CASE WHEN arm_key='treatment' THEN CAST(redeemed_in_window AS INT) END) p2,
       100*(AVG(CASE WHEN arm_key='treatment' THEN CAST(redeemed_in_window AS INT) END)
          - AVG(CASE WHEN arm_key='control'   THEN CAST(redeemed_in_window AS INT) END)) lift_pp,
       COUNT(*)/2 AS n_per_arm
FROM eo GROUP BY stratum
ORDER BY CASE stratum WHEN 'Blue' THEN 1 WHEN 'Silver' THEN 2 WHEN 'Gold' THEN 3 ELSE 4 END;

-- post-stratification weights: design (sample) vs population (68/20/9/3)
SELECT stratum,
       COUNT(*)::DOUBLE / (SELECT COUNT(*) FROM eo) AS w_design,
       CASE stratum WHEN 'Blue' THEN 0.68 WHEN 'Silver' THEN 0.20
                    WHEN 'Gold' THEN 0.09 ELSE 0.03 END AS w_pop
FROM eo GROUP BY stratum;
