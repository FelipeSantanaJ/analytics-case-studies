# 08 — Do redeemers stay? The observational redeemer → retention link

**Decision it informs:** is "get members to redeem" a retention lever, or just a correlate?
**Audience:** CRM / retention manager. **Window:** reference month 2025-08, outcome observed
through 2026-08 (12-month look-ahead).

## Question
Members who redeem lapse less — but is that because redeeming *keeps* them, or because the
kind of member who redeems was never going to leave anyway?

## Grain
`fact_member_month` (member × month). **Engagement lapse** = 12 consecutive months with no
flight and no redemption (card-only earn does not count — see docs/01 §6; plain "account
lapse" runs ~4% because card auto-earn keeps accounts nominally active).

## Hypothesis
There is a real retention effect, but it is smaller than the raw gap because a latent
"engagement" trait drives both redeeming and staying.

## Method (both tracks)
1. Raw 12-month engagement-lapse rate: prior redeemers vs never-redeemers.
2. **Adjusted** — logistic regression of lapse on `prior_redeemer + tenure + tier +
   log(prior earn) + prior flights + card-only flag`; average marginal effect of
   `prior_redeemer`.
3. Forward 12-month flight revenue per member, redeemer vs never.
pandas + DuckDB, parity on the two lapse rates.

## Evidence
- **Raw:** prior redeemers lapse at **10.6%** (n = 14,108), never-redeemers at **21.1%**
  (n = 42,447) → **raw gap −10.5 pp**.
- **Adjusted:** average marginal effect of prior-redeemer on lapse = **−6.0 pp**
  (logit +0.436, p = 1 × 10⁻³¹). ~40% of the raw gap is explained by tenure / tier / earn
  activity; ~60% survives.
- **Forward flight revenue:** redeemers R$3,337/member/yr vs never-redeemers R$1,596 —
  raw difference +R$1,741 (redeemers are ~2× as valuable).
- Table: `outputs/tables/08_redeemer_retention.csv`.

## Conclusion
The association is large and survives adjustment, but it **cannot be read as a −6 pp causal
effect** — the blocking covariates do not capture the latent engagement trait, so the
adjusted gap still over-states causation. The clean causal evidence is the experiment's
**90-day disengagement guardrail (finding 04, G3): −2.0 pp, p = 0.001** — a real reduction
in disengagement from *randomly enabling* more redemption, on a 12-week-plus-90-day horizon.
Directionally, everything points the same way: redeeming is a retention lever, not just a
marker; the magnitude on a full 12-month horizon is somewhere between the experiment's −2 pp
short-run signal and the adjusted −6 pp observational gap.

## Limitations
- **Confounding by latent engagement** — the core caveat; observational only.
- The reference-month design uses one cut point; a cohort/time-varying treatment model would
  be more robust.
- Forward-revenue difference is unadjusted and largely selection.
- The experiment's causal number is a 90-day proxy, not a 12-month lapse outcome.

## Recommendation
Treat redemption enablement (Flash Redemption for Blue/Silver) as a **retention
intervention**, not only an engagement one — but size its retention benefit conservatively
(closer to the experiment's −2 pp than the observational −6 pp) until a longer post-rollout
window is available.
