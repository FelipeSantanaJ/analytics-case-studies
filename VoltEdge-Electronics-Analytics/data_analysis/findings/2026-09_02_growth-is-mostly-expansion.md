# Finding 02 — The +137% headline is mostly market expansion, not the core business

**Decision it informs:** how the CEO/CFO should read the growth story in the board pack —
and whether to plan next year on the +137% top-line or the +40% like-for-like rate.
**Audience:** CEO, CFO.
**Time window:** CY 2025-07-01→2026-06-30 vs PY 2024-07-01→2025-06-30.

## Question
Net Revenue grew **+137% YoY** ($9.3M → $22.0M). How much of that is the *existing* business
growing, and how much is simply *new markets opening* (UK + DE from 2025-01, BR from 2025-07)?

## Hypothesis
Most of the jump is expansion: three of four markets were partly or fully absent in PY, so a
raw YoY overstates organic momentum.

## Method (both tracks — `parity/02_growth_decomposition.py`, all checks pass)
- Net Revenue (USD) = `SUM(net_amount_usd) − SUM(refund_amount_usd)`, `order_status <> 'cancelled'`,
  on `fact_order_lines` (grain: order line). Split CY/PY by `order_date_key`.
- **Comparable Base** = `dim_market.is_comparable_base` = **US only** (live the whole CY+PY span),
  matching DAX `Net Revenue (Comparable Base)`.
- **Expansion** = Total − Comparable Base = UK + DE + BR.
- Plan from `fact_target` where `metric = 'Net Revenue'`, CY months.
- SQL track: DuckDB `FILTER (WHERE …)` aggregates over the same parquet. Python: pandas pivot.
  Parity to <1e-6 relative on every market × period cell and every subtotal.

## Evidence

| Cut | PY | CY | YoY |
|---|---:|---:|---:|
| **Total (all markets)** | $9.30M | $22.05M | **+137.1%** |
| **Comparable Base (US like-for-like)** | $7.33M | $10.29M | **+40.4%** |
| Expansion (UK + DE + BR) | $1.97M | $11.76M | — |

- Expansion is **53% of CY Net Revenue** and **77% of the $12.7M YoY gain**.
- Per-market CY YoY: US **+40%**, UK +247%, DE +285%, BR n/a (no PY). UK/DE multiples are
  a 6-month-PY vs 12-month-CY artefact, not real 3–4× growth.

### Actual CY vs plan (`fact_target`)

| Market | CY actual | CY plan | vs plan |
|---|---:|---:|---:|
| United States | $10.29M | $10.54M | **−2.4%** |
| United Kingdom | $3.78M | $3.34M | +12.9% |
| Germany | $3.39M | $3.16M | +7.3% |
| Brazil | $4.59M | $4.61M | −0.4% |
| **Total** | **$22.05M** | **$21.65M** | **+1.8%** |

## What the data says
1. The core (US) business grew **+40% like-for-like** — genuinely healthy for a growth-stage
   DTC retailer — but landed **2% under its own plan**. The proven market is the only one
   missing plan.
2. The eye-catching **+137%** is a one-time step from geography. It will not recur at that
   rate; next year's comparable base includes UK+DE (and eventually BR), so the reported
   number will step *down* toward the underlying ~30–40% range even if performance holds.
3. Europe (UK+DE) is the plan-beat story: +$0.67M combined over plan. Brazil, in its first
   12 months, is already the #3 market by revenue and essentially on plan.

## Limitations & assumptions
- Comparable Base = US only (the static DAX definition). A **Core-3** (US+UK+DE from
  2025-01) cut would give a like-for-like read from 2025 onward — not done here.
- US +40% is not yet decomposed into price / volume / category-mix — **Finding 03**.
- PY UK/DE is a partial (6-month) base, so their YoY% is not meaningful; only absolute
  dollars are used in the decomposition.
- Plan reconciliation uses `fact_target` as loaded; not yet cross-checked to the Power BI
  "vs plan" tile (open item from Finding 00).

## Recommendation
- **Report growth two ways on every board slide** (already the report's design intent): lead
  with **+40% like-for-like**, show +137% total as "incl. expansion". Do not let $22M / +137%
  anchor next-year targets.
- **CFO:** press on the **US −2% vs plan** — it is the single most important growth signal in
  the pack and is hidden by the blended beat (+1.8%).
- Set FY27 US plan off the +40% trajectory with a deceleration assumption; treat European
  outperformance as upside, not run-rate.
