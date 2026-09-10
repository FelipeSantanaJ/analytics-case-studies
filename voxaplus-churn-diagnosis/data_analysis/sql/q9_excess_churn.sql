WITH act AS (
      SELECT month_idx,
             COUNT(*) FILTER (WHERE status='active') AS active,
             SUM(CASE WHEN is_voluntary_churn OR is_involuntary_churn THEN 1 ELSE 0 END) AS churned
      FROM fact_subscription_month GROUP BY 1),
    r AS (SELECT month_idx, churned,
                 LAG(active) OVER (ORDER BY month_idx) AS start_active FROM act),
    base AS (SELECT AVG(churned::DOUBLE/start_active) AS b FROM r WHERE month_idx BETWEEN 24 AND 32)
    SELECT SUM(churned - start_active*(SELECT b FROM base))::INT AS excess_churned_since_shift
    FROM r WHERE month_idx BETWEEN 33 AND 35
