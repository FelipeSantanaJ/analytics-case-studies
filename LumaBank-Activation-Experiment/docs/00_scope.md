# 00 — Scope & Scaffold (Phase 0)

**Project:** LumaBank — New-User Activation & the Onboarding Experiment That Broke Mid-Flight
**Fictional company:** LumaBank — a Brazilian neobank (digital account + card).
**Randomization:** per **user**, 50/50, via a feature-flag service.
**Primary metric:** **Day-7 Activation** — account created **and** first transaction within 7 days.
**Date locked:** 2026-09-10

> **PT — resumo.** Projeto de portfólio nº 5, e o primeiro de **fintech**. A LumaBank é um
> neobank brasileiro fictício (conta digital + cartão), moeda **BRL apenas**. O time de
> Growth/Produto redesenhou o fluxo de **onboarding/KYC** (menos etapas, upload de
> documento adiado para *depois* da criação da conta) para aumentar a ativação de novos
> usuários. A métrica primária é **Day-7 Activation** (conta criada **e** primeira
> transação até o 7º dia). O experimento é **randomizado por usuário**, 50/50, com janela
> planejada de **6 semanas**. Por volta do **dia 11**, o monitoramento diário de **SRM
> (sample ratio mismatch)** detecta um desvio significativo da proporção 50/50 — que
> começa **exatamente no dia de um deploy do app mobile** sem relação com o experimento. A
> investigação precisa separar dois efeitos do bug (contaminação de quem já estava no
> teste × viés de atribuição dos novos cadastros, correlacionado com região/timezone),
> avaliar três alternativas de correção com trade-offs de viés × poder × prazo, e refazer o
> experimento numa **janela mais curta** com o **poder/MDE recalculado**. Não é a história
> de "rodei um A/B test e deu certo" — é a de um experimento que quebra em produção e é
> diagnosticado e refeito sob prazo.

---

## 1. Premise

LumaBank is a Brazilian neobank: users open a free digital checking account and a card
entirely in-app. Growth is healthy at the top of the funnel — paid social, referral and
app-store search all bring signups — but a large share of new users **never transact**.
They download the app, start the sign-up, hit the KYC step (a full identity-document
upload *before* the account exists), and drop. The users who do get through often take
more than a week to make a first payment, by which point intent has cooled.

The Growth and Product teams redesigned the onboarding flow: **fewer steps to a working
account, and the identity-document upload deferred to *after* account creation** (the
account opens in a limited state, and the document is requested before limits are lifted
or a physical card ships). The hypothesis is that getting a usable account into the
user's hands sooner converts early intent into a first transaction.

This was launched as a **randomized experiment, unit = user, 50/50**, through the
feature-flag service: on assignment a new user sees either the **new** onboarding
(treatment) or the **existing** one (control). Planned window: **6 weeks**. Primary
metric: **Day-7 Activation**.

**What makes this project a portfolio piece is what happened next.** Around **day 11**,
the daily **sample-ratio-mismatch (SRM)** check — a standing part of how LumaBank runs
any experiment — flagged that the arms were no longer 50/50, and the drift had started on
the exact day of an unrelated **mobile app deploy**. The rest of the project is the
incident: detection → root-cause diagnosis → a documented decision between three
imperfect fixes under business time pressure → statistical re-planning → a clean re-run.

---

## 2. Locked scope decisions

