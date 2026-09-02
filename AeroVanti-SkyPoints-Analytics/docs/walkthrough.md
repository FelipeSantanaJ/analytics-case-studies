# AeroVanti SkyPoints — Build Walkthrough

A running narrative of the build. Each entry: what was done, why, where to look.
Newest at the bottom.

---

## Phase 0 — Scope & scaffold  (2026-09-02)

- Locked scope in `docs/00_scope.md`. Key calls: analysis-heavy (Phase 10 primary),
  Power BI "lite" (4 pages), reduced ETL (6 source systems, 6 DQ classes), BRL only,
  120k enrolled members, 15k-member experiment.
- Created the folder tree under `PBI Pessoal/AeroVanti-SkyPoints-Analytics/`.

## Phase 1 — Company story & KPI framework  (2026-09-02)

- `docs/01_business_context_kpis.md`. Fictional Brazilian domestic airline; SkyPoints
  relaunched Sep-2024 so the 24-month window is the whole modern program.
- Two point currencies (spendable SkyPoints, 24-month lot expiry; status Tier Points).
- Flash Redemption experiment fully specified: member-level, stratified-by-tier with
  Gold/Platinum oversampling, 50/50, primary = redemption rate, four guardrails, SRM +
  novelty + heterogeneity diagnostics, power/MDE rationale.

## Phase 2 — Data architecture  (2026-09-02)

- `docs/02_data_architecture.md`. Medallion raw -> staging -> curated. 6 simulated
  systems (SkyCore, BancoAV, Reserva, Aurora, Flesk, Loyalty Sub-Ledger). Curated star
  with pre-built experiment tables so Phase 10 goes straight to tests.

## Phase 3 — ETL pipeline  (2026-09-02)

### 3.1 The true effect (kept only in `etl/config.py::FLASH_EFFECT`)
Decided per instruction #3: real, non-trivial, not-obvious. Per-tier absolute lift in
P(redeem in window): Blue +3.3pp, Silver +2.8pp, Gold +1.3pp, Platinum ~0. Design-weighted
pooled ~+2.6pp; post-stratified to population mix ~+2.9pp (pooled understates because Blue
is undersampled by the oversampling design). ~+1.4pp week-1 novelty bump decaying with
tau=2.5 weeks. Guardrails: revenue/member -0.4% (NI holds vs -3%), net liability cost/member
favourable, average redemption *value* per redeeming member down ~R$16 (shallower Flash
redemptions — a watch item), 90-day post disengagement -1.6pp. A latent per-member
"engagement" factor drives both redemption and retention so the *observational* redeemer/
non-redeemer lapse gap over-states causation; the experiment is the clean test.

### 3.2 Pipeline shape
`config.py` (one SEED, every tunable) · `utils.py` (rng, messy-export helpers, retrying
writers) · `01_generate_raw.py` (builds the world in memory, emits source-shaped messy
files) · `02_clean_stage.py` (typed `stg_*` + DQ fragments) · `03_build_curated.py` (star +
experiment tables) · `dq_checks.py` (hard assertions + accounting identities + `dq_report.md`)
· `run_pipeline.py` · `gen_data_dictionary.py`.

### 3.3 Fixes made during the build (this is where section-1-style guardrails come from)
- **Vectorise everything.** First cut had Python row loops in the point-lot engine, the
  raw `point_transactions` builder, and the member-month `months_since_last_activity`
  counter. At 120k members these ran for many minutes. Rewrote all three as vectorised
  numpy / groupby. 01 ~5 min, 03 ~5 min now.
- **Gzip files must be named `.csv.gz`.** `df.to_csv(path, compression="gzip")` writes
  gzip regardless of the name, but `pd.read_csv` only *infers* gzip from the `.gz`
  suffix -> staging blew up with `UnicodeDecodeError: 0x8b` (the gzip magic byte). Renamed
  the four large raw exports to `.csv.gz`.
