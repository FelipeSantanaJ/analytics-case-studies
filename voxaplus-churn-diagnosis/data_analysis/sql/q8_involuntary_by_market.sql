WITH m AS (
      SELECT sub_market AS market, month_idx,
             COUNT(*) FILTER (WHERE status='active') AS active,
             SUM(is_involuntary_churn::INT) AS invol
      FROM sm GROUP BY 1,2),
    r AS (SELECT market, month_idx,
                 invol::DOUBLE / NULLIF(LAG(active) OVER (PARTITION BY market ORDER BY month_idx),0) AS ic
          FROM m)
    SELECT market,
           ROUND(AVG(ic) FILTER (WHERE month_idx BETWEEN 24 AND 32),5)  AS invol_pre,
           ROUND(AVG(ic) FILTER (WHERE month_idx BETWEEN 33 AND 35),5) AS invol_peak
    FROM r GROUP BY 1 ORDER BY 1
