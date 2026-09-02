# 07 — The hoarding problem: the redemption funnel and the point liability

**Decision it informs:** how big is the prize Flash Redemption is chasing, and what does the
unredeemed-points liability cost? **Audience:** CFO / loyalty finance.
**Window:** 24-month program history; funnel measured at the latest month (2026-08).

## Question
Where in the "earn → redeem" journey do SkyPoints members fall out, and how large / how
fast-growing is the point liability?

## Grain
`fact_member_month` (member × month), `fact_point_transaction` (one ledger entry),
`fact_liability_month` (one calendar month).

## Method (both tracks)
1. Redemption funnel at the latest month: active → balance ≥ Flash threshold (3,500) → ever
   redeemed → redeemed in the last 12 months → redeemed in the last quarter, overall and by
   tier.
2. Points roll-forward: issued / redeemed / expired, window-to-date, and issuance by source.
3. Liability trajectory (gross vs breakage-adjusted) + a sensitivity of the recognised cost
   to the breakage assumption.
pandas + DuckDB, parity on the points roll-forward totals and the ever-redeemed share.

## Evidence
**Redemption funnel (109,458 active members, 2026-08):**

| segment | active | balance ≥ 3,500 | ever redeemed | redeemed 12m | redeemed last qtr |
|---|---|---|---|---|---|
| **All** | 109,458 | 68% | **32%** | 25% | **9%** |
| Blue | 71,147 | 65% | 25% | 19% | 6% |
| Silver | 24,496 | 72% | 37% | 30% | 10% |
| Gold | 10,739 | 78% | 53% | 46% | 18% |
| Platinum | 3,076 | 83% | 70% | 66% | 34% |

**Points window-to-date:** issued 2,089M · redeemed 636M (**burn/earn 30.4%**) · expired
228M (**10.9% of issued**, the first legacy-lot expiry wave).

**Issuance by source (M pts):** co-brand card **1,146 (55%)** · legacy migration 397 ·
flight 301 · promo 88 · partners 103 · service recovery 53.

**Point liability at 2026-08:** R$25.7M gross · R$15.4M breakage-adjusted (40%).
Sensitivity of recognised liability to the breakage assumption:

| assumed breakage | recognised liability | vs 40% base |
|---|---|---|
| 20% | R$20.6M | +R$5.1M |
| 30% | R$18.0M | +R$2.6M |
| **40%** | **R$15.4M** | — |
| 50% | R$12.9M | −R$2.6M |

Figure: `outputs/figures/07_hoarding.png`.

## Conclusion
The hoarding problem is real and **concentrated in Blue**: two-thirds of active members
clear the Flash threshold but **only a quarter of Blue members have ever redeemed** and only
**6% redeemed last quarter**. The dominant issuance engine is the **co-brand card (55% of
all points issued)** — points earned with no flight attached, by members with the weakest
redemption pull, which is exactly the population that accumulates and lets points expire.
Burn/earn is 30%; realised breakage is already 11% of issued points (legacy lots), trending
toward the ~40% lifetime expectation. The liability is R$25.7M gross and the recognised
figure swings **±R$2.6M per 10 pp** of breakage assumption — a real estimate risk.

## Limitations
- Realised breakage (11%) is window-to-date; most window lots have not yet reached their
  24-month expiry, so lifetime breakage is a projection.
- Per-lot FIFO attribution is not in curated (docs/08 §4) — breakage here is an aggregate
  roll-forward, not a cohort ledger.
- The liability unit cost (R$0.021/pt) and the 40% breakage assumption are program inputs.

## Recommendation
Flash Redemption attacks the right funnel stage for the right tier. Pair the rollout with a
**co-brand-card redemption nudge** (the 55%-of-issuance segment) and tighten the breakage
assumption with a cohort study once a full lot lifetime of data exists — the recognised-cost
uncertainty is material.
