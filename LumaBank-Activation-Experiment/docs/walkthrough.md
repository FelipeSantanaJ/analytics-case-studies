# LumaBank Activation Experiment — Build Walkthrough

A running narrative of the build. Each entry: what was done, why, where to look. Newest at
the bottom. Written as the phases complete, not reconstructed after the fact.

---

## Phase 0 — Scope & scaffold (2026-09-10)

Locked scope in `docs/00_scope.md`. Key calls: analysis-primary (Phase 10 is the headline
deliverable, following the AeroVanti model rather than VoltEdge/Voxa+/SwiftBite), Power BI
"lite" (4 pages), fintech-specific guardrails (KYC rejection, flagged fraud) as
non-negotiable, BRL only. The core hook — an onboarding A/B test that breaks mid-flight on
a real production bug — is what the whole project exists to demonstrate, so the scope doc
spends most of its length on the break mechanics (§4.2, §6) rather than on the product
itself. Created the folder tree under `PBI Pessoal/LumaBank-Activation-Experiment/`.

## Phase 1 — Business context & KPI framework (2026-09-10)

`docs/01_business_context_kpis.md`. Fictional Brazilian neobank; the two onboarding flows
(control = document upload before account creation, treatment = account-first with KYC
deferred to a limits gate) are specified before any data exists, exactly like AeroVanti's
Flash Redemption spec. The centerpiece is §9: the **continuous SRM + assignment-integrity
monitoring runbook** — five tests, WARN/ALERT thresholds, an ordered triage checklist. This
is what makes the project different from AeroVanti's balance check: there, SRM is a single
pre-flight test; here it's a standing process that has to *catch* something.

## Phase 2 — Data architecture (2026-09-10)

`docs/02_data_architecture.md`. Medallion raw → staging → curated. Six simulated systems
(Lumen Core Banking, Flagfox feature-flag service, Trilha onboarding, RiskGuard KYC/fraud,
Beacon mobile-release log, Órbita growth CRM). The curated star's two load-bearing tables
are `fact_activation` (the read-out surface) and `fact_srm_daily` (the integrity-monitor
surface) — both fully speced here, before either exists.

## Phase 3 — ETL pipeline (2026-09-10)

### 3.1 The true effect and the bug (kept only in `etl/config.py::EFFECT` / `BUG`)

Design intent: a real, channel-heterogeneous Day-7 Activation lift (paid_social/influencer
biggest, referral/organic smallest) sized close enough to the re-run's MDE that the
"deadline cost us precision" story actually bites. The break: a deploy-triggered cache
reset (contamination) plus a region/timezone-biased fallback for post-deploy signups
(composition bias) — both deterministic functions of a stable per-user hash, never the
RNG directly, so the same seed always reproduces the same incident.

### 3.2 Pipeline shape

Same shape as the sibling projects: `config.py` → `utils.py` → `01_generate_raw.py` →
`02_clean_stage.py` → `03_build_curated.py` → `dq_checks.py` → `run_pipeline.py`, plus
`gen_data_dictionary.py`.

### 3.3 Fixes made during the build

