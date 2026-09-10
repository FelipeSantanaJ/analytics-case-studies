# Data Analysis — Start Here

Orientation for anyone (human or AI agent) about to analyse the **VoltEdge Electronics**
dataset. This file gives you the paths, the reading order, and the method. It does **not**
tell you which analyses to run — that is the analyst's job.

Two standing rules for this work:
- **Every analysis is built twice — once in SQL, once in Python — and the two must produce
  the same numbers** (§3).
- **It ends in two presentations** (§8): a short *board summary* and an extensive *deep
  dive* that documents every business problem found and analysed.

Everything below is relative to the project root (`VoltEdge-Electronics-Analytics/`).

Save all analysis work under `data_analysis\` (this folder).

---

## 1. Where everything lives

### Data — `data\`
| Path | What it is | Use it for |
|---|---|---|
| `data\raw\` | ~19 source-faithful exports with deliberate mess (bad dates, money strings, encodings, dupes) | Studying data-quality handling; **not** for analysis |
| `data\staging\` | 20 typed, cleaned `stg_*` tables (one per entity) | Tracing a transformation; rarely the analysis surface |
| **`data\curated\`** | **The star schema — 16 dimensions + 12 facts, as `.parquet` and `.csv`** | **This is your analysis surface.** Prefer the `.parquet` files |
| `data\quality\dq_report.md` | Generated data-quality report: what was fixed, what checks pass | Understanding known issues before you trust a column |
| `data\quality\stage_02_metrics.csv` | Row-level fix counts from the cleaning stage | Same |

### Documentation — `docs\`
| File | Read it to learn |
|---|---|
| `01_business_context_kpis.md` | The business, the 4 markets, the money model, and the exact definition of every KPI. **Read first.** |
| `05_data_model.md` | The star schema — bus matrix, every fact's grain and keys, the relationship list. **Read second.** |
| `03_data_dictionary.md` | Every table and every column, with dtype, null-rate and a sample value (auto-generated from the files on disk) |
| `06_dax_measures.md` | How each reported metric is actually calculated (Net Revenue, Gross Profit, Contribution Margin, CCC, comparable-base, …). Your source of truth for "what does this number mean" |
| `08_data_quality.md` | Where issues are handled and which limitations are accepted |
| `04_etl_pipeline.md` | How raw became curated (stage by stage) |
| `07_report_guide.md` | What the Power BI report already shows, page by page |
| `VoltEdge-Electronics-Documentation.pdf` / `…-Summary.pdf` | The above, bundled |

### Reference code — `etl\`
| File | Why you'd open it |
|---|---|
| `config.py` | The single random seed, the window dates, market launch dates, all tunable constants |
| `pbi_measures.py` | The DAX measure logic in one place — the ground truth if a doc and a number disagree |
| `03_build_curated.py` | Exactly how each curated table was assembled (grain, joins, derived columns) |

### The finished report — `powerbi\`
The `.pbip` project and theme. Open it in Power BI Desktop to see the numbers an executive
already sees; use it as a **cross-check**, not a starting point.

---

## 2. The analysis surface (curated star schema)

- **Facts** hold the events (`fact_order_lines`, `fact_orders`, `fact_payment_schedule`,
  `fact_returns`, `fact_purchase_orders`, `fact_inventory_movement`,
  `fact_inventory_snapshot`, `fact_marketing_spend`, `fact_web_traffic_daily`,
  `fact_support_tickets`, `fact_exchange_rate`, `fact_target`).
- **Dimensions** hold the descriptors (`dim_date`, `dim_market`, `dim_customer`,
  `dim_product`, `dim_supplier`, `dim_channel`, `dim_campaign`, `dim_payment_method`,
  `dim_carrier`, `dim_currency`, `dim_warehouse`, plus small attribute dims).
- Join facts to dimensions on the integer surrogate keys (`*_key`). The exact key list per
  fact is in `05_data_model.md` §2.
- **Facts are never joined to each other** — they are different grains of the same business.
  Slice them by shared dimensions instead.
- Every monetary column exists twice: `*_local` (transaction currency) and `*_usd`
  (converted at the transaction-date rate). **Use `*_usd` unless you are specifically
  studying currency mix.**

Minimal load (Python / pandas):

```python
import pandas as pd, pathlib
# repo checkout → VoltEdge-Electronics-Analytics/data/curated
CUR = pathlib.Path(__file__).resolve().parents[1] / "data" / "curated"
def t(name): return pd.read_parquet(CUR / f"{name}.parquet")

ol   = t("fact_order_lines")
dprod = t("dim_product"); dmkt = t("dim_market"); ddate = t("dim_date")
ol = (ol.merge(dprod, on="product_key", how="left")
        .merge(ddate, left_on="order_date_key", right_on="date_key", how="left"))
