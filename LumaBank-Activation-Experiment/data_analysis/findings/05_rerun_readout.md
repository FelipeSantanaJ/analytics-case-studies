# 05 — Re-run readout: power recomputed, primary effect, guardrails, heterogeneity

**Decision it informs:** did the redesigned onboarding work, safely, once the experiment
is clean? **Audience:** Growth, Product, and Risk & Compliance — this is the number the
business actually acts on.

## Question
On the clean re-run (`in_analysis_flag = TRUE`: rerun cohort, never contaminated, never
touched the fallback), is the Day-7 Activation lift real, and do the fintech guardrails
hold?

## Grain
`fact_activation`, filtered to the clean re-run population — 9,254 users (4,666 control /
4,588 treatment).

## Hypotheses
Primary: H₀ = no Day-7 Activation difference between arms, two-sided α = 0.05. Guardrails:
one-sided non-inferiority — H₀ = treatment worse by ≥ the margin (KYC rejection +1.5 pp,
flagged fraud +0.5 pp); reject H₀ (establish non-inferiority) if the one-sided 95% upper
bound on the treatment − control difference is below the margin.

## Method (both tracks)
Power/MDE recomputed for the actual re-run sample (not the original 6-week planning
value); two-proportion test with a 95% CI for the primary effect; one-sided
non-inferiority tests for the two hard guardrails; a directional check on the secondary
guardrail; a formal arm × channel interaction test (logistic regression, likelihood-ratio)
for heterogeneity.

## Evidence

**Power, recomputed.** At ~4,600/arm the achievable MDE (80% power) is **2.92 pp** — worse
than the original design's 2.41 pp, exactly the cost of the deadline stated in block 04.
Matching the original design's MDE would have needed 6,722/arm.

**Primary effect.**

| | Control | Treatment |
|---|---:|---:|
| Day-7 Activation | 45.24% | 49.83% |
| n | 4,666 | 4,588 |

**Lift = +4.58 pp**, 95% CI **[+2.55, +6.62]**, z = 4.41, **p ≈ 1.0×10⁻⁵**. The lift clears
the recomputed MDE (2.92 pp) with room to spare — this is a real, statistically resolved
effect, not a coin flip that happened to land on the right side of significance.

**Guardrails.**

| Guardrail | Control | Treatment | Δ (pp) | One-sided 95% upper bound | Margin | Verdict |
|---|---:|---:|---:|---:|---:|---|
| KYC rejection rate | 10.48% | 10.17% | **−0.31** | +0.92 pp | +1.5 pp | **Non-inferiority established** |
| Flagged-fraud rate (30d) | 0.95% | 1.31% | **+0.36** | +0.89 pp | +0.5 pp | **NOT established** |
| Onboarding tickets / 1k | 93.7 | 99.6 | +5.9 | — (directional) | — | worse, secondary guardrail only |

The KYC-rejection guardrail is unambiguously fine — treatment is directionally *better*.
**The flagged-fraud guardrail is the finding that should stop an unconditional rollout**:
the point estimate (+0.36 pp) is inside the +0.5 pp margin, but the uncertainty around it
is not — the one-sided 95% upper bound (+0.89 pp) sits above the margin, so non-inferiority
is **not established** at this sample size. This is not the same as "fraud got worse"; it
is "we cannot yet rule out that it did, within the pre-agreed safety margin."

**Heterogeneity by acquisition channel.**

| Channel | Control | Treatment | Lift (pp) | 95% CI | p |
|---|---:|---:|---:|---:|---:|
| influencer | 38.1% | 45.4% | +7.3 | [−0.4, +15.0] | 0.065 |
| paid_social | 38.8% | 45.0% | **+6.2** | **[+3.0, +9.4]** | **<0.001** |
| app_store_search | 46.7% | 50.3% | +3.6 | [−1.3, +8.5] | 0.150 |
| organic | 50.6% | 54.1% | +3.5 | [−0.8, +7.9] | 0.113 |
| referral | 56.5% | 58.1% | +1.5 | [−3.7, +6.8] | 0.567 |

The ordering matches the design intent — low-intent, top-of-funnel channels (paid_social,
influencer) show the largest lift; warm channels (referral) show the least. **Only
paid_social's effect is individually significant** at this sample size (the largest
channel, ~3,657 of the 9,254 clean subjects). The formal arm × channel interaction test
(likelihood-ratio) is **not significant** (χ² = 3.25, df = 4, p = 0.52) — the channel cut
is directionally consistent with the prior but the sample is not large enough to prove the
effect genuinely differs by channel, as opposed to one channel simply carrying more
statistical weight.

## Conclusion
The redesigned onboarding **works**: a real, statistically significant **+4.58 pp** Day-7
Activation lift, safely inside the recomputed power. It is **not an unconditional pass**:
the KYC-rejection guardrail is clean, but the flagged-fraud guardrail's non-inferiority is
**not established** at this sample size — the point estimate is small but the confidence
interval reaches meaningfully past the agreed safety margin. Heterogeneity is directionally
as expected (paid_social/influencer benefit most) but not formally proven at this n.

## Limitations
The re-run's smaller, deadline-capped sample (vs. the original 6-week design) under-powers
both the guardrail non-inferiority tests and the heterogeneity interaction test — a larger
or longer follow-up window would sharpen both without necessarily changing the primary
conclusion.

## Recommendation
**Do not ship an unconditional rollout.** Recommend a **monitored rollout with a fraud
circuit-breaker**: ship to the highest-lift, best-guardrail-margin segment first
(paid_social), keep both hard guardrails on a live dashboard (Experiment Integrity Monitor
pattern extended into steady-state monitoring), and re-evaluate the fraud guardrail once
more post-launch data accrues rather than treating this read as final.
