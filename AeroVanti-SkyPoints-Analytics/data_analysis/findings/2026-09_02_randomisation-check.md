# 02 — Randomisation check: SRM + covariate balance

**Decision it informs:** whether any measured effect can be attributed to the treatment.
**Audience:** experimentation lead, and anyone reviewing the read-out.

## Question
Did randomisation produce balanced arms — same size (no sample-ratio mismatch) and same
pre-treatment composition?

## Grain
`fact_experiment_assignment` — one row per subject, with pre-period covariates frozen at
2026-03-01.

## Hypotheses
- SRM: H₀ = 50/50 allocation within each stratum. χ² goodness-of-fit.
- Balance: |standardized mean difference| < 0.1 on each frozen covariate.

## Method (both tracks)
Arm counts overall and per stratum → χ². Covariate means by arm → SMD =
(mean_treatment − mean_control) / pooled SD. Love plot. pandas + DuckDB, parity on the arm
counts and on the treatment−control covariate deltas.

## Evidence
- **SRM:** every stratum is exactly 7,500 / 7,500 → 3,500/3,500 (Blue), 1,900/1,900
  (Silver), 1,300/1,300 (Gold), 800/800 (Platinum). χ² = 0.000, p = 1.000 everywhere.
- **Balance (SMD, treatment − control):**

  | covariate | control | treatment | SMD |
  |---|---|---|---|
  | pre 12-month earn (pts) | 10,195 | 10,192 | −0.000 |
  | pre 12-month flights | 4.28 | 4.26 | −0.003 |
  | pre 12-month redemptions | 0.432 | 0.463 | +0.039 |
  | pre balance (pts) | 12,348 | 12,066 | −0.023 |
  | pre tenure (months) | 12.81 | 12.73 | −0.016 |
  | prior-redeemer flag | 0.325 | 0.338 | +0.028 |

  **max |SMD| = 0.039** — well inside the 0.1 threshold. Figure:
  `outputs/figures/02_love_plot.png`.

## Conclusion
Randomisation is clean. There is no sample-ratio mismatch, and the arms are balanced on
every frozen pre-period covariate. This is expected: assignment used **blocked (pair-
matched) randomisation** within each tier stratum (rank subjects by a pre-period redemption-
propensity score, pair adjacent ranks, flip a coin per pair — see `docs/04` §1.5), which
balances prior behaviour by construction while keeping real assignment randomness.

## Limitations
Balance on *observed* frozen covariates does not guarantee balance on unobservables; the
blocking score covers the main ones (prior redemption, balance, earn). The 30 ineligible
late-correction rows Flesk exported were reconciled out before this check.

## Recommendation
The randomisation supports a causal reading of the effect. Proceed to the primary test.
