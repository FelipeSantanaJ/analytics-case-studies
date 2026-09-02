-- 04 — Guardrails.  .read data_analysis/sql/_prelude.sql first.

-- G1/G2/G3 arm means + deltas
SELECT
  AVG(CASE WHEN arm_key='control'   THEN revenue_brl_window_plus8w END) rev_c,
  AVG(CASE WHEN arm_key='treatment' THEN revenue_brl_window_plus8w END) rev_t,
  AVG(CASE WHEN arm_key='treatment' THEN revenue_brl_window_plus8w END)
- AVG(CASE WHEN arm_key='control'   THEN revenue_brl_window_plus8w END) d_rev,
  AVG(CASE WHEN arm_key='treatment' THEN net_liability_cost_brl END)
- AVG(CASE WHEN arm_key='control'   THEN net_liability_cost_brl END) d_cost,
  AVG(CASE WHEN arm_key='treatment' THEN CAST(disengaged_90d_post AS INT) END)
- AVG(CASE WHEN arm_key='control'   THEN CAST(disengaged_90d_post AS INT) END) d_diseng
FROM eo;

-- G4 redemption value per redeeming member, by arm
SELECT arm_key,
       AVG(redemption_value_brl)                       AS value_per_redeemer,
       AVG(CAST(low_cost_only AS INT))                 AS low_cost_only_share,
       COUNT(*)                                        AS n_redeemers
FROM eo WHERE redeemed_in_window
GROUP BY arm_key ORDER BY arm_key;
