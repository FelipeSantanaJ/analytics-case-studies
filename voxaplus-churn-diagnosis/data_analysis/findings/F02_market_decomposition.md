# F02 — Is it global, or concentrated in one market?

**Question.** Did churn rise the same way in Brazil, Mexico and the United States, or is the
company-wide number hiding different stories per market?

**Hypothesis.** The spike is not uniform: at least one market steps up sharply at
window-month 34 while another was already drifting up beforehand, and a third is roughly
stable.

**Method (both tracks).** `sm` view (`fact_subscription_month` joined to
`dim_subscriber`). Per market per `month_idx`: gross monthly churn (as in `F01`).
Two derived quantities per market: the **drift** (mean churn over months 28–32 minus mean
over 24–27) and the **step** (month 33 minus month 32). `q2_churn_by_market` /
`q2_market_summary`; SQL and pandas agree exactly.

**Evidence** (`results/q2_market_summary.csv`).

| Market | Pre-shift | Peak | Drift (m28–32 vs m24–27) | Step (m32 → m33) |
|---|---|---|---|---|
| **Brazil** | 3.4 % | **7.0 %** | +0.2 pp (none) | **+3.0 pp** |
| **Mexico** | 5.4 % | **8.1 %** | **+0.6 pp** | +2.3 pp |
| **United States** | 4.1 % | 4.4 % | −0.3 pp | +0.7 pp |

**Conclusion.** Three different shapes:

- **Brazil** — flat at ~3.4 % through window-month 33, then a clean **+3.0 pp step** to
  ~7.0 %. An acute event.
- **Mexico** — already the highest market, and **drifting upward from ~window-month 28**
  (before anyone was looking), then a further step to ~8.1 %. A pre-existing problem that
  got worse.
- **United States** — essentially unchanged (4.1 % → 4.4 %). The control.

The company-wide "nearly doubled" is a Brazil step **plus** a Mexico ramp; the US shows
the shift is not a platform-wide, every-market phenomenon. That already rules out
explanations that would hit all three markets equally.

**Limitations.** Mexico and the US have shorter histories; the US in particular has a
smaller base and noisier monthly rates.

**Recommendation.** Run two workstreams, not one: an acute-incident review focused on
Brazil (what changed at window-month 32–33), and a separate look at why Mexico has been
deteriorating since mid-2025. `F05`–`F07` identify the specific causes.
