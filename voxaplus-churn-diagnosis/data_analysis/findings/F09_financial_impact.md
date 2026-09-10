# F09 — What the elevated churn is costing

**Question.** Translate the ~2.7 pp of extra monthly churn into subscribers and revenue, so
the board can size the response.

**Method (both tracks).** From `fact_subscription_month`: blended gross monthly churn
pre-shift vs peak; implied average lifetime = 1 ÷ monthly churn; ARPU and MRR at the peak.
Cumulative **excess churned subscribers** since the shift = Σ over months 33–35 of
(actual churned − start-of-month active × pre-shift churn rate). `q9_financial`,
`q9_excess_churn`; SQL and pandas agree exactly.

**Evidence** (`results/q9_financial.csv`, `results/q9_excess_churn.csv`).

| | Pre-shift | Peak |
|---|---|---|
| Blended gross monthly churn | 4.11 % | 6.82 % |
| Implied average subscriber lifetime | **24.3 months** | **14.7 months** |
| ARPU (USD, at peak) | | $7.51 |
| MRR (USD, at peak) | | ~$499 k / month |

| | Value |
|---|---|
| **LTV erosion** (lifetime peak ÷ lifetime pre − 1) | **−39.5 %** |
| **Excess subscribers churned in the 3 elevated months** vs the pre-shift rate | **≈ 5,400** |

**Conclusion.** The churn step cuts the average subscriber lifetime from ~24 to ~15
months — a **~40 % reduction in lifetime value per subscriber**. In the three elevated
months alone, **~5,400 subscribers left over and above what the old rate would have
produced**; at ~$7.5 ARPU and a ~15-month remaining lifetime, that is on the order of
**$0.5–0.6 M of lifetime recurring revenue already forgone**, and it compounds every month
the rate stays elevated. It also breaks the growth maths: a 40 % lower LTV means the
allowable CAC falls by ~40 %, so acquisition that was economic at the old churn rate is not
at the new one.

**Limitations.** Lifetime = 1 ÷ current monthly churn is a standard but simple proxy; it
overstates the loss if churn reverts quickly and understates it if the rate keeps climbing.
The revenue figure is an order-of-magnitude estimate, not a booked number.

**Recommendation.** Fund the `F05` connected-TV fix and the `F06` Brazil price-migration
pause as revenue-protection, not cost. Freeze or trim spend on the least-economic
acquisition sources (Mexico especially, `F07`) until LTV recovers, and re-plan net-adds on
the ~15-month lifetime, not the ~24-month one, until the rate is back near 4 %.
