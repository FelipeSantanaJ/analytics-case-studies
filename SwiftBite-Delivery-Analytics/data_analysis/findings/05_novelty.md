# 05 — Novelty / decay: does the lift fade?

**Question.** Is the fulfillment lift a durable operating change, or a launch bump
that decays as couriers stop reacting to the "surge zone" push?

**Method (both tracks).** From `fact_experiment_zone_block_week` (zone × experiment
week × peak hour-block): the weekly treated-minus-control fulfillment lift; an OLS
of that weekly lift on week number (slope test); the week-1 lift vs the settled
(weeks 8–10) lift.

**Evidence** (`outputs/tables/05_weekly_lift.csv`, `05_decay.csv`,
`outputs/figures/05_novelty.png`).

| Week | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 |
|---|---|---|---|---|---|---|---|---|---|---|
| Lift (pp) | +1.59 | −0.17 | −0.27 | −0.17 | −1.77 | −0.72 | +0.20 | −1.47 | +0.76 | +0.48 |

Slope **−0.045 pp/week** (p = 0.71 — not significant). Week-1 lift **+1.59 pp**;
weeks 8–10 mean **≈ 0 pp**.

**Conclusion.** There is **no statistically detectable decay trend** — but the
weekly series is very thin (each week is ~6 zones × ~4 peak blocks per arm), so the
week-to-week lift swings by ±1–2 pp on noise alone and the settled estimate is
unreliable. Plan on the **pooled +1.87 pp from `03`** (which uses all 840
zone-days); the weekly series is too noisy to either
confirm a launch bump or rule one out. If the incentive were ever restructured and
re-run, the design should carry more zone-days per week to resolve this.

**Limitations.** The block-week grain trades power for a time axis; the primary
estimate does not depend on it.
