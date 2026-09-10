WITH m AS (
          SELECT CASE WHEN tenure_months<=1 THEN '0-1' WHEN tenure_months<=6 THEN '2-6' WHEN tenure_months<=12 THEN '7-12' WHEN tenure_months<=24 THEN '13-24' ELSE '25+' END AS grp, month_idx,
                 COUNT(*) FILTER (WHERE status='active') AS active,
                 SUM(CASE WHEN is_voluntary_churn OR is_involuntary_churn THEN 1 ELSE 0 END) AS churned
          FROM sm GROUP BY 1,2),
        r AS (SELECT grp, month_idx,
                     churned::DOUBLE / LAG(active) OVER (PARTITION BY grp ORDER BY month_idx) AS gc
              FROM m)
        SELECT 'tenure_band' AS cut, grp,
               ROUND(AVG(gc) FILTER (WHERE month_idx BETWEEN 24 AND 32), 5) AS pre_shift,
               ROUND(AVG(gc) FILTER (WHERE month_idx BETWEEN 33 AND 35), 5) AS peak
        FROM r GROUP BY 1,2
