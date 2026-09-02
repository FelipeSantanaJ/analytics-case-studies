-- 02 — SRM + covariate balance.  .read data_analysis/sql/_prelude.sql first.

-- arm counts overall + per stratum (feed to a chi-square GoF vs 50/50)
SELECT 'ALL' AS stratum, arm_key, COUNT(*) n FROM ea GROUP BY 2
UNION ALL
SELECT stratum, arm_key, COUNT(*) n FROM ea GROUP BY 1, 2
ORDER BY 1, 2;

-- covariate means by arm + standardized mean difference
WITH s AS (
  SELECT arm_key,
         AVG(pre_earn_12m_pts)     m_earn,   STDDEV_SAMP(pre_earn_12m_pts)     s_earn,
         AVG(pre_flights_12m)      m_fl,     STDDEV_SAMP(pre_flights_12m)      s_fl,
         AVG(pre_redemptions_12m)  m_rd,     STDDEV_SAMP(pre_redemptions_12m)  s_rd,
         AVG(pre_balance_pts)      m_bal,    STDDEV_SAMP(pre_balance_pts)      s_bal,
         AVG(pre_tenure_months)    m_ten,    STDDEV_SAMP(pre_tenure_months)    s_ten,
         AVG(CAST(prior_redeemer_flag AS INT)) m_pr
  FROM ea GROUP BY arm_key)
SELECT
  (SELECT m_bal FROM s WHERE arm_key='treatment') - (SELECT m_bal FROM s WHERE arm_key='control') AS d_balance,
  (SELECT m_fl  FROM s WHERE arm_key='treatment') - (SELECT m_fl  FROM s WHERE arm_key='control') AS d_flights,
  (SELECT m_rd  FROM s WHERE arm_key='treatment') - (SELECT m_rd  FROM s WHERE arm_key='control') AS d_redemptions,
  (SELECT m_earn FROM s WHERE arm_key='treatment')- (SELECT m_earn FROM s WHERE arm_key='control') AS d_earn;
