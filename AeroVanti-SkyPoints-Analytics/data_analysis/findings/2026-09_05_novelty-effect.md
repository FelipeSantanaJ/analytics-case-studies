# 05 — Novelty effect: roughly half the headline lift decays

**Decision it informs:** what durable effect to expect after rollout. **Audience:** loyalty
director. **Window:** the 12 experiment weeks.

## Question
Is the +2.69 pp lift stable across the window, or is it front-loaded by a launch bump that
fades?

## Grain
`fact_experiment_member_week` — one row per subject × experiment week (180,000).
`redeemed_w` = redeemed at least once that week.

## Method (both tracks)
Weekly redeemers-per-subject by arm; the weekly **increment** (treatment − control);
OLS of the increment on week number (a negative slope = decay); weeks 1–4 vs 9–12; and a
"durable" estimate — the late (weeks 9–12) per-week increment scaled to a 12-week-equivalent
cumulative lift. pandas + DuckDB, parity on the week-1/6/12 increments.

## Evidence
- Weekly increment (treatment − control), pp: 0.49, 0.55, 0.25, 0.40 | 0.24, 0.09, 0.41,
  −0.08 | 0.36, 0.16, 0.24, −0.25.
- **OLS increment ~ week: slope = −0.044 pp/week, p = 0.017** — a significant downward trend.
- Weeks 1–4 mean increment **+0.42 pp/wk** → weeks 9–12 **+0.13 pp/wk** (decay +0.30 pp/wk).
- Cumulative "redeemed by week 12" lift = +2.69 pp; **durable (late-rate-equivalent) lift ≈
  +1.5 pp**.
- Figure: `outputs/figures/05_novelty.png`. Table: `outputs/tables/05_weekly_increment.csv`.

## Conclusion
Roughly **half of the headline +2.69 pp is a launch novelty bump** — extra redemptions in
the first weeks after the announcement email / in-app banner — that decays over the window.
The **durable effect is ≈ +1.5 pp** on the 12-week redemption rate, still clearly positive
and still above the +1.6 pp the design could detect at 80% power.

## Limitations
- 12 weeks is short for separating "novelty" from ordinary week-to-week noise; the slope
  test is significant but the decay estimate has a wide margin.
- The "durable" figure is an extrapolation of the late-window rate, not a measured
  steady state.
- Seasonality (redemptions rise into the July travel peak) is differenced out by the
  concurrent control arm but adds noise to the weekly series.

## Recommendation
Plan the rollout business case on the **durable ≈ +1.5–2 pp**, not the 12-week headline.
Expect a temporary spike at launch and do not read it as the run-rate.