- **`pandas.to_datetime` on mixed-precision ISO-8601 silently drops rows.** The generator
  emits onboarding-step timestamps as `.isoformat()`; `signup_started` events always land
  on a whole minute (no fractional seconds) while activation events carry microseconds.
  Parsing the column with the pandas default (`format=None`) infers ONE format from the
  first non-null value and returns `NaT` for every row that doesn't match — silently, no
  error. Every user's `signup_ts` came back null, which cascaded into a `KeyError:
  'user_id'` three layers downstream (an empty `pd.DataFrame(rows)` had no columns to
  merge on) that took longer to trace than the actual bug. Fix: pin `format="ISO8601"` on
  every ISO parse call in `02_clean_stage.py` — it's the one format string that accepts
  mixed precision.
- **Lambda aggs on a multi-million-row `groupby` are dramatically slower than precomputed
  booleans.** `fact_transaction_day`'s per-type counts (`lambda s: (s == "pix").sum()`
  inside `.agg(...)`) took several minutes over ~2.7M transaction rows. Replaced with
  boolean columns computed once (`tx["pix_count"] = (tx["type"] == "pix").astype("int32")`)
  and summed inside a plain `.agg()` — seconds instead of minutes.
- **The treatment-effect double-count.** First cut computed `day7_eligible` for the
  baseline using each arm's OWN actual funnel (control's KYC-gated timing vs. treatment's
  account-first timing), then added the explicit per-channel ATE flips on top. Treatment's
  structurally higher account-creation rate (~94% vs. control's ~74%) was *already* an
  implicit ~10pp lift before a single flip was applied — the realised pooled lift came out
  at **+12.8 pp** against a **+3.6 pp** target. Fixed by splitting the funnel into a
  **counterfactual control-flow** version (arm-independent, drives the common baseline
  `day7_base`) and the **actual flow** (drives the emitted onboarding/KYC/account data).
  The explicit ATE flips are now the *only* source of the treatment effect on Day-7.
- **...and then losing ~3 pp of it in the curated recompute.** After the fix above, the
  realised lift measured directly in the generator (`world["day7"]`) matched the +3.6pp
  target, but `fact_activation.day7_activated` — recomputed in curated from `account_
  opened_flag AND first_txn_ts <= assigned_ts + 7d`, independently of the generator's own
  flag, by design (`dq_checks` asserts the two agree) — showed only +1.1pp for the re-run.
  Cause: a flipped (explicitly-activated) treatment user was drawn from the counterfactual
  eligibility pool, but their *actual* account-creation roll (`t_acc_first`, ~94%) is an
  independent coin flip — about 9% of flipped users had no real account row, so the
  curated recompute correctly saw them as not activated. Fixed at the source: any user who
  ends up `day7` or a later (`late_act`) activator is now **forced** to have an account
  (`acc_created |= day7 | late_act`) with a timestamp inside their flow's normal window —
  the generator's intent and the curated recompute now agree exactly, by construction
  rather than by coincidence.
- **Calibrating the break to actually trip the SRM runbook's thresholds.** The first
  calibration pass (moderate fallback share, mild geographic skew) produced a
  detectable-but-weak signal: cumulative χ² p bottomed around 0.03, never crossing the
  0.001 ALERT threshold, and the daily counts were too thin for the trailing-7-day test to
  fire cleanly either. Raised `fallback_share_0` (0.55 → 0.72) and sharpened the
  region-skew spread (`fallback_treat_frac_by_region` SE 0.66→0.78, N 0.31→0.35) so the
  bias is large enough, and geographically distinct enough, for the trailing-7-day χ² test
  to reach `p < 0.001` — the way the runbook actually catches things. Final calibration:
  ALERT fires on day 13 (2026-07-18, two days after the deploy); the cumulative test never
  crosses 0.001 (diluted by ten clean pre-deploy days), which is itself the right
  behaviour and is why the runbook (doc 01 §9) runs both tests, not just one.
- **Near-future censoring.** A handful of late (day 8–30) activators from signups near the
  window's end would have their first transaction *after* `WINDOW_END` — the generator now
  drops those transaction rows rather than fabricating post-window history, so `day30_
  activated` for those users is correctly `0` (unobserved), not silently wrong.
- **`dq_checks` assertion tuned to the real detector.** Originally asserted the
  *cumulative* SRM p-value crosses 0.001 by 2026-07-17 — too strict once the fallback
  timing was recalibrated (ALERT fires on the trailing-7-day test one day later than that,
  which is the correct and intended detection path). Rewrote the hard check to require an
  `alert_state == "alert"` day on/after 2026-07-17 and downgraded "does the cumulative test
  also cross 0.001" to a soft, informational check.

**Final run (SEED 20260910) — 0 hard DQ failures, 1 benign warning:** 135,000 signups;
re-run control Day-7 Activation 45.2%, treatment 49.8% (**lift +4.6 pp**, re-run MDE ≈
3.0 pp); KYC rejection 8.1%, flagged-fraud 0.95%, onboarding tickets 94/1k; 191
contaminated + 681 biased-fallback users in the original run; SRM ALERT first fires
2026-07-18.

## Phase 4 — Data documentation (2026-09-10)

`docs/03_data_dictionary.md` (auto-generated, 17 tables), `docs/04_etl_pipeline.md`,
`docs/05_data_model.md` (bus matrix, 9 facts × 8 dims, mermaid ER diagram). No surprises
here — the corrections that *do* touch these docs (the `fact_activation` grain change)
were made later, in Phase 7, and backported into docs 02/05 at that time rather than
re-litigated here.

## Phase 5 — Visual identity (2026-09-10)

Proposed "deep ink-blue + coral" verbally before touching any file. Building
`assets/brand.py`, checked the actual hex values of the four sibling palettes and found the
proposed ink-blue sat close to VoltEdge's navy (`#0E2A4E`/`#123E6E`) and wasn't far from
AeroVanti's blue (`#0B5FA5`) either — exactly the collision the brief said to avoid.
Switched to **petrol/teal-ink `#0E4A52`** + **coral `#E2624B`** + **stone `#93A29C`**, warm
off-white ground — verified distinct from all four siblings (2× blue, 1× violet, 1×
forest-green) before committing. `assets/gen_logo.py` draws the mark as a rising step-line
to a coral dot (the Day-7 activation moment) rather than a vault/shield/piggy-bank cliché.

