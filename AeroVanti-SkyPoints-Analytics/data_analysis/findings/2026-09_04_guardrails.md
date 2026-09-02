# 04 — Guardrails: is Flash Redemption safe to ship?

**Decision it informs:** whether the redemption lift comes at an unacceptable cost.
**Audience:** CFO. **Window:** experiment + 8-week look-ahead for revenue; + 90 days for
disengagement.

## Question
Does driving more redemption hurt flight revenue, inflate the point-liability cost, push
members toward disengagement, or just buy shallow "trinket" redemptions?

## Grain
`fact_experiment_outcome` — one row per subject.

## Method (both tracks)
| Guardrail | Test |
|---|---|
| G1 Revenue per member (window + 8 wk) | Welch t (two-sided) **and** a one-sided **non-inferiority** test at a −3% margin |
| G2 Net point-liability cost per member | Welch t + 95% CI |
| G3 90-day post-window disengagement | Two-proportion z |
| G4 Redemption value **per redeeming member** + low-cost-only share | Welch t |
pandas + DuckDB, parity on all four arm deltas.

## Evidence
| Guardrail | control | treatment | Δ | 95% CI | p | verdict |
|---|---|---|---|---|---|---|
| G1 Revenue / member | R$884.1 | R$883.3 | −R$0.8 (−0.09%) | [−R$48, +R$46] | 0.97 | no diff; **NI vs −3% NOT established** (one-sided p = 0.14) |
| G2 Net liability cost / member | −R$10.42 | −R$11.23 | −R$0.81 | [−R$1.78, +R$0.16] | 0.10 | favourable direction, not significant |
| G3 90-day disengagement | 18.0% | 16.0% | **−2.01 pp** | [−3.21, −0.81] | **0.001** | **favourable** (leading indicator) |
| G4 Value / redeeming member | R$288 | R$268 | **−R$19 (−6.8%)** | [−R$31, −R$8] | **0.001** | **watch** — shallower redemptions; 9% of treatment redeemers use the low-cost catalog only |

Backing table: `outputs/tables/04_guardrails.csv`.

## Conclusion
Three of the four guardrails are fine or favourable; one is a genuine watch item.
- **Revenue is not harmed** — the point estimate is essentially zero — but the sample is
  **too small to formally establish non-inferiority** at a −3% margin (the CI spans ±R$47).
  This is not evidence of a problem; it is a reason to keep a revenue guardrail live during
  rollout rather than declaring the question closed.
- **Disengagement improves** by 2 pp over 90 days — the clean, causal echo of the
  observational redeemer→retention link (08), on a short horizon.
- **Net liability cost per member is slightly lower** in treatment (more redemption draws
  down points that would otherwise have expired), though not significantly.
- **Redemptions get shallower** — treatment redeemers get ~R$19 less value each, and a
  slice redeem only from the low-cost catalog. Flash is partly converting "no redemption"
  into "a small redemption", which is still engagement, but the program should watch that
  the mix does not drift entirely to trinkets.

## Limitations
- 90-day disengagement is a **proxy** — the program's real retention metric is 12-month
  engagement lapse, which the experiment window cannot observe.
- Revenue is noisy (flight spend is skewed); the NI test would need a larger arm or a
  longer horizon to conclude.
- G2/G4 cash costs use the modelled partner-reward cost factors (docs/04 §1.5).

## Recommendation
Ship, with (a) a **live revenue-per-member guardrail** monitored for the first two quarters
of rollout and (b) a **redemption-mix guardrail** (share of redemptions that are low-cost-
catalog only) so the program can throttle the low-cost catalog if depth erodes further.
