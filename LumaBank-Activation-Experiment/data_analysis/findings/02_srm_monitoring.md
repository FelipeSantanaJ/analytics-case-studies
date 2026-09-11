# 02 — Daily SRM monitoring: catching the break

**Decision it informs:** can the original run be trusted at all, and on what day did the
standing monitor first have grounds to say no? **Audience:** the experimentation platform
on-call, and whoever has to reconstruct the incident afterwards.

## Question
Did the daily sample-ratio-mismatch monitor (doc 01 §9) catch the break, and how fast?

## Grain
`fact_variant_assignment` (one row per assignment **event**), re-aggregated to
experiment-day. This is an **independent re-derivation** of `fact_srm_daily`, built here
directly from the raw assignment log rather than trusted from the curated table — exactly
what the runbook intends: the daily job and this analysis should never depend on each
other being right.

## Hypotheses
H₀ = 50/50 allocation, tested two ways every day: **cumulative** (all assignments to date)
and **trailing-7-day** (the window that actually catches a mid-flight break). WARN at
p < 0.01, ALERT at p < 0.001 on either test, per the runbook.

## Method (both tracks)
Daily first-assignment counts by arm; Pearson χ² goodness-of-fit, cumulative and
trailing-7-day; `alert_state` per the runbook thresholds; cross-checked against the
pre-built `fact_srm_daily` table.

## Evidence
- Allocation is clean for the first 10 days (2026-07-06 → 2026-07-15): daily counts hover
  around 50/50, trailing-7d p-values range 0.18–0.88, `alert_state = ok` throughout.
- **2026-07-16** (the deploy day): the daily split visibly shifts (87 control / 173
  treatment / 198 fallback that day alone) but the trailing-7d p-value (0.41) hasn't yet
  accumulated enough post-deploy days to trip a threshold.
- **2026-07-17:** trailing-7d p = 0.0107 — just above the 0.01 WARN line, one more day
  from tripping.
- **2026-07-18 — first ALERT.** Trailing-7d p = **0.00008** (cumulative p = 0.033). ALERT
  persists through 2026-07-21 (the last day before enrollment was paused), even as the
  fallback's share visibly decays (198 → 141 → 123 → 118 → 72 → 29 as the hotfix rolls).
- **Cumulative p never crosses 0.001** in the original run (it bottoms at 0.030) — ten
  clean pre-deploy days dilute it. This is the reason the runbook runs **both** tests: the
  trailing-7-day window is what actually catches a break that starts mid-flight.
- Cross-checked against the independently-built `fact_srm_daily` curated table:
  **100% day-by-day agreement** on `alert_state`.

## Conclusion
The standing SRM monitor works as designed: it raises ALERT on **2026-07-18**, exactly
**2 days** after the 2026-07-16 deploy. The cumulative-only check that a single pre-flight
balance test (à la AeroVanti's Flash Redemption check) would have run once, at the *end* of
the window, would likely have missed this — the deploy sits inside the window and the
cumulative test is diluted by the clean pre-deploy days. Continuous, trailing-window
monitoring is what makes this incident detectable at all.

## Limitations
The daily test is a repeated-testing procedure (one test per day for the life of the
experiment); the WARN/ALERT thresholds (0.01 / 0.001) are chosen tighter than the usual
0.05 specifically to control the false-alarm rate over many days, not tuned against this
particular incident.

## Recommendation
Treat 2026-07-18 as the incident start date for root-cause purposes (block 03) and for
any post-hoc analysis of the original run (block 04).
