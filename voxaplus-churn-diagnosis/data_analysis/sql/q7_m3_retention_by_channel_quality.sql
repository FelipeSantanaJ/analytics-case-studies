WITH c0 AS (SELECT subscriber_key, MIN(month_idx) AS coh
                FROM fact_subscription_month WHERE status IN ('active','churned') GROUP BY 1),
    m3 AS (SELECT DISTINCT subscriber_key FROM fact_subscription_month
           WHERE tenure_months = 3 AND status='active'),
    j AS (
      SELECT s.market,
             CASE WHEN dc.is_low_quality THEN 'low_quality' ELSE 'other' END AS chan_q,
             CASE WHEN c0.coh BETWEEN 24 AND 30 THEN 'post_shift_cohorts'
                  WHEN c0.coh BETWEEN 12 AND 23 THEN 'pre_shift_cohorts' END AS coh_era,
             (m3.subscriber_key IS NOT NULL) AS alive_m3
      FROM dim_subscriber s
      JOIN c0 USING (subscriber_key)
      LEFT JOIN dim_channel dc ON dc.channel = s.acquisition_channel
      LEFT JOIN m3 USING (subscriber_key))
    SELECT market, chan_q, coh_era,
           COUNT(*) AS cohort_n, ROUND(AVG(alive_m3::INT), 4) AS m3_retention
    FROM j WHERE coh_era IS NOT NULL GROUP BY 1,2,3 ORDER BY 1,2,3