| Dimension | Decision |
|---|---|
| Deliverable language | **English** (all docs, code, reports). Every deliverable also carries a short **PT** explanation of each step. Working chat in Portuguese. |
| Priority | **Phase 10 (`data_analysis/`) is the primary deliverable** — the experiment incident, end to end. Power BI is secondary, scoped to **4 pages**. Follows the AeroVanti model (analysis-primary, PBI lite), not VoltEdge/Voxa+/SwiftBite. |
| Portfolio gap this fills | No other project covers **fintech**, and none covers an experiment that **breaks mid-flight on a real production bug** and is diagnosed and re-run under deadline. |
| Geography / currency | **Brazil only, BRL only.** No second country, no FX — that ground is covered by VoltEdge. |
| Data window | **21 months: 2025-01-01 → 2026-09-30.** Months 1–17 give the pre-experiment activation trend; the original experiment sits in month 19; the re-run finishes inside month 21 (with room for its Day-7 outcomes). |
| Original experiment window | **6 weeks planned: 2026-07-06 → 2026-08-16.** Terminated early. |
| The break | **Mobile app deploy on 2026-07-16** (experiment day 11) resets the local variant-assignment cache for a subset of users. Hotfix release **2026-07-22**. |
| Re-run window | **4 weeks: 2026-08-24 → 2026-09-20**, bug fixed, **power/MDE recomputed** for the smaller sample the shorter window allows. The business could not wait another full 6 weeks. |
| Platform scale | ~**130,000 signups** over the 21 months; end run-rate ~**2,200–2,600 signups/week**; ~**60,000** active users (≥1 transaction in the trailing 30 days) at window end. |
| Experiment scale | Original: ~**13,500** randomized users (~6,750/arm). Re-run: ~**9,000** (~4,500/arm). |
| ETL / data-quality depth | **Balanced** (matches the other four): **6** simulated source systems, **7** generic data-quality issue classes (§5) **plus** a bug-specific catalog (§6). |
| Power BI track | Semantic model as code (TMDL) + PBIR report + `theme.json` + build script; **4 pages**, one business question per page. |
| Visual identity | **New palette, designed in Phase 5** — must not reuse AeroVanti (navy/amber), VoltEdge (navy), or Voxa+ (violet/amber). Direction: trust/fintech without the money-green cliché. |

---

## 3. Phase-1 report pages (4 pages, one question each)

| # | Page | The question it answers |
|---|---|---|
| 1 | **Executive Overview** | Is new-user activation healthy and trending the right way, and what did the (re-run) onboarding experiment conclude? |
| 2 | **Onboarding & Activation Funnel** | Where do new users drop — signup → KYC → first transaction — and how does the funnel differ between the old flow and the new one? |
| 3 | **Experiment Integrity Monitor** | Can the experiment be trusted? Daily allocation by arm, SRM p-value over time, the deploy/break marked, contaminated vs clean population. *This page exists to tell the break story visually.* |
| 4 | **Experiment Readout** | Did the new onboarding work on the re-run — primary effect with CI, guardrails (KYC rejection / fraud) held, and does the effect differ by acquisition channel? |

---

## 4. Experiment design (locked at Phase 0, detailed in Phase 1)

### 4.1 The original experiment (as pre-registered)

| Element | Decision |
|---|---|
| Unit of randomization | **User**, at the moment they enter the onboarding flow (feature-flag exposure ≈ signup start). |
| Split | **50/50**, treatment (new onboarding) vs control (existing onboarding). |
| Eligibility | Every new signup entering onboarding during the window, on a supported app version. Existing users are not re-onboarded and are out of frame. |
| Assignment | Feature-flag service hashes a stable user id → arm. Assignment timestamp and the serving app version are logged. |
| Treatment | Fewer onboarding steps; **identity-document upload deferred to after account creation** (account opens limited; document gates limit increases and the physical card). |
| Control | Current onboarding: full KYC document upload before the account is created. |
| Primary metric | **Day-7 Activation rate** = share of randomized users with account created **and** ≥1 transaction within 7 days of assignment. |
| Guardrail metrics | **(1) KYC rejection rate** — share of submissions rejected; **must not worsen** (non-negotiable — fintech). **(2) Flagged-fraud rate** — accounts with a fraud signal in the first 30 days; **must not worsen** (non-negotiable). **(3) Onboarding support tickets per 1,000 signups** — operational-cost guardrail. Health metric: time-to-first-transaction. |
| Planned analyses | SRM / balance check (see §4.3 — here it is **continuous**, not pre-flight only); stated hypothesis + **MDE / power for the 6-week window**; primary effect with 95% CI; **heterogeneity by acquisition channel** with a formal arm×channel interaction test; novelty check across the window. |
| Planning values (to finalize in Phase 1) | Control Day-7 Activation ≈ **48%**; target detectable lift ≈ **+3 pp**; α = 0.05 two-sided, power = 80%; ~6,750/arm → MDE ≈ **2.4–2.6 pp**. |

### 4.2 The break (deterministic, baked in Phase 3)

The 2026-07-16 mobile deploy reset the on-device variant-assignment cache for a subset of
users. Two distinct effects, which the investigation must **separate**:

