-- 08 — Observational redeemer -> engagement-lapse.  .read data_analysis/sql/_prelude.sql first.
WITH ms AS (SELECT DISTINCT month_key FROM mm ORDER BY month_key),
     ref AS (SELECT month_key FROM ms ORDER BY month_key DESC LIMIT 1 OFFSET 12),
     lastm AS (SELECT MAX(month_key) k FROM mm),
     pre AS (
       SELECT member_key,
              MAX(CASE WHEN redemptions_m > 0 THEN 1 ELSE 0 END) prior_redeemer,
              MAX(tenure_months) ten
       FROM mm WHERE month_key <= (SELECT month_key FROM ref) GROUP BY member_key),
     post AS (
       SELECT member_key, SUM(flights_m) fl, SUM(redemptions_m) rd,
              SUM(flight_revenue_brl_m) fwd_rev
       FROM mm
       WHERE month_key > (SELECT month_key FROM ref) AND month_key <= (SELECT k FROM lastm)
       GROUP BY member_key)
SELECT pre.prior_redeemer,
       COUNT(*)                                                        AS n,
       AVG(CASE WHEN post.fl = 0 AND post.rd = 0 THEN 1.0 ELSE 0 END)  AS eng_lapse_rate,
       AVG(post.fwd_rev)                                               AS fwd_rev_per_member
FROM pre JOIN post USING (member_key)
WHERE pre.ten >= 6
GROUP BY 1 ORDER BY 1;
