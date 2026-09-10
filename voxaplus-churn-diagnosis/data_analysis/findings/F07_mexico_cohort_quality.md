# F07 — Mexico: a pre-existing acquisition / cohort-quality drag  *(Factor 3)*

**Question.** Mexico's churn was already the highest and was drifting up before the spike
(`F02`). Is that a cohort-quality problem — are the subscribers Mexico has been acquiring
since mid-2025 simply retaining worse?

**Hypothesis.** Mexican cohorts acquired from ~window-month 24 onward retain materially
worse than earlier Mexican cohorts, and worse than the equivalent drop in Brazil or the
US — a slow-building drag that predates, and then compounds with, the app regression.

**Method (both tracks).**
1. `dim_subscriber` + `dim_channel`: share of each cohort-month's new subscribers coming
   through low-quality channels (affiliate + partner bundle), by market.
2. First-spell start month per subscriber (`fact_subscription_month`), and whether the
   subscriber was still active at tenure month 3. **M3 retention** by market × channel
   quality × cohort era: *pre-shift cohorts* = first paid month 12–23, *post-shift
   cohorts* = 24–30.
`q7_lowq_share_by_cohort`, `q7_m3_retention_by_channel_quality`; SQL and pandas agree
exactly.

**Evidence** (`results/q7_m3_retention_by_channel_quality.csv`).

| Market | Cohort era | M3 retention (low-quality ch.) | M3 retention (other ch.) |
|---|---|---|---|
| Brazil | pre-shift | 82.9 % | 82.7 % |
| Brazil | post-shift | 80.2 % (−2.7 pp) | 79.7 % (−3.0 pp) |
| **Mexico** | pre-shift | 81.7 % | 81.9 % |
| **Mexico** | **post-shift** | **74.0 % (−7.7 pp)** | **72.9 % (−9.0 pp)** |
| US | pre-shift | 83.0 % | 82.5 % |
| US | post-shift | 81.0 % (−2.0 pp) | 80.9 % (−1.6 pp) |

Low-quality-channel share of Mexican new subscribers sat at **~46 % throughout**
window-months 24–36 (`results/q7_lowq_share_by_cohort.csv`) — high, but not *rising*.

**Conclusion.** Every market's newer cohorts retain a little worse, but **Mexico's are
~8–9 pp worse at month 3** — three times the Brazil or US drop. Notably it is **not
channel-specific**: within post-shift Mexico, low-quality-channel cohorts (74.0 %) retain
about the same as everyone else (72.9 %). So this is not "the channel mix kept getting
worse" — it is **Mexican market conditions for newly-acquired subscribers deteriorating
across the board** from ~window-month 24, on top of an already-high involuntary base
(`F08`). That is **Factor 3**: a months-old, Mexico-specific cohort-quality drag that was
lifting Mexican churn ~0.6 pp before window-month 33 (`F02`) and is still there underneath
the spike.

**Limitations.** Acquisition channel is sampled (`docs/08` limitation 1), so the
low-vs-other split is directional; the era-level M3 drop is the robust signal. Cohort eras
are bounded so every cohort has ≥ 3 months of observable tenure inside the window.

**Recommendation.** Audit Mexican acquisition since mid-2025 — creative, offers, bundle
terms, onboarding — and the first-90-day experience specifically for Mexico. Until M3
retention recovers toward ~82 %, cap spend on the weakest Mexican sources and rebalance
toward the channels whose cohorts still retain.
