# Finding 10 — Fulfilment runs well; the lever is shipping-fee recovery, not carrier performance

**Decision it informs:** where (if anywhere) to invest in logistics — service, carriers, or
the free-shipping threshold.
**Audience:** COO / VP Operations, CFO.
**Time window:** full 24m; CY vs PY; Q4 vs rest.

## Question
Is fulfilment a problem — speed, reliability, cost — and does it explain the UK's negative
contribution margin (Finding 03)?

## Method (both tracks — `parity/10_fulfillment.py`, all checks pass)
`docs/06 §10`: `On-Time Delivery %`, `Avg Delivery Days` (delivered only), `Perfect Order
Rate %`, `Shipping Cost (USD)`, `Shipping Cost per Order`, `Shipping Cost Recovery % = fee
revenue ÷ shipping cost`, all on non-cancelled `fact_orders`. Sliced by market, carrier,
and Q4 vs rest. SQL = DuckDB `COUNT(DISTINCT …) FILTER`; Python = pandas. Parity exact on
every KPI and market cell.

## Evidence

| KPI | VoltEdge | Benchmark | Read |
|---|---:|---:|---|
| On-time delivery % | 94.5% | 92–96% | ✅ in range, flat YoY, flat by market |
| Avg delivery days | 4.5 | 3–6 | ✅ |
| **Perfect order rate %** | **82.9%** | 88–93% | ⚠️ **below** benchmark |
| Shipping cost / order | $10.39 | $6–14 | mid-range, flat across markets ($10.29–$10.43) |
| **Shipping cost recovery %** | **28%** | — | **only 28% of shipping cost recouped in fees** |

- **Everything operational is uniform and on-target.** Carrier on-time spread is tiny
  (Royal Mail 95.2% best, Evri 94.0% worst). There is no bad carrier or bad lane to fix.
- **Q4 stress is real but mild:** shipping cost/order $11.19 in Q4 vs $10.00 otherwise
  (+12%); on-time 94.2% vs 94.6%. Manageable.
- **The gap is fee recovery.** Shipping costs $1.74M over 24m; fees recover ~$0.49M →
  ~**$1.25M / 24m structural shipping loss** (~$0.6M/yr). Recovery by market: UK 38%,
  US 31%, DE 29%, **BR 5%** (Brazil is effectively free-shipping).
- **Perfect-order rate 83%** is dragged by the ~5.5% not-on-time plus the returns
  (Finding 09) and cancellation components — it is a *composite* symptom, not a new problem.

## Correcting Finding 03
Finding 03 speculated the UK's −1.7% contribution margin was partly "£-heavy shipping". **That
is wrong.** UK shipping cost/order ($10.29) is the *lowest* of the four markets and its fee
recovery (38%) is the *highest*. The UK CM drag is **gross margin** (15.4%, lowest —
category/product mix) plus its marketing load, **not** fulfilment. Fixing this cross-reference
in the deep dive.

## What the data says
1. Operations do not need investment for *service* — they hit benchmark everywhere.
2. VoltEdge is **subsidising shipping** to the tune of ~$0.6M/yr, most visibly in Brazil.
   That is a pricing/threshold choice, not an ops failure — and it is a lever on
   contribution margin comparable in size to the entire CY CM (+$325k).
3. Perfect-order rate is the one metric below benchmark; it improves automatically as
   returns (Finding 09) and on-time both improve — no separate program needed yet.

## Limitations & assumptions
- Synthetic carrier data shows very little differentiation — real carrier scorecards would
  likely have more spread; don't over-read the "no bad carrier" conclusion.
- `shipping_fee_usd` is revenue charged to customers; recovery % compares it to
  `shipping_cost_usd` (what VoltEdge pays carriers). Free-shipping-threshold logic is
  embedded in the fee, not modelled separately here.
- Q4 = calendar quarter 4 (`dim_date.quarter`); the Black Friday week sits inside it.
- Perfect-order composition not decomposed into its sub-flags here.

## Recommendation
- **CFO/CMO joint call on the free-shipping threshold**, market by market. Lifting blended
  recovery from 28% → 45% ≈ **+$0.3–0.4M/yr contribution** with minimal ops change. Start
  with **Brazil (5%)** — even a modest paid-shipping tier or higher threshold moves the needle.
- **Do not** spend on carrier changes or network redesign — service KPIs don't justify it.
- Keep Q4 surge capacity as-is; the +12% peak cost is within tolerance.
- Track **shipping cost recovery %** on the Executive Summary alongside CCC — both are
  cash/'margin levers currently invisible at board level.
