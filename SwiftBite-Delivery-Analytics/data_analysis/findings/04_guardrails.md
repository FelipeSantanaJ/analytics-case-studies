# 04 — Guardrails: is it safe, and does it pay?

**Question.** G1 — does the bonus clear its cost per **incremental** delivered order?
G2 — ETA. G3 — cancellation by cause. G4 — courier earnings.

**Method (both tracks).** G1: incremental delivered orders = (treated − control
fulfillment) × treated orders placed, evaluated per zone against its matched control
and **pooled** (Σ/Σ, so a zone with ≈ zero real lift contributes ≈ zero incremental
rather than a clipped near-zero denominator); zone-cluster bootstrap of the pooled
ratio (4,000 draws). Compared to the delivered-order contribution margin
(**R$ 10**, doc 01 §9.4). G2–G4: OLS with cluster-robust SE.

**Evidence** (`outputs/tables/04_g1.csv`, `04_guardrails.csv`).

**G1 — the economics.**

| | |
|---|---|
| Incentive spend (treated) | **R$ 35,820** on 7,446 delivered orders |
| Incremental delivered orders | **≈ 127** — only **1.7%** of the subsidised orders |
| **Cost per incremental order** | **R$ 281** (zone-bootstrap 95% CI [R$ 195, R$ 431]) |
| vs contribution margin R$ 10 | **fails by ~28×** — CI nowhere near the margin |
| Value destroyed per subsidised order | ≈ **R$ 4.6** (≈ the bonus itself) |

**G2–G4 (cluster-robust).**

| Guardrail | Control | Treatment | Effect | 95% CI | p |
|---|---|---|---|---|---|
| ETA p50 (min) | 36.8 | 33.9 | −2.96 | [−4.29, −1.63] | 1×10⁻⁵ |
| ETA p90 (min) | 46.2 | 40.1 | −6.06 | [−8.56, −3.57] | 2×10⁻⁶ |
| Cancellation rate | 4.25% | 2.39% | −1.87 pp | [−2.46, −1.27] | 7×10⁻¹⁰ |
| No-courier rate | 1.16% | 0.80% | −0.36 pp | [−0.64, −0.08] | 0.011 |
| Courier earnings / active hr | R$ 33.0 | R$ 41.2 | **+R$ 8.12** | [+5.64, +10.59] | 1×10⁻¹⁰ |

**Conclusion.** Every **operational** guardrail is favourable — ETA down at both
percentiles, all cancellation causes down, couriers earn materially more (the bonus
plus more trips). But **G1 fails hard**: the bonus is a **flat payment on every
delivery in the treated zone-block**, and ~98% of those orders would have been
delivered anyway, so the R$ 35,820 buys only ~127 extra orders at ~R$ 281 each
against a R$ 10 margin. The lever improves the marketplace; its **pricing** is
wrong.

**Limitations.** The contribution margin is a mid-band point value; a saved order
also has retention value not counted here, but no plausible order value closes a
28× gap. The incremental-order count is small (127) so its bootstrap CI is wide.
