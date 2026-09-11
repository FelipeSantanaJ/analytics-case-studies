# Finding 05 — Discounting overall is modest; the promo calendar erases gross profit

**Decision it informs:** whether to keep the current promo calendar as-is, shrink discount
depth, or shorten/re-target events.
**Audience:** CFO, CMO, merchandising.
**Time window:** full 24m; promo classification from `dim_date.is_promo_period` / `promo_name`.

## Question
Is VoltEdge leaking margin through discounts — and if so, is it broad "discount creep" or
concentrated in the sale events?

## Method (both tracks — `parity/05_discount_leakage.py`, all checks pass)
`docs/06`: `Discount Rate % = SUM(discount_amount_usd) ÷ SUM(gross_amount_usd)`,
`order_status <> 'cancelled'`. Sliced full/CY/PY, promo vs non-promo days, by event, by
category, and monthly. Promo-day P&L uses actual line-level `gp = (net_amount_usd −
refund_amount_usd) − cogs_usd`, aggregated to a per-day average, promo vs non-promo.
SQL = DuckDB view + grouped aggregates; Python = pandas. Discount-rate parity exact to 1e-9;
per-day gross profit parity (sum/mean/variance per group) before any test runs on it.
Significance: Welch's t-test (unequal variance). Uncertainty: percentile bootstrap, 10,000
resamples, seed 42. Seasonality check: OLS with calendar-month fixed effects, HC3 robust SE.

## Evidence
- **Blended discount rate 4.6%** ($1.67M on $36.5M gross) — the **low end** of the 4–10%
  DTC benchmark (`docs/01 §9.1`). Mild upward drift: **PY 4.3% → CY 4.7%** (+0.4pp).
- **All of the discounting is in the events.** Non-promo days: **2.7%**. Promo days: **15.7%**
  (58 of 730 days, $0.84M of the $1.67M total discount).

| Event | Discount rate |
|---|---:|
| Black Friday / Cyber Monday 2025 | 19.0% |
| Black Friday / Cyber Monday 2024 | 17.7% |
| Mid-Year Sale 2025 / 2024 | 14.7% / 14.1% |
| Holiday Countdown 2025 / 2024 | 12.1% |
| Spring Tech Days 2025 / 2026 | 11.3% / 11.0% |

- Discount rate is **flat across categories** (4.5–4.9%) — no single category is being
  over-discounted; depth is time-driven, not product-driven.

### The promo-day P&L

| | Non-promo day (n=672) | Promo day (n=58) |
|---|---:|---:|
| Avg gross revenue (list) | $46,325 | $92,177 (**+99%**) |
| Avg units | 414 | 819 (**+98%**) |
| Avg discount given | $1,239 | $14,499 |
| **Avg gross profit** | **$5,680** | **$372** |

A promo day does ~2× the volume of a normal day but returns **$372 of gross profit vs
$5,680** — the ~15.7% discount more than consumes the ~18% product margin.

### Is this a real gap, or could 58 promo days just be noisy?

It's real. Comparing daily gross profit on the 58 promo days vs the 672 non-promo days
(Welch's t-test, unequal variance): **t = −8.80, p = 1.2×10⁻¹²** — not distinguishable from
zero is not on the table.

| | Estimate | 95% CI |
|---|---:|---:|
| Gap per promo day (naive) | **−$5,308** | [−$6,529, −$4,173] (bootstrap, 10,000 resamples) |
| Annualized (× 58 promo days) | **−$307,871** | [−$378,698, −$242,016] |
| Gap per promo day, **seasonality-adjusted** | −$5,710 | [−$7,076, −$4,345] (p = 2.5×10⁻¹⁶) |

The seasonality-adjusted row controls for calendar month (promo days only fall in
Mar/Jul/Nov/Dec, which could have different baseline demand than the rest of the year on
their own) via a fixed-effects regression (`gp ~ is_promo + month`, robust SE). The
adjusted gap is essentially the same as the naive one — **the promo P&L hole is not a
seasonality artifact.** Even the conservative end of the annualized CI (−$242k) is a
sizeable chunk of CY contribution margin (Finding 03, +$325k): **the promo calendar is
comparable in size to the company's entire operating contribution**, with real
uncertainty only in exactly how comparable (79%–117% of it, at the CI bounds).

Method for all three: `parity/05_discount_leakage.py` — daily gross profit is
parity-checked SQL vs. pandas (sum, mean, variance per promo/non-promo group) before any
test runs on it; the t-test, bootstrap and regression are then computed once from those
agreed-upon numbers.

## What the data says
1. There is **no discount-creep problem** to solve — 2.7% on normal days is healthy.
2. The **sale events are close to gross-profit-neutral or negative.** They buy revenue and
   units, not profit. Black Friday at 17–19% off is the worst offender.
3. Because promo depth is uniform across categories, the fix is a **calendar / depth**
   decision, not a merchandising one.

## Limitations & assumptions
- **Pull-forward not modelled.** Some promo-day volume is demand that would have arrived
   later at full price — accounting for it makes promos look **worse**.
- **Acquisition & clearance value not credited.** If sale events disproportionately land
   *new* customers with strong repeat value, or clear aged stock that would otherwise be
   written down, the −$308k is an overstatement. Needs the cohort view (Finding 08) and the
   aged-inventory view (Finding 06) to net out.
- "Baseline day" GP is a blended average, and promo days concentrate in specific calendar
   months (Mar/Jul/Nov/Dec) that could have different baseline demand on their own. Tested
   this directly with the month-fixed-effects regression above: adjusting for it moves the
   gap from −$5,308 to −$5,710/day — **the true counterfactual is if anything worse**, not
   better, so this isn't inflating the finding.
- Gross profit here is line-level (incl. moving-avg COGS); excludes marketing pulled forward
   to support the event.

## Recommendation
- **Cap Black Friday depth** (e.g. 12–14% vs 17–19%) and test shorter windows. The elasticity
  data here (≈1.0 unit-uplift per event) does not justify 19% off.
- **Re-scope the mid-year and holiday events** toward margin-carrying categories (audio,
  accessories, wearables — Finding 04) rather than blanket sitewide percentages.
- Before cutting, run the **new-customer contribution** of BF/CM cohorts (Finding 08). If
  BF acquires customers who repeat, keep BF as an acquisition line item — but fund it from
  the marketing budget with a CAC target, not from gross margin invisibly.
- Add **"gross profit per promo day vs baseline"** to the CFO pack so event ROI is visible.