## Phase 6 — Semantic model as code (TMDL) (2026-09-10)

`powerbi/gen_semantic_model.py` — same schema-introspection pattern as the sibling
projects: read every curated Parquet, emit TMDL. 18 tables (17 curated + a `dim_month`
helper scoped to the fact window), 22 relationships.

- **`dim_app_release` fan-out.** The bug-catalogue release (`version = "4.61.0"`) and its
  hotfix are emitted for *both* iOS and Android — two rows sharing one version string. The
  first relationship-building pass joined `fact_variant_assignment.app_version` to
  `dim_app_release.version` directly, which isn't unique, so the join fanned out and
  `fact_variant_assignment` inflated from 13,709 to 17,323 rows (breaking the "unique on
  `(user_id, assignment_seq)`" hard check). Fixed by deduplicating the release lookup on
  `version` before the merge — platform isn't needed for this join, only the release
  metadata is.
- **A real sentinel row, not just a schema-sample one.** The sibling projects' generators
  add a sentinel dimension row (e.g. `member_key = -1`) only to the 50-row *sample*
  `gen_semantic_model.py` uses for TMDL dtype inference — checking, the actual curated
  Parquet files never contain that row, so orphan fact rows (KYC decisions referencing a
  `user_id` absent from Core, ~1.5% of them) resolve to nothing in the real model. Fixed it
  properly here: `etl/03_build_curated.py` now appends a genuine `user_key = -1` row to
  the curated `dim_user.parquet` itself.

## Phase 7 — DAX measure library (2026-09-10)

`etl/pbi_measures.py` — 46 measures across 9 folders, `etl/gen_dax_doc.py` →
`docs/06_dax_measures.md`.

- **`fact_activation`'s grain was wrong for platform-health measures.** It had been built
  (Phase 3) as one row per **experiment subject** — 13,577 of 135,000 signups — which made
  perfect sense for the read-out but left no way to answer "is activation trending up" for
  the ~90% of signups outside the two experiment windows, exactly what the Executive
  Overview page needs. Widened `fact_activation` to **one row per signup, platform-wide**
  (135,000 rows), with a new `is_experiment_subject` column carrying the old meaning
  forward. Backported the correction into `docs/02_data_architecture.md`,
  `docs/05_data_model.md`, and the data-dictionary description; re-ran `dq_checks`
  (rescoped the assignment-integrity check to subjects only, added a grain assertion) —
  still 0 hard failures.

## Phase 8 — Report build, 4 pages (2026-09-10)

Built directly with the `pbir` CLI rather than a bespoke Python driver. The CLI now
exposes `add visual --from-json`, `pages background/resize/move`, `add filter`, and
`visuals sort/bind` natively — everything the sibling projects' `_drive_pbir.py` +
`gen_report_visuals.py` used to hand-roll. `powerbi/build_report.sh` +
`_visuals_0N_<page>.json` (one manifest per page) replace that pair.

- **No `Workspace/Model.SemanticModel` to connect to.** `pbir new report -c
  "Workspace/Model.SemanticModel"` expects a Fabric-published model; this project has no
  Fabric workspace and never will (it's a local, offline portfolio artifact). The working
  pattern: `pbir new report ... --thick --no-title` (a throwaway embedded connection),
  then `pbir report rebind ... --local "../LumaBankActivation.SemanticModel"` to point it
  at the real sibling `.SemanticModel` folder — a `byPath` connection, exactly what a
  normal Power BI Desktop PBIP project uses.
- **A pbir/OneDrive interaction bug, hit repeatedly.** `pbir rm` (page or visual) and
  `pbir pages rename` delete a folder by renaming it to a `.{page,visual}-delete-<id>`
  staging name and then removing that — and the final removal intermittently failed with
  `[WinError 5] Acesso negado` on this OneDrive-synced repo, **not transiently**: retrying
  the identical command 5–6 times over 20+ seconds failed identically every time. A plain
  PowerShell `Remove-Item -Recurse -Force` on the exact path named in the error succeeded
  where Python's own delete did not. One rename attempt left `pages.json`'s `pageOrder` /
  `activePageName` pointing at a half-deleted page; fixed by hand (a narrow, justified
  exception to "never hand-edit report JSON" — removing an orphaned id after a botched CLI
  delete, not authoring new report semantics) and re-validated. `build_report.sh` wraps
  every delete-sensitive `pbir` call in a retry-with-backoff helper and documents the
  manual-cleanup fallback in its header. This wasn't independently re-run end-to-end after
  being written, to avoid re-risking a report that now validates clean.
- **`multiRowCard` doesn't take a list of fields in one `--from-json` entry.** The
  Experiment Readout page's guardrail card needed three unrelated measures as its
  `Values`; the JSON manifest's `"Values": [...]` array was rejected. Created the visual
  with one measure, then appended the other two with `pbir visuals bind -a`.
- **Page-level filters carry the story.** The Experiment Integrity Monitor page is
  filtered to `fact_srm_daily[experiment_phase] = "original"` and the Experiment Readout
  page to `fact_activation[in_analysis_flag] = TRUE()` — every visual on each page is
  automatically about the right population without a single measure needing an explicit
  `CALCULATE` filter for it.

**`pbir validate --all`:** 4 pages, 26 visuals, 69 fields resolved, 0 warnings, 1 info.
Screenshot verification skipped — no live Power BI Desktop session available in this
environment; structural validation is the confidence check here.

## Phase 10 — Data analysis, the primary deliverable (2026-09-11)

`data_analysis/` — five investigation blocks, dual-track (pandas + DuckDB) throughout,
`parity/run_all.py` confirming all of it.

- **01 setup & pre-registration** — the platform's own pre-experiment Day-7 Activation
  (45.9%) and guardrail baselines; the original 6-week design's MDE (2.41 pp at
  ~6,750/arm) checked against what the platform history actually said.
- **02 SRM monitoring** — re-derived `fact_srm_daily` independently from the raw
  assignment log (not trusted from the curated table) and cross-checked 100% agreement.
  ALERT fires 2026-07-18, two days after the deploy; the cumulative test never crosses
  0.001 in the original run (diluted by ten clean days) — confirms why the runbook runs
  both a cumulative and a trailing-7-day test, not just one.
- **03 root-cause** — the release calendar pins the trigger to 2026-07-16 exactly; 191
  contaminated users (4.4%); the fallback allocates 65.6% to treatment overall, skewed
  from 76.5% treatment in the Southeast down to 35.3% in the North.
- **04 decision analysis** — truncating gives an MDE of 5.4–6.6 pp (worse in real time);
  excluding only the flagged users gets to 4.8 pp with an unresolved residual bias;
  neither would have reliably detected the +4.58 pp effect block 05 recovers. Restart was
  the only option with zero bias.
- **05 re-run readout** — **+4.58 pp** (95% CI [+2.55, +6.62], p ≈ 1.0e-5) against a
  recomputed MDE of 2.92 pp. KYC-rejection guardrail passes non-inferiority cleanly
  (treatment is directionally *better*); the **flagged-fraud guardrail does not** — the
  point estimate is small (+0.36 pp) but the one-sided 95% upper bound (+0.89 pp) sits
  above the +0.5 pp margin. Heterogeneity favours paid_social/influencer as designed, but
  the formal arm×channel interaction test is not significant (p = 0.52) at this sample.

### Fix made while building block 03 — a version-string collision

`dim_app_release.is_cache_reset_release` was flagged by matching `version == "4.61.0"` —
the hardcoded label for the deploy/hotfix releases. The generator's organic version
counter (shared across both platforms and 21 months) coincidentally reached the same
number once already, on an unrelated Android release in **2025-10-21**, so the release
cross-reference in block 03 initially printed three "cache-reset" releases instead of two,
one of them a year early. Fixed by matching on the exact **deploy date**
(`released_at == C.DEPLOY_DATE`) instead of the version string — unambiguous regardless of
any future numbering coincidence. Re-ran `03_build_curated.py` + `dq_checks` (still 0 hard
failures) and regenerated the data dictionary and semantic model.

**Deliverables:** `deliverables/build_deliverables.py` → `board_summary.{html,pdf}`
(decision-first) and `deep_dive.{html,pdf}` (the five findings in full, plus a day-by-day
incident timeline from the 2026-07-06 launch through the 2026-08-24→09-20 clean re-run).
Recommendation delivered: a **monitored rollout with a fraud circuit-breaker**, not an
unconditional launch — the guardrail split (one clean pass, one not established) is a more
interesting and more honest result than either "ship it" or "don't ship it" would have
been, and it fell out of the data rather than being written in beforehand.

## Phase 11 — Portfolio gallery images (2026-09-11)

`portfolio/gen_portfolio_images.py`, adapted from AeroVanti's generator (the closest
sibling — same analysis-primary structure, same "frame a real chart + one-line takeaway"
pattern) rather than SwiftBite's PBI-screenshot-heavy one, since LumaBank's headline
evidence lives in `data_analysis/outputs/figures/`, not the report canvas. Five images,
1600×820, built entirely from real numbers already computed in Phase 10 — no new analysis:

