-- 05 — Re-run readout. .read data_analysis/sql/_prelude.sql first.

-- primary effect: Day-7 Activation by arm, clean re-run population
SELECT arm_key, COUNT(*) n, AVG(CAST(day7_activated AS DOUBLE)) day7_rate
FROM fa
WHERE in_analysis_flag
GROUP BY 1;

-- guardrail 1: KYC rejection rate by arm (of submissions)
SELECT arm_key,
       SUM(CASE WHEN kyc_rejected_flag THEN 1 ELSE 0 END) * 1.0 / COUNT(*) AS kyc_reject_rate
FROM fa
WHERE in_analysis_flag AND kyc_submitted_flag
GROUP BY 1;

-- guardrail 2: flagged-fraud rate by arm (of Day-7 activators)
SELECT arm_key,
       SUM(CASE WHEN fraud_flag_30d THEN 1 ELSE 0 END) * 1.0 / COUNT(*) AS fraud_rate
FROM fa
WHERE in_analysis_flag AND day7_activated = 1
GROUP BY 1;

-- heterogeneity: Day-7 Activation by arm x acquisition channel
SELECT c.channel_name, f.arm_key, COUNT(*) n, AVG(CAST(f.day7_activated AS DOUBLE)) day7_rate
FROM fa f
JOIN dch c ON f.channel_key = c.channel_key
WHERE f.in_analysis_flag
GROUP BY 1, 2
ORDER BY 1, 2;