1. **Contamination** — users **already assigned before the deploy** whose cache was reset
   (`cache_reset_flag = 1`). A fraction of them received a **second assignment** on their
   next app open, sometimes to the **other arm** → they experienced part of one arm's
   treatment and part of the other's, mid-journey.
2. **Post-deploy attribution bias** — **new signups after the deploy** fell into an
   assignment **fallback** (`assignment_source = 'fallback'`) that does **not** randomize
   correctly: the fallback arm is a deterministic function of **region / timezone**. So
   the post-deploy arms differ **in composition** (geography, and everything correlated
   with it), not only in **proportion**. The fallback share decays as the 2026-07-22
   hotfix rolls out.

### 4.3 SRM monitoring as a standing process (not a one-off)

Unlike AeroVanti — where the balance check is a single **pre-flight** test done once
before trusting the result — LumaBank runs SRM monitoring **continuously for the life of
every experiment**. Documented in Phase 1 as an operational **runbook**: a daily job runs
a chi-square test on cumulative and trailing-7-day arm counts; an alert fires at
**p < 0.001 confirmed on two consecutive days**; escalation pauses enrollment and notifies
the experiment owner and platform on-call; the triage checklist checks recent releases,
the `assignment_source` mix, and the per-region split. **This monitoring is what catches
the bug** — it is the difference between this project and AeroVanti.

### 4.4 The decision (three options, documented with trade-offs)

| Option | Bias | Statistical power | Timeline | Note |
|---|---|---|---|---|
| **1. Truncate** — use only data up to the day before the deploy | Low (clean randomization pre-deploy) | **Very low** — ~10 days, ~¼ of planned N, and assignments in days 4–10 are right-censored before their Day-7 window closes | Immediate, but inconclusive | Honest but almost certainly can't clear the MDE |
| **2. Exclude only the contaminated** — keep clean pre-deploy users; drop arm-switchers; drop or re-weight the biased post-deploy fallback | **Residual** — can't prove every contaminated user was found; re-weighting rests on the observed covariates only | Moderate — loses ~30–40% of the post-deploy sample | A few days of analysis, no new data | Fastest defensible answer, but reviewer-fragile |
| **3. Restart clean** — fix the cache/fallback bug, re-randomize, run again | **None** | Recomputed for whatever window the business allows | Worst — but capped at 4 weeks, not another 6 | The choice |

**Chosen: restart**, in a **4-week** window with the bug fixed and **power/MDE recomputed
from scratch** for the ~9,000 users available — *not* the original 6-week MDE reused. The
deep dive states the explicit cost of the deadline: at ~4,500/arm the re-run can only
reliably detect a lift of roughly **≥ 3 pp**, so a true effect in the **2–3 pp** range —
which the original 6-week design was powered for — would now likely be missed.

### 4.5 The final readout (re-run, clean)

Hypothesis restated; power recomputed for the 4-week window; **primary effect** (Day-7
Activation, treatment − control) with 95% CI; **guardrails** — KYC rejection rate and
flagged-fraud rate treated as **non-negotiable** (a faster activation bought at the cost
of letting risk through is a fail), plus support-ticket load; **heterogeneity by
acquisition channel** (paid social, organic, referral, app-store search, influencer) with
a formal interaction test.

**Underlying true effect:** decided during Phase 3 (ETL) and baked into the generated
data with plausible noise and channel heterogeneity. The true values live only in
`etl/config.py`; Phase 10 must detect and quantify them **as if blind**. The bug
magnitudes (reset share, arm-switch fraction, fallback share and its region skew) are
likewise set in Phase 3 and recovered by the investigation, not read off.

---

## 5. Data-quality issues to inject (generic set)

1. **Multiple date/time formats** across source exports — `DD/MM/YYYY` in the onboarding
   CSV, ISO-8601 in the KYC feed, Unix epoch-milliseconds in the transaction log.
2. **Timezone drift** — the risk/fraud system logs in **UTC**; everything else is
   `America/Sao_Paulo`, with no offset column.
3. **Money as strings** — `"R$ 1.234,56"`, `"1234.56"`, `"1.234,56"` mixed in
   transaction-amount and fee fields.
4. **Mojibake / mixed encoding** in user names and city fields.
5. **Duplicate rows** — the app retries on flaky mobile connections, so a slice of
   onboarding-step events and variant-assignment events are exact or near-exact duplicates.
6. **Missing master rows** — some `user_id`s appear in event feeds with no row in the
   user dimension export (referential gap).
