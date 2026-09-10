# 02 — Randomisation & balance: can the assignment be trusted?

**Question.** Was the zone-day assignment balanced, and is there any hidden
selection to worry about?

**Method (both tracks).** (1) χ² sample-ratio test on treated/control counts —
overall, per stress tier, per weekday/weekend. (2) Standardized mean differences
(treatment − control) on the frozen pre-period (months 1–15) covariates:
`pre_fulfillment_rate`, `pre_eta_p90_min`, `pre_orders_placed_mean`,
`pre_liquidity_ratio`, `pre_idle_courier_ratio`, plus `is_weekend`. A Love plot.

**Evidence** (`outputs/tables/02_srm.csv`, `02_balance.csv`, `outputs/figures/02_love_plot.png`).

| Cut | χ² | p |
|---|---|---|
| overall · per tier · per weekday/weekend | 0.0 | 1.00 |

All standardized mean differences are **0.000**.

**Conclusion.** The allocation is **exactly 50/50 within every (zone × weekday/weekend)
cell** — it was drawn that way (stratified, balanced on day-type), so the χ² is
degenerate and passes trivially. The covariate SMDs are exactly zero because the
pre-period covariates are **zone-level** (one frozen value per zone) and each zone is
split 50/50, so the two arms carry identical covariate means by construction.

This means the two classic A/B risks do **not** apply here: there is no
sample-ratio mismatch to investigate, and there is no differential attrition — a
zone-day cannot "drop out". What *could* still bias the estimate is a
**time-varying shock** that lands differently on treated vs control zone-days
(weather, a local event). Those enter the analysis in `03` as covariates
(`is_rainy`, `has_local_event` on `fact_zone_hour`) and via the concurrent control
arm; the day-of-week balance above rules out the largest such confounder.

**Limitations.** Balance on *observed* zone-level covariates only; the design's real
protection is the within-zone split and the concurrent control, not covariate
adjustment.
