# Finding 09 — Returns aren't rising, but $1.65M of margin leaks — mostly for fixable reasons

**Decision it informs:** whether returns need a dedicated reduction program, and where
(quality? content? reverse logistics?).
**Audience:** VP Customer, COO, merchandising.
**Time window:** full 24m; CY vs PY for the trend.

## Question
Electronics carries high return rates. Is VoltEdge's under control, and what is it costing
in margin?

## Method (both tracks — `parity/09_returns.py`, all checks pass)
`docs/06 §13`: `Return Rate % = SUM(returned_qty) ÷ Units Sold` (product lines,
non-cancelled). `Return Value = SUM(fact_returns.refund_amount_usd)`; `Restock Rate % =
restocked returned_qty ÷ returned_qty`. Net margin drag = refund − `cogs_recovered_usd`
(returns cut Net Revenue by the refund; restocked goods credit COGS back). Sliced by
category, market, reason. SQL = DuckDB; Python = pandas. Rate & value parity exact.

## Evidence
- **Return rate 8.0%** — mid-range of the 7–12% benchmark, and **flat**: PY 8.0% → CY 8.0%,
  and 8.0–8.1% in *every* market. Not a deteriorating problem.
- **Margin drag $1.65M** over 24m (refund $3.48M − COGS recovered $1.83M). That is **5.3% of
  Net Revenue** and **29% of gross profit** — material despite the benign rate.
- **Restock rate only 54.3%** — 46% of returned units go to quarantine and are written down.
  This is the biggest single lever on the *drag* (not the rate).
- **Category concentration:** Smartphones 11.8%, Wearables 11.2% at the top; Accessories
  5.0% at the bottom. The high-return categories are exactly the ones **US growth is
  concentrating into** (Finding 04) and the **thinnest-margin** ones (Finding 01) — a
  compounding drag.
- **Reason mix — 63% "controllable":**

| Reason | Refund (24m) | Bucket |
|---|---:|---|
| Defective / not working | $963k | quality |
| Changed my mind | $864k | customer choice |
| Not as described | $545k | content/PDP |
| Found better price | $409k | customer choice |
| Arrived late | $267k | fulfilment (→ Finding 10) |
| Wrong item shipped | $247k | pick/pack |
| Damaged in transit | $190k | packaging/carrier |

Ops/quality-driven refunds total **$2.21M (63%)**; pure customer choice **$1.27M (37%)**.

## What the data says
1. The **rate** is fine and stable — no fire to fight there.
2. The **cost** is not fine: $1.65M net drag, and it is addressable. "Defective",
   "Not as described", "Wrong item", "Damaged" and "Arrived late" — $1.67M of refunds — are
   process failures, not customer whims.
3. **Two independent levers:**
   - **Reduce the drag per return** by lifting restock from 54% (better triage / refurb /
     open-box channel). Each +10pp of restock ≈ +$180k COGS recovered on current volume.
   - **Reduce controllable returns** via QA on the defect-prone SKUs, better PDP content
     (photos, specs, sizing) for "not as described", and pick accuracy.
4. Returns also **hurt retention** (Finding 08): a defective first order is a likely churn.
   The $963k defective bucket is probably under-counting its true cost.

## Limitations & assumptions
- `fact_returns.refund_amount_usd` total ($3.48M) is slightly above the `fact_order_lines`
  refund column used for Net Revenue ($3.46M, Finding 00) — a handful of returns map to
  cancelled/again-adjusted orders. Immaterial (<1%); the DAX `Return Value` uses `fact_returns`.
- "Controllable vs choice" is my bucketing of the 7 reason codes, not a model field.
- Return rate is unit-based (DAX definition); a value-based rate would be higher for
  Smartphones/Laptops (bigger tickets).
- No SKU-level drill here — the category view is enough to target a program; SKU QA list is
  a follow-up query.

## Recommendation
- **COO/merchandising:** stand up a returns-cost program with two KPIs on the CRM/Ops page —
  **restock rate** (target 54% → 70%) and **controllable return rate** (defect + wrong-item
  + damaged). Combined realistic recovery ≈ **$0.4–0.7M/yr** of margin.
- Prioritise QA and PDP work on **Smartphones and Wearables** — highest return rate,
  thinnest margin, and where volume is growing.
- Feed "Arrived late" returns ($267k) into the Finding 10 fulfilment case — they are a
  logistics cost showing up as a returns number.