```

`duckdb` is a good alternative if you prefer SQL over parquet — install with
`pip install duckdb` and `SELECT ... FROM 'data/curated/fact_order_lines.parquet'`.

---

## 3. Environment & the two tracks

- Python 3, `pandas` + `pyarrow` are already available.
- Install the rest: `pip install duckdb matplotlib seaborn jupyter` (SQL engine and plots
  are not installed yet).
- The data is static and seeded (`SEED` in `etl\config.py`) — results are fully reproducible;
  there is no "latest" to refresh.

**Every analysis is done twice, on two tracks, and the results must match:**

| Track | Stack | Reads |
|---|---|---|
| **SQL** | DuckDB (`SELECT … FROM 'data/curated/xxx.parquet'`) | the curated parquet files directly — no DB server |
| **Python** | pandas (or polars) in a notebook / script | the same curated parquet files |

Why both: it forces you to state the logic precisely twice, it catches silent errors (a
join fan-out or a wrong grain rarely breaks *both* implementations the same way), and the
portfolio shows range. Treat a mismatch as a bug on one side — never "close enough" — and
fix it before the finding counts. Compare on a sensible tolerance (exact for counts, rounded
to cents / 1e-6 relative for money and ratios).

---

## 4. How to work like an expert data analyst

Principles, in the order they matter:

1. **Frame before you query.** Decide the *decision* a piece of analysis would inform and
   *who* would act on it. An analysis with no decision attached is trivia.
2. **Learn the business first.** Read `01_business_context_kpis.md` before touching a file.
   You cannot interpret a margin number without knowing this is a thin-margin, growth-stage,
   multi-market business.
3. **Know the grain.** Before you `groupby`, state what one row of the table *is*. Summing a
   column across the wrong grain is the most common silent error (e.g. order-header vs
   order-line, snapshot vs ledger).
4. **Anchor on a known number.** Reproduce one published metric first — e.g. total Net
   Revenue per `06_dax_measures.md` — and match it to the Power BI report. If you can't
   reproduce a known figure, you don't yet understand the data well enough to explore it.
5. **Profile before you analyse.** For every table you use: row count, time coverage,
   null-rate per column, cardinality of keys, obvious outliers, and whether it ties to a
   parent (lines → headers, schedule → order totals). `03_data_dictionary.md` and
   `dq_report.md` give you a head start.
6. **Every number traces to a definition.** When you report "contribution margin", cite the
   formula you used and confirm it against `06_dax_measures.md` (or `pbi_measures.py`).
   Don't invent a second definition of an existing metric.
7. **Segment deliberately, and watch for Simpson's paradox.** This dataset has markets that
   launch mid-window and a shifting channel/category/payment mix — a blended trend can move
   opposite to every segment inside it. Always ask "is this composition or performance?"
8. **Separate growth from expansion.** Raw year-over-year mixes organic growth with new
   markets opening. Use the comparable-base (US-only, like-for-like) cut alongside the total
   — see `01_business_context_kpis.md` §5.
9. **Respect time.** 24-month window, clear current-year vs prior-year split, a Q4 peak, and
   trailing-12-month views to smooth it. State the window on every time-based result.
10. **Correlation is not causation.** Name the plausible confounder before you claim a
    driver. Prefer a decomposition (price / volume / mix) over a hand-wave.
11. **Quantify uncertainty and edge cases.** Report the denominator, flag small-n segments,
    show the distribution not just the mean.
12. **Write down assumptions and limitations** as you go, in the same spirit as
    `08_data_quality.md`. An analysis whose caveats are undocumented is not finished.
13. **One chart, one message.** Lead with the "so what", annotate the point you're making,
    round aggressively at the summary level, keep full precision in the backing table.
14. **Make it reproducible.** A saved notebook/script + its output, re-runnable end to end
    from the curated files.
15. **Do it twice — SQL and Python.** Every number that ends up in a finding is computed on
    both tracks (§3) and the two agree within tolerance. A disagreement is a bug on one
    side; resolve it before the finding counts.

---

## 5. A working loop

```
Orient      → read 01 + 05; skim 03; list the tables you'll touch and their grain
Anchor      → reproduce one known metric; reconcile to the Power BI report
Profile     → EDA on each table: coverage, nulls, cardinality, outliers, parent ties
Explore     → follow a question; keep the query, not just the answer
Cross-check → implement the result in SQL and in Python; assert they match
Segment     → by market / category / channel / cohort / time — test composition vs performance
Synthesize  → what changed, by how much, why, and what's uncertain
Record      → write the finding to findings\ (question, both-track method, result, caveats)
Communicate → roll every finding up into the two deliverables (§8)
```

Iterate. Most findings only hold up after the third "but is that just mix?" check.

---

## 6. VoltEdge-specific gotchas

- **Market launch dates** (in `dim_market.live_date`, also `config.py`): US always-on,
  UK + DE from 2025-01, BR from 2025-07. Any cross-market or YoY total is affected.
- **Cancelled orders** are excluded from most revenue/'cost measures (`order_status <>
  'cancelled'`). Decide explicitly whether your cut should include them.
- **Returns** reduce Net Revenue by the refund amount; COGS of *restocked* goods is credited
  back via `fact_returns.cogs_recovered_usd`. Don't double-count.
- **COGS is moving-average**, rebuilt from purchase-order receipts — it is not a static list
  cost, and it drifts over time.
- **Warranty** is a separate line: `fact_order_lines.line_type = 'warranty'`. Product-only
  cuts must filter it out.
- **Installments**: order-grain totals are in `fact_orders`; the per-tranche cash timing is
  in `fact_payment_schedule` (revenue booked on `order_date_key`, cash received on
  `due_date_key`). That gap is the DSO story.
- **Snapshot vs ledger**: `fact_inventory_snapshot` is *derived* from
  `fact_inventory_movement`. Use the snapshot for point-in-time stock; use the ledger for
  flow.
- **A blank `dim_date` member** can appear where cash settles past the window end — a known,
  documented limitation.
- **`fact_target`** only has rows for months a market was live, and only for Net Revenue,
  Orders, New Customers, Blended CAC, Gross Margin %.

---

## 7. Folder conventions for `data_analysis\`

Keep it consistent:

```
data_analysis\
  00_START_HERE.md          ← this file
  sql\                      ← one .sql per analysis (DuckDB dialect), prefixed 01_, 02_, …
  python\                   ← the matching .ipynb / .py for the same analysis, same prefix
  parity\                   ← scripts that run both tracks for a finding and assert equal
  outputs\
    figures\                ← exported charts (png/svg), dated
    tables\                 ← exported result tables (csv)
  findings\                 ← one .md per business problem (see §8)
  deliverables\             ← the two presentations (see §8)
  utils.py  /  utils.sql    ← shared loaders / helpers (e.g. the star-schema join above)
