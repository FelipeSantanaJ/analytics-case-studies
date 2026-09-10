# 03 — Primary effect: does the zone-hour incentive lift fulfillment?

**Question.** Causal effect of arming the peak-block bonus on the **fulfillment
rate** (primary), and on the two co-primaries **ETA p90** and the **no-courier
cancellation rate**.

**Hypothesis.** H₀: treated = control zone-day fulfillment. H₁: treated > control.

**Method (both tracks).** Unit = zone-day (420/arm, 12 zones). Three inference
routes, all reported:
- **A** — OLS `y ~ treat` with **cluster-robust (by zone) SE** (12 clusters — a
  floor, anti-conservative);
- **B** — **randomization inference**: permute `arm` within (zone × weekday/weekend),
  3,000 draws, two-sided p;
- **C** — **wild-cluster bootstrap** (Rademacher weights on the null-model residuals,
  resampled by zone), 2,000 draws.
Plus a covariate-adjusted OLS (`pre_fulfillment_rate + pre_liquidity_ratio +
C(tier)`) for variance reduction, and the realised MDE for the design.

**Evidence** (`outputs/tables/03_primary.csv`, `03_power.csv`).

| Metric | Control | Treatment | Effect | Cluster 95% CI | Cluster p | RI p | Wild-boot 95% CI (p) |
|---|---|---|---|---|---|---|---|
| **Fulfillment rate** | 95.75% | 97.61% | **+1.87 pp** | [+1.27, +2.46] | 7×10⁻¹⁰ | **0.0003** | [+1.20, +2.55] (0.0015) |
| ETA p90 (min) | 46.2 | 40.1 | **−6.06** | [−8.56, −3.57] | 2×10⁻⁶ | 0.0003 | [−9.25, −3.01] (0.002) |
| No-courier rate | 1.16% | 0.80% | **−0.36 pp** | [−0.64, −0.08] | 0.011 | 0.031 | [−0.67, −0.04] (0.023) |

Covariate-adjusted fulfillment effect **+1.87 pp** (p = 8×10⁻¹⁰) — the pre-period
covariates are zone-level and add no precision here. Design: 420/arm, zone-day SD
0.050, ICC ≈ 0.068, design effect ≈ 5.7 → **MDE ≈ +1.6 pp** at 80% power; the
observed +1.87 pp clears it.

**Conclusion.** The incentive **causes a real, statistically robust improvement in
marketplace liquidity**: fulfillment **+1.87 pp**, ETA p90 **−6 min**, no-courier
cancels **−0.36 pp**. The effect survives cluster-robust SEs, randomization
inference and a wild-cluster bootstrap — the three routes agree, which matters with
only 12 clusters. Whether it is *worth* the bonus cost is `04`.

**Limitations.** Fulfillment starts at ~96% in control, so the primary metric is
ceiling-compressed — the effect reads more clearly on ETA p90 and no-courier rate,
which is why they are treated as co-primary. 12 clusters is few; the RI p-value
(assumption-light) is the one to anchor on.
