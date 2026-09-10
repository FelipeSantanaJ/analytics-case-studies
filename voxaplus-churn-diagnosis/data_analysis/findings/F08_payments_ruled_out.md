# F08 — Payment failures and involuntary churn: tested and ruled out

**Question.** Did payment authorisation, dunning recovery, or involuntary churn deteriorate
at the shift — i.e. are people being *dropped* rather than *leaving*?

**Hypothesis (to falsify).** The spike is (partly) involuntary: failed renewals rising or
dunning recovery falling, especially in Mexico with its OXXO / carrier-billing mix.

**Method (both tracks).** `fact_billing_attempt`: first-attempt payment-failure rate
(failed ÷ non-dunning attempts) and dunning-recovery rate (recovered ÷ dunning attempts),
by market, pre-shift vs peak. `sm` view: involuntary churn rate by market, pre-shift vs
peak. `q8_payments`, `q8_involuntary_by_market`; SQL and pandas agree exactly.

**Evidence** (`results/q8_payments.csv`, `results/q8_involuntary_by_market.csv`).

| Market | Payment-failure rate (pre → peak) | Dunning recovery (pre → peak) | Involuntary churn (pre → peak) |
|---|---|---|---|
| Brazil | 7.6 % → 7.7 % | 50.7 % → 52.0 % | 0.43 % → 0.41 % |
| Mexico | 18.8 % → 18.2 % | 37.0 % → 36.8 % | 1.25 % → 1.30 % |
| United States | 8.0 % → 7.8 % | 57.9 % → 56.9 % | 0.31 % → 0.32 % |

**Conclusion.** **Nothing moved.** Payment-failure rates, dunning recovery and involuntary
churn are flat within noise across every market from pre-shift to peak. Mexico's payment
economics are structurally worse (18 % first-attempt failure, 37 % recovery, 1.3 %
involuntary churn) — a standing cost, not a new one. Combined with `F01` (90 % of peak
churn is voluntary), this **rules payments out as a driver of the spike**. The elevated
churn is people deciding to leave, not billing dropping them.

**Limitations.** Payment method mix and authorisation rates are modelled
(`docs/01` §9, `docs/08`); the finding is about the *change* over time, which is robust to
the absolute calibration.

**Recommendation.** No action on the spike from here. Separately, Mexico's ~18 % payment-
failure rate and 37 % dunning recovery are worth a dedicated project — every point of
recovery there is ~0.1 pp off Mexican churn — but that is an efficiency programme, not the
answer to the board's question.
