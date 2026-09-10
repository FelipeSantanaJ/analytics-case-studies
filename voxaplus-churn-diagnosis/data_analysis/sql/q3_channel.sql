WITH m AS (
          SELECT acquisition_channel AS grp, month_idx,
                 COUNT(*) FILTER (WHERE status='active') AS active,
                 SUM(CASE WHEN is_voluntary_churn OR is_involuntary_churn THEN 1 ELSE 0 END) AS churned
          FROM sm GROUP BY 1,2),
        r AS (SELECT grp, month_idx,
                     churned::DOUBLE / LAG(active) OVER (PARTITION BY grp ORDER BY month_idx) AS gc
              FROM m)
        SELECT 'channel' AS cut, grp,
               ROUND(AVG(gc) FILTER (WHERE month_idx BETWEEN 24 AND 32), 5) AS pre_shift,
               ROUND(AVG(gc) FILTER (WHERE month_idx BETWEEN 33 AND 35), 5) AS peak
        FROM r GROUP BY 1,2
