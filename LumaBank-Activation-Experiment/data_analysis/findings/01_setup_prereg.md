# 01 — Setup & pre-registration: what was known before the test ran

**Decision it informs:** was the original 6-week design's power reasonable, given the
platform's own history? **Audience:** whoever reviews the experiment plan before it ships.

## Question
What did the platform's own pre-experiment data say about Day-7 Activation and the
fintech-critical guardrails, and did the planned 6-week / ~13,500-user design have enough
power to detect a meaningful lift?

## Grain
`fact_activation` restricted to `experiment_cohort = 'not_in_experiment'` — the 18 months
of platform history before the original run (121,423 signups).

## Method (both tracks)
Platform Day-7 Activation rate, KYC-submit rate, KYC rejection rate (of submissions),
flagged-fraud rate (of Day-7 activators), and onboarding-ticket rate over the
pre-experiment window; the two-proportion sample-size formula solved for the achievable
MDE at the ~6,750/arm the original 6-week design expected, and for the n required to
detect a +3.0 pp lift.

## Evidence
- **Platform Day-7 Activation baseline: 45.9%** (n = 121,423). Close to, but a touch below,
  the planning value doc 01 used (48%) — a small, expected drift between an a-priori
  estimate and the realised platform trend.
- **Guardrail baselines:** KYC-submit rate 78.8%; KYC rejection rate 10.4% of submissions;
  flagged-fraud rate 1.29% of Day-7 activators; 104.6 onboarding tickets per 1,000 signups.
- **Power, original 6-week design:** at ~6,750/arm and a 45.9% control rate, the achievable
  MDE at 80% power is **2.41 pp**. Detecting a +3.0 pp lift at 80% power would need only
  **4,347/arm** — well inside the planned sample, so the original design was comfortably
  powered for anything in the +2.4 pp range or larger.

## Conclusion
The original design was reasonable on paper: a 6-week window at the planned enrollment
rate gives an MDE (2.41 pp) tight enough to resolve a business-meaningful lift, with room
to spare. Nothing in the pre-experiment baseline flagged the design as underpowered or the
guardrail levels as already stressed. The design's only failure mode was operational (the
day-11 production bug, blocks 02–04), not statistical.

## Limitations
The pre-experiment baseline spans 18 months of organic platform growth and channel-mix
drift; it is a reasonable planning anchor, not a guarantee that the concurrent control arm
of the actual test would land at exactly 45.9%.

## Recommendation
Proceed to block 02 — daily SRM monitoring is what actually decides whether this plan's
execution can be trusted.
