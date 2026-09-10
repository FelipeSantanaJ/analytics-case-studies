# Finding 08 — Repeat behaviour is healthy and improving, but not yet the revenue engine

**Decision it informs:** whether "repeat revenue gets us to profit" is a credible strategy
or wishful thinking — and where retention spend should go.
**Audience:** VP Customer, CEO, CFO.
**Time window:** full 24m for lifetime rates; monthly cohorts 2024-07 → 2026-06.

## Question
Only ~16% of CY revenue is "new-customer revenue" per the DAX measure inversion (Finding 07
⇒ 84% new). Is the repeat engine weak, or is the customer base just too young for it to show?

## Method (both tracks — `parity/08_retention_cohorts.py`, headline rates parity-exact)
- `Repeat Purchase Rate % = (customers with >1 non-cancelled order) ÷ (customers with ≥1)`
  (`docs/06 §12`), full window and CY-scoped.
- **Cohort retention:** assign each customer an acquisition month = month of first
  non-cancelled order; for each month-offset *n*, share of the cohort placing ≥1 order in
  month *n*. Averaged over cohorts with ≥6 months maturity (acquired ≤ 2025-12).
- **New vs returning revenue** at *(customer, calendar-month)* grain: revenue is "new" only
  in the acquisition month, "returning" every month after.
- SQL = DuckDB `COUNT(DISTINCT order_id)` per customer; Python = pandas. Repeat rates agree to 1e-9.

## Evidence
- **Lifetime repeat rate 37.6%** (100,281 buyers; 37,755 with ≥2 orders) — **above** the
  25–35% benchmark. CY-scoped repeat rate 34.4%. Avg **1.67 orders per customer**.
- **Newer markets already out-repeat the US:** DE 40.5%, BR 40.2%, UK 40.0%, **US 36.0%**
  (partly a censoring effect — younger cohorts have had less time to lapse — but the gap is
  consistent with `docs/01 §7` "brand awareness builds").
- **Retention decays fast:** 16% of a cohort orders again at +1 month, 9.5% at +3, 5.9% at
  +6, **2.1% at +12**. A low, fast-decaying curve — expected for big-ticket electronics
  (long replacement cycles) but thin.
- Only **26.5% of buyers are "Active"** (`dim_customer.customer_status`); 26% already "Churned".
- **Returning revenue is rising:** the returning share of monthly revenue climbed from ~20%
  in late 2024 to **~40–55% through 2026**, ~45% on average in CY.

## Reconciling the two "returning revenue" numbers
| Definition | CY value | Meaning |
|---|---:|---|
| DAX `New Revenue %` (Finding 07) — customer is "new" for their whole first year | 84% new / **16% returning** | share of revenue from customers acquired *this year* (incl. their repeat orders) |
| Order-month grain (this finding) | 56% new / **44% returning** | share of revenue from orders that are *not* a customer's first-ever |

Both are correct. The gap is the within-year repeat orders of customers acquired in CY.
**Read them together:** the repeat mechanism is genuinely contributing ~44% of order
revenue, but because the whole business is <2 years old, ~84% of customers spending in CY
are still first-year customers.

## What the data says
1. Repeat is **not broken** — the rate beats benchmark and the newer markets are better than
   the mature one. The "path to profit via repeat" is not wishful.
2. But it is **not yet an engine**: 1.67 orders/customer and a +12-month re-order rate of 2%
   mean lifetime value is shallow. The business still lives or dies on new-customer
   acquisition economics (Finding 07).
3. The **highest-leverage window is months +1 to +3** (16% → 13% → 10%). A few points of lift
   there compounds through the curve and is the cheapest incremental revenue available.

## Limitations & assumptions
- **Left-censoring** everywhere: cohorts before 2024-07 are invisible; recent cohorts have
  short observation windows, which flatters newer-market repeat rates and depresses the
  tail of the average curve.
- `customer_status` (Active/Lapsed/Churned) is a modelled attribute in `dim_customer`, not
  recomputed here.
- Retention curve counts "placed ≥1 order that month", not revenue-weighted; a revenue
  curve would decay slightly slower (repeat orders skew larger).
- `customer_key = -1` (484 orders) excluded from cohorting.

## Recommendation
- **VP Customer:** own a **+1-to-+3-month reactivation program** (post-purchase lifecycle
  email/CRM, accessory cross-sell into the categories that carry margin — Finding 04).
  Target: lift +1-month re-order from 16% to 20%.
- **CFO:** in the profit bridge, model repeat revenue as an *improving* line but do not
  assume it carries the plan yet — new-customer CAC (Finding 07) is still the swing factor.
- Report **both** returning-revenue definitions on the CRM page with the reconciliation, so
  the 16% and the 44% don't read as a contradiction.
- Investigate why **US repeat lags the newer markets** by 4pp — product mix? shipping
  experience (Finding 10)? support (returns)? — it is the largest, most mature market and
  should be the retention leader.