7. **Snapshot-vs-log drift** — a "current variant" snapshot table that disagrees with the
   variant-assignment **event log**. (Diagnostically relevant: this disagreement is one of
   the first visible symptoms of the contamination.)

---

## 6. Bug-specific data catalog (the break, injected on purpose in Phase 3)

| Element | Behaviour to simulate |
|---|---|
| `cache_reset_flag` | Emitted for **~12–18%** of users **already assigned before 2026-07-16**, on or shortly after the deploy. |
| Arm switch | **~40%** of the reset users get a **second `variant_assignments` row** on next app open; of those, ~50% land in the **opposite** arm → contaminated. |
| `assignment_source = 'fallback'` | For signups **after 2026-07-16**: ~**30–40%** on day 1, **decaying to ~0 over ~5 days** as the 2026-07-22 hotfix rolls out. |
| Fallback bias | Fallback arm = deterministic hash of **region / timezone**, not the RNG → post-deploy arms diverge in **geographic composition**, not just in count. |
| `app_releases` | Contains the routine 2026-07-16 deploy (cause) and the 2026-07-22 hotfix (fix), among ~2–4 releases/month of noise. |

---

## 7. Simulated source systems

| System | Feeds | Grain |
|---|---|---|
| **Feature-flag / experiment service** | `variant_assignments` (user, arm, `assigned_ts`, `assignment_source`, `cache_reset_flag`, app version), `exposure_log`, `variant_snapshot` (current-state table) | assignment / exposure event |
| **Onboarding / KYC service** | `onboarding_steps` (step, ts), `kyc_submissions` (doc type, submitted_ts), `kyc_decisions` (approved / rejected / manual_review, reason code, decided_ts) | step / submission / decision |
| **Mobile app release log** | `app_releases` (version, platform, `released_ts`, rollout %, notes) — the release calendar for root-cause cross-check | release |
| **Core banking / ledger** | `accounts` (user, opened_ts, status), `transactions` (account, ts, type, `amount_brl`, MCC) — first transaction = activation | account / transaction |
| **Risk / fraud system** | `fraud_signals` (user, flagged_ts UTC, signal type, score), `kyc_reason_codes` reference | fraud signal |
| **CRM / marketing / support** | `acquisition` (user, channel, campaign, first_touch_ts), `support_tickets` (user, opened_ts, category, channel) | user / ticket |

---

## 8. Curated star schema (detailed in Phase 2)

- **Dimensions:** `dim_user`, `dim_date`, `dim_acquisition_channel` (paid social · organic ·
  referral · app-store search · influencer), `dim_region` (UF + macro-region + timezone
  offset), `dim_experiment_arm` (control · treatment · ambiguous), `dim_app_release`,
  `dim_kyc_outcome`, `dim_onboarding_step`.
- **Facts:**
  - `fact_variant_assignment` — **one row per assignment event** (contaminated users have
    ≥2): `user_key`, `arm_key`, `assigned_ts`, `assignment_source`, `cache_reset_flag`,
    `app_release_key`, `is_first_assignment`, `is_effective_assignment`.
  - `fact_onboarding_step` — user × step × ts.
  - `fact_kyc_decision` — one row per decision: `outcome_key`, `reason_code`, `is_rejected`.
  - `fact_activation` — **one row per randomized user** (the analysis surface for the
    read-out): effective `arm_key`, `assigned_date_key`, `account_opened_flag`,
    `first_txn_ts`, `days_to_first_txn`, `day7_activated`, `cohort`
    (`pre_deploy` · `post_deploy` · `restart`), `contaminated_flag`, `in_analysis_flag`.
  - `fact_transaction_day` — user × day (platform trend, time-to-first-transaction).
  - `fact_fraud_event` — one row per fraud signal.
  - `fact_support_ticket` — one row per ticket.
- `dq_checks.py` includes a check that **would catch the SRM as a data-quality failure**
  (arm-count chi-square by day), not only as an analysis step later.

---

## 9. Out of scope (explicit)

- A second country, region expansion, multi-currency / FX (covered by VoltEdge).
- Credit underwriting, limit-setting, lending — the account here is a checking account + card.
- A **fraud-detection model** — the flagged-fraud rate is a **guardrail input**, not modelled.
- Full customer-LTV / unit-economics modelling — activation is the outcome; downstream
  revenue is not modelled.
