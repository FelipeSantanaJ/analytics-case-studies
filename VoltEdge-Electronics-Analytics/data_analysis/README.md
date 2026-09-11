# VoltEdge — data_analysis

Analysis of the curated star schema (`../data/curated/*.parquet`). Every result is built
**twice** — DuckDB SQL and pandas — and the two must agree (parity scripts).

## Layout
```
utils.py                     shared loaders, theme palette, assert_close(), setup_mpl()
parity/NN_*.py               runs BOTH tracks for a finding and asserts equality  <- run these
python/NN_*_figure.py        the headline chart for that finding
sql/01_anchor_net_revenue.sql  reference SQL (DuckDB dialect)
findings/2026-09_NN_*.md      one write-up per business problem (decision / method / evidence /
                             limitations / recommendation)
outputs/figures/             exported PNG charts (dated)
outputs/tables/              exported backing tables (csv)
deliverables/                board_summary.{html,pdf} + deep_dive.{html,pdf} + build script
```

## Run everything
```bash
pip install duckdb matplotlib seaborn pandas pyarrow
for f in parity/*.py; do python "$f"; done          # all must print ALL PARITY CHECKS PASSED
for f in python/*_figure.py; do python "$f"; done    # regenerate charts
python deliverables/build_deliverables.py            # rebuild the two HTML deliverables
# PDF: open each .html in Chrome -> print to PDF (or headless --print-to-pdf)
```

## Findings (all parity-verified)
| # | Title | Headline |
|---|---|---|
| 00 | Anchor — Net Revenue | $31.35M (24m); reproduces the DAX exactly on both tracks |
| 02 | Growth is mostly expansion | +137% total vs **+40% US like-for-like**; US −2% vs plan (not distinguishable from month-to-month noise, p=0.90) |
| 03 | Contribution margin | Break-even (+$325k CY vs −$365k PY); UK the only negative market |
| 04 | US growth is all volume | +110% volume, +8% price, −17% mix (into thin-margin Smartphones) |
| 05 | Promo depth | Promo days earn $372 gross profit vs $5,680 → ≈ −$308k/yr [95% CI: −$379k, −$242k] |
| 06 | Working capital | CCC ≈ 134d, all inventory; **~$4.4M cash freeable**; BR DSO 37d |
| 07 | CM depends on cheap CAC | +$325k at $26.91 CAC; **−$51k at the $32.80 plan CAC** |
| 08 | Retention | Repeat rate 37.6% (above bm) but decays fast; 16% vs 44% reconciliation |
| 09 | Returns | 8.0% rate (fine); **$1.65M net margin drag**, 63% controllable, restock 54% |
| 10 | Fulfilment | On-benchmark; only lever = shipping-fee recovery 28% (BR 5%) ≈ $0.6M/yr |

Reconciled: the anchor is **$31.35M** ($31,347,077), identical on both tracks, and is the
figure of record.