```

Pair the tracks by name: `sql\04_delivery_time.sql` ↔ `python\04_delivery_time.ipynb`.
Name things so a stranger can tell what they are:
`findings\2026-09_repeat-purchase-by-cohort.md`.

---

## 8. Deliverables — the two presentations

Everything above feeds **two** final documents, both in `deliverables\`:

### 8.1 Board summary — `deliverables\board_summary.*`
- Audience: executives. **Decision-first**, not method-first.
- Short: think 1–2 pages / ~8–12 slides.
- Only the findings that change a decision — each as headline + number + "so what" +
  recommendation, one chart maximum. No SQL, no caveat walls.
- Reuse the report's visual identity (navy / blue / amber) so it sits next to the dashboard.

### 8.2 Deep dive — `deliverables\deep_dive_*`
- Audience: analysts / managers who will act on it. The exhaustive record.
- **One section — or one file — per business problem found and analysed.** Split into
  `deep_dive_01_<slug>.md`, `deep_dive_02_<slug>.md`, … with a `deep_dive_00_index.md`
  once it gets large.
- Each problem covers: context & why it matters · the question · hypothesis · method on
  **both tracks** (SQL + Python, parity check noted) · evidence (charts + backing tables) ·
  what the data says · limitations & assumptions · recommendation.
- The board summary is a distillation of this.

Format is your call (HTML → Chrome print-to-PDF like the `docs\` set, notebook export, or a
deck tool); the structure above is not.

---

## 9. Definition of done (per analysis)

- [ ] The decision it informs and the audience are stated at the top.
- [ ] Grain of every table used is stated.
- [ ] Implemented on **both tracks (SQL + Python)**; results match within tolerance, parity
      check saved under `parity\`.
- [ ] At least one number reconciles to `06_dax_measures.md` / the Power BI report.
- [ ] Segments checked for composition vs performance (Simpson's paradox).
- [ ] Time window stated; comparable-base considered where growth is claimed.
- [ ] Assumptions and limitations written down.
- [ ] Re-runnable end to end from `data\curated\`.
- [ ] One clear headline chart + the backing table.
- [ ] Written up in `findings\`, rolled into the deep dive, and promoted to the board
      summary if it changes a decision.

---

## 10. First five steps

1. Read `docs\01_business_context_kpis.md` end to end.
2. Read `docs\05_data_model.md` §1–§2 (bus matrix + fact grains).
3. Skim `docs\03_data_dictionary.md` for the tables you expect to use.
4. Reproduce **total Net Revenue (USD)** for the full window **in SQL and in Python**,
   confirm the two match each other, then check them against the Power BI Executive
   Summary page. This sets up the dual-track habit on a known number.
5. Profile the two or three tables you'll start with (coverage, nulls, cardinality, outliers).

Only after those five: pick a question and follow it.
