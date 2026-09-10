# 06 — Heterogeneity: does it work everywhere, or only where supply is short?

**Question.** Is the fulfillment effect the same across the baseline supply-stress
tiers (short / balanced / long), or concentrated where there is unmet demand to
recover?

**Method (both tracks).** Per-tier fulfillment effect with cluster-robust (by zone)
CIs. A formal **arm × tier interaction test**: OLS
`fulfillment_rate ~ treat * C(tier)` (long = reference) with cluster-robust SEs — a
Wald test on the two interaction terms — cross-checked with a nested-model F. A
forest plot.

**Evidence** (`outputs/tables/06_per_tier.csv`, `06_interaction.csv`,
`outputs/figures/06_forest.png`).

| Tier | Zones | Control | Treatment | Effect | 95% CI | p |
|---|---|---|---|---|---|---|
| **short** | 6 | 94.44% | 96.73% | **+2.29 pp** | [+1.54, +3.04] | 2×10⁻⁹ |
| **balanced** | 2 | 95.62% | 98.05% | **+2.43 pp** | [+0.69, +4.18] | 0.006 |
| **long** | 4 | 97.78% | 98.72% | **+0.94 pp** | [+0.36, +1.53] | 0.001 |

Arm × tier interaction: cluster-robust Wald **χ² = 10.98, p = 0.0041**; nested-model
F = 1.95, p = 0.14 (the two disagree — expected with 12 clusters and a 2-parameter
Wald; the per-tier CIs are the cleaner evidence).

**Conclusion.** The effect is **real in all three tiers but roughly 2.5× larger
where supply is short or balanced** (~+2.3–2.4 pp) than where it is already long
(~+0.9 pp). The long-tier CI [+0.36, +1.53] does not overlap the short-tier CI
[+1.54, +3.04] — so "short > long" is clear even though the omnibus interaction test
is borderline. Operationally: the incentive buys the most liquidity exactly where
the marketplace needs it, and near-nothing in the well-supplied zones — where it is
**pure cost** (`04` G1).

**Limitations.** Only 2 balanced-tier zones, so that estimate is wide. The tier
labels are themselves derived from months 1–15 liquidity (`dim_zone`), not assigned.
