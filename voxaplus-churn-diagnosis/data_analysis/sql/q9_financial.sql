WITH act AS (
      SELECT month_idx,
             COUNT(*) FILTER (WHERE status='active') AS active,
             SUM(CASE WHEN status='active' THEN mrr_usd ELSE 0 END) AS mrr_usd,
             SUM(CASE WHEN is_voluntary_churn OR is_involuntary_churn THEN 1 ELSE 0 END) AS churned
      FROM fact_subscription_month GROUP BY 1),
    r AS (SELECT month_idx, active, mrr_usd,
                 churned::DOUBLE / LAG(active) OVER (ORDER BY month_idx) AS gc
          FROM act)
    SELECT
      ROUND(AVG(gc) FILTER (WHERE month_idx BETWEEN 24 AND 32),5)  AS churn_pre,
      ROUND(AVG(gc) FILTER (WHERE month_idx BETWEEN 33 AND 35),5) AS churn_peak,
      ROUND(1.0/AVG(gc) FILTER (WHERE month_idx BETWEEN 24 AND 32),1)  AS lifetime_pre_m,
      ROUND(1.0/AVG(gc) FILTER (WHERE month_idx BETWEEN 33 AND 35),1) AS lifetime_peak_m,
      ROUND(AVG(mrr_usd/NULLIF(active,0)) FILTER (WHERE month_idx BETWEEN 33 AND 35),2) AS arpu_peak,
      ROUND(AVG(mrr_usd) FILTER (WHERE month_idx BETWEEN 33 AND 35),0) AS mrr_peak
    FROM r
