# Voxa+ — Build Walkthrough

A running log. Each entry: what was done · why · where to look. Newest at the bottom.

---

## Phase 0 — Scope & scaffold

- Locked scope with the stakeholder (see `README.md`): SVOD service **Voxa+**, 36-month
  window (Sep 2023 – Aug 2026), churn shift at window-month 34, markets BR/MX/US with MX and
  US launching mid-window, USD reporting currency + slicer, balanced depth, `.pbip`/PBIR
  from code, single `SEED`.
- Three stakeholder choices resolved via a decision prompt: **balanced data scale**
  (~120k cumulative sign-ups, ~70k active at window end, viewing at subscriber-day grain),
  **market launch months** MX = window-month 10 / US = window-month 16, and **North Star =
  Paid Active Subscribers** with watch metric Gross Monthly Churn %.
- Created the folder tree (`docs/ etl/ data/{raw,staging,curated,quality}/ powerbi/
  assets/ portfolio/ data_analysis/`).

## Phase 1 — Company story & KPI framework

- `docs/01_business_context_kpis.md`: company profile, the 36-month window rationale
  (CY = months 25–36, PY = 13–24), expansion timeline, plan line-up and margin structure,
  financial definitions (the churn/subscriber spine), North Star, Total vs Comparable Base
  (= Brazil) vs Expansion, multi-currency handling, seasonality, the seven stakeholder
  personas → the seven report pages, and the full KPI framework with benchmark ranges → targets.
- **Section 8 "Events in the window"** lists 12 neutral, dated business events (cancellation
  redesign, support migration, ad-tier renegotiation, licence expiries, marketing-mix shift,
  app "v3" rollout, Brazil price increase, plan-lineup tweak, …). None is flagged as a cause
  — they are the candidate context the Phase 10 investigation weighs.
- The root cause is deliberately **absent** from this document (assumption A15).

## Phase 2 — Data architecture

- `docs/02_data_architecture.md`: medallion principles (raw → staging → curated; seeded,
  idempotent, layered), tech stack + run instructions, naming conventions, an inventory of
  **13 simulated source systems**, the raw-file catalogue with volumes, the staging fix
  classes, the curated Kimball star (**14 dimensions + 14 facts**), a **15-item
  data-quality issue catalogue (Q01–Q15)** each mapped injected-in → handled-in → hard-check,
  and a Mermaid architecture diagram.
- Key design choices carried into build: `fact_subscription_month` is **folded from the
  movement ledger** (the Ketch snapshot is used only to measure drift); annual plans
  explode into 12 monthly recognitions; subscriber-level QoE is preserved so engagement can
  be tied to individual churn; `is_comparable_base` propagated from `dim_subscriber`.

## Phase 3 — ETL pipeline

### 3.0 Structure
- `etl/config.py` — one `SEED`, window dates, launch months, every tunable, plus
  **section 9 "ROOT-CAUSE EFFECT SIZES"** (see below). `POP_SCALE` (env `VOXA_POP_SCALE`)
  scales the population for fast calibration; `1.0` → ~117k sign-ups / ~67k active at end.
- `etl/utils.py` — deterministic per-stream RNG (`rng("name", …)`), atomic + retry-on-lock
  IO (OneDrive WinError 5/32), messy-format emitters (Excel serials, locale money strings,
  mojibake, BOM, category jitter), DQ-fragment writer.
- `etl/gen/world.py` — the clean generative world model (subscriber-level monthly
  simulation: acquisition → engagement → billing/dunning → churn hazard → plan changes /
  pause / reactivation → the movement ledger). Full-length NumPy buffers per attribute; loop
  over 36 months, vectorised over the active set.
- `etl/gen/content.py` — catalogue, licence windows, release schedule, amortisation + cash.
- `etl/gen/economics.py` — FX random walk, marketing spend (from acquisition × CAC by
  channel), SSP ad revenue, support tickets, a monthly GL roll-up.
- `etl/01_generate_raw.py` — builds the world, then serialises it into 13 source-shaped
  messy exports; every Q01–Q15 injection is counted into `dq_fragments/raw_injection.json`.
- `etl/02_clean_stage.py` — one `stg_*` per raw entity; parsing / encoding repair /
  de-dup / unit normalisation / category harmonisation; counts every fix.
- `etl/03_build_curated.py` — the conformed star; `fact_subscription_month` replays the
  ledger per subject (events sorted `subject, month_idx, event-priority, ts` so logical
  order survives the random within-month timestamps).