- `01_cover.png` — branded title card (petrol/coral), the four headline numbers.
- `02_the_break.png` — frames `02_srm_break.png` (the daily SRM chart): trailing-7d ALERT
  on 2026-07-18, cumulative test never gets there.
- `03_fallback_bias.png` — frames `03_fallback_bias.png`: the region-skewed fallback,
  Southeast 76.5% vs North 35.3% treatment share.
- `04_heterogeneity.png` — frames `05_heterogeneity_forest.png`: the clean re-run's
  +4.58 pp effect and per-channel breakdown.
- `05_deliverables.png` — the two PDF deliverables, mocked as stacked sheets.

All three source charts (generated in Phase 10) already matched the brand palette without
edits — the framing script only adds the header band, kicker, and takeaway strip. Visually
verified all five renders before committing.

## Phase 12 — Docs bundle & finalize (2026-09-11)

`docs/build_docs_bundle.py`, adapted from AeroVanti's markdown → HTML → headless-Chrome
print-to-PDF pattern, re-themed to the petrol/coral palette. This project's doc set stops
at `07_visual_identity.md` (no separate `08_data_quality`/`09_report_structure` docs were
produced, unlike SwiftBite/AeroVanti — DQ lives in `data/quality/dq_report.md` and report
structure was never split into its own doc). Two PDFs:

- `LumaBank-Activation-Documentation.pdf` (2.4 MB) — 00 scope through 07 visual identity,
  plus the full build walkthrough. 52 pages.
- `LumaBank-Activation-Summary.pdf` (0.9 MB) — scope, business context, data model only.

Rendered the cover page to confirm styling before committing. Added the `## Result`
section to the project README (the real numbers, not written until the project was
actually done) and closed out the phase checklist.
