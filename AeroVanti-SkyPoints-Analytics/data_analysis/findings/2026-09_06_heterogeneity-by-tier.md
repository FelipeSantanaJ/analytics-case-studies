# 06 — Heterogeneity: the effect is concentrated in the lower tiers

**Decision it informs:** roll out to everyone, or only to Blue + Silver? **Audience:**
loyalty director / CFO. This is the cut the rollout decision hinges on.

## Question
Does the Flash Redemption effect differ by member tier? The prior (to test, not assume):
largest for **Blue** (structurally locked out by the 10,000-point threshold) and ~zero for
**Platinum** (already redeem freely).

## Grain
`fact_experiment_outcome` — one row per subject. Strata: Blue / Silver / Gold / Platinum.

## Method (both tracks)
1. Per-tier effect + 95% CI (two-proportion) → forest plot.
2. **Omnibus arm × tier interaction** — logistic `redeemed ~ arm * C(tier)` vs
   `redeemed ~ arm + C(tier)`, likelihood-ratio χ² test (3 df).
3. **Linear-in-tier-rank interaction** — `redeemed ~ arm * tier_rank + C(tier)`, a single-df
   directional test.
pandas + DuckDB, parity on every per-tier lift.

## Evidence
| tier | control | treatment | lift (pp) | 95% CI (pp) | p | significant |
|---|---|---|---|---|---|---|
| **Blue** | 6.1% | 9.9% | **+3.77** | [+2.50, +5.04] | 2e-8 | **yes** |
| **Silver** | 10.8% | 13.0% | **+2.16** | [+0.10, +4.22] | 0.040 | **yes (marginal)** |
| Gold | 19.4% | 21.9% | +2.54 | [−0.57, +5.65] | 0.11 | no |
| Platinum | 35.6% | 35.1% | −0.50 | [−5.19, +4.19] | 0.83 | no |

- **Interaction LR test: χ² = 17.0, df = 3, p = 0.0007** — the effect **does** differ by
  tier.
- **Linear-in-rank interaction: −0.172, p = 0.0001** — the effect (on the logit) shrinks
  monotonically from Blue to Platinum.
- Forest plot: `outputs/figures/06_forest.png`. Tables: `06_per_tier_effect.csv`,
  `06_interaction_tests.csv`.

## Conclusion
The lift is **real for Blue and Silver and absent for Gold and Platinum.** Blue members —
the segment the intervention was designed for, sitting just below the old threshold with
nowhere to spend — gain the most (+3.8 pp on a 6% base, a **+62% relative** increase).
Silver gains a smaller but significant +2.2 pp. Gold's point estimate is positive but the
CI includes zero (the stratum is underpowered even at n = 1,300/arm); Platinum shows nothing
— consistent with the prior that top-tier members already redeem whenever they want to. The
formal interaction test confirms the gradient is not noise.

## Limitations
- Gold/Platinum are **underpowered** — "not significant" means "consistent with no effect",
  not "proven zero". A dedicated Gold test would need ~3× the arm size.
- The Gold point estimate (+2.5 pp) is above the true design intent; treat the CI, not the
  point.
- Effects are on the 12-week redemption rate; the tier gradient in the *durable* effect
  (post-novelty) was not separately estimated.

## Recommendation
**Roll out Flash Redemption to Blue and Silver only.** Hold Gold and Platinum at the current
threshold — there is no evidence of benefit there, and the low-cost catalog would add reward
cash cost for tiers that already redeem. Revisit Gold with a larger, dedicated test if the
program wants a definitive answer.
