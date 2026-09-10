# Walkthrough — What Was Built, Step by Step

The running narrative of the project: each entry records what was done, why, and where to
look. Newest work at the bottom.

---

## Step 0 — Scoping (done)

Decisions locked with the stakeholder:

| Decision | Choice |
|---|---|
| Deliverable language | English |
| Power BI environment | Power BI Desktop available; deliver as `.pbip` (PBIR) + report |
| Data scale | Robust: ~3 years, ~30k customers, ~150k orders, ~300 SKUs |
| Data-engineering depth | Raw (messy, multi-source) + Python ETL + architecture diagram |
| Market scope | Multi-country / multi-currency: US, UK, DE, BR |
| Curated storage | CSV + Parquet (no Excel workbook) |
| Phase 1 scope | Foundation + 3 pages: Executive Summary, Sales Performance, Marketing & Acquisition |

## Step 1 — Project scaffold (done)

Created the folder structure (`docs/`, `etl/`, `data/{raw,staging,curated,quality}/`,
`powerbi/`, `assets/`) and the top-level [`README.md`](../README.md).

## Step 2 — Business context & KPI framework (done, awaiting review)

Wrote [`01_business_context_kpis.md`](01_business_context_kpis.md): company profile, market
expansion timeline, product catalog and margins, business model & financial definitions,
embedded seasonality, stakeholder personas, and the full KPI framework (definitions +
benchmarks) across Sales, Marketing, Web, Logistics and CRM. (Assumptions later resolved
in §12.)

## Step 3 — Data architecture (done, awaiting review)

Wrote [`02_data_architecture.md`](02_data_architecture.md): medallion design principles,
layer-by-layer spec, source-system inventory (10 simulated systems), the catalogue of
data-quality issues to inject, tech stack, run instructions, and naming conventions.
Includes the Mermaid architecture diagram.

## Step 3a — Scope revision after stakeholder feedback (done)

Stakeholder adjustments folded into `01` and `02`:

- **Extract window shortened to 24 months** (2024-07-01 → 2026-06-30) for a clean YoY;
  expansion dates moved *inside* the window (UK+DE 2025-01, BR 2025-07) so **Total vs
  Comparable Base (US like-for-like)** analysis is possible. New `01` §5.
- **Payments deepened**: `dim_payment_method` with MDR by scheme, fixed fees, settlement
  lag; `fact_orders` + `fact_payment_schedule` (instalment tranches); interest-free
  merchant-funded vs customer-funded plans. New `01` §3.
