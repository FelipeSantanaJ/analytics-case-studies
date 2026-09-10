# F03 — Which cohorts, tenures, plans and channels are churning?

**Question.** Is the extra churn concentrated in one segment (new sign-ups, a plan tier, a
weak channel), or is it broad-based?

**Hypothesis.** If a single cause dominated we would expect the churn lift to land mostly
in one segment. A broad, roughly even lift across segments would instead point to several
overlapping causes.

**Method (both tracks).** `sm` view. For each cut — plan tier, tenure band (0–1, 2–6, 7–12,
13–24, 25+ months), acquisition channel, billing period — gross monthly churn averaged over
the pre-shift baseline (24–32) and the peak (33–35), and the lift in percentage points.
`q3_cohort_cuts`; SQL and pandas agree exactly.

**Evidence** (`results/q3_cohort_cuts.csv`, lift = peak − pre-shift).

| Cut | Segment | Pre-shift | Peak | Lift |
|---|---|---|---|---|
| Tenure | 25+ months | 3.4 % | 6.6 % | **+3.2 pp** |
| Tenure | 13–24 months | 2.7 % | 5.9 % | **+3.1 pp** |
| Tenure | 0–1 months | 7.6 % | 10.7 % | +3.1 pp |
| Tenure | 2–6 months | 4.5 % | 7.1 % | +2.6 pp |
| Tier | Básico | 4.8 % | 7.6 % | +2.8 pp |
| Tier | Standard | 4.2 % | 6.9 % | +2.7 pp |
| Tier | Premium | 3.0 % | 5.7 % | +2.7 pp |
| Channel | paid_search / paid_social / organic / direct | ~4.0 % | ~6.8 % | +2.7–2.8 pp |
| Billing | **monthly** | 4.1 % | 6.8 % | +2.7 pp |
| Billing | **annual** | 5.9 % | 7.8 % | **+1.9 pp** |

**Conclusion.** The lift is **broad and remarkably even** — roughly +2.7 pp on almost
every tenure band, tier and channel. Two exceptions are informative:

1. **Annual plans lifted only +1.9 pp** vs +2.7 pp for monthly — locked-in subscribers
   were partly shielded (they cannot act until renewal, and are stickier by selection).
2. **Long-tenure subscribers (25+ months) were hit as hard as brand-new ones.** A cause
   confined to bad new cohorts would not move the 13–24 and 25+ bands by +3 pp.

A single narrow cause does not produce this pattern. The even, cross-segment lift is the
first quantitative sign that **multiple factors are acting at once**, each touching a
different slice of the base.

**Limitations.** Acquisition channel is a sampled attribute (`docs/08` limitation 1), so
channel-level rates are directional. Tenure band uses `tenure_months` which resets on
reactivation.

**Recommendation.** Do not chase a single segment. The next findings test the specific
mechanisms — app quality by device (`F05`), the Brazil price change (`F06`), and Mexico
acquisition/cohort quality (`F07`) — and `F10` shows how they add up.
