-- 07 — Hoarding funnel + point liability.  .read data_analysis/sql/_prelude.sql first.
WITH last_m AS (SELECT MAX(month_key) k FROM mm),
     latest AS (SELECT m.* FROM mm m, last_m WHERE m.month_key = last_m.k AND m.is_active_eom)
SELECT COALESCE(dt.tier_name, 'ALL')                                   AS segment,
       COUNT(*)                                                        AS active,
       AVG(CASE WHEN latest.balance_pts_eom >= 3500 THEN 1.0 ELSE 0 END)   AS balance_ge_flash,
       AVG(CAST(latest.has_redeemed_ever_eom AS INT))                  AS ever_redeemed
FROM latest LEFT JOIN dt ON latest.tier_key = dt.tier_key
GROUP BY ROLLUP (dt.tier_name)
ORDER BY 1;

-- points roll-forward + realised breakage
SELECT SUM(CASE WHEN txn_type='earn'   THEN points END)              AS issued,
      -SUM(CASE WHEN txn_type='redeem' THEN points END)              AS redeemed,
      -SUM(CASE WHEN txn_type='expire' THEN points END)              AS expired,
      -SUM(CASE WHEN txn_type='redeem' THEN points END)::DOUBLE
       / SUM(CASE WHEN txn_type='earn' THEN points END)              AS burn_earn_ratio,
      -SUM(CASE WHEN txn_type='expire' THEN points END)::DOUBLE
       / SUM(CASE WHEN txn_type='earn' THEN points END)              AS realised_breakage
FROM pt;

-- issued by source
SELECT s.source_name, SUM(pt.points) AS points_issued
FROM pt JOIN des s ON pt.earn_source_key = s.earn_source_key
WHERE pt.txn_type='earn'
GROUP BY 1 ORDER BY 2 DESC;
