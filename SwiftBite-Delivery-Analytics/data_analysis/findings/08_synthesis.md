# 08 — Synthesis: the decision

**Question.** Should SwiftBite roll out the zone-hour incentive?

**What the read-out establishes.**

| Dimension | Result | Route |
|---|---|---|
| **Primary — fulfillment** | **+1.87 pp** ([+1.27, +2.46]) | cluster-robust + RI (p = 3×10⁻⁴) + wild-boot agree |
| Co-primary — ETA p90 | **−6.06 min** ([−8.56, −3.57]) | all p < 0.002 |
| Co-primary — no-courier rate | **−0.36 pp** ([−0.64, −0.08]) | p ≈ 0.01–0.03 |
| Guardrail — cancellations (all causes) | −1.87 pp | favourable |
| Guardrail — courier earnings / active hr | **+R$ 8.12** | favourable |
| Heterogeneity | short +2.29 · balanced +2.43 · **long +0.94** pp | interaction Wald p = 0.004; short-CI ∩ long-CI = ∅ |
| Decay | none detectable (series too thin) | slope p = 0.71 |
| Cannibalisation | ≈ 17% of local, **n.s.**; metro net ≈ 83% | adjacent-control gap p = 0.76 |
| **G1 — cost per incremental order** | **R$ 281** ([R$ 195, R$ 431]) vs **R$ 10** margin | fails by ~28× |

**Recommendation.**

> **Do not roll out the flat per-delivery bonus as tested.** It genuinely improves
> marketplace liquidity — fulfillment +1.9 pp, ETA p90 −6 min, no-courier −0.4 pp,
> concentrated in the supply-short and balanced zones, with only a small
> (~17%, not significant) neighbour-zone drag. **But** at ~R$ 281 per *incremental*
> delivered order against a ~R$ 10 contribution margin it destroys roughly R$ 4.6 of
> value on every subsidised order: the bonus pays for all ~7,400 treated-block
> deliveries while only ~127 of them (1.7%) are incremental.
>
> The lever works; its pricing is wrong. **Re-run only with the bonus restructured to
> reward incremental supply** — a threshold or surge-triggered payment that fires
> only when a zone is actually short, not a flat per-delivery bonus — **capped to the
> supply-short and balanced zones**, with the neighbour-zone spillover guardrail and
> a hard budget live. Long (well-supplied) zones should never be in scope.

**Why the experiment was still worth running.** It cleanly separates two things ops
conflated: the incentive *does* pull supply and clear demand (a real, robust,
heterogeneous liquidity effect), and it *cannot* pay for itself in its current form
(a pricing-design failure, not a lever failure). Both are actionable; neither was
knowable from the dashboard.
