-- 04 — Decision analysis. .read data_analysis/sql/_prelude.sql first.

-- Option 1 (truncate): pre-deploy signups only
SELECT COUNT(*) n, SUM(CASE WHEN contaminated_flag THEN 1 ELSE 0 END) n_still_contaminated
FROM fa
WHERE experiment_cohort = 'pre_deploy';

-- Option 2 (exclude contaminated + fallback-sourced), broad/auditable reading
SELECT COUNT(*) n
FROM fa
WHERE experiment_cohort IN ('pre_deploy', 'post_deploy')
  AND NOT contaminated_flag
  AND user_key NOT IN (SELECT DISTINCT user_key FROM fva WHERE assignment_source = 'fallback');

-- Option 2 residual composition check: region mix, kept vs excluded
WITH keep AS (
  SELECT user_key FROM fa
  WHERE experiment_cohort IN ('pre_deploy', 'post_deploy') AND NOT contaminated_flag
    AND user_key NOT IN (SELECT DISTINCT user_key FROM fva WHERE assignment_source = 'fallback')
)
SELECT g.macro_region,
       SUM(CASE WHEN k.user_key IS NOT NULL THEN 1 ELSE 0 END) AS n_kept,
       SUM(CASE WHEN k.user_key IS NULL THEN 1 ELSE 0 END) AS n_excluded
FROM fa f
JOIN dreg g ON f.region_key = g.region_key
LEFT JOIN keep k ON f.user_key = k.user_key
WHERE f.experiment_cohort IN ('pre_deploy', 'post_deploy')
GROUP BY 1;