- Real-time / streaming data; everything is batch.
- App clickstream / screen-level telemetry beyond the onboarding-step events.
- Marketing-attribution modelling beyond a **first-touch channel** label.
- Real personal data — every user, account, transaction, KYC decision and fraud signal is
  synthetic and seed-generated.
- The **true treatment effect** and the **exact bug magnitudes** — set in Phase 3,
  detected blind in Phase 10.

---

## 10. Resolved-assumptions log

| # | Assumption | Resolution |
|---|---|---|
| A1 | Product | Free digital checking account + card. No credit/lending in frame. |
| A2 | Window & anchor | 21 months, 2025-01-01 → 2026-09-30; data-gen ("today") = 2026-09-10, so the last ~3 weeks are near-future relative to the build and exist only to close the re-run's Day-7 windows. |
| A3 | Primary metric | Day-7 Activation = account created **and** ≥1 transaction within 7 days of assignment. |
| A4 | "Active user" | ≥1 transaction in the trailing 30 days (platform-health metric, not the experiment metric). |
| A5 | Unit / split | User-level, 50/50, feature-flag hash assignment; assignment ≈ signup start. |
| A6 | Original experiment window | 6 weeks, 2026-07-06 → 2026-08-16; terminated early on the SRM alert. |
| A7 | The break | Mobile deploy 2026-07-16 (day 11) resets the variant cache for a user subset; hotfix 2026-07-22. |
| A8 | Two bug effects | (1) contamination of already-assigned users via arm switch; (2) region/timezone-correlated fallback bias for post-deploy signups. Baked in Phase 3, separated in Phase 10. |
| A9 | SRM monitoring | Continuous daily chi-square (cumulative + trailing-7d); alert at p < 0.001 confirmed 2 consecutive days; documented as a runbook in Phase 1. |
| A10 | Decision | Restart, not truncate or exclude-contaminated. Rationale + trade-off table in the deep dive. |
| A11 | Re-run window | 4 weeks, 2026-08-24 → 2026-09-20; ~9,000 users; **power/MDE recomputed** — original 6-week MDE not reused. |
| A12 | Guardrails | KYC rejection rate + flagged-fraud rate = non-negotiable; onboarding support tickets / 1k signups = secondary. |
| A13 | Heterogeneity | By acquisition channel, with a formal arm×channel interaction test. |
| A14 | Planning values | Control Day-7 ≈ 48%; target lift ≈ +3 pp; α = 0.05, power = 80%. Finalized in Phase 1; true effect set in Phase 3. |
| A15 | Currency | BRL only; no FX. |
| A16 | True effect & bug magnitudes | **Not** decided here — set in ETL (Phase 3), detected blind in Phase 10. |

---

## 11. Folder scaffold (created)

```
LumaBank-Activation-Experiment/
  docs/            00 scope · 01 business context & KPIs (+ SRM runbook) · 02 architecture ·
                   03 data dict · 04 ETL · 05 model · 06 DAX · 07 visual identity ·
                   09 report structure (DQ lives in data/quality/dq_report.md, not a
                   separate doc) · walkthrough.md · PDF bundle
  etl/             config (one SEED, true effect + bug magnitudes) · 01 generate raw ·
                   02 clean/stage · 03 build curated · dq_checks (incl. SRM check) ·
                   doc + DAX generators · run_pipeline · vocab/
  data/
    raw/           source-faithful messy exports        (git-ignored, regenerated)
    staging/       typed stg_* tables                   (git-ignored, regenerated)
    curated/       Kimball star, CSV + Parquet          (git-ignored, regenerated)
    quality/       dq_report.md
  powerbi/         semantic model as code (TMDL) · PBIR report · theme · build script
  assets/          brand.py · logo / page-background generators
  data_analysis/   sql/ python/ findings/ parity/ deliverables/ outputs/   ← PRIMARY
                   (5-block investigation narrative: setup → SRM monitoring → root cause →
                    decision analysis → re-run readout)
  portfolio/       5 gallery images only
  README.md
```

---

*End of Phase 0 deliverable. Next gate: **Phase 1** — `docs/01_business_context_kpis.md`
(business context, KPI definitions, stakeholder personas, and the SRM monitoring runbook
as a documented operational process). Review before Phase 2.*
