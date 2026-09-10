# Finding 03 — VoltEdge runs at break-even; the trajectory is up, UK is the drag

**Decision it informs:** whether VoltEdge can "afford" its growth — i.e. is each incremental
dollar of revenue carrying operating contribution, and which market is destroying it.
**Audience:** CFO, CEO.
**Time window:** full 24m, plus CY (2025-07→2026-06) vs PY (2024-07→2025-06).

## Question
The business is designed thin-margin. After marketing, shipping and payment costs, is
contribution margin positive, and is it improving or deteriorating?

## Method (both tracks — `parity/03_margin_to_breakeven.py`, all 30 checks pass)
Exactly the DAX chain in `docs/06`:
- `Gross Profit = Net Revenue − COGS + Returns COGS Recovered`
  (COGS = `SUM(fact_order_lines.cogs_usd)`, moving-average; recovery = `SUM(fact_returns.cogs_recovered_usd)`)
- `Contribution Margin = Gross Profit − Marketing Spend − Shipping Cost − (Payment Fees + Financing Cost Interest-Free)`
  - Marketing = `SUM(fact_marketing_spend.cost_usd)` by `date_key`
  - Shipping = `SUM(fact_orders.shipping_cost_usd)`, non-cancelled
  - Payment Fees = `SUM(fact_orders.payment_fee_usd)`, non-cancelled
  - Financing = `SUM(fact_payment_schedule.financing_cost_usd)` where `installment_plan = 'Interest-Free'`
- Periods split by `order_date_key` (returns by `return_date_key`, marketing by `date_key`).
- SQL: DuckDB CTE per component over the parquet; Python: pandas. Parity <1e-4 abs on every component.

## Evidence — the margin walk

| | Full 24m | Current Year | Prior Year |
|---|---:|---:|---:|
| Net Revenue | $31.35M | $22.05M | $9.30M |
| − COGS | $27.51M | $19.20M | $8.31M |
| + Returns COGS recovered | $1.83M | $1.09M | $0.54M |
| **= Gross Profit** | **$5.67M (18.1%)** | **$3.93M (17.8%)** | **$1.53M (16.5%)** |
| − Marketing | $2.91M | $1.72M | $1.10M |
| − Shipping cost | $1.74M | $1.20M | $0.54M |
| − Payment fees | $0.82M | $0.57M | $0.25M |
| − Financing ("sem juros") | $0.12M | $0.11M | $0.01M |
| **= Contribution Margin** | **+$76k (0.2%)** | **+$325k (1.5%)** | **−$365k (−3.9%)** |

### Contribution margin % by market — Current Year

| Market | Net Revenue | Gross Margin % | Contribution Margin | CM % |
|---|---:|---:|---:|---:|
| Brazil | $4.59M | 21.0% | **+$225k** | **+4.9%** |
| United States | $10.29M | 17.7% | +$164k | +1.6% |
| Germany | $3.39M | 16.7% | −$0.8k | −0.0% |
| United Kingdom | $3.78M | 15.4% | **−$63k** | **−1.7%** |

## What the data says
1. **The whole 24-month business made $76k of operating contribution on $31M of revenue** —
   0.2%. This is break-even by construction, exactly the tension `docs/01` frames.
2. **It is improving fast**: CM% went **−3.9% → +1.5% YoY**, +5.4pp, driven by (a) gross
   margin +1.3pp (16.5→17.8%) and (b) marketing falling from 11.9% to 7.8% of Net Revenue
   as the mix shifts to owned/earned channels (see Finding 07, planned).
3. **Brazil is the most profitable market on contribution** (+4.9%), not the riskiest —
   highest gross margin (21%, category mix) and cheap payments (Pix). Its merchant-funded
   "sem juros" financing cost is real but small ($0.10M CY).
4. **The UK is the only market losing money on contribution** (−1.7%, −$63k CY): lowest
   gross margin (15.4%) plus its marketing load. Germany is at exactly break-even.
   *(Correction: Finding 10 shows UK shipping cost/order is the **lowest** of the four
   markets — the drag is gross margin / category mix, not fulfilment.)*

## Limitations & assumptions
- `Gross Profit` **adds back** `Returns COGS Recovered` per the live DAX formula
  (`pbi_measures.py`). `docs/06` prose line 21 says it is *not* added back — the prose is
  stale; the measure and this analysis add it (+$1.83M over the window, +5.9pp of gross
  margin). Flag for the deep dive.
- Marketing spend has no market allocation issue here (it carries `market_key`), but ~??%
  of email-tooling cost may be global — not separated.
- Contribution margin excludes fixed cost, payroll, tech — it is an operating-contribution
  proxy, not net profit. Real profit is materially negative.
- CM by market does not reallocate any shared/HQ marketing; taken at `market_key` face value.

## Recommendation
- **Headline for the board:** "profitable at the contribution line for the first time
  (+1.5% CY vs −3.9% PY)" — but state plainly it is $325k, i.e. fragile.
- **CFO action on the UK**: −$63k contribution on £-heavy shipping and sub-16% gross margin.
  Either lift the free-shipping threshold / renegotiate carrier rates, or rebalance the
  category mix toward audio/accessories. Quantify in the logistics finding.
- Protect the **marketing-efficiency gain** — it, not gross margin, is what moved CM to
  positive. If CAC reverts, contribution goes back underwater.