- **Tier is a status property, not a derived flight count.** First design derived tier from
  trailing-12-month Tier Points. With a realistic mean of ~2-3 flights/year almost nobody
  reached Gold/Platinum, so the experiment's Gold/Platinum strata could not be filled
  (Platinum eligible pool = 5). Rebuilt: each member gets a `target_tier_rank` drawn to hit
  the 68/20/9/3 mix (tilted by engagement), and flight frequency is *boosted* by tier so
  revenue-by-tier still rises steeply.
- **Emit an initial "qualification" tier-change event.** The tier-change ledger only
  recorded month-over-month changes, so a member who started above Blue had no event and
  the curated fold-forward left them at Blue forever -> 10% snapshot-vs-ledger "drift"
  that was actually a reconstruction bug. Added a Blue -> status event at enrolment.
- **Legacy opening balances need an issuance transaction.** Migrated members carry an
  opening SkyPoints balance (so the "members hoard points" starting condition and the
  mid-window breakage wave exist). It lived only in the lot matrix, so the transaction
  ledger didn't contain it and the points roll-forward identity broke once those lots
  expired. Added a one-off `legacy_migration` earn row at each migrated member's enrol
  month, and folded legacy into the sub-ledger's month-0 issuance.
- **`pd.NA` is not `None`.** The money-string parser did `x.strip()` inside a `.map`;
  pyarrow-backed string columns feed `pd.NA` (not Python `None`) to the mapper ->
  `AttributeError: 'NAType'`. Guarded with `pd.isna` and a list comprehension.
- **Windows console is cp1252.** `dq_checks.py` printed a `Σ`; the script died on
  `UnicodeEncodeError` before writing the report. Added `sys.stdout.reconfigure(utf-8)`
  and kept console strings ASCII.
- **`SKP_SCALE`** (dev-only member-count scale) and **`SKP_NO_CSV`** (skip the curated CSV
  mirror) env knobs added to make calibration passes faster. Both default to the full build.

### 3.4 Calibration (7 full pipeline runs)
Tuned the redemption-hazard intercept `A0` (−3.62 → −3.25) and the balance coefficient
(0.28 → 0.18) until the pre-experiment steady state sat mid-band. Two structural changes
during calibration:
- **Deterministic per-stratum conversion.** The first cut drew each treatment member's
  conversion from `Bernoulli(q)`, which added a second layer of Monte-Carlo noise on top of
  base-rate sampling — per-tier effects bounced ±2 pp between runs. Switched to converting a
  **fixed count** `round(effect_pp × n_treatment)` of eligible non-redeemers.
