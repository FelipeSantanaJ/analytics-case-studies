WITH m AS (
      SELECT month_idx,
             COUNT(*) FILTER (WHERE status='active')                         AS active,
             SUM(CASE WHEN is_voluntary_churn   THEN 1 ELSE 0 END)           AS vol,
             SUM(CASE WHEN is_involuntary_churn THEN 1 ELSE 0 END)           AS invol
      FROM fact_subscription_month GROUP BY 1),
    w AS (
      SELECT *, LAG(active) OVER (ORDER BY month_idx) AS start_active FROM m)
    SELECT month_idx, active, vol, invol, start_active,
           ROUND((vol+invol)::DOUBLE / start_active, 5) AS gross_churn,
           ROUND(vol::DOUBLE   / start_active, 5)       AS vol_churn,
           ROUND(invol::DOUBLE / start_active, 5)       AS invol_churn
    FROM w WHERE month_idx BETWEEN 12 AND 35 ORDER BY month_idx
