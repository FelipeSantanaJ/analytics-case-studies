# Finding 00 — Anchor: Net Revenue (USD) reproduced on both tracks

**Decision it informs:** none directly. This is the calibration step — prove the grain and
the DAX definitions are understood before exploring, and set up the SQL+Python dual-track
habit on a known number.
**Audience:** the analyst (me).
**Time window:** full 24-month extract, 2024-07-01 → 2026-06-30.

## Question
Can I reproduce **Net Revenue (USD)** exactly as `docs/06_dax_measures.md` defines it, on
both the DuckDB (SQL) and pandas (Python) tracks, and does it tie to the published report?

## Method (both tracks — parity check `parity/01_anchor_net_revenue.py`)
Per `docs/06`:
- `Gross Sales (USD)` = `SUM(fact_order_lines.net_amount_usd)` where `order_status <> 'cancelled'`
- `Returns (USD)`     = `SUM(fact_order_lines.refund_amount_usd)` where `order_status <> 'cancelled'`
- `Net Revenue (USD)` = Gross Sales − Returns

**Grain of `fact_order_lines`:** one row per order line (order × product), plus a
`line_type = 'warranty'` add-on line on some orders. 276,962 rows; after removing
`order_status = 'cancelled'` → 275,020 lines / 167,214 distinct `order_id`.

## Result — the two tracks agree to sub-cent

| Metric | Value |
|---|---:|
| Gross Sales (USD) | $34,803,648.93 |
| Returns (USD) | −$3,456,571.79 |
| **Net Revenue (USD), full window** | **$31,347,077.15** |
| Net Revenue — Current Year (2025-07→2026-06) | $22,046,677.12 |
| Net Revenue — Prior Year (2024-07→2025-06) | $9,300,400.03 |
| Orders (`fact_orders`, non-cancelled, distinct) | 167,396 |
| AOV = Net Revenue ÷ Orders | $187.26 |

By market (full window): US $17.62M · UK $4.86M · BR $4.59M · DE $4.28M.

Parity: every line — counts exact, money within 1e-6 relative (largest abs diff $0.00004,
floating-point summation order only).

## Reconciliation to the published report
- The DAX **formula** is reproduced exactly (both tracks).
- Net Revenue computed here: **$31.35M** ($31,347,077), identical on both tracks. This is
  the figure of record for this dataset (parquet files rebuilt 2025-08-31).

## Caveats / notes for later
1. **Header vs line grain gap.** `fact_orders` has 167,396 non-cancelled orders;
   `fact_order_lines` has 167,214 distinct non-cancelled `order_id` — a 182-order gap
   (0.1%). The DAX `[Orders]` measure counts on `fact_orders`, so AOV's denominator is
   167,396. Do not count orders off `fact_order_lines`.
2. **`order_status` in `fact_order_lines`** only ever takes `delivered` or `cancelled` in
   this build — there is no separate `returned` status; returns are carried as
   `refund_amount_usd` / `returned_qty` columns on the delivered line.
3. **AOV ≈ $208** in `docs/01 §12` is `fact_orders.net_amount_usd ÷ orders` (pre-returns,
   order grain) = $208.30 here. The DAX-consistent AOV (Net Revenue ÷ Orders) is $187.26.
   Use $187 when citing the measure.
4. All of `fact_order_lines` falls inside `in_extract_window`; no window filter needed.

## Status
✅ Grain stated · ✅ both tracks, parity saved · ⚠️ report reconciliation ~1% (narration,
open item) · n/a segmentation · ✅ window stated · ✅ re-runnable from `data/curated/`.
