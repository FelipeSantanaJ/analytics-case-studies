-- 01 — Anchor: redemption rate by arm (DuckDB over the curated parquet)
-- run:  duckdb -c ".read data_analysis/sql/01_anchor.sql"   (from project root)

CREATE OR REPLACE VIEW exp AS
SELECT * FROM read_parquet('data/curated/fact_experiment_outcome.parquet');

-- pooled
SELECT arm_key,
       COUNT(*)                                  AS n,
       SUM(CAST(redeemed_in_window AS INT))      AS redeemers,
       AVG(CAST(redeemed_in_window AS INT))      AS redemption_rate
FROM exp
GROUP BY arm_key
ORDER BY arm_key;

-- pooled lift (pp)
SELECT 100 * (
         AVG(CASE WHEN arm_key='treatment' THEN CAST(redeemed_in_window AS INT) END)
       - AVG(CASE WHEN arm_key='control'   THEN CAST(redeemed_in_window AS INT) END)
       ) AS pooled_lift_pp
FROM exp;

-- by stratum x arm
SELECT stratum, arm_key,
       COUNT(*)                             AS n,
       AVG(CAST(redeemed_in_window AS INT)) AS redemption_rate
FROM exp
GROUP BY stratum, arm_key
ORDER BY stratum, arm_key;

-- per-stratum lift (pp), tier order Blue<Silver<Gold<Platinum
SELECT stratum,
       100 * (
         AVG(CASE WHEN arm_key='treatment' THEN CAST(redeemed_in_window AS INT) END)
       - AVG(CASE WHEN arm_key='control'   THEN CAST(redeemed_in_window AS INT) END)
       ) AS lift_pp
FROM exp
GROUP BY stratum
ORDER BY CASE stratum WHEN 'Blue' THEN 1 WHEN 'Silver' THEN 2
                      WHEN 'Gold' THEN 3 WHEN 'Platinum' THEN 4 END;
