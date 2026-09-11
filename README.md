# Data & Analytics Portfolio — Felipe Santana

Senior data / analytics professional (5–6 years) working at the intersection of **data,
product, and business decision-making** — SQL-first, comfortable designing and reading A/B
tests, and used to turning ambiguous business questions into a defensible recommendation.
Based in Brazil, open to international remote roles.

Five end-to-end analytics projects. Each one takes a **fictional company** from raw
source-system exports, through a **medallion ETL pipeline** and a **Kimball star schema**,
into a **code-generated Power BI report** and a **dual-track (SQL + Python) analysis** where
every number is computed twice and asserted equal.

> **All data is synthetic** and generated from a single random seed per project. No real
> company, customer, or transaction is represented. See [Note on the data](#note-on-the-data).

Each project is self-contained in its own folder with its own `README.md`, `docs/`, and
reproduction steps. This document is the map — read it
[by project](#browse-by-project--company) or [by type of work](#browse-by-type-of-work).

---

## At a glance

| Project | Domain | Headline deliverable | Core result |
|---|---|---|---|
| [**AeroVanti SkyPoints**](AeroVanti-SkyPoints-Analytics/) | Airline loyalty program | A/B test read-out (*Flash Redemption*) + 4-page Power BI | +2.7 pp redemption-rate lift (p ≈ 2×10⁻⁶), concentrated in the two lowest tiers → roll out there only |
| [**VoltEdge Electronics**](VoltEdge-Electronics-Analytics/) | Consumer-electronics e-commerce | 7-page executive Power BI + 10-finding analysis | Growth is +137% total but only **+40% like-for-like**; ~**$4.4M** cash trapped in a 134-day cash-conversion cycle |
| [**Voxa+**](voxaplus-churn-diagnosis/) | SVOD streaming | Churn root-cause diagnosis + 7-page Power BI | Churn nearly doubled from month 34 — **three overlapping causes**; payments ruled out |
| [**SwiftBite Delivery**](SwiftBite-Delivery-Analytics/) | Food-delivery marketplace | Zone-hour incentive experiment read-out + 4-page Power BI | Incentive lifts fulfillment **+1.9 pp** (ETA p90 −6 min) in supply-short zones — **but fails on cost** (~R$281/incremental order vs R$10 margin) → don't ship the flat bonus |
| [**LumaBank Activation**](LumaBank-Activation-Experiment/) | Fintech neobank onboarding | A/B test read-out for an experiment that **breaks mid-flight** + 4-page Power BI | Real production bug corrupts randomisation on day 11 (caught by daily SRM monitoring); after root-causing and restarting clean, redesigned onboarding lifts Day-7 Activation **+4.58 pp** (p ≈ 1×10⁻⁵) — but the fraud guardrail's non-inferiority is **not established** → monitored rollout, not unconditional |

---

## Skills demonstrated

| Skill area | Where to see it |
|---|---|
| **Data engineering** | Seeded, deterministic Python pipelines (`*/etl/`): messy multi-source raw → typed staging → conformed curated star, with hard data-quality gates. Medallion architecture in every project. |
| **Data modelling** | Power BI semantic models built **as code** (TMDL): 15 / 18 / 21 / 24 / 28 tables, star schemas with role-playing dates and disconnected helper tables. DAX libraries of **46 / 62 / 71 / 113 / 167** measures (time intelligence, comparable-base, multi-currency re-denomination, budget-vs-plan, dynamic narrative measures). |
| **Dashboard design** | Reports assembled through the `pbir` CLI / PBIR project format — theme, layout, and every visual version-controlled. Committed visual identity per project. |
| **Analysis & statistics** | Dual-track **DuckDB SQL + pandas**, every result parity-checked. Experiment read-out with SRM / balance checks, post-stratification, guardrails, novelty-effect and heterogeneity tests. Root-cause diagnosis with cohort/retention decomposition and interaction tests. |
| **Communication** | Two audience-specific deliverables per project — a decision-first **board summary** and an exhaustive **deep dive** — plus full `docs/` sets and bundled PDFs. |

---

## Browse by project / company

### 1. AeroVanti SkyPoints — airline loyalty redemption & retention
📂 [`AeroVanti-SkyPoints-Analytics/`](AeroVanti-SkyPoints-Analytics/) · [project README](AeroVanti-SkyPoints-Analytics/README.md)

**Scenario.** SkyPoints members accumulate miles but rarely redeem — ~40% of issued points
sit unused as breakage, and members who don't redeem within 12 months lapse at a much higher
rate. The loyalty team piloted **Flash Redemption** (lower minimum redemption threshold +
more low-cost reward options) as a member-level 50/50 A/B test on ~15,000 active members
over 12 weeks.

**Question.** Does it work, is it safe on the guardrails, and should it roll out to everyone?

**What's in it.**
- **Primary deliverable — the A/B test read-out** ([`data_analysis/`](AeroVanti-SkyPoints-Analytics/data_analysis/)): anchor → randomisation check → primary effect → guardrails → novelty → heterogeneity by tier → hoarding & liability → redeemer retention. Eight parity-verified analyses.
- **Deliverables:** [board summary](AeroVanti-SkyPoints-Analytics/data_analysis/deliverables/board_summary.pdf) · [deep dive](AeroVanti-SkyPoints-Analytics/data_analysis/deliverables/deep_dive.pdf) (A: A/B test read-out, B: program health).
- **Secondary deliverable — Power BI** ([`powerbi/`](AeroVanti-SkyPoints-Analytics/powerbi/)): 4 pages — Executive · Tiers · Experiment · Redemption Funnel. 21-table TMDL model, 62 DAX measures.
- **Docs:** [`docs/`](AeroVanti-SkyPoints-Analytics/docs/) 00–09 (scope → context → architecture → dictionary → ETL → model → DAX → visual identity → DQ → report structure) + [PDF bundle](AeroVanti-SkyPoints-Analytics/docs/AeroVanti-SkyPoints-Documentation.pdf).
- **Visual case study:** [7-page PDF carousel](AeroVanti-SkyPoints-Analytics/portfolio/AeroVanti-SkyPoints-case-study.pdf).

**Result.** Flash Redemption lifts the 12-week redemption rate **+2.7 pp pooled / +3.2 pp
re-weighted** (p ≈ 2×10⁻⁶), concentrated in **Blue + Silver** (arm×tier interaction
p = 0.0007); roughly half is a launch bump (durable ≈ +1.5 pp). Guardrails benign except
redemptions get shallower. **Recommendation: roll out to Blue + Silver only.**

**Scale.** Brazil / BRL · 24 months (2024-09 → 2026-08) · ~120k enrolled / ~65k active
members · experiment weeks 2026-03-02 → 2026-05-24.

---

### 2. VoltEdge Electronics — executive analytics for a D2C retailer
📂 [`VoltEdge-Electronics-Analytics/`](VoltEdge-Electronics-Analytics/) · [project README](VoltEdge-Electronics-Analytics/README.md)

**Scenario.** VoltEdge is a pure-play online electronics retailer selling direct to
consumers across four markets launched in sequence (US 2022, UK & DE 2025-01, BR 2025-07).
The 24-month extract (2024-07 → 2026-06) gives every metric a full year-over-year
comparison; because three markets go live *inside* the window, growth is always shown as
**Total** vs **Comparable Base** (US like-for-like).

**Question.** Is the business actually growing, is it profitable, and where is cash and
margin leaking?

**What's in it.**
- **Power BI** ([`powerbi/`](VoltEdge-Electronics-Analytics/powerbi/)): 7 pages — Executive Summary · Sales Performance · Marketing & Acquisition · Website & Digital · Logistics & Fulfillment · CRM & Customer · Product & Inventory. **28-table** TMDL model (16 dims + 12 facts, ~65 relationships), **167-measure** DAX library with reporting-currency re-denomination (USD/EUR/GBP/BRL from one slicer), comparable-base, targets-vs-plan, price-volume-mix, and a dynamic *Exec Insight* narrative measure.
- **Analysis** ([`data_analysis/`](VoltEdge-Electronics-Analytics/data_analysis/)): 10 parity-verified [findings](VoltEdge-Electronics-Analytics/data_analysis/findings/) — anchor, growth decomposition, contribution margin, price-volume-mix, promo depth, working capital, CAC sensitivity, retention, returns leak, fulfilment.
- **Deliverables:** [board summary](VoltEdge-Electronics-Analytics/data_analysis/deliverables/board_summary.pdf) · [deep dive](VoltEdge-Electronics-Analytics/data_analysis/deliverables/deep_dive.pdf).
- **Docs:** [`docs/`](VoltEdge-Electronics-Analytics/docs/) 01–09 + [walkthrough](VoltEdge-Electronics-Analytics/docs/walkthrough.md) + [PDF bundle](VoltEdge-Electronics-Analytics/docs/VoltEdge-Electronics-Documentation.pdf).
- **Visual case study:** [7-page PDF carousel](VoltEdge-Electronics-Analytics/portfolio/VoltEdge-Electronics-case-study.pdf).

**Result.** Net Revenue **$31.35M** over 24 months. Growth is **+137% total but only
+40% US like-for-like** — mostly expansion. Contribution margin just reached break-even. The real problem is **working capital**: a ~134-day cash-conversion
cycle, all in inventory, with **~$4.4M freeable**. Returns are a **$1.65M net-margin drag**
(~63% controllable); promo days cost ≈ $0.3M/yr of gross profit.

**Scale.** 294 SKUs · ~103k customers · ~167k orders · ~275k order lines · blended gross
margin ~18%.

---

### 3. Voxa+ — subscriber churn root-cause diagnosis
📂 [`voxaplus-churn-diagnosis/`](voxaplus-churn-diagnosis/) · [project README](voxaplus-churn-diagnosis/README.md)

**Scenario.** Voxa+ is an SVOD streaming service in Brazil, Mexico, and the United States.
Monthly gross subscriber churn **nearly doubled starting in month 34** of a 36-month window
and has stayed elevated. Leadership needs a data-driven root cause before the next board
meeting.

**Question.** What caused the spike — content, price, acquisition quality, billing, the app,
or the market?

**What's in it.**
- **Diagnosis** ([`data_analysis/`](voxaplus-churn-diagnosis/data_analysis/)): 10 findings F01–F10 — spike size & persistence → market decomposition → segment breadth → engagement-precedes-churn → CTV app regression → Brazil price interaction → Mexico cohort quality → payments ruled out → financial impact → synthesis. Dual-track SQL + pandas, parity-checked.
- **Deliverables:** [board summary](voxaplus-churn-diagnosis/data_analysis/deliverables/board_summary.pdf) · [deep dive](voxaplus-churn-diagnosis/data_analysis/deliverables/deep_dive.pdf).
- **Power BI** ([`powerbi/`](voxaplus-churn-diagnosis/powerbi/)): 7 pages — Executive Summary · Retention & Cohorts · Content & Engagement · Pricing & Plans · Acquisition Quality · CX, Billing & App Quality · Market Context. Code-generated TMDL model, 113 DAX measures.
- **Docs:** [`docs/`](voxaplus-churn-diagnosis/docs/) 01–09 + [walkthrough](voxaplus-churn-diagnosis/docs/walkthrough.md) + [PDF bundle](voxaplus-churn-diagnosis/docs/Voxa+_Documentation.pdf).
- **Visual case study:** [7-page PDF carousel](voxaplus-churn-diagnosis/portfolio/Voxa+-case-study.pdf).

**Result.** The near-doubling is **three overlapping factors, none sufficient alone**:
1. an **app "v3" connected-TV playback regression** — the acute trigger (CTV-heavy churn
   4.1% → 8.4% while the rest went 4.1% → 5.6%);
2. the **Brazil price increase** — did nothing to engaged subscribers, **+18 pp** to
   already-disengaged ones (the amplifier, Brazil-only);
3. a **months-old Mexico cohort-quality drag** — newer Mexican cohorts retain ~8 pp worse at
   month 3 (the pre-existing drain).

Payments were tested and **ruled out**.

**Scale.** BR / MX / US · 36 months · ~120k cumulative / ~70k active subscribers · viewing
at subscriber-day grain.

---

### 4. SwiftBite Delivery — a marketplace supply-side incentive experiment
📂 [`SwiftBite-Delivery-Analytics/`](SwiftBite-Delivery-Analytics/) · [project README](SwiftBite-Delivery-Analytics/README.md)

**Scenario.** SwiftBite is a food-delivery marketplace in one Brazilian metro, 12 zones.
At Friday/Saturday dinner peak, and in structurally supply-short zones, courier supply
lags demand → high ETA, no-courier cancellations, and couriers idle in the wrong zones.
Ops piloted a **dynamic per-delivery bonus** for a named zone during the peak block, run as
a **randomized experiment with the zone-day as the unit** — a supply-side intervention on a
two-sided marketplace, with a real risk of cannibalising supply from neighbouring zones.

**Question.** Does the incentive lift marketplace liquidity enough to beat the bonus cost?
Only in the supply-short zones, or everywhere? How much of the local gain is just supply
pulled from adjacent zones?

**What's in it.**
- **Primary deliverable — the read-out** ([`data_analysis/`](SwiftBite-Delivery-Analytics/data_analysis/)): anchor → randomisation & balance → primary effect → guardrails → novelty → heterogeneity by supply-stress tier → neighbour-zone cannibalisation → synthesis. Eight parity-verified analyses, dual-track pandas + DuckDB. The zone-day design is analysed three ways — **cluster-robust (by zone) SEs, randomization inference, and a wild-cluster bootstrap** — with every number reported on all three.
- **Deliverables:** [board summary](SwiftBite-Delivery-Analytics/data_analysis/deliverables/board_summary.pdf) · [deep dive](SwiftBite-Delivery-Analytics/data_analysis/deliverables/deep_dive.pdf).
- **Secondary deliverable — Power BI** ([`powerbi/`](SwiftBite-Delivery-Analytics/powerbi/)): 4 pages — Executive Overview · Marketplace Health · Pricing & Incentive Experiment · Courier Economics. 15-table TMDL model (28 relationships, `fact_order` role-playing `dim_zone` ×3, an adjacency bridge), 71 DAX measures.
- **Docs:** [`docs/`](SwiftBite-Delivery-Analytics/docs/) 00–09 + [walkthrough](SwiftBite-Delivery-Analytics/docs/walkthrough.md) + [PDF bundle](SwiftBite-Delivery-Analytics/docs/SwiftBite-Delivery-Documentation.pdf).
- **Visual case study:** [7-page PDF carousel](SwiftBite-Delivery-Analytics/portfolio/SwiftBite-Delivery-case-study.pdf).

**Result.** The incentive **improves marketplace liquidity** — fulfillment **+1.87 pp**
(cluster CI [+1.27, +2.46]; randomization-inference p = 3×10⁻⁴; wild-cluster bootstrap
agrees), ETA p90 **−6 min**, no-courier cancels **−0.36 pp**, concentrated in the
supply-short and balanced zones (arm × tier interaction p = 0.004), with only a small
(~17%, not significant) neighbour-zone drag. **But it does not pay for itself:** a flat
R$4.5 bonus on every treated-block delivery buys ~127 incremental orders at **~R$281 each**
against a ~R$10 contribution margin. **Recommendation: don't ship the flat bonus —
restructure it to reward incremental supply and cap it to the short + balanced zones.**

**Scale.** One metro / BRL · 20 months · 12 zones · ~7.5M orders · 10-week experiment,
unit = zone-day (~840, 420/arm).

---

### 5. LumaBank Activation — an onboarding A/B test that breaks mid-flight
📂 [`LumaBank-Activation-Experiment/`](LumaBank-Activation-Experiment/) · [project README](LumaBank-Activation-Experiment/README.md)

**Scenario.** LumaBank is a fictional Brazilian neobank. Growth redesigned onboarding —
fewer steps, identity-document upload **deferred to after** account creation — and launched
it as a user-level 50/50 A/B test, primary metric **Day-7 Activation**. Around day 11 of a
planned 6-week window, a real **mobile app deploy** resets the on-device variant-assignment
cache: some already-assigned users **switch arms mid-journey**, and post-deploy signups fall
into a **fallback that assigns by region**, not at random. This project *is* the incident —
catching it, diagnosing it, and deciding what to do under deadline pressure.

**Question.** Did the onboarding redesign work — and once the experiment breaks, how do you
salvage a defensible answer without either burning the timeline or accepting bias?

**What's in it.**
- **Primary deliverable — the incident read-out** ([`data_analysis/`](LumaBank-Activation-Experiment/data_analysis/)): pre-registration & baseline power → **continuous SRM monitoring** (re-derived independently from the raw assignment log) → root-cause diagnosis of the two-part failure → a documented three-option decision (truncate / exclude-contaminated / restart) with MDE and residual-bias trade-offs → re-planned power → clean re-run readout with guardrails and channel heterogeneity. Five parity-verified analyses, dual-track pandas + DuckDB.
- **Deliverables:** [board summary](LumaBank-Activation-Experiment/data_analysis/deliverables/board_summary.pdf) · [deep dive](LumaBank-Activation-Experiment/data_analysis/deliverables/deep_dive.pdf) (includes a day-by-day incident timeline).
- **Secondary deliverable — Power BI** ([`powerbi/`](LumaBank-Activation-Experiment/powerbi/)): 4 pages — Executive Overview · Onboarding & Activation Funnel · Experiment Integrity Monitor · Experiment Readout. 18-table TMDL model, 46 DAX measures.
- **Docs:** [`docs/`](LumaBank-Activation-Experiment/docs/) 00–07, 09 (scope → context & SRM runbook → architecture → dictionary → ETL → model → DAX → visual identity → report structure) + [walkthrough](LumaBank-Activation-Experiment/docs/walkthrough.md) + [PDF bundle](LumaBank-Activation-Experiment/docs/LumaBank-Activation-Documentation.pdf).
- **Visual case study:** [7-page PDF carousel](LumaBank-Activation-Experiment/portfolio/LumaBank-Activation-case-study.pdf).

**Result.** The daily SRM check fires **2 days after the deploy** (trailing-7d p crosses
0.001; the cumulative test never does, diluted by ten clean pre-deploy days). Root cause:
191 contaminated users plus a fallback that skews treatment share from **76.5% (Southeast)
to 35.3% (North)**. Truncating or excluding the affected users both leave an MDE too wide to
trust — **restart was the only zero-bias option**. On the clean re-run, Day-7 Activation
lifts **+4.58 pp** (95% CI [+2.55, +6.62], p ≈ 1×10⁻⁵). The KYC-rejection guardrail clears
non-inferiority; the **flagged-fraud guardrail does not** (95% upper bound above the agreed
margin). **Recommendation: a monitored rollout with a fraud circuit-breaker**, not an
unconditional launch.

**Scale.** Brazil / BRL · 21 months (2025-01 → 2026-09) · ~135k platform signups · ~13.5k in
the original (broken) run · ~9k in the clean re-run.

---

## Browse by type of work

### 📊 Dashboards — Power BI reports (built as code)

Every report is a PBIR project: semantic model in TMDL, report assembled with the `pbir`
CLI, theme and every visual under version control. Data layer is a set of import partitions
over the curated Parquet via a `pDataFolder` parameter.

| Project | Pages | Semantic model | DAX measures | Entry point |
|---|---|---|---|---|
| AeroVanti SkyPoints | 4 — Executive · Tiers · Experiment · Funnel | 21 tables | 62 | [`powerbi/`](AeroVanti-SkyPoints-Analytics/powerbi/) · [report structure](AeroVanti-SkyPoints-Analytics/docs/09_report_structure.md) |
| VoltEdge Electronics | 7 — Exec · Sales · Marketing · Web · Logistics · CRM · Product | 28 tables (~65 rels) | 167 | [`powerbi/`](VoltEdge-Electronics-Analytics/powerbi/) · [report guide](VoltEdge-Electronics-Analytics/docs/07_report_guide.md) |
| Voxa+ | 7 — Exec · Retention · Content · Pricing · Acquisition · CX/Billing/App · Market | code-generated TMDL | 113 | [`powerbi/`](voxaplus-churn-diagnosis/powerbi/) · [report structure](voxaplus-churn-diagnosis/docs/09_report_structure.md) |
| SwiftBite Delivery | 4 — Executive Overview · Marketplace Health · Pricing & Incentive Experiment · Courier Economics | 15 tables (28 rels) | 71 | [`powerbi/`](SwiftBite-Delivery-Analytics/powerbi/) · [report structure](SwiftBite-Delivery-Analytics/docs/09_report_structure.md) |
| LumaBank Activation | 4 — Executive Overview · Onboarding & Activation Funnel · Experiment Integrity Monitor · Experiment Readout | code-generated TMDL, 18 tables (22 rels) | 46 | [`powerbi/`](LumaBank-Activation-Experiment/powerbi/) · [report structure](LumaBank-Activation-Experiment/docs/09_report_structure.md) |

Gallery images and diagram sources: `*/portfolio/` and `voxaplus-churn-diagnosis/portfolio/gallery/`.

### 🔬 Exploratory & diagnostic analyses

| Project | Deliverable | What it does |
|---|---|---|
| **VoltEdge Electronics** | [10 findings](VoltEdge-Electronics-Analytics/data_analysis/findings/) + [board summary](VoltEdge-Electronics-Analytics/data_analysis/deliverables/board_summary.pdf) / [deep dive](VoltEdge-Electronics-Analytics/data_analysis/deliverables/deep_dive.pdf) | Decomposes growth, margin, working capital, returns and CAC for an exec audience; every result computed in SQL and pandas and asserted equal. |
| **Voxa+** | [10 findings F01–F10](voxaplus-churn-diagnosis/data_analysis/findings/) + [board summary](voxaplus-churn-diagnosis/data_analysis/deliverables/board_summary.pdf) | Root-cause investigation of a churn spike: market decomposition, engagement-before-cancellation, cohort-quality retention curves, an interaction test on price, and an explicit "ruled out" section for payments. |
| **AeroVanti SkyPoints** | [Deep dive B — program health](AeroVanti-SkyPoints-Analytics/data_analysis/deliverables/deep_dive_B_program_health.md) | Point hoarding, breakage sensitivity, redemption funnel, redeemer-vs-non-redeemer retention. |

### 🧪 Experiments (A/B tests)

| Project | Deliverable | Method highlights |
|---|---|---|
| **AeroVanti SkyPoints — Flash Redemption** | [Deep dive A — A/B test read-out](AeroVanti-SkyPoints-Analytics/data_analysis/deliverables/deep_dive_A_ab_test_readout.md) · [findings](AeroVanti-SkyPoints-Analytics/data_analysis/findings/) | Sample-ratio-mismatch + covariate-balance checks before reading any effect; stated hypothesis with MDE/power rationale; primary metric with effect size, 95% CI and post-stratified + covariate-adjusted estimates; four guardrails including a non-inferiority test on revenue; novelty-effect decay check; heterogeneity by tier with a formal interaction test (p = 0.0007). |
| **SwiftBite Delivery — zone-hour incentive** | [board summary](SwiftBite-Delivery-Analytics/data_analysis/deliverables/board_summary.pdf) · [deep dive](SwiftBite-Delivery-Analytics/data_analysis/deliverables/deep_dive.pdf) · [findings](SwiftBite-Delivery-Analytics/data_analysis/findings/) | A supply-side experiment on a two-sided marketplace, **unit = zone-day** (~840, 12 clusters). Inference three ways — cluster-robust SEs, randomization inference, wild-cluster bootstrap. Realised MDE for the clustered design; formal arm × tier interaction test; a **spatial spillover / cannibalisation** analysis (adjacent-control gap, per-neighbour drag regression, clean-control bound, cannibalisation-adjusted metro net); guardrail **G1 = incentive cost per *incremental* delivered order** with a zone-cluster bootstrap CI. Conclusion: the lever works, its pricing does not — **do not roll out the flat bonus**. |
| **LumaBank Activation — onboarding redesign** | [board summary](LumaBank-Activation-Experiment/data_analysis/deliverables/board_summary.pdf) · [deep dive](LumaBank-Activation-Experiment/data_analysis/deliverables/deep_dive.pdf) · [findings](LumaBank-Activation-Experiment/data_analysis/findings/) | **Continuous SRM monitoring** (not a one-time pre-flight check) that catches a real production bug corrupting randomisation mid-experiment; root-cause diagnosis separating contamination from a region-biased fallback; a documented three-option decision under deadline pressure (truncate / exclude-contaminated / restart) with MDE and residual-bias trade-offs for each; power/MDE **re-planned from scratch** for the shorter re-run window; one-sided **non-inferiority tests** on two fintech guardrails (one passes, one doesn't); formal arm × channel interaction test. Conclusion: the redesign works, but ship it monitored, not unconditionally. |

### 🏗️ Data engineering — ETL pipelines

All four follow the same shape and are byte-reproducible from one seed:
**raw** (messy multi-source exports: CSV / XLSX / JSON / JSONL) → **staging** (typed,
cleaned, conformed) → **curated** (Kimball star, Parquet + CSV) → **DQ gate** (hard checks
must pass).

| Project | Pipeline | Docs |
|---|---|---|
| AeroVanti SkyPoints | [`etl/`](AeroVanti-SkyPoints-Analytics/etl/) — `01_generate_raw` → `02_clean_stage` → `03_build_curated` → `dq_checks` | [02_data_architecture](AeroVanti-SkyPoints-Analytics/docs/02_data_architecture.md) · [04_etl_pipeline](AeroVanti-SkyPoints-Analytics/docs/04_etl_pipeline.md) |
| VoltEdge Electronics | [`etl/`](VoltEdge-Electronics-Analytics/etl/) — `run_pipeline.py` | [02_data_architecture](VoltEdge-Electronics-Analytics/docs/02_data_architecture.md) · [04_etl_pipeline](VoltEdge-Electronics-Analytics/docs/04_etl_pipeline.md) |
| Voxa+ | [`etl/`](voxaplus-churn-diagnosis/etl/) — `gen/` world+content+economics → `01`→`02`→`03` → `dq_checks` | [02_data_architecture](voxaplus-churn-diagnosis/docs/02_data_architecture.md) · [04_etl_pipeline](voxaplus-churn-diagnosis/docs/04_etl_pipeline.md) |
| SwiftBite Delivery | [`etl/`](SwiftBite-Delivery-Analytics/etl/) — vectorised marketplace simulator (6 systems + geo ref) → `01_generate_raw` → `02_clean_stage` → `03_build_curated` → `dq_checks` | [02_data_architecture](SwiftBite-Delivery-Analytics/docs/02_data_architecture.md) · [04_etl_pipeline](SwiftBite-Delivery-Analytics/docs/04_etl_pipeline.md) |
| LumaBank Activation | [`etl/`](LumaBank-Activation-Experiment/etl/) — 6-system neobank simulator (seeded true effect + bug magnitudes) → `01_generate_raw` → `02_clean_stage` → `03_build_curated` → `dq_checks` | [02_data_architecture](LumaBank-Activation-Experiment/docs/02_data_architecture.md) · [04_etl_pipeline](LumaBank-Activation-Experiment/docs/04_etl_pipeline.md) |

### 🧱 Data modelling — semantic layer & DAX

| Project | Model | DAX library | Docs |
|---|---|---|---|
| AeroVanti SkyPoints | 21-table star + experiment tables (TMDL) | 62 measures | [05_data_model](AeroVanti-SkyPoints-Analytics/docs/05_data_model.md) · [06_dax_measures](AeroVanti-SkyPoints-Analytics/docs/06_dax_measures.md) |
| VoltEdge Electronics | 28 tables, ~65 relationships, role-playing dates, helper tables | 167 measures in 14 folders | [05_data_model](VoltEdge-Electronics-Analytics/docs/05_data_model.md) · [06_dax_measures](VoltEdge-Electronics-Analytics/docs/06_dax_measures.md) |
| Voxa+ | code-generated TMDL star | 113 measures | [05_data_model](voxaplus-churn-diagnosis/docs/05_data_model.md) · [06_dax_measures](voxaplus-churn-diagnosis/docs/06_dax_measures.md) |
| SwiftBite Delivery | 15-table star, 28 relationships, `fact_order` role-playing `dim_zone` ×3, zone-adjacency bridge | 71 measures in 6 folders | [05_data_model](SwiftBite-Delivery-Analytics/docs/05_data_model.md) · [06_dax_measures](SwiftBite-Delivery-Analytics/docs/06_dax_measures.md) |
| LumaBank Activation | code-generated TMDL star, 18 tables, 22 relationships | 46 measures in 9 folders | [05_data_model](LumaBank-Activation-Experiment/docs/05_data_model.md) · [06_dax_measures](LumaBank-Activation-Experiment/docs/06_dax_measures.md) |

The DAX is generated from Python (`etl/pbi_measures.py` in each project) so the measure list,
the docs, and the model stay in sync.

### 📚 Documentation

Each project carries a numbered `docs/` set (business context → architecture → data
dictionary → data model → DAX → visual identity, most with data quality → report structure
too), a `walkthrough.md` build log, and bundled PDFs.

| Project | docs/ set | Walkthrough | PDF bundle |
|---|---|---|---|
| AeroVanti SkyPoints | 00–09 | [walkthrough](AeroVanti-SkyPoints-Analytics/docs/walkthrough.md) | [Documentation](AeroVanti-SkyPoints-Analytics/docs/AeroVanti-SkyPoints-Documentation.pdf) · [Summary](AeroVanti-SkyPoints-Analytics/docs/AeroVanti-SkyPoints-Summary.pdf) |
| VoltEdge Electronics | 01–09 | [walkthrough](VoltEdge-Electronics-Analytics/docs/walkthrough.md) | [Documentation](VoltEdge-Electronics-Analytics/docs/VoltEdge-Electronics-Documentation.pdf) · [Summary](VoltEdge-Electronics-Analytics/docs/VoltEdge-Electronics-Documentation-Summary.pdf) |
| Voxa+ | 01–09 | [walkthrough](voxaplus-churn-diagnosis/docs/walkthrough.md) | [Documentation](voxaplus-churn-diagnosis/docs/Voxa+_Documentation.pdf) · [Summary](voxaplus-churn-diagnosis/docs/Voxa+_Summary.pdf) |
| SwiftBite Delivery | 00–09 | [walkthrough](SwiftBite-Delivery-Analytics/docs/walkthrough.md) | [Documentation](SwiftBite-Delivery-Analytics/docs/SwiftBite-Delivery-Documentation.pdf) · [Summary](SwiftBite-Delivery-Analytics/docs/SwiftBite-Delivery-Summary.pdf) |
| LumaBank Activation | 00–07, 09 | [walkthrough](LumaBank-Activation-Experiment/docs/walkthrough.md) | [Documentation](LumaBank-Activation-Experiment/docs/LumaBank-Activation-Documentation.pdf) · [Summary](LumaBank-Activation-Experiment/docs/LumaBank-Activation-Summary.pdf) |

---

## Tech stack

- **Python** — pandas, DuckDB, PyArrow, NumPy, SciPy/statsmodels, matplotlib / seaborn
- **SQL** — DuckDB (analysis runs against the curated Parquet)
- **Power BI** — semantic models in **TMDL**, reports in **PBIR**, driven by
  [`pbir-cli`](https://pypi.org/project/pbir-cli/); themes as JSON
- **Architecture** — medallion (raw → staging → curated), Kimball dimensional modelling
- **Reproducibility** — one `SEED` per project; pipelines are deterministic; analysis
  results are parity-checked across the SQL and Python tracks

---

## Repository layout

```
data-analytics-portfolio/
├── README.md                        ← this file
├── AeroVanti-SkyPoints-Analytics/
├── VoltEdge-Electronics-Analytics/
├── voxaplus-churn-diagnosis/
├── SwiftBite-Delivery-Analytics/
└── LumaBank-Activation-Experiment/
        ├── README.md                ← project overview + reproduce steps
        ├── docs/                    ← numbered documentation + PDFs
        ├── etl/                     ← seeded raw→staging→curated pipeline + DQ checks
        ├── data/                    ← NOT in git — regenerated by the pipeline
        │     └── quality/dq_report.md   ← the one committed data artifact
        ├── powerbi/                 ← TMDL semantic model + PBIR report + theme
        ├── data_analysis/           ← sql/ + python/ + findings/ + parity/ + deliverables/
        ├── portfolio/               ← gallery images + write-up copy
        └── assets/                  ← brand palette + logo/background generators
```

The `data/` layers, Power BI caches (`.pbi/`, `*.abf`), and `__pycache__/` are
**git-ignored** — see [`.gitignore`](.gitignore). Everything
needed to rebuild them is in the repo.

---

## Reproducing a project

```bash
cd <project>

# 1. data pipeline: raw → staging → curated → DQ gate (deterministic)
python -m pip install -r etl/requirements.txt
python etl/run_pipeline.py

# 2. Power BI report (close Power BI Desktop first)
#    then in Desktop set the pDataFolder parameter to <project>/data/curated
cd powerbi && bash build_report.sh

# 3. the analysis — dual-track, must all print parity OK
cd ../data_analysis
for f in parity/*.py; do python "$f"; done      # VoltEdge / AeroVanti
python run_analysis.py                          # Voxa+
```

Per-project details are in each `README.md`. The Power BI models load from a
`pDataFolder` parameter that ships as a placeholder (`C:/PATH/TO/REPO/...`) — point it at
your local `<project>/data/curated` after running the pipeline.

---

## Note on the data

Every dataset in this repository is **synthetic**, produced by the generator scripts in each
project's `etl/` folder from a fixed random seed. Company names, brands, customers,
transactions, prices, and outcomes are invented for the purpose of demonstrating an
analytics workflow. Any resemblance to a real organisation or person is coincidental. The
scenarios are designed to be realistic — including the messiness in the raw layer and the
ambiguity in the findings — but they are not real.

---

## Contact

**Felipe Santana** — Senior Data / Product Analyst, open to international remote roles (USD/EUR).

[LinkedIn](https://www.linkedin.com/in/j-felipe-santana/) · [GitHub](https://github.com/FelipeSantanaJ)

Each project's `README.md` has the full write-up; `docs/` holds the supporting
documentation for each.
