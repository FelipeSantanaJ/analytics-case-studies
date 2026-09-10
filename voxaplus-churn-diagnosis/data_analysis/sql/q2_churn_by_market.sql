WITH m AS (
      SELECT sub_market AS market, month_idx,
             COUNT(*) FILTER (WHERE status='active')                    AS active,
             SUM(CASE WHEN is_voluntary_churn OR is_involuntary_churn THEN 1 ELSE 0 END) AS churned
      FROM sm GROUP BY 1,2),
    w AS (SELECT *, LAG(active) OVER (PARTITION BY market ORDER BY month_idx) AS start_active FROM m)
    SELECT market, month_idx, ROUND(churned::DOUBLE / start_active, 5) AS gross_churn
    FROM w WHERE month_idx BETWEEN 20 AND 35 ORDER BY market, month_idx