- **Blocked (pair-matched) randomisation.** Plain `permutation` produced a ~2.5 pp base-rate
  imbalance between arms in the Gold stratum on the project seed. Switched to ranking each
  stratum's chosen members by a pre-period redemption-propensity score, pairing adjacent
  ranks, and flipping a coin per pair. Arms are now balanced on prior behaviour by
  construction (Phase 10's balance check will show it) with real assignment randomness kept.

**Final run (SEED 20260902) — all DQ hard + soft checks pass:**
- Program: 120k enrolled, ~109k active @2026-08; tier mix 65/22/10/3; point liability
  R$25.7M gross / R$15.4M breakage-adjusted; burn/earn 30.4%; 228M pts (10.9% of issued)
  expired so far (legacy-lot wave — lifetime breakage trends to ~40%).
- Experiment: control redemption rate 12.8%, treatment 15.5%, **pooled lift +2.69 pp**
  (n = 7,500/arm). By stratum (lift pp): Blue +3.8, Silver +2.2, Gold +2.5, Platinum −0.5.
  Guardrails: revenue/member −0.1%, net liability cost/member −R$0.81 (favourable),
  redemption value ~−R$20 per *redeeming* member (shallower), 90-day disengagement −2.0 pp.

### Phases 4-9 — docs + Power BI "lite" track  (2026-09-02)

- **Phase 4:** `03_data_dictionary.md` auto-generated from `data/curated/` (20 tables);
  `04_etl_pipeline.md`, `05_data_model.md` (bus matrix + grains + 20 relationships),
  `08_data_quality.md` written.
- **Phase 5:** `assets/brand.py` (AeroVanti sky-blue / amber / steel palette),
  `assets/gen_logo.py` (mark + wordmark + 4 page-background PNGs), `powerbi/theme/theme.json`
  (adapted from the VoltEdge/Voxa theme, re-coloured), `docs/07_visual_identity.md`.
- **Phase 6:** `powerbi/gen_semantic_model.py` — generates the whole `.SemanticModel` (TMDL)
  from the curated Parquet schemas: 19 imported tables + a `dim_month` spine + `Funnel Stage`
  + `_Measures`, Parquet import partitions via a `pDataFolder` parameter, 20 relationships.
  Adds two sentinel `dim_member` rows so non-member / orphan flight segments resolve.
- **Phase 7:** `etl/pbi_measures.py` — 62 measures in 10 display folders (Program, Earn &
  Burn, Breakage & Liability, Tiers/Commercial, Retention & Lapse, A/B Test, Time & Targets,
  Narrative, Funnel). The A/B group computes the lift, a two-proportion pooled z-stat, a
  Wald 95% CI on the lift, an SRM ratio, and the four guardrails. `Exec Insight` is a
  dynamic narrative text measure. `etl/gen_dax_doc.py` -> `docs/06_dax_measures.md`.
- **Phase 8:** `powerbi/gen_report_visuals.py` (4-page `_report_layout.json`),
  `_drive_pbir.py` (adapted from Voxa), `build_report.sh`. `pbir validate --all` **passes**
  (4 pages, 59 visuals, 128 fields; 99 cosmetic overlap/undersize warnings — the KPI frame
  sits behind the cards by design). Screenshot-verification skipped (needs a live Desktop).
  `docs/09_report_structure.md` written.
- **Phase 9:** this file.

### Phase 10 — Data analysis (the primary deliverable)  (2026-09-02)

`data_analysis/` — dual-track (pandas + DuckDB), 8 analyses, each self-checking parity
inline; `parity/run_all.py` runs all and confirms every SQL/Python check passes.

- **01 anchor** — control 12.8% / treatment 15.5% redemption rate.
- **02 randomisation** — SRM χ²=0 (p=1) everywhere; max |SMD|=0.039. Blocked randomisation
  balances by construction.
- **03 primary** — +2.69 pp pooled, 95% CI [+1.58, +3.81], z=4.74, p=2.2e-6; post-stratified
  to the member base **+3.21 pp** [+2.20, +4.22]; covariate-adjusted AME +2.78 pp; power
  0.97 at the +2.2 pp MDE.
- **04 guardrails** — revenue/member −0.09% (n.s.), **NI vs −3% NOT established** (one-sided
  p=0.14); net liability cost/member −R$0.81 (n.s., favourable dir.); 90-day disengagement
  **−2.0 pp, p=0.001**; value per redeeming member **−R$19 (−6.8%), p=0.001** (shallower).
- **05 novelty** — weekly increment OLS slope −0.044 pp/wk, p=0.017; durable ≈ **+1.5 pp**.
- **06 heterogeneity** — Blue +3.8 (sig) · Silver +2.2 (sig, marginal) · Gold +2.5 (n.s.) ·
  Platinum −0.5 (n.s.); **arm×tier interaction LR χ²=17.0, df=3, p=0.0007**; linear-in-rank
  interaction −0.172, p=0.0001.
- **07 hoarding/liability** — 32% of active members ever redeemed (25% Blue); co-brand card
  = 55% of issuance; liability R$25.7M gross / R$15.4M adj; ±R$2.6M per 10 pp of breakage
  assumption.
- **08 redeemer→retention** — engagement-lapse gap raw −10.5 pp, adjusted −6.0 pp
  (p=1e-31); latent-engagement caveat; the experiment's −2.0 pp 90-day guardrail is the
  clean causal signal.

**Recommendation delivered:** roll out Flash Redemption to **Blue + Silver**, hold
Gold/Platinum, keep a revenue and a redemption-depth guardrail live; size the durable effect
at ≈ +1.5–2 pp. → this matches the baked `FLASH_EFFECT` (Blue/Silver real, Gold/Platinum ~0,
novelty decay, benign guardrails), detected blind.

Deliverables: `deliverables/board_summary.html` + `.pdf` (decision-first, AeroVanti
identity); `deliverables/deep_dive_00_index.md` + `deep_dive_A_ab_test_readout.md` +
`deep_dive_B_program_health.md` (+ rendered `deep_dive.html`/`.pdf`). Built by
`build_deliverables.py` (markdown -> HTML -> Chrome print-to-PDF).

### Fix — Power BI load error: non-unique key on the "one" side  (2026-09-02)

Opening the `.pbip` failed: *"a coluna 'month_key' na tabela 'dim_date' contém um valor
duplicado '202701' e isso não é permitido … para a chave primária de uma tabela"*. Cause:
`gen_semantic_model.py` emitted an **inactive** `dim_month.month_key → dim_date.month_key`
relationship "for optional drill". Power BI requires the "one" side of **any** relationship
(active or not) to be unique, and `dim_date.month_key` has ~30 rows per month. Removed that
relationship entirely — month-grain facts already join `dim_month` (unique `month_key`),
day-grain facts join `dim_date[date_key]`; no `dim_month ↔ dim_date` link is needed.
`docs/05` §4 updated. `pbir validate --all` still passes.

### Fix — first-open in Desktop: theme import + blank/errored visuals  (2026-09-02)

Data model loaded fine; three cosmetic/logic issues on first open:
1. **Theme import failed** ("problema com o arquivo JSON do tema"). The elaborate
   `visualStyles` block (adapted from the Voxa/VoltEdge theme) is rejected by this Desktop
   version. Stripped `theme.json` to an **import-safe minimal** theme (name, `dataColors`,
   core colours, semantic colours, `textClasses`) — the page-background PNGs carry the
   identity; visual styling falls back to Power BI defaults.
2. **KPI cards showed "(Em branco)"**. `dim_month` spanned to 2026-12, so
   `MAX(dim_month[month_key])` = 202612 — a month with no fact rows. Rebuilt `dim_month` to
   span **only the fact window, 2024-09 → 2026-08** (24 rows).
3. **Two visuals errored** ("Erro ao buscar os dados"). `Exp Redemption Rate` and
   `Exp Disengaged 90d %` used `AVERAGE( <boolean column> )`, which DAX rejects. Rewrote as
   `DIVIDE( CALCULATE( COUNTROWS(...), col = TRUE() ), COUNTROWS(...) )`. Every measure that
   chains off `Exp Redemption Rate` (control/treatment rate, lift, SRM, Exec Insight) is
   fixed by this.

Re-ran `gen_semantic_model.py` + `gen_dax_doc.py`; `pbir validate --all` passes.

### Phases 11-12 — packaging  (2026-09-02)

- **Phase 11:** `portfolio/gen_portfolio_images.py` → 5 gallery images (1600×820): cover,
  effect-by-tier, novelty decay, hoarding+liability, deliverables mock.
- **Phase 12:** `docs/build_docs_bundle.py` → `AeroVanti-SkyPoints-Documentation.pdf`
  (full, 2.2 MB) + `AeroVanti-SkyPoints-Summary.pdf` (0.7 MB, < 2 MB target). markdown →
  HTML → Chrome print-to-PDF.

### 3.5 Refinement noted for Phase 10 — "engagement lapse"
Realized 12-month **account** lapse (the doc-01 definition: no earn *and* no redemption) is
low (~4%), because co-brand-card auto-earn keeps most accounts nominally active. The
meaningful retention metric is **engagement lapse** — no *flight* and no *redemption* for 12
months — which Phase 10 computes from `fact_member_month` alongside the strict definition.
`docs/01` §6 / §11.5 updated to introduce it.
