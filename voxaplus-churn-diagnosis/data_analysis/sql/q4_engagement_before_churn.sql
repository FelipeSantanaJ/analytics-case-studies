WITH e AS (SELECT subscriber_key, month_idx, streamed_hours, below_healthy_engagement
               FROM fact_engagement_month),
    churn AS (SELECT subscriber_key, month_idx AS cm
              FROM fact_subscription_month WHERE is_voluntary_churn),
    j AS (
      SELECT c.cm,
             MAX(CASE WHEN e.month_idx = c.cm     THEN e.streamed_hours END) AS h_m0,
             MAX(CASE WHEN e.month_idx = c.cm - 1 THEN e.streamed_hours END) AS h_m1,
             MAX(CASE WHEN e.month_idx = c.cm - 2 THEN e.streamed_hours END) AS h_m2,
             MAX(CASE WHEN e.month_idx = c.cm - 1 THEN e.below_healthy_engagement::INT END) AS bh_m1
      FROM churn c LEFT JOIN e ON e.subscriber_key = c.subscriber_key
      GROUP BY c.subscriber_key, c.cm)
    SELECT CASE WHEN cm BETWEEN 24 AND 32 THEN 'pre_shift'
                WHEN cm BETWEEN 33 AND 35 THEN 'peak' ELSE 'other' END AS period,
           COUNT(*)                          AS churners,
           ROUND(AVG(h_m2), 2)               AS avg_hours_m_minus_2,
           ROUND(AVG(h_m1), 2)               AS avg_hours_m_minus_1,
           ROUND(AVG(h_m0), 2)               AS avg_hours_m0,
           ROUND(AVG(bh_m1), 3)              AS share_below_healthy_prior_month
    FROM j WHERE cm BETWEEN 24 AND 35 GROUP BY 1 ORDER BY 1
