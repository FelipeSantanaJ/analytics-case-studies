-- 01 — Setup & pre-registration. .read data_analysis/sql/_prelude.sql first.

-- pre-experiment platform baseline (control-equivalent planning values)
SELECT
  COUNT(*) AS n_pre,
  AVG(CAST(day7_activated AS DOUBLE)) AS control_day7,
  AVG(CAST(kyc_submitted_flag AS DOUBLE)) AS kyc_submit_rate,
  SUM(onboarding_tickets_n) * 1000.0 / COUNT(*) AS tickets_per_1k
FROM fa
WHERE experiment_cohort = 'not_in_experiment';

-- KYC rejection rate and flagged-fraud rate baselines (of the relevant denominators)
SELECT
  SUM(CASE WHEN kyc_submitted_flag AND kyc_rejected_flag THEN 1 ELSE 0 END) * 1.0
    / NULLIF(SUM(CASE WHEN kyc_submitted_flag THEN 1 ELSE 0 END), 0) AS kyc_reject_rate,
  SUM(CASE WHEN day7_activated = 1 AND fraud_flag_30d THEN 1 ELSE 0 END) * 1.0
    / NULLIF(SUM(CASE WHEN day7_activated = 1 THEN 1 ELSE 0 END), 0) AS fraud_rate_30d
FROM fa
WHERE experiment_cohort = 'not_in_experiment';
