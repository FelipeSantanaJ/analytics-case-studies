WITH b AS (
      SELECT market, method, month_idx,
             COUNT(*) FILTER (WHERE NOT is_dunning) AS first_attempts,
             COUNT(*) FILTER (WHERE NOT is_dunning AND status='failed') AS first_fail,
             COUNT(*) FILTER (WHERE is_dunning) AS dunning_attempts,
             COUNT(*) FILTER (WHERE is_dunning AND status='approved') AS dunning_recovered
      FROM fact_billing_attempt WHERE market IS NOT NULL GROUP BY 1,2,3)
    SELECT market,
           CASE WHEN month_idx BETWEEN 24 AND 32 THEN 'pre_shift'
                WHEN month_idx BETWEEN 33 AND 35 THEN 'peak' END AS period,
           ROUND(SUM(first_fail)::DOUBLE / NULLIF(SUM(first_attempts),0), 4)          AS payment_failure_rate,
           ROUND(SUM(dunning_recovered)::DOUBLE / NULLIF(SUM(dunning_attempts),0), 4) AS dunning_recovery_rate
    FROM b WHERE month_idx BETWEEN 24 AND 35
    GROUP BY 1,2 HAVING period IS NOT NULL ORDER BY 1,2
