# F06 — The Brazil price increase, and why it bit  *(Factor 2)*

**Question.** Brazil raised Standard and Premium list prices at window-month 32 (migrating
existing members on their next renewal). Did that trigger the Brazil step in churn — and if
so, who left?

**Hypothesis.** The price increase on its own is not enough to explain a +3 pp step
(in-place price rises usually cause a small bump). It bit because it landed on a base that
was **already disengaged** — so the churn lift is concentrated in Brazil Standard/Premium
subscribers who were below the healthy-engagement line, not in engaged ones.

**Method (both tracks).** `sm` view restricted to Brazil, Standard/Premium tiers. Each
subscriber-month tagged **disengaged** if below the healthy-engagement threshold that month
(`fact_engagement_month`; missing → disengaged). Gross monthly churn by month for the
engaged and disengaged segments, compared before the hike (months 26–29) and after
(months 31–35). `q6_br_price_engaged_split`, `q6_price_summary`; SQL and pandas agree
exactly.

**Evidence** (`results/q6_price_summary.csv`).

| Brazil Std/Prem segment | Churn before hike (m26–29) | Churn after hike (m31–35) | Lift |
|---|---|---|---|
| **Engaged** | 0.0 % *(rounds to zero — very low)* | 0.0 % | **≈ 0 pp** |
| **Disengaged** | 23.9 % | **42.2 %** | **+18.3 pp** |

**Conclusion.** The price increase had **no measurable effect on engaged Brazil
subscribers** and a very large effect on **already-disengaged** ones (+18 pp on a segment
that was already churning at ~24 %/month). The disengaged Std/Prem segment is small, but
the interaction is exactly the amplifier the hypothesis predicted: **price alone did not
move engaged users; price × prior disengagement produced the Brazil step.** Because `F05`
(the CTV regression) pushed a wave of Brazil subscribers into the disengaged bucket in
window-months 32–33, the price migration then landed on a bigger disengaged pool than it
otherwise would have. This is **Factor 2**, and it is Brazil-only.

**Limitations.** The engaged-segment rate is so low it rounds to zero at the reported
precision; the signal is entirely in the disengaged segment. Migration timing is
approximate (existing members move on their renewal date, spread across months 32–36).

**Recommendation.** For Brazil Standard/Premium, pause or slow the remaining price
migrations for subscribers flagged as low-engagement; offer them a retention path (a month
of the prior price, a downgrade to Básico, or a pause) rather than a renewal at the new
price. Re-test the elasticity once the CTV fix (`F05`) has restored engagement.
