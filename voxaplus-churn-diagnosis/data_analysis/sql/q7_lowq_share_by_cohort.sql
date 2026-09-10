WITH n AS (
      SELECT s.market, s.first_paid_month_idx AS coh,
             COUNT(*) AS new_subs,
             SUM(CASE WHEN c.is_low_quality THEN 1 ELSE 0 END) AS lowq
      FROM dim_subscriber s LEFT JOIN dim_channel c ON c.channel = s.acquisition_channel
      GROUP BY 1,2)
    SELECT market, coh, new_subs,
           ROUND(lowq::DOUBLE / new_subs, 4) AS lowq_share
    FROM n WHERE coh BETWEEN 12 AND 35 ORDER BY 1,2
