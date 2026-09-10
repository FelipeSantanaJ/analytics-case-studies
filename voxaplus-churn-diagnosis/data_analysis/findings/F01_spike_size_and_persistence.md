# F01 — The spike: size, split, and whether it is still going

**Context.** Leadership reported that monthly churn "nearly doubled" ~3 months ago.
**Question.** By how much did gross monthly churn rise, is it voluntary or involuntary,
and has it plateaued, kept climbing, or started to recede?

**Hypothesis.** Gross monthly churn roughly doubled at window-month 34 and has stayed
elevated; the increase is predominantly voluntary (member-initiated), not payment-driven.

**Method (both tracks).** From `fact_subscription_month`, per `month_idx`: paid-active count,
voluntary and involuntary churn counts. Gross monthly churn = (voluntary + involuntary) ÷
active at the start of the month (prior-month active). Pre-shift baseline = mean over
`month_idx` 24–32; peak = mean over 33–35. DuckDB `q1_churn_trend` and the pandas
equivalent agree exactly (`parity/parity_report.md`).

**Evidence** (`results/q1_summary.csv`, `results/q1_churn_trend.csv`).

| | Value |
|---|---|
| Pre-shift blended gross monthly churn | **4.11 %** |
| Peak blended (window-months 34–36) | **6.82 %** |
| Ratio | **1.66×** |
| Month-by-month at the peak | 34 = 6.85 % · 35 = 6.58 % · 36 = 7.02 % |
| Voluntary share of peak churn | **90.4 %** |

**Conclusion.** Gross monthly churn stepped from ~4.1 % to ~6.8 % — a **1.66×**
increase, fairly described as "nearly doubled." It has **not** receded: the three
elevated months are 6.85 %, 6.58 %, 7.02 % — flat-to-rising. The rise is **overwhelmingly
voluntary** (people are choosing to leave), which points the investigation at product,
price and value, not at billing mechanics (that is tested and ruled out in `F08`).

**Limitations.** Blended monthly-average rate; a single unusually large acquisition month
can move the denominator. Reactivations are excluded from the churn numerator (they are
tracked separately).

**Recommendation.** Treat this as an active, unresolved leak — plan on the ~4 % baseline
not being restored on its own. Size the response to a sustained ~2.7 pp of excess monthly
churn (see `F09` for the subscriber and revenue impact).