- `etl/dq_checks.py` — hard structural + accounting-identity checks (fails the build) plus
  soft plausibility/calibration checks; assembles `data/quality/dq_report.md`.
- `etl/run_pipeline.py` (`--from`, `--only`), `etl/gen_data_dictionary.py`.

### 3.1 The root cause (decided here; kept out of `docs/01`)
The window-month-34 gross-churn spike (~4.1% pre-shift → ~6.8% peak, **1.66×** — "nearly
doubled") is the product of **three overlapping factors**, encoded as tunable effect sizes
in `config.py` §9:

| | Factor | Role | Where it shows |
|---|---|---|---|
| **F1** | App **"v3" connected-TV playback regression** — the re-platformed player shipped device-by-device, CTV last (smart-TV/stick at window-month 33, console 34). Video-start-failure / rebuffer / crash rise ~2–3× on CTV; CTV-heavy subscribers lose ~30% of viewing hours and carry an extra ~3.5 pp monthly voluntary hazard, **lagged one month**. US barely affected (`APP_V3_CTV_US_SENSITIVITY`). | Acute trigger | Content & Engagement (by device), CX/App Quality |
| **F2** | **Brazil price increase** (Std/Prem +13/15% at window-month 32) — migrated on each subscriber's next renewal, spread over months 32–36. Engaged BR subs absorb it (+3 pp); **disengaged** BR Std/Prem leave (+13.5 pp) — and F1 is what makes many of them disengaged. Basico reacts to the month-33 plan-lineup change. | Amplifier (BR only) | Pricing & Plans (engagement × tier × timing) |
| **F3** | **Mexico acquisition-quality decline** — from the month-25 marketing-mix shift, MX acquisition tilts ~50% to a telco bundle + affiliate. Low-quality-channel cohorts churn +4–5 pp while young; MX gross churn **drifts up from ~month 28** (4.7% → 5.9%) *before* the visible spike, then F1 accelerates it. OXXO/carrier involuntary churn worsens too. | Pre-existing drag (MX) | Acquisition Quality & Channels (channel × market), Market Context |

**US is the control**: card-only (no dunning tail), no price increase, little bundle, little
F1 → US gross churn stays ~4% throughout. No single report page shows all three factors;
the diagnosis needs Content&Engagement + Pricing&Plans + AcquisitionQuality + MarketContext
read together.

### 3.2 Calibration
Calibrated against the world truth over ~10 passes at `POP_SCALE` 0.05–0.25 (churn rates are
scale-invariant). Final full run (`POP_SCALE=1.0`):

| Metric | Result | Target |
|---|---|---|
| Pre-shift blended gross monthly churn (idx 24–32) | **4.11 %** | 3.7–4.4 % |
| Peak blended (idx 33–35) | **6.82 %** | ~7 % ("nearly doubled") |
| Peak / pre ratio | **1.66×** | ~1.7–2.0× |
| BR churn idx 32 → 33 | 4.0 % → **7.0 %** (step) | acute |
| MX churn idx 26 → 32 → 34 | 5.3 % → 5.9 % → **8.3 %** (ramp) | gradual then accelerating |
| US churn idx 26 → 34 | 4.3 % → **4.4 %** (flat) | control |
| Cohort retention M1 / M6 / M12 | 89 % / 74 % / 64 % | M12 a touch above the doc-01 band |
| Active subscribers at window end | ~66.8 k | ~70 k |
| DQ checks | 6 hard PASS, 0 soft warnings | all pass |

### 3.3 Problems hit (for the playbook guardrails)
- **Staging was ~45 min** at full scale: row-wise `.map(parse_date_any)` / `.map(parse_money)`
  / per-row `norm()` on the 2–4 M-row Ketch tables and the 17 M-row PlayLog/Trackpad loop.
  Rewrote the hot paths as **vectorised** `parse_date_series` / `parse_money_series` /
  `norm_series` (Series `.str` + `.map(dict)`), and PagStream `meta` JSON via vectorised
  regex extract instead of `json.loads` per row. Staging dropped to **141 s**.
- `fact_subscription_month` folded from the *shuffled* ledger initially lost ~15 % of churn
  events because two events in the same month were ordered by their random timestamps. Fixed
  by sorting on an explicit event-type priority before replay.
- Recording bug: churned-this-month rows were skipped (subscriber already `status=3`), so
  churn never landed in `fact_subscription_month`. Now emits active + paused + churned-now.
- Content amortisation was ~10× too high (P&L ≈ −$10 M/month on ~$1.1 M MRR). Recalibrated
  `content.py` cost draw so amortisation lands near ~50–60 % of subscription revenue.
- Raw generation ≈ 19 min at full scale (~17 M PlayLog rows across 36 monthly Parquet files).

## Phase 4 — Data documentation

- `docs/03_data_dictionary.md` — **auto-generated** by `etl/gen_data_dictionary.py` from
  `data/curated/`: 24 tables, grain guess + row count + every column with dtype and sample
  values.
- `docs/04_etl_pipeline.md` — stage-by-stage narrative: the generative world model
  (`gen/world.py`+`content.py`+`economics.py`), raw messiness per source, the staging fix
  classes and the vectorisation that took staging 45 min → 2.5 min, the curated star build
  (ledger fold-forward with event-priority ordering, sentinels, USD everywhere), and the DQ
  gate. The churn-shift mechanism is referenced as `config.py §9` without enumerating the
  factors (kept for the Phase-10 diagnosis).
- `docs/05_data_model.md` — bus matrix (13 facts × 11 dims), per-fact grain + measures +
  degenerate dims + row counts, dimension attribute list, the relationship list (single
  direction, `subscriber_key` as the hub, one active date role, `dim_price_history` and
  `fact_fx_rate` unrelated/DAX-resolved), and the Total / Comparable Base / Expansion cut.
- `docs/08_data_quality.md` — Q01–Q15 each mapped injected(count) → handled → asserted with
  real numbers from the shipped run; the 6 hard + 7 soft check results; and 8 accepted
  limitations (sampled acquisition channel, schedule-based billing amount, partial last
  month, measured-not-corrected snapshot drift, M12 retention ~64 % slightly high, thin
  ramping gross margin, no external data).

## Phase 5 — Visual identity

- `assets/brand.py` — the palette + type single source of truth (imported by `gen_logo.py`
  now and `gen_report_visuals.py` in Phase 8). Brand violet `#4B2E83`, one accent amber
  `#E6A23C`, one comparison steel `#5B7FB0`, muted lavender-grey ground `#F2F1F7`, quiet
  `#E7E5EF` gridlines, good/bad `#2E7D5B`/`#C0453B` (churn = lower-is-better, so deltas
  invert).
- `assets/gen_logo.py` (Pillow) — emits the rounded-tile **play + amber-plus mark**
  (on-light / on-dark), the **Voxa+ wordmark**, and **7 full-page background PNGs**: violet
  band + wordmark + a quiet "Subscriber Churn Diagnosis" label, amber hairline, then the
  page title + business question on the light body. Also writes `_page_heights.json`
  (Executive 900, rest 720).
- `powerbi/theme/theme.json` — `visualStyles` for ~20 visual types + `page`; **passes
  `pbir theme validate`**. Soft drop shadow on charts only; horizontal gridlines only;
  cards transparent (a white rounded frame shape supplies the surface); slicers headerless;
  waterfall sentiment pinned to the KPI-delta colours.
- `docs/07_visual_identity.md` — the written identity spec + the signature-element recipe
  repeated on every page (band → title → Currency/Market slicers → Analysis-Period slicer →
  6 KPI cards → two 3-30-300 content rows).

## Phase 6 — Semantic model as code

- Added `fact_engagement_device_month` to the curated star (market x device family x month,
  ~500 rows, with `vsf_rate` / `playback_error_rate`) and a `date_key` to
  `fact_billing_attempt`, then re-ran `--from 03` (dq still 6/6 + 0 warnings). This keeps
  the 13.5 M-row `fact_viewing_daily` **out of the semantic model** — it stays analyst-only
  for Phase 10 — while the report still gets a device-level QoE cut. `fact_engagement_device_month`
  cleanly shows F1: CTV video-start-failure 1.1 % -> 2.6 % (idx 32) -> 3.4 %, non-CTV flat.
- `powerbi/gen_semantic_model.py` generates the whole `.pbip` from the curated Parquet
  schemas: `VoxaChurnDiagnosis.pbip` + `.SemanticModel/` (TMDL: `database`, `model`
  (auto date/time **off**), `expressions` (`pDataFolder` parameter), `relationships`,
  `tables/*.tmdl` — each with a `Parquet.Document` import partition) + a `.Report/` shell.
  **24 imported tables + 5 helper tables** (`Reporting Currency`, `P&L Line`,
  `Subscriber Bridge`, `Funnel Stage`, `_Measures`) built from M `#table` literals.
  **34 relationships**, `dim_subscriber` as the hub, direct `dim_market` links only for
  subscriber-less aggregate facts, `dim_content[release_date_key]` inactive.
- Problems hit: pandas `Path.write_text` on Windows emitted CRLF -> routed every TMDL/JSON
  write through an LF helper; `datetime64[ms]` / `datetime64[us, UTC]` weren't in the
  string dtype map -> switched to `pandas.api.types` checks so date columns type as
  `dateTime`, not `string`.
- `powerbi/README.md` documents the one-time Desktop pass (point `pDataFolder`, Refresh,
  mark `dim_date`). Structural self-check passes: 29 tables, all relationship column refs
  and all partition file refs resolve.

## Phase 7 — DAX measures

- Two small curated additions first (re-ran `--from 03`, dq still 6/6 + 0): `dim_date[abs_month]`
  (`year*12 + month_num`, a linear index for time intelligence) and
  `dim_subscriber[is_incentivised]` (sampled from the channel's promo-code rate — same
  caveat as the sampled channel).
- `etl/pbi_measures.py` — `MEASURE_LIBRARY`: **107 measures in 15 display folders**
  (Currency plumbing · Subscribers · Churn · Cohorts · Engagement · App Quality · Payments ·
  Revenue · Unit Economics · Time Intelligence · Comparable Base · Targets · Acquisition ·
  Support · Narrative). Design choices:
  - **Time intelligence with no marked date table**: PY = `abs_month - 12` via
    `TREATAS(SELECTCOLUMNS(VALUES(dim_date[abs_month]), ..., -12), dim_date[abs_month])`;
    YTD / MAT / MoM all use `abs_month` arithmetic. No `SAMEPERIODLASTYEAR`.
  - **Reporting currency**: `[FX Rate to Reporting]` (USD→selected, date-context aware) is
    multiplied into every leaf monetary measure; `[Currency Symbol]` for labels/narrative.
  - **Gross Monthly Churn %** = mean of the monthly `churned / start-of-month active` ratios
    (matches the `dq_checks.py` definition). `[Pre-Shift Baseline Churn %]` fixes the
    window-month 25-33 band; `[Churn vs Baseline (x)]` gives the "nearly doubled" multiple.
  - **Cohort retention** via `[Retention %]` (cohort_month × tenure_months matrix) plus
    explicit `M1/M3/M6/M12 Retention %`.
  - **Targets** one `… vs Target %` per KPI; churn / CAC flagged lower-is-better (negative =
    good) in the description and inverted on the KPI cards in Phase 8.
  - **`[Exec Insight]`** — a dynamic narrative text measure that reports the churn level vs
    baseline, the worst market and net adds, and updates with the slicers (replaces the
    Smart Narrative visual).
- `powerbi/gen_semantic_model.py` now injects the library into `_Measures.tmdl` (TMDL
  `measure` blocks with `/// description`, `formatString`, `displayFolder`, `lineageTag`).
- `etl/gen_dax_doc.py` -> `docs/06_dax_measures.md` (auto-generated, DAX in fenced blocks).
- Self-check: all 107 measures present and quoted; every `[Measure]` reference resolves to
  a defined measure or a real column. DAX semantics get their first real check on the
  Phase-8 Desktop open.

## Phase 8 — Report build

- **pbir reads the code-generated TMDL model from disk** (thick `byPath` report), so the
  whole report can be built and field-validated here without Power BI Desktop. Flow:
  `pbir new report --thick --no-title` -> `pbir report rebind --local ../<name>.SemanticModel`
  -> per page `pbir add visual --from-json <bundle>` -> `pbir visuals sort` / `pbir visuals cf`
  -> report-level `dim_date[in_analysis_window]` filter -> `pbir validate --all`.
- `powerbi/gen_report_visuals.py` -> `powerbi/_report_layout.json`: 7 pages, the signature
  furniture (bg PNG, 3 slicers, white KPI frame + 6 value cards + delta cards), two content
  rows each. `powerbi/_drive_pbir.py` turns the manifest into `pbir` calls (retry-on-lock,
  `PBIR_ALLOW_OVERLAP=1` for the layered KPI band). `powerbi/build_report.sh` orchestrates
  (abort if Desktop running, regen assets/model/manifest, drive pbir).
- **Result: 7 pages, 113 visuals, 239 fields bound, `pbir validate --all` PASSES** (0 errors).
  188 warnings remain, all from the deliberate dense-KPI design: `VISUAL_OVERLAP` (cards on
  the frame), `VISUAL_UNDERSIZED` (compact KPI tiles), `TOO_MANY_VISUALS` (~20 on 4 pages) —
  the kind `pbir validate` flags but only a Desktop screenshot can actually judge.
- Problems hit: `--from-json` only accepts keys `visual_type/name/title/x/y/width/height/
  fields` (no `z`, no `objects`); role names are `Category`/`Y`/`Series` (charts),
  `Rows`/`Columns`/`Values` (matrix), `Values` (card/slicer/table) — **`lineChart` has no
  `Series` role**, so series breakdowns use `clusteredColumnChart`; `subprocess` needed
  `encoding="utf-8"` for pbir's box-drawing output; `definition.pbism` needed a `$schema`;
  720px pages needed the content rows remapped (tuned for the 900px exec page).
- `pbir theme apply-template` only takes registered template *names*; our authored
  `theme/theme.json` is applied in Desktop (View > Themes > Browse) on first open.
- `docs/09_report_structure.md` — the page-by-page spec + the first-open checklist
  (`pDataFolder`, theme, mark `dim_date`).
- **Next: the user opens `powerbi/VoxaChurnDiagnosis.pbip` in Desktop and we iterate on
  screenshots** (layout polish, KPI-card formatting, per-visual data-label toggles, the
  chronological sort verification).

### Phase 8 — Desktop iteration (round 1)

Opened the `.pbip` in Desktop and drove fixes through the `pbir desktop` bridge
(`PBIR_ADOMD_DIR="C:\Program Files\Power BI Report Builder"` for the live-model queries):

- **`compatibilityLevel` 1550 → 1600** — Desktop auto-upgrades on open and refuses a
  downgrade on the next open.
- **Friendly tab names** via `pbir set "...Page.displayName"` (folder / internal id kept):
  Executive Summary · Retention & Cohorts · Content & Engagement · Pricing & Plans ·
  Acquisition Quality · CX, Billing & App · Market Context.
- **Removed the default `Title.Visual` textboxes** `pbir add page` injects (the background
  PNG carries the title).
- **Chronological x-axis**: `dim_date[year_month]` and `dim_subscriber[cohort_month]` given
  `sortByColumn` in the TMDL; every time-series visual then `pbir visuals sort`-ed by its
  Category ascending (new charts default to sort-by-first-measure-descending).
- **KPI measures fixed** — the headline cards were summing/averaging levels across all 36
  months:
  - `Paid Active Subscribers` → mean of the monthly active counts (was `DISTINCTCOUNT` over
    the whole window = 107 k).
  - New **`… (Latest)`** wrappers anchor to the last in-window month (`window_month_idx`,
    not `MAX(abs_month)` which hit the padded `dim_date` end at Dec 2027 and returned
    blank). Exec + Market-Context KPI cards use them; `Exec Insight` too.
  - `LTV` guarded with `MAX(0, …)`.
- **Verified against the live model**: `[Exec Insight]` = *"Gross monthly churn is 7.0%.
  That is about 1.7x the pre-shift baseline of 4.1% and the highest of the three markets is
  Mexico (8.3%). Net adds in the latest month: 205."* — the diagnosis reads correctly.

Open polish items (left for the next Desktop round; the model + data are verified correct):
apply `powerbi/theme/theme.json` (View > Themes > Browse); a **Home > Refresh** to clear
Desktop's stale visual cache; the KPI frame `shape` fill; a `(blank)` month on two exec
charts; the compact KPI value/delta cards (`VISUAL_UNDERSIZED` is by design).

## Phase 10 — Data analysis (dual-track)

- `data_analysis/run_analysis.py` — **10 questions, each computed twice** (DuckDB SQL over
  the curated Parquet, and pandas over the same files) with `lib/parity.assert_parity`
  asserting the two agree before any number is used. `python data_analysis/run_analysis.py`
  → `sql/qNN.sql` (17), `results/qNN_*.csv` (17), `parity/parity_report.md`
  (**14/14 checks pass, all exact**).
- Bugs found and fixed while building it: `LAG()` evaluated after `WHERE` in the same
  SELECT (moved the window into its own CTE); a `LEFT JOIN` on a non-distinct `m3` set
  fanning out the aggregate (`SELECT DISTINCT`); orphan-billing rows with null `market`
  inflating a SQL `GROUP BY` (filter `market IS NOT NULL`); a per-row `.loc` lookup in Q4
  replaced with a vectorised shifted merge.
- **The diagnosis** (`findings/F01`–`F10`, `deliverables/deep_dive_00_index.md`):
  churn 4.1% → 6.8% (1.66×, 90% voluntary, not receding); **three overlapping factors**,
  none sufficient alone —
  1. **F05** connected-TV app-v3 regression: CTV video-start-failure 1.1% → 3.0% at
     window-month 32; CTV-heavy churn 4.1% → **8.4%** vs 4.1% → 5.6% for the rest.
  2. **F06** Brazil price increase: **~0 pp** on engaged Std/Prem, **+18 pp** on
     already-disengaged — the amplifier, Brazil-only.
  3. **F07** Mexico cohort-quality drag: post-mid-2025 Mexican cohorts retain **−8–9 pp**
     at month 3 (vs −2–3 pp elsewhere) — the pre-existing drain.
  - **F08** rules payments out (failure / dunning / involuntary all flat).
  - **F09**: implied lifetime 24 → 15 months (**−40% LTV**); ~5,400 excess churned in 3
    months (~$0.5–0.6 M lifetime revenue).
  - **F10** decomposition: in Brazil 85% of peak voluntary churn carries F1 or F2; in
    Mexico ~64% carries F1 or F3; US "39% none" is just its unchanged baseline (the control).
- `deliverables/board_summary.html` — one-page, decision-first, Voxa+ identity.

## Phase 11 — Portfolio assets

- `portfolio/gallery/` — **5 gallery images**, rendered to 3200×1640 PNG with headless
  Chrome. Four are self-contained HTML (Voxa+ identity, no external assets): medallion
  pipeline, semantic-model bus matrix, DAX library, report-structure map. Image 1 frames
  a live Executive Summary screenshot (`powerbi/_shots/round2/`) inside the same HTML
  template.

## Phase 12 — Docs bundle & delivery

- `docs/build_docs_pdf.py` — collates the docs (markdown → one styled HTML: navy headers,
  amber rule, navy table headers + zebra rows, amber callout quotes, dark mono code blocks,
  A4 with controlled page breaks; mermaid fences flattened to plain code) → Chrome
  `--headless=new --no-pdf-header-footer --print-to-pdf`.
  - `docs/Voxa+_Documentation.pdf` — full set (README + 01–09 + deep-dive + walkthrough), ~2.9 MB.
  - `docs/Voxa+_Summary.pdf` — condensed (context + DQ + diagnosis), **0.7 MB (< 2 MB)**.
- **Trimmed the curated CSVs**: Parquet is the source of truth; `03_build_curated._save`
  now writes a CSV mirror only for tables ≤ 200 k rows. Removed the 4 large fact CSVs
  (~360 MB); `data/curated/` went 689 MB → 344 MB.
- Finalised `README.md` (the diagnosis up top, a layout map, a reproduce block).
- **Sync**: the delivery folder copy (e.g. Google Drive) is the last manual step — the
  project lives under `PBI Pessoal/voxaplus-churn-diagnosis/`.

---

**Project complete** (Phases 0–12). Known follow-up: a final Power BI report polish round
via the `pbir desktop` loop — **Home > Refresh** to clear the stale visual cache the current
gallery image 1 and `_shots/` captures still show (a couple of ghosted KPI-card labels).

### Phase 8 — Desktop iteration (round 2, file-level)

Applied without Desktop (the bridge was unavailable):

- **Theme applied.** `pbir theme serialize powerbi/theme/theme.json -o _voxa.Theme` →
  `pbir theme build _voxa.Theme -o VoxaChurnDiagnosis.Report -f --clean` bakes
  "Voxa Plus Diagnosis" into `report.json` (27 visual types) — replaces the default
  sqlbi theme that was giving the KPI band its blue look. `_drive_pbir.py` now does this
  on every build.
- **KPI frame shapes** → white fill, no drop shadow, on all 7 pages
  (`pbir set "**/*kpiframe*.Visual.fill.{show,fillColor}"`).
- **Narrative cards** (`exec_insight`, `insight_7`) → 10 pt text + word wrap so the
  dynamic `[Exec Insight]` paragraph fits.
- `pbir validate --all` passes (178 warnings, all the by-design KPI overlap / undersized).

Still needs a Desktop pass by the user: **Home > Refresh** (the open instance still holds a
stale visual cache from before the measure fixes), then re-capture the Executive Summary
screenshot gallery image 1 frames.
