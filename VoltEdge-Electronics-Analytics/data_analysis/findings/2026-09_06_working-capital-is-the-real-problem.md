# Finding 06 — The working-capital problem is bigger than the P&L: ~$4.4M frozen in inventory

**Decision it informs:** where the CFO should focus to free cash — the analysis says
inventory, not payables or receivables.
**Audience:** CFO, COO.
**Time window:** trailing 12M (2025-07→2026-06) for flow metrics; as-of 2026-06-30 for stocks.

## Question
VoltEdge is break-even on contribution (Finding 03). How much cash is tied up in the
operating cycle, and which lever — inventory, receivables, or payables — releases it?

## Method (both tracks — `parity/06_cash_conversion_cycle.py`, all checks pass)
Per `docs/06 §11`:
- `DSO = SUMX(fps, gross_amount_usd × settlement_lag_days) ÷ SUM(gross_amount_usd)` (all `fact_payment_schedule`)
- `Avg Inventory Value` = mean over snapshot months of `SUM(inventory_value_usd)`; used the **last 12** snapshots
- `COGS Trailing 12M` = `SUM(cogs_usd)` for CY (window ends 2026-06-30)
- `DIO = Avg Inventory Value × 365 ÷ COGS_12M`
- `AP Open` = `SUM(po_value_usd)` where `actual_receipt ≤ asOf < supplier_paid`. The DAX point-in-time
  value is noisy month-to-month ($0.33M at 2026-06-30, a trough); primary DPO uses the
  **mean month-end AP over the last 12** ($2.17M).
- `DPO = AP Open × 365 ÷ COGS_12M`; `CCC = DIO + DSO − DPO`
- SQL: DuckDB aggregates over the parquet; Python: pandas. Parity exact on every component.

## Evidence

| Metric | VoltEdge | Benchmark (`docs/01 §4`) | Read |
|---|---:|---:|---|
| **DIO** | **158 days** | 45–75 | **2× too high — the problem** |
| DSO | 17.8 days | US/EU ~2–4, BR higher | acceptable blended |
| DPO | 41 days | 30–60 | healthy, paid ~1 day past terms |
| **CCC** | **≈ 134 days** (88 on a 24-month inventory basis) | lower is better | driven ~entirely by DIO |

- Average inventory is **rising fast**: 24-month avg $5.85M → last-12-month avg **$8.31M**.
- At the top of the DIO benchmark (75 days) inventory would be ~$3.95M ⇒ **≈ $4.4M of cash
  is frozen in excess stock**. That is ~13× CY contribution margin and ~20% of a full year's
  Net Revenue in the comparable market.
- Payables already run at terms — **no easy cash there**. Receivables are fine except Brazil.

### DSO by market

| Market | DSO |
|---|---:|
| Brazil | **36.7 days** |
| United Kingdom | 17.5 |
| Germany | 14.9 |
| United States | 13.4 |

Brazil's DSO is 3× the US because of 12× "parcelado" installments; the merchant-funded
"sem juros" plans also cost **$114k in CY financing** (`fact_payment_schedule.financing_cost_usd`,
`installment_plan = 'Interest-Free'`). The DSO drag (working capital) is the bigger cost;
the fee is second-order.

## What the data says
1. VoltEdge's cash constraint is a **balance-sheet** story more than a P&L story. The P&L is
   at break-even; the operating cycle locks up ~$8M in inventory and growing.
2. **Inventory is the single lever.** DIO at 158 days on a fast-growing COGS base means
   purchasing is running ahead of demand (see also Finding 09 aged-inventory, planned).
3. Payables and (ex-BR) receivables are already well managed — do not chase them.
4. Brazil trades cash-cycle length for revenue: +$4.6M Net Revenue and the best contribution
   margin (Finding 03), at 37-day DSO and $114k/yr financing. On current numbers that is a
   **good trade**, but it should be monitored as BR scales.

## Limitations & assumptions
- `Avg Inventory Value` basis matters: last-12 months gives DIO 158; the full 24-month
   average gives DIO 111. Both are well above benchmark; the report should fix one basis.
- Point-in-time `AP Open` (DAX literal) is volatile; the 12-month mean is more stable but
   still a modelled proxy for a true daily AP balance.
- COGS trailing 12M == CY COGS only because the window ends exactly at 2026-06-30.
- `settlement_lag_days` drives DSO directly; not independently reconciled to `due_date_key −
   order_date_key` at the row level (spot-checked only).
- No cost-of-capital rate applied — the $4.4M is gross cash, not an interest saving.

## Recommendation
- **CFO priority #1: an inventory-reduction program.** Target DIO 90 within two quarters
   (SKU-level reorder points, kill dead stock — Finding 09). Frees ~$3M immediately, ~$4.4M
   at benchmark. This dwarfs every P&L lever in this analysis.
- Keep paying suppliers at terms; **do not** extend DPO further — it is already fine and
   stretching it risks the reliability the COO depends on.
- Put **CCC and Inventory Value trend** on the Executive Summary, not buried in a Phase-2
   page — it is the most material number in the pack.
- Hold Brazil's installment mix under review; revisit if BR DSO pushes past ~45 days or
   financing cost past ~0.5% of BR Net Revenue.
