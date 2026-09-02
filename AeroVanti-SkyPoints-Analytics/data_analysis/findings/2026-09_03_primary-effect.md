# 03 — Primary metric: Flash Redemption lifts the redemption rate

**Decision it informs:** should Flash Redemption roll out at all? **Audience:** loyalty
director / CFO. **Window:** 12-week experiment, months 19–21.

## Question
Does lowering the minimum redemption threshold (10,000 → 3,500 SkyPoints) and adding a
low-cost reward catalog increase the share of members who redeem?

## Hypothesis
H₀: redemption rate is equal in the two arms. H₁: treatment > control. One-sided α = 0.05;
a two-sided 95% CI is always reported. **Planning:** control 11.0%, MDE +2.2 pp (+20%
relative), 80% power → ≈ 3,450/arm; realised design has 7,500/arm.

## Grain
`fact_experiment_outcome` — one row per subject. Primary metric = `redeemed_in_window`.

## Method (both tracks)
1. Two-proportion z-test; effect size (absolute pp, relative %, Cohen's h); 95% CI (Wald
   and Newcombe score — they agree here).
2. **Post-stratification** — re-weight the per-stratum effects to the population active-
   member tier mix (68/20/9/3). The pooled estimate is on the *oversampled* design, which
   under-weights Blue (the largest effect).
3. **Covariate-adjusted** — logistic regression `redeemed ~ arm + stratum + frozen
   covariates`; report the average marginal effect of `arm`.
pandas + DuckDB, parity on the pooled lift, the z-stat, and every per-stratum lift.

## Evidence
| | value |
|---|---|
| Control redemption rate | 12.76% (957 / 7,500) |
| Treatment redemption rate | 15.45% (1,159 / 7,500) |
| **Absolute lift** | **+2.69 pp** — 95% CI **[+1.58, +3.81] pp** |
| Relative lift | +21.1% |
| z = 4.74 · two-sided p | **2.2 × 10⁻⁶** · one-sided p 1.1 × 10⁻⁶ · Cohen's h 0.077 |
| **Post-stratified to population mix** | **+3.21 pp** — 95% CI [+2.20, +4.22] |
| Covariate-adjusted average marginal effect | +2.78 pp (logit +0.274, p = 1.0 × 10⁻⁷) |
| Achieved power at the +2.2 pp MDE | 0.974 · 80%-detectable effect ≈ +1.60 pp |

Backing table: `outputs/tables/03_primary_summary.csv`, `03_per_stratum.csv`.

## Conclusion
Flash Redemption **works.** The 12-week redemption rate rises by +2.69 pp pooled (highly
significant), and the design-weighted, post-stratified and covariate-adjusted estimates all
land in the +2.7 to +3.2 pp band. The population-weighted figure is the one to quote for a
full rollout: **≈ +3 pp** (from ~13% to ~16%). The pooled number understates it because the
oversampled design under-weights Blue, where the effect is largest.

## Limitations
- The effect is not uniform (see 06) — the pooled/post-stratified figures are averages over
  a strong tier gradient.
- Part of the 12-week lift is a launch novelty bump that decays (see 05); the durable
  effect is smaller.
- 12-week redemption is the *engagement* outcome, not a P&L outcome — the guardrails (04)
  and the liability picture (07) qualify what it is worth.

## Recommendation
On the primary metric alone, roll out. Read 04–06 before finalising *to whom* and *what to
expect*.
