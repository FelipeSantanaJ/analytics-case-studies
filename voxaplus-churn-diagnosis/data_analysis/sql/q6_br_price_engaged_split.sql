WITH br AS (
      SELECT sm.subscriber_key, sm.month_idx, sm.status, sm.sub_current_tier,
             (sm.is_voluntary_churn OR sm.is_involuntary_churn) AS churned,
             COALESCE(em.below_healthy_engagement, TRUE) AS disengaged
      FROM sm LEFT JOIN fact_engagement_month em
             ON em.subscriber_key = sm.subscriber_key AND em.month_idx = sm.month_idx
      WHERE sm.sub_market = 'BR' AND sm.sub_current_tier IN ('Standard','Premium')),
    m AS (
      SELECT disengaged, month_idx,
             COUNT(*) FILTER (WHERE status='active') AS active,
             SUM(CASE WHEN churned THEN 1 ELSE 0 END) AS churned
      FROM br GROUP BY 1,2),
    w AS (SELECT *, LAG(active) OVER (PARTITION BY disengaged ORDER BY month_idx) AS start_active FROM m)
    SELECT disengaged, month_idx, ROUND(churned::DOUBLE / start_active, 5) AS gc
    FROM w WHERE month_idx BETWEEN 26 AND 35 ORDER BY 1,2
