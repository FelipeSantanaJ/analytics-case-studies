# Voxa+ — SQL vs Python parity report

Every analytical result is computed independently in DuckDB SQL and in pandas; the two must agree within tolerance before the number becomes a finding.

| Question | Result | Rows | Value columns | Detail |
|---|---|--:|---|---|
| Q1 churn trend | ✅ pass | 24 | active, vol, invol, start_active, gross_churn, vol_churn, invol_churn | exact |
| Q2 churn by market | ✅ pass | 48 | gross_churn | exact |
| Q3 cohort cuts | ✅ pass | 16 | pre_shift, peak | exact |
| Q4 engagement before churn | ✅ pass | 2 | churners, avg_hours_m_minus_2, avg_hours_m_minus_1, avg_hours_m0, share_below_healthy_prior_month | exact |
| Q5 QoE by device | ✅ pass | 30 | vsf_rate, pberr_rate | exact |
| Q5 CTV-heavy churn | ✅ pass | 2 | pre_shift, peak | exact |
| Q6 BR price engaged/disengaged | ✅ pass | 20 | gc | exact |
| Q7 low-q channel share | ✅ pass | 69 | new_subs, lowq_share | exact |
| Q7 M3 retention by channel quality | ✅ pass | 12 | cohort_n, m3_retention | exact |
| Q8 payments | ✅ pass | 6 | payment_failure_rate, dunning_recovery_rate | exact |
| Q8 involuntary by market | ✅ pass | 3 | invol_pre, invol_peak | exact |
| Q9 financial | ✅ pass | 1 |  | exact |
| Q9 excess churn | ✅ pass | 1 |  | exact |
| Q10 driver decomposition | ✅ pass | 3 | peak_voluntary_churn, share_f1_ctv, share_f2_price, share_f3_lowq, share_none | exact |

**14/14 checks pass.**