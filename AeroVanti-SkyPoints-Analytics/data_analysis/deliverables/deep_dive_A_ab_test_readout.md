# Deep Dive A — Flash Redemption A/B test read-out

**Business problem.** SkyPoints members accumulate miles but rarely redeem: only ~32% of
active members have ever redeemed, and non-redeemers lapse far more often. The loyalty team
believes the **10,000-point minimum redemption threshold** is the common cause — a Blue
member with 4,000 points can do nothing with them, never gets the "I got something" moment,
and disengages. In program months 19–21 they ran **Flash Redemption** as a randomised,
member-level A/B test: threshold **10,000 → 3,500** points, plus a low-cost reward catalog
(seat selection, extra bag, lounge pass, gift cards, Wi-Fi vouchers).

**The decision.** Roll Flash Redemption out to the whole program, roll it out to some tiers,
or don't. Plus: what durable lift to put in the business case, and which guardrails to keep
live.

---

## 1. Design & data (docs/01 §7)

| Element | Value |
|---|---|
| Unit / split | member / 50-50, **blocked (pair-matched)** within tier strata |
| Eligible | active (earn or flight in trailing 12m) and not lapsed at 2026-03-01 |
| Sample | **15,000** — Blue 7,000 · Silver 3,800 · Gold 2,600 · Platinum 1,600 (Gold/Platinum oversampled for the heterogeneity cut) |
| Window | 12 weeks, 2026-03-02 → 2026-05-24; + 8 wk (revenue) / 90 d (disengagement) look-ahead |
| Primary metric | **redemption rate** = share with ≥ 1 redemption in the window |
| Guardrails | revenue / member · net point-liability cost / member · 90-day disengagement · redemption value per redeemer |
| Surface | `fact_experiment_outcome` (1 row/subject), `fact_experiment_member_week` (weekly), `fact_experiment_assignment` (frozen covariates) |

Power: planning was control 11.0%, MDE +2.2 pp, 80% power → ≈ 3,450/arm. The realised design
(7,500/arm, control 12.8%) gives **0.97 power at the +2.2 pp MDE** and an 80%-detectable
effect of **≈ +1.6 pp**.

---

## 2. Randomisation check (finding 02)

- **Sample-ratio mismatch:** every stratum is exactly 50/50 (χ² = 0.000, p = 1.000).
- **Covariate balance:** SMD on all six frozen covariates (pre-period earn, flights,
  redemptions, balance, tenure, prior-redeemer flag) — **max |SMD| = 0.039**, all inside the
  0.1 threshold. `outputs/figures/02_love_plot.png`.
- Blocked randomisation (rank by a pre-period redemption-propensity score → adjacent pairs →
  coin flip per pair) balances prior behaviour by construction.

**→ the effect can be read causally.**

---

## 3. Primary metric (finding 03)

| | control | treatment |
|---|---|---|
| Redemption rate | 12.76% (957/7,500) | 15.45% (1,159/7,500) |

| Estimate | Value | 95% CI |
|---|---|---|
| **Absolute lift (pooled)** | **+2.69 pp** (+21.1% rel.) | [+1.58, +3.81] pp |
| z / two-sided p | 4.74 / **2.2 × 10⁻⁶** | — |
| **Post-stratified to population tier mix** | **+3.21 pp** | [+2.20, +4.22] pp |
| Covariate-adjusted (logistic AME) | +2.78 pp | (p = 1 × 10⁻⁷) |

The pooled estimate is on the *oversampled* design, which under-weights Blue (largest
effect); **post-stratified to the 68/20/9/3 member base the lift is ≈ +3 pp** — the number
to quote for a full rollout.

---

## 4. Heterogeneity by tier (finding 06) — the decision hinges here

| tier | control | treatment | lift (pp) | 95% CI | significant |
|---|---|---|---|---|---|
| **Blue** | 6.1% | 9.9% | **+3.77** | [+2.50, +5.04] | yes (p = 2e-8) |
| **Silver** | 10.8% | 13.0% | **+2.16** | [+0.10, +4.22] | yes, marginal (p = 0.04) |
| Gold | 19.4% | 21.9% | +2.54 | [−0.57, +5.65] | no (underpowered) |
| Platinum | 35.6% | 35.1% | −0.50 | [−5.19, +4.19] | no |

- **Arm × tier interaction: LR χ² = 17.0, df = 3, p = 0.0007** — the effect genuinely
  differs by tier.
- **Linear-in-tier-rank interaction: −0.172, p = 0.0001** — a monotone decreasing gradient
  Blue → Platinum.
- Forest plot: `outputs/figures/06_forest.png`.

Blue — the segment the intervention was designed for — gains +3.8 pp on a 6% base
(**+62% relative**). Gold/Platinum show no measurable benefit and already redeem freely.
"Not significant" for Gold/Platinum means *consistent with no effect*, not *proven zero*
(both are underpowered), but the interaction test says the gradient is real.

---

## 5. Novelty effect (finding 05)

- Weekly (treatment − control) increment: **OLS slope −0.044 pp/week, p = 0.017.**
- Weeks 1–4: +0.42 pp/wk → weeks 9–12: +0.13 pp/wk.
- Cumulative 12-week lift +2.69 pp; **durable (late-rate-equivalent) ≈ +1.5 pp.**
- `outputs/figures/05_novelty.png`.

Roughly half the headline is a launch bump that decays. **Build the business case on
≈ +1.5–2 pp durable**, expect a temporary launch spike.

---

## 6. Guardrails (finding 04)

| Guardrail | Δ (treatment − control) | 95% CI | p | Verdict |
|---|---|---|---|---|
| Revenue / member (window + 8 wk) | −R$0.8 (−0.09%) | [−R$48, +R$46] | 0.97 | no harm, but **NI vs −3% not established** (one-sided p = 0.14) |
| Net liability cost / member | −R$0.81 | [−R$1.78, +R$0.16] | 0.10 | favourable direction, n.s. |
| 90-day disengagement | **−2.01 pp** | [−3.21, −0.81] | **0.001** | **favourable** |
| Value per redeeming member | **−R$19 (−6.8%)** | [−R$31, −R$8] | **0.001** | **watch** — shallower redemptions; 9% of treatment redeemers use only the low-cost catalog |

Revenue is not hurt (point estimate ≈ 0) but the sample is too small to *prove*
non-inferiority — keep a revenue guardrail live. Disengagement improves (the clean causal
echo of finding 08). Redemptions get shallower — Flash partly converts "no redemption" into
"a small redemption"; watch the mix.

---

## 7. Decision

**Roll out Flash Redemption to Blue and Silver.** Hold Gold and Platinum at the 10,000-point
threshold (no measured benefit; the low-cost catalog would only add reward cash cost).

- **Expected durable effect:** ≈ +1.5–2 pp on the quarterly redemption rate for Blue/Silver
  (≈ +3 pp headline at launch, decaying).
- **Keep live during rollout:** (1) revenue per member vs a −3% floor; (2) share of
  redemptions that are low-cost-catalog-only.
- **Follow-ups:** a larger dedicated Gold test if a definitive answer is wanted; a longer
  post-rollout window to convert the 90-day disengagement signal into a 12-month lapse
  number; pair with a co-brand-card redemption nudge (Deep Dive B).

---

## 8. Limitations

- Post-window horizon ~14 weeks → lapse guardrails are **90-day proxies**.
- Gold/Platinum strata underpowered even at n = 1,300 / 800 per arm.
- Novelty vs noise: 12 weeks is short; the decay slope is significant but its magnitude is
  imprecise.
- Non-inferiority on revenue is **inconclusive**, not passed.
- All data synthetic and seeded (`etl/config.py`); benchmark ranges are directional.
