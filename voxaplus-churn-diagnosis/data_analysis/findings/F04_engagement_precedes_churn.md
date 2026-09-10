# F04 — Did viewing behaviour drop *before* people cancelled?

**Question.** For subscribers who cancelled during the elevated months, was their viewing
already falling in the weeks before, or did they leave from a healthy level of use?

**Hypothesis.** Peak-period churners show a decline in streamed hours in the one or two
months before cancellation that pre-shift churners do not — i.e. disengagement leads the
cancellation, rather than the cancellation being a bolt from the blue.

**Method (both tracks).** For every voluntary churn in `fact_subscription_month`, join
`fact_engagement_month` to read streamed hours in the churn month `M`, `M−1` and `M−2`, and
whether the subscriber was below the healthy-engagement threshold (< 5 h) in `M−1`.
Averages split by whether the churn month is pre-shift (24–32) or peak (33–35).
`q4_engagement_before_churn`; SQL and pandas agree exactly.

**Evidence** (`results/q4_engagement_before_churn.csv`).

| Churn cohort | Churners | Avg hours M−2 | Avg hours M−1 | Below healthy in M−1 |
|---|---|---|---|---|
| **Pre-shift** (m24–32) | 17,146 | 43.2 h | 43.6 h | 11.5 % |
| **Peak** (m33–35) | 12,243 | **37.3 h** | **35.7 h** | **12.7 %** |

**Conclusion.** Pre-shift churners left from a roughly flat ~43 h/month — their exit was
not preceded by a viewing decline. **Peak-period churners were already sliding**: ~37 h two
months out, ~36 h the month before they cancelled, and a higher share (12.7 % vs 11.5 %)
had fallen below the healthy-engagement line. The extra churn is **engagement-led** — value
erodes first, the cancellation follows. That tells us to look for what suppressed viewing
in the months just before the spike (`F05`), and it explains why a price change would bite
harder now than before (`F06`): people were already getting less for the money.

**Limitations.** `M` (churn-month) engagement is sparse — many subscribers do not stream in
the month they cancel — so the analysis leans on `M−2`/`M−1`. Engagement is measured at the
subscriber-month grain from `fact_engagement_month`.

**Recommendation.** Add a leading "engagement health" watch to the retention dashboard
(share of the base below the healthy line, and its 2-month trend) so the next value shock
is visible before it turns into cancellations.
