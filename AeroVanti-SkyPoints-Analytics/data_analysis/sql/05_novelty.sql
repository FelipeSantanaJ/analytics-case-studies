-- 05 — Novelty.  .read data_analysis/sql/_prelude.sql first.
-- weekly redeemers per subject by arm, and the treatment-control increment
WITH n AS (SELECT arm_key, COUNT(*) na FROM eo GROUP BY 1)
SELECT w.week,
       SUM(CASE WHEN w.arm_key='control'   THEN CAST(w.redeemed_w AS INT) END)::DOUBLE
         / (SELECT na FROM n WHERE arm_key='control')   AS control_rate,
       SUM(CASE WHEN w.arm_key='treatment' THEN CAST(w.redeemed_w AS INT) END)::DOUBLE
         / (SELECT na FROM n WHERE arm_key='treatment') AS treatment_rate,
       ( SUM(CASE WHEN w.arm_key='treatment' THEN CAST(w.redeemed_w AS INT) END)::DOUBLE
           / (SELECT na FROM n WHERE arm_key='treatment')
       - SUM(CASE WHEN w.arm_key='control'   THEN CAST(w.redeemed_w AS INT) END)::DOUBLE
           / (SELECT na FROM n WHERE arm_key='control') ) * 100 AS incr_pp
FROM ew w GROUP BY w.week ORDER BY w.week;
