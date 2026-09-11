-- 03 — Root-cause investigation. .read data_analysis/sql/_prelude.sql first.

-- the release calendar around the break
SELECT version, platform, released_at, release_type, is_cache_reset_release
FROM drel
WHERE released_at BETWEEN DATE '2026-07-01' AND DATE '2026-07-31'
ORDER BY released_at;

-- contaminated vs clean, by cohort
SELECT experiment_cohort, contaminated_flag, COUNT(*) n,
       AVG(CAST(day7_activated AS DOUBLE)) day7_rate
FROM fa
WHERE experiment_cohort IN ('pre_deploy', 'post_deploy')
GROUP BY 1, 2
ORDER BY 1, 2;

-- fallback vs primary treatment share, by macro region (the geographic bias)
SELECT f.assignment_source, g.macro_region, COUNT(*) n,
       AVG(CASE WHEN f.arm_key = 'treatment' THEN 1.0 ELSE 0 END) AS treatment_share
FROM fva f
JOIN du   u ON f.user_key = u.user_key
JOIN dreg g ON u.region_key = g.region_key
WHERE f.is_first_assignment
  AND f.assigned_date_key BETWEEN 20260716 AND 20260721
GROUP BY 1, 2
ORDER BY 1, 2;
