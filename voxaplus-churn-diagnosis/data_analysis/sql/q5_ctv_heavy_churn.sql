WITH tagged AS (
      SELECT s.*, (primary_device_family IN ('smart_tv','streaming_stick','console')) AS ctv_heavy
      FROM sm s),
    m AS (
      SELECT ctv_heavy, month_idx,
             COUNT(*) FILTER (WHERE status='active') AS active,
             SUM(CASE WHEN is_voluntary_churn OR is_involuntary_churn THEN 1 ELSE 0 END) AS churned
      FROM tagged GROUP BY 1,2),
    r AS (SELECT ctv_heavy, month_idx,
                 churned::DOUBLE / LAG(active) OVER (PARTITION BY ctv_heavy ORDER BY month_idx) AS gc
          FROM m)
    SELECT ctv_heavy,
           ROUND(AVG(gc) FILTER (WHERE month_idx BETWEEN 24 AND 32),5) AS pre_shift,
           ROUND(AVG(gc) FILTER (WHERE month_idx BETWEEN 33 AND 35),5) AS peak
    FROM r GROUP BY 1 ORDER BY 1
