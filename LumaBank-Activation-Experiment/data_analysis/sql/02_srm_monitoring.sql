-- 02 — Daily SRM monitoring (original run). .read data_analysis/sql/_prelude.sql first.

-- daily first-assignment counts by arm, original run window
SELECT assigned_date_key, arm_key, assignment_source, COUNT(*) n
FROM fva
WHERE is_first_assignment AND assigned_date_key BETWEEN 20260706 AND 20260721
GROUP BY 1, 2, 3
ORDER BY 1, 2;

-- the pre-built, independently-computed integrity-monitor table (cross-check target)
SELECT assign_date, n_control, n_treatment, n_fallback,
       srm_p_cumulative, srm_p_trailing7, alert_state
FROM fsrm
WHERE experiment_phase = 'original'
ORDER BY assign_date;

-- first day the trailing-7d test crosses the ALERT threshold
SELECT MIN(assign_date) AS first_alert_day
FROM fsrm
WHERE experiment_phase = 'original' AND alert_state = 'alert';