- **Procurement & inventory added**: `dim_supplier` (Net 30/45/60 terms, lead time),
  `fact_purchase_orders`, `fact_inventory_movement` ledger → derived `fact_inventory_snapshot`;
  moving-average COGS; DIO/DSO/DPO/**CCC** and a company cash-flow timeline. New `01` §4.
- Source systems grew from 10 to 12 (added PSP and Procurement). `02` §2–4 updated,
  Mermaid diagram redrawn.
- All open assumptions resolved — `01` §12.

## Step 4 — ETL pipeline built and run (done)

`etl/` now holds the full four-stage pipeline (`config.py`, `utils.py`,
`01_generate_raw.py`, `02_clean_stage.py`, `03_build_curated.py`, `dq_checks.py`,
`run_pipeline.py`, `gen_data_dictionary.py`). Seeded, reproducible, ~10 min end to end.

- **Raw** — 19 files / 12 simulated source systems with injected mess (category
  spellings ×3, money strings, 5 date formats + Excel serials, Latin-1 BR file, 6 SKUs
  omitted from the ERP master, mislabelled PSP fee column, snapshot-vs-ledger drift,
  negative sessions).
- **Staging** — 20 typed `stg_*` tables; every fix counted into DQ fragments.
- **Curated** — 16 dims + 12 facts (Parquet + CSV). Moving-average COGS from PO receipts;
  `fact_payment_schedule` explodes instalments; `fact_inventory_snapshot` derived from the
  movement ledger; USD conversion on every money column; `is_comparable_base` = US.
- **DQ gate** — all HARD checks pass: no null keys, full referential integrity,
  `net = gross − discount`, lines roll up to headers, payment schedule ties to order
  totals, comparable base = US, FX sane, volume/AOV/margin bands.

Calibrated over 4 regen passes. Final realised numbers: 294 SKUs · ~103k customers ·
~158k orders · ~262k lines · AOV **$208** · blended gross margin **14.2%** · return rate
**7.8%** · MER **7.6×** · blended CAC **$47** · repeat rate **40%** · inventory turnover
**~5×** · YoY **Total +140%** vs **Comparable-Base +36%**.

## Step 5 — data documentation (done)

- [`03_data_dictionary.md`](03_data_dictionary.md) — **auto-generated** by
  `etl/gen_data_dictionary.py` from the files on disk (raw + staging + curated, 1,186 lines).
- [`04_etl_pipeline.md`](04_etl_pipeline.md) — stage-by-stage narrative + techniques.
- [`05_data_model.md`](05_data_model.md) — bus matrix, fact grain & measures, dimension
  attributes, cross-cutting decisions, Power BI relationship list.
- [`08_data_quality.md`](08_data_quality.md) — where issues are handled + the generated
  `data/quality/dq_report.md` + accepted limitations.

## Step 6 — Power BI semantic model (done)

`etl/gen_semantic_model.py` generates the whole `.pbip` project from the curated Parquet
schemas (model-as-code):

- **`powerbi/VoltEdge Electronics.SemanticModel/`** — TMDL: 28 data tables (16 dims + 12
  facts) each with a `Parquet.Document` import partition driven by a `pDataFolder`
  parameter; `database.tmdl`, `model.tmdl` (auto date/time **off**), `expressions.tmdl`,
  `relationships.tmdl` (**65 relationships**, secondary date roles inactive), plus
  disconnected helpers `Reporting Currency` and `Funnel Stage`.
- **`_Measures` table — 145 DAX measures** from `etl/pbi_measures.py`, in 14 display
  folders: Sales · Time Intelligence · Comparable Base · Targets · Reporting Currency ·
  Payments & Cash · Price/Volume/Mix · Marketing · Website & Funnel · Logistics ·
  Working Capital · CRM · Support & Returns.
- **`powerbi/VoltEdge Electronics.Report/`** — PBIR scaffold (7 pages, theme
  `powerbi/theme/VoltEdge.json`), verified: `pbir` loads the local model and validates
  **233 field references** with no errors.

## Step 7 — Report pages (done)

`etl/gen_report_visuals.py` emits per-page `--from-json` bundles; applied with the `pbir`
CLI. **7 pages, 93 visuals**: Executive Summary · Sales Performance · Marketing &
Acquisition · Website & Digital · Logistics & Fulfillment · CRM & Customer · Product &
Inventory. `pbir validate --all` → **Valid** (cosmetic warnings only: compact KPI cards,
alt text, exec-page density). Layout and per-page rationale in
[`07_report_guide.md`](07_report_guide.md).

## Step 8 — Measure & report docs (done)

- [`06_dax_measures.md`](06_dax_measures.md) — **auto-generated** from `pbi_measures.py`:
  every measure with its DAX and format string, grouped by display folder.
- [`07_report_guide.md`](07_report_guide.md) — model overview, page-by-page walkthrough,
  the polish backlog, and how to verify in Desktop.

## Step 9 — Visual design pass (done)

Stakeholder feedback: "visuals too raw (white on white, square corners), review the whole
graphical layer, create and apply a company colour theme."

- **Design identity committed** — corporate tone, one accent (electric blue = current
  period, amber = prior year), muted neutrals, quiet gridlines. Signature: title band +
  right-side slicers + one 6-KPI row + two content rows on the detail gradient.
- **Comprehensive theme** `powerbi/theme/VoltEdge.json` — brand palette, semantic
  good/neutral/bad, six text classes, and `visualStyles` for 15 visual types + `page`
  (light `#F4F7FB` ground, white cards, 12 px radius, **no drop shadow**, axis titles off,
  value gridlines `#EEF1F6`, top-centre legends, clean tables). `pbir theme validate` passes.
- **Report rebuilt leaner** — canvas 1280×720; every page now = title + 2 slicers + 6 KPI
  cards + 4 content visuals (Exec has 5). **92 visuals, 0 overlaps**, `pbir validate --all`
  → Valid (warnings only: compact cards, one 4-series chart).
- **Measures fixed** — `New Customers` / `New Customer Revenue` / `Repeat Purchase Rate`
  now key off `dim_customer[customer_key]` so the new-vs-returning split propagates to
  `fact_order_lines`; `DATESYTD` year-end set to `"06-30"`.
- One command rebuilds the whole report: `cd powerbi && bash build_report.sh`.

## Step 10 — Design pass 2 (stakeholder feedback)

Feedback after opening in Desktop: model loaded past the TMDL errors; some measures still
error; "better, but needs more punch; cards have a duplicate label and feel cramped; put
the date axes in ascending date order."

- **Duplicate KPI label removed** — `card.*.categoryLabels.show = false` (the visual title
  is the label); KPI value 24 → 32 pt; card height 84 → 100 px so the number breathes.
- **Header signature** — every page gets a `#EEF3FB` header zone with a `#1F6FEB` brand
  accent rule beneath it, title on the band. `shape` styling folded into the theme.
- **Date axes ordered** — `dim_date` now carries hidden `month_sort` / `quarter_sort`
  keys and `sortByColumn` on `month_year` / `month_name` / `quarter_name` / `day_name`;
  every time-series visual also gets an explicit ascending `pbir visuals sort`.
- **Measures** — `New Customers` / `New Customer Revenue` / `Repeat Purchase Rate` /
  `Customers with Orders` / `Active Customers` re-keyed to `dim_customer[customer_key]`
  so the filter propagates to `fact_order_lines`; `DATESYTD` → `"06-30"`.

`bash powerbi/build_report.sh` → theme valid, model loads, 215 fields resolve, no errors.

## Step 11 — Design v2: deep blue + logo

Stakeholder: "better; go darker blue; create a company logo and put it top-left of every page."

- **`etl/gen_logo.py`** (Pillow) generates the VoltEdge mark — a lightning-bolt icon +
  "VOLT" / "EDGE" wordmark — as `powerbi/assets/voltedge-logo-light.png` (for the navy
  bar), `-dark.png` and an icon-only variant.
- **Theme v2** — deep blue `#123E6E` primary, navy `#0E2A4E` header, amber `#D99311`
  comparison, mid-blue `#2E70B0` second series; cooler `#EAEFF6` page ground; KPI value
  32 pt deep blue.
- **Header** — every page now has a 56 px navy bar with the logo top-left and a `#2E70B0`
  accent rule; the page title and the two slicers sit on the line below.
- `bash powerbi/build_report.sh` → theme valid, model loads, 215 fields, **no errors, no
  real content overlaps** (only the expected decorative header-band overlaps).

## Step 12 — v3: header image, combo charts, date filter, richer seasonality

Stakeholder: logo not rendering; title poorly placed (wants it on the navy bar in a light
colour); dual-axis for discrepant-scale chart pairs; a date filter to pick the analysis
base month; and the data is too smooth — add seasonality to revenue, cash, sessions, and
new-vs-returning (so those lines cross more than once); the funnel's 500M→9M drop is
extreme.

- **Header is now one image per page** (`etl/gen_logo.py` → `assets/header-<slug>.png`):
  navy bar with the white bolt + `VOLTEDGE` wordmark + divider + page title + a `#2E70B0`
  accent rule. Fixes the un-rendered image visual *and* puts a light-on-dark title on the
  bar. The band shapes + separate logo + title textbox are gone.
- **Combo charts** — every "big number + ratio" pair (sessions/CR, delivery-days/on-time,
  spend/ROAS, revenue/margin%, inventory-value/weeks-of-cover, RPS/CR) is now a
  `lineClusteredColumnComboChart`: the magnitude as bars, the ratio as a line on a
  secondary axis.
- **Analysis-period slicer** — a date-range slicer (`dim_date[date]`) on every page, so
  KPIs and point-in-time measures (inventory, receivables) are "as of" the chosen range
  end rather than always the latest data.
- **Data seasonality** (`etl/config.py`, `etl/01_generate_raw.py`): deeper monthly
  seasonality curve, a slow demand wave, ±10% month noise, and occasional hot/soft
  months; `RETURNING_ORDER_SHARE` now oscillates so new- and returning-customer revenue
  weave and cross several times. Cash-received / revenue-booked and sessions inherit the
  shape from orders.
- **Funnel** rebuilt as the **on-site funnel** — Sessions → Add-to-Cart → Cart → Orders
  (sane ~100/12/8/2 ratios). Media metrics (impressions, clicks, CTR) stay as cards.

## Step 13 — v4: profitability logic, budget everywhere, chart re-evaluation

Stakeholder feedback (contribution margin too negative, illegible filters, "vs budget" on
every KPI, add Orders to Sales, more delivery variance, explain booked vs cash, is 100 %
of new revenue from marketing?, inventory chart only shows one month, re-evaluate every
chart, grow the page if needed).

**Data / model**
- **Returns COGS double-count fixed** — `fact_returns` now carries `cogs_recovered_usd`
  (restocked → full moving-avg cost back, scrapped → 25 % salvage); `Gross Profit` credits
  it. ~$2 M swing. Blended gross margin 14 % → **19 %**, contribution margin −18 % → **−4 %**
  (near break-even in normal months, dips in the Q4 promo pushes — the CM bridge shows why).
- Category margins +5 pp, `TARGET_MER` 8.5 → 10.
- **Booked vs cash gap made real** — an 8 % processor **rolling reserve** released at +90 d
  on card/wallet/BNPL volume, on top of settlement lag and BR instalments. Cumulative gap
  ≈ 5–7 % of revenue, now visible.
- **Delivery variance** — smooth monthly logistics-stress (AR-1) + carrier-crisis months +
  a heavy/oversized-item effect. Avg delivery days ≈ 5.6 (range 4.3–8.5); on-time % 81 %
  (range 38–95 %).
- New measures: `Returns COGS Recovered`, `CM Bridge Value` (+ `PL Line` helper table),
  `Revenue Booked/Cash Received (Cumulative)`, `Booked − Cash Gap`,
  `Inventory Value / Weeks of Cover (Month-End)`, `% New Customers via Paid`,
  `… vs Target %` for Orders / New Customers / Blended CAC / Gross Margin %.

**Report**
- Canvas **1280 × 860**. Header stays a single navy image; **slicer row** with a wide
  date-range slicer + Currency/Market as **horizontal tiles** (readable).
- **KPI tiles are `kpi` visuals** (value + plan Goal + trend sparkline) wherever a target
  exists; `card` otherwise. Executive Summary carries a **Budget scorecard** table.
- **Contribution margin bridge** waterfall replaces the flat CM-% line.
- **Every chart re-evaluated** (see `07_report_guide.md`): Sales gets Orders + cumulative
  booked-vs-cash; Marketing gets *New customers by acquisition channel* + on-site funnel;
  Product & Inventory swaps the revenue×margin combo for *margin % by category* +
  *return rate % by category*, and the inventory trend uses month-end measures so **all**
  months render.

`bash powerbi/build_report.sh` → theme valid, model loads, 244 fields resolve, no errors,
no real overlaps.

## Step 14 — v5: fixes to the fixes

Stakeholder feedback on v4 (budget scorecard broken; PY missing on the exec trend; Nov CM
crater; want a revenue-vs-plan bridge too; booked-vs-cash should be monthly and the gap
bigger; want vs-plan by category on Sales; want an AI-fed insights section; campaign
orders/revenue nonsensical; delivery-days range still too wide; cards should show only the
% vs plan, not the target number — all in English).

- **Budget scorecard** — was repeating the grand total on every row (`dim_metric` on rows +
  measures that don't vary by metric). Rebuilt with `Budget Actual` / `Budget Target` /
  `Budget Attainment %` — `SWITCH` on the row's metric; CAC scored as lower-is-better.
- **KPI cards** — dropped the `kpi` visual (it forces the goal number). Back to `card` with
  two values: the metric + its `… vs Target %`. English throughout.
- **Exec net-revenue trend** — visual filter to `date ≥ 2025-01`, so the prior-year overlay
  covers most of the plot (PY only exists from 2025-07 in a 24-month extract).
- **Nov CM crater** — in promo months the generator now **pulls marketing back ~30 %**
  (demand is already there) and promo discount depth is ~25 % lighter. Monthly CM % went
  from ~−14 % in the Q4 pushes to ~−7 %, most months −1 to −3 %; blended −2 %. New
  **`Contribution Margin % (Trailing 12M)`** line on the Exec page shows the improving,
  toward-break-even trend without the Q4 spikes.
- **Revenue-vs-plan bridge** — new `Revenue Bridge` helper table + `Rev Bridge Value`:
  waterfall Plan → ± each market's variance → Actual, next to the CM bridge on Exec.
- **Booked vs cash** — back to **monthly** (not cumulative); processor rolling reserve
  8 % → **14 %**, released at 75 d; card settlement +2 d. The monthly gap now swings ±10–25 %
  (peak months collect less than they book; trough months collect the reserve/instalment
  tail). Shown as clustered bars + a receivables-outstanding line.
- **Sales — revenue vs plan by category** — `fact_target` has no category grain, so a new
  measure allocates the month/market Net Revenue target to categories by their revenue
  share; waterfall on the Sales page.
- **AI insights** — a native **AI Narratives (Smart Narrative)** visual on the Exec page:
  auto-generated summary that updates with the date slicer and every filter, ships in the
  `.pbip`, no external key. Productizable as-is.
- **Campaign table** — orders/revenue aren't campaign-attributed in the data (no order↔
  campaign link; would need MTA). Table now shows media metrics only — Spend, Impressions,
  Clicks, CTR %, CPC. Limitation documented.
- **Delivery variance** — logistics-stress amplitude cut, carrier-crisis spikes made mild,
  bulky-item effect shrunk, carrier base days compressed. Avg delivery days ≈ 5.5 (monthly
  4.6–7.5, was 4.3–10.9).
- **Buffer months** — `in_extract_window = true` page filter on every page removes the
  pre-window dim_date rows from the axes.
- Canvas **1280 × 900** to fit the narrative band.

`bash powerbi/build_report.sh` → theme valid, model loads, 265 fields resolve, no errors,
no real overlaps.

## Step 15 — v6: broken filter, header, and a real profitability trajectory

v5 opened with several visuals broken. Causes and fixes:

- **`in_extract_window` page filter broke every page** (boolean column + a string
  `"true"` categorical value → "Algo está errado com um ou mais filtros", cascading to all
  visuals). Replaced with a string calc column `dim_date[period_label]`
  ("Analysis window" / "Buffer") filtered categorically — safe.
- **Header images not rendering** — `imageScaling.imageScalingType` was `Normal`; set to
  `Fit` on every header image and in the theme.
- **Budget scorecard** — one table column can't format $ + count + % rows. Added
  `Budget Actual (fmt)` / `Budget Target (fmt)` string measures that `FORMAT` per row;
  table total turned off.
- **CM "improving" was invisible because it wasn't improving** — real trailing-12M CM %
  was flat at ~−2.5 %. Engineered a genuine trajectory in the data: **marketing
  efficiency ramps over the window** (`TARGET_MER` 6.5× → 14×, so spend falls from ~15 %
  to ~7.6 % of revenue) and **unit costs drift down ~0.4 %/mo** (procurement scale
  economies). Result: monthly CM % **−6.5 % (Jul-24) → +4.2 % (Jun-26)**; trailing-12M
  **−3.4 % → +1.9 %**; blended ≈ break-even. The Exec CM chart is now a combo — monthly
  bars + the trailing-12-month line so the upward trend is unmistakable.
- **Delivery days** — `PEAK_DELAY_INFLATION` 1.6 → 1.22, promised buffer +1 d: monthly
  avg now **4.7–6.3 d** (was 4.6–10.9); on-time 91–100 %.
- Removed the `eff` reference left dangling in `gen_marketing` (had halted stage 01).

`bash powerbi/build_report.sh` → theme valid, model loads, 266 fields resolve, no errors,
no real overlaps.

## Step 16 — v7: kill the fragile bits

v6 still had broken visuals. Root causes were the workarounds themselves:

- **The page filters I added broke the pages.** `dim_date[period_label]` (a calc column)
  as a page filter and `dim_date[date] ≥ 2025-01` on `exec_trend` both threw
  "Algo está errado com um ou mais filtros", cascading to the KPI cards. **Removed every
  added filter.** The pre-window buffer months are not actually an axis problem (the
  time-series visuals join on `order_date_key`, which only has in-window rows).
- **The image-header approach is unreliable through `pbir`** on a hand-generated PBIR —
  Desktop shows "no image selected" even with the resource registered. Replaced with a
  plain **`shape` header strip** (`#E7EDF7`) + a `#123E6E` accent rule + a `pbir add title`
  textbox (dark text on the light strip). No image resources, always renders.
- **AI Narratives visual needs a manual "Personalizado" click** to activate (or Copilot).
  Replaced with a **dynamic insight `card`** bound to a new `[Exec Insight]` text measure:
  a one-paragraph summary (net revenue, YoY total + like-for-like, vs plan, gross &
  contribution margin, trailing-12m CM and its verdict, CAC, repeat rate, on-time) that
  **updates with the date slicer and every filter**, no interaction, ships in the file.
  Smart Narrative remains available for anyone who wants to add it.
- **Build hardened** — `build_report.sh` now resets and retries a page if a OneDrive/AV
  file lock corrupts its bundle mid-write (this had left the Sales page half-built).

`bash powerbi/build_report.sh` → theme valid, model loads, 244 fields resolve, no errors,
no real overlaps (only the header shapes sit behind the title, by design).

## Step 17 — v8: the real root causes

v7's "fixes" were built on a broken toolchain. Found and removed the actual causes.

- **`pbir` 0.9.29 was silently corrupting every multi-measure KPI card.** Each card that
  shows a value plus its "vs plan %" got an *empty* `Advanced` filter injected per measure.
  An empty filter → "Algo está errado com um ou mais filtros" → the card renders as a dead
  "Ver detalhes" tile. That was the "visuais quebrados". Upgraded to **`pbir` 0.9.31**,
  which builds these cards clean. Verified: no `filterConfig` on any KPI card now.
- **`pbir` 0.9.31 needs the .NET ADOMD client** (it now schema-checks every field binding).
  Not on PATH here → `add visual --from-json` threw `NameError: AdomdConnection` and added
  *zero* visuals. `build_report.sh` now exports
  `PBIR_ADOMD_DIR="/c/Program Files/Power BI Report Builder"`.
- **Header is a real image again.** Reverted the v7 shape-strip hack. Each page gets
  `assets/header-<page>.png` as an `image` visual across the top (x0 y0 1280×60); the PNG
  already carries the bolt + VOLTEDGE + page title + rule. 0.9.31 registers the resource
  in `report.json` correctly — the earlier "no image selected" was a 0.9.29 bug.
- **Date slicer is usable.** Was sitting on the raw `date` column with a stray empty
  filter and no control. Now a **`Between` range slider** ("Analysis period"); currency /
  market are horizontal tiles. Header row grew to fit (slicers y72 h64, KPIs y148,
  content starts y352/y556). Removed "(trailing 18 months)" from the revenue chart title.
- **Delivery days back in the 4–5 band.** `PEAK_DELAY_INFLATION` 1.22 → 1.06 (killed the
  Q4 spike to ~7), tighter logistics-stress band, transit σ 0.8 → 0.6. Result: every
  month 4.5–4.9, overall 4.67.
- **On-time delivery engineered to ~93%.** With the calmer transit, nothing was ever late
  (flat 99–100%). Added `SLIGHTLY_LATE_SHARE = 0.055`: a seeded slice of orders has its
  *promise* pulled in so the (unchanged) delivery lands 1–2 days past it. Result:
  on-time 92–94% by month (overall 93.3%), ~6.7% of orders 1–2 days late; average
  delivery time stays 4.5–5.1 days (overall 4.81).
- **`pbir` 0.9.31 mangles `—` in visual *titles*** (writes `â€"`) and its `--from-json`
  field resolver won't bind a measure whose name contains `" - "`. So every report title
  and ~12 measure names were made fully ASCII (`Funnel — Value` → `Funnel Value`,
  `PVM — Price Effect` → `PVM Price Effect`, `CLV — Gross Profit` → `CLV Gross Profit`,
  `Booked − Cash Gap` → `Booked vs Cash Gap`, etc.). Field bindings themselves keep
  working; it is only the title literal and the `" - "` separator that break.
- **`pbir` 0.9.31 validates `add visual` fields against the *running* Desktop's live
  model, not the TMDL on disk.** With Desktop open on the report, every renamed/added
  measure reads as "not found in model" and the page builds with only its header.
  `build_report.sh` now aborts if `PBIDesktop.exe` / `msmdsrv.exe` is running — close
  Desktop, build, reopen.

`bash powerbi/build_report.sh` (Desktop closed) → 7 pages, 103 visuals, 244 fields,
0 errors, 67 advisory warnings (dense KPI tiles + short slicers, all by design). Header
images registered + referenced on all 7 pages.

## Step 18 — v9: verified against the running canvas

With the Desktop bridge on, screenshotted all 7 pages and fixed what the JSON couldn't show.

- **The header image *visual* never renders a bound RegisteredResource through `pbir`** —
  Desktop shows "select an image". A **page background image** does render. Header is now a
  full-canvas `pagebg-<slug>.png` (1280×900: navy brand band on top, `#EAEFF6` below) set
  via `pbir pages background`. `gen_logo.py` emits it; `build_report.sh` applies it and the
  `image` visual is gone.
- **The classic `card` visual shows exactly one field.** The "value + vs-plan %" cards were
  the "Ver detalhes" tiles all along (not the 0.9.29 filter bug — that was real but
  separate). Live fix: KPI cards reverted to single-measure (all 7 pages render clean).
  Generator fix for the next rebuild: each KPI tile is a value card **plus a small "vs plan"
  delta card** beneath it where a plan target exists; KPI band height re-flowed
  (value h58 @ y148, delta h34 @ y208, content from y250).
- **`kpi` visual type rejected** — it shows the *last* trend point, not the period total
  ($1.9M not $29.5M), and went blank for CAC / New Customers. Not used.
- **Grand-total rows** removed from the four `tableEx` visuals (`total.totals = false`).
- **Narrow monthly combo charts scrolled** (24 bars in a 4-col slot). `sal_cash` and
  `mkt_trend` widened to 8 cols in the generator; `sal_planbridge` dropped to make room
  (revenue-vs-plan is still on the exec page, by market).
- **Stale data in Desktop.** `.SemanticModel/.pbi/cache.abf` is Power BI's imported-data
  snapshot; reopening the `.pbip` reuses it instead of re-reading the current parquet, so
  the canvas still showed the pre-fix delivery numbers. `build_report.sh` now deletes
  `cache.abf`; until a rebuild, hit **Atualizar** in Desktop to re-import.

Live report (via `pbir` mutations, no rebuild): headers on all 7 pages, KPI rows clean,
table totals gone, chronological sorts, exec Budget scorecard trimmed to
metric / Actual / Attainment % (this is the "vs budget" until the delta cards land),
`crm_cohort` filtered to the 24 in-window months. After the stakeholder hit **Atualizar**
the fresh data showed: delivery 4.8 d/mo (no Q4 spike), on-time 93.9% (waving 93-95%),
gross margin 18.3%, contribution margin at break-even, CM% trend visibly rising.

Known, deferred to the rebuild / ETL:
- `dim_date[month_year]` surfaces a blank "(Em branco)" member on `log_cash` (a fact date
  key falls outside the 2024-2026 dim_date span — `Cash Received` settling past 2026-06).
  Fix in ETL: widen `DIM_DATE_END` or clamp payment/PO date keys.
- `sal_cash` / `mkt_trend` still narrow with a scrollbar (generator widens them to 8 cols).
- KPI cards have no inline vs-plan yet (generator adds the delta sub-cards).

## Step 19 — v10: stakeholder review round

Screenshot review with the stakeholder. Points raised and how each was handled:

- **Slicers showed no options.** The row was 64 px tall — a Between slider and Dropdown
  buttons need more. Page canvas grown to **1280 × 1000**; slicer row is now 92 px, KPI
  row 72 px, content rows re-flowed. Date slicer = `Between`, currency/market = `Dropdown`.
- **KPI values were clipped.** Value cards back to a real height (72), value type 30 pt;
  the "vs plan %" delta card sits underneath (28 px) where a plan target exists.
- **"+44% YoY but −10% vs plan — does that make sense?"** It didn't: the old plan was
  `actual ÷ attainment(0.9–1.1)` every month — a plan with no link to prior-year growth,
  effectively "actual + 11%". Reworked `gen_targets`: current-year months are planned as
  the **prior-year actual grown by `PLAN_YOY_GROWTH` (40%)**; pre-CY months sit near
  actual. So a +44% YoY delivery now lands a few points **ahead** of a 40%-growth plan,
  with monthly attainment swinging on `PLAN_MONTH_NOISE`.
- **Data labels.** Added at theme level for bar/column/line/combo/waterfall (9 pt); the
  five dense 24-month time-series keep labels off so the axis stays readable.
- **"Explain the logistics working-capital chart."** It plots the Cash Conversion Cycle
  by month — **DIO** (days of stock held) + **DSO** (days from sale to cash) − **DPO**
  (days taken to pay suppliers) = **CCC** (net days cash is tied up). It was mis-scaled:
  DIO/DPO divided a one-month inventory/payables balance by a *trailing-12-month* COGS, so
  in the first year (window not yet full) the denominator was tiny and the bars blew up to
  ~3,000 "days". Fixed to a period-consistent formula
  (`balance × days-in-period ÷ COGS-of-that-period`). Also cut `TARGET_WEEKS_OF_COVER`
  5 → 3 so inventory (and therefore DIO) sits in a believable band.

## Next

- [ ] **`bash powerbi/build_report.sh` → open the `.pbip`** (Desktop already closed) for
      the v10 layout + rebased plan + fixed CCC measures + fresh data.
- [ ] ETL: kill the blank dim_date member feeding `log_cash`.
- [ ] Alt text pass; trim curated CSVs; finalise README; sync to Google Drive.
- [ ] Step 5 — `02_clean_stage.py`, `03_build_curated.py`, `dq_checks.py`, run pipeline
- [ ] Step 6 — data dictionary, ETL doc, data model doc, DQ doc
- [ ] Step 7 — Power BI semantic model + measures + 3 pages + theme
- [ ] Step 8 — DAX measures doc, report guide
- [ ] Step 9 — finalize walkthrough & README, sync to Google Drive
