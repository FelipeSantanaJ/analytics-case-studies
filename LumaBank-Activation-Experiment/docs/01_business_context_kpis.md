# LumaBank — Business Context & KPI Framework

**Document status:** Phase 1 deliverable · authored at project kickoff, before any analysis.
**Data generation date:** 2026-09-10 · **Platform-history window:** 2025-01-01 → 2026-09-30 (21 months — LumaBank's life to date).
**Embedded experiment:** onboarding redesign A/B test — original 2026-07-06 → 2026-08-16 (terminated on day 11), clean re-run 2026-08-24 → 2026-09-20.
**Audience:** LumaBank's Growth, Product, and Risk & Compliance leadership.

> This document frames the problem and defines the metrics. It deliberately does **not**
> state whether the new onboarding worked, or by how much — that is the job of the read-out
> (Phase 10). Everything here was knowable *before* the analysis. The true underlying
> treatment effect, and the exact magnitudes of the production bug that broke the first
> run, are decided during ETL (Phase 3), baked into the synthetic data with plausible
> noise and channel heterogeneity, and kept only in `etl/config.py`; Phase 10 must detect
> and quantify them **as if blind**.
>
> **PT — resumo.** A LumaBank é um neobank brasileiro fictício (conta digital + cartão),
> lançado em jan/2025; a janela de 21 meses é a vida inteira da plataforma. O problema:
> muita gente se cadastra e **nunca transaciona** — o fluxo de onboarding/KYC (upload de
> documento *antes* de a conta existir) derruba os usuários. Growth/Produto redesenhou o
> fluxo (menos etapas, documento adiado para *depois* da criação da conta) e rodou um
> **A/B test randomizado por usuário, 50/50**, com métrica primária **Day-7 Activation**
> (conta criada **e** primeira transação até o 7º dia). Este documento define contexto,
> KPIs, personas e o **runbook de monitoramento de SRM** — o processo operacional diário
> que, no dia 11 do experimento, detectou a quebra.

---

## 1. The situation

**LumaBank** is a Brazilian neobank. A user downloads the app, opens a free digital
checking account and gets a Mastercard — in principle in minutes, entirely in-app. The
top of the funnel is healthy: paid social, referral, app-store search and influencer
campaigns all deliver signups at acceptable cost. The problem is what happens next.

**A large share of new users never transact.** They install the app, begin sign-up, reach
the **KYC step** — a full identity-document upload (RG or CNH, plus a selfie/liveness
check) that today happens *before* the account is created — and drop. Of those who do get
through, many take more than a week to make a first payment or transfer, by which point
the initial intent that brought them in has cooled and a competitor's card is already in
their wallet.

The Growth and Product teams' hypothesis: **the document-upload wall is in the wrong
place.** A user who has to photograph two documents and pass a liveness check *before they
have anything* is being asked to pay a cost before receiving any value. Move the account
creation ahead of the document upload — open the account in a **limited state** (low
transaction and balance caps, no physical card) and request the documents *before those
limits are lifted* — and more users will reach a first transaction, faster.

In LumaBank's 19th month of operation the teams ran this as a **randomized, user-level
A/B test**. The rest of this project is what happened to that test: it **broke in
production on day 11**, was caught by the standing SRM monitor (§9), diagnosed, and
re-run clean in a shorter window (§10–11).

---

## 2. Company profile

| | |
|---|---|
| Name | **LumaBank** (legal entity *LumaBank Instituição de Pagamento S.A.*) |
| Type | Neobank / *instituição de pagamento* — digital checking account (*conta de pagamento*) + Mastercard debit; no credit product in scope |
| Headquarters | São Paulo, SP, Brazil |
| Launched | **January 2025** (public launch). This project's 21-month window is the platform's whole life to date. |
| Market / currency | **Brazil only, BRL only.** No FX, no cross-border — that ground is covered by the VoltEdge project. |
| Reporting calendar | Calendar months; growth reporting weekly; experiment reporting daily |
| Scale at window end | ~**130,000** cumulative signups · ~**60,000** active users (≥1 transaction in the trailing 30 days) · end-of-window signup run-rate ~**2,200–2,600 / week** |
| Regulatory frame | Bacen *instituição de pagamento* rules; KYC/AML obligations (identity verification, sanctions/PEP screening, transaction monitoring). KYC and fraud controls are a **hard constraint**, not a dial to trade away for growth — this is why they are non-negotiable guardrails (§8.3). |

---

## 3. The product and the two onboarding flows

### 3.1 What a user gets

A free digital checking account, a virtual Mastercard immediately and a physical card on
request, Pix (instant payments), boletos, transfers, and a simple in-app statement. Revenue
(out of scope to model) is interchange on card spend, float, and Pix-for-business fees. The
**activation** the business cares about is the user's **first transaction** — Pix, card
purchase, boleto payment or transfer — because a user who transacts once is an order of
magnitude more likely to still be here in 90 days.

### 3.2 Control flow ("old" — document upload before the account)

```
open app → phone + CPF + email → basic personal data → **upload RG/CNH + selfie/liveness**
→ KYC decision (approve / manual review / reject) → account created → first transaction
```

The KYC document step sits **before** the account exists. A rejected or stuck KYC means the
user never had an account at all.

### 3.3 Treatment flow ("new" — account first, documents deferred)

```
open app → phone + CPF + email → basic personal data → **account created (LIMITED state)**
→ first transaction possible within limits → prompt to upload RG/CNH + selfie
→ KYC decision → limits lifted / physical card enabled
```

Fewer steps to a usable account; the document upload is deferred and gates only **limit
increases and the physical card**, not the account itself. Limited-state caps (indicative,
finalized in Phase 3): balance ≤ R$ 1,000, Pix ≤ R$ 500/day, no boleto issuance, no
physical card.

### 3.4 Why this is a genuinely two-sided bet

Moving the KYC wall later is expected to lift activation — but it also means **unverified
users can transact**, briefly and within caps, before the platform has confirmed who they
are. That is exactly the population where **KYC rejection** and **first-party / synthetic
fraud** concentrate. The experiment therefore cannot be read on the primary metric alone;
the risk guardrails (§8.3) decide as much as the activation lift does.

---

## 4. The activation funnel and its definitions

| Stage | Definition |
|---|---|
| **Signup started** | User submits phone + CPF and enters the onboarding flow. This is the **randomization point** — feature-flag exposure is logged here with a timestamp and the serving app version. |
| **KYC submitted** | Identity documents + liveness uploaded (in control, before account creation; in treatment, after). |
| **KYC decision** | `approved` · `manual_review` (routed to an analyst queue, later resolved to approved/rejected) · `rejected` (with a reason code). |
| **Account created** | A usable account exists (in control, only after KYC approval; in treatment, at the limited-state step). |
| **First transaction** | First Pix, card purchase, boleto payment or transfer of any amount. The activation event. |
| **Day-7 Activation** *(primary metric)* | Account created **and** ≥1 transaction **within 7 calendar days of the randomization timestamp**. A user assigned on 2026-07-06 12:40 has until 2026-07-13 12:40. |
| **Day-1 / Day-30 Activation** | Same construct at 1-day and 30-day horizons (context metrics). |
| **Time-to-first-transaction (TTFT)** | Hours from randomization to first transaction, for activated users. Reported as median and p90. |
| **Active user** | ≥1 transaction in the trailing 30 days. Platform-health metric — **not** the experiment metric. |

**Indicative control-flow funnel, per 100 signups started** (planning values; the real
numbers come from the pre-period in Phase 10):

| Signup started | KYC submitted | KYC approved | Account created | Day-7 Activation | Day-30 Activation |
|---:|---:|---:|---:|---:|---:|
| 100 | ~82 | ~74 | ~74 | **~48** | ~58 |

The ~18-point fall from "signup started" to "KYC submitted" — the document-upload wall — is
the drop the redesign is aimed at.

---

## 5. Acquisition channels

Randomization is independent of channel, but channel is the pre-registered **heterogeneity
dimension** (§8.6): the redesign may help low-intent, top-of-funnel traffic (which bounces
hardest at the document wall) more than warm, high-intent traffic — or the reverse. This is
a prior to **test**, not to assume.

| Channel | ~Share of signups | Indicative control Day-7 Activation | Character |
|---|---:|---:|---|
| **Paid social** (Meta, TikTok) | ~38% | ~42% | Highest volume, lowest intent, most price/creative-driven |
| **Organic / direct** | ~22% | ~54% | Searched for LumaBank by name; warm |
| **App-store search** (ASO) | ~18% | ~50% | Category intent ("conta digital"), medium-warm |
| **Referral** (member-get-member) | ~15% | ~58% | Invited by an existing user; warmest, but capped volume |
| **Influencer / affiliate** | ~7% | ~40% | Spiky with campaigns; intent varies wildly by creator |

`dim_acquisition_channel` also carries campaign and a first-touch timestamp; only the
**first-touch channel** is modelled (no multi-touch attribution — out of scope, §16).

---

## 6. KYC, risk and fraud (guardrail context)

The controls that the experiment must not damage:

| Control | Definition | Indicative baseline (control flow) |
|---|---|---|
| **KYC rejection rate** | Share of KYC submissions with a final decision of `rejected` (document invalid/illegible, identity mismatch, sanctions/PEP hit, suspected forgery). | ~**9%** of submissions |
| **KYC manual-review rate** | Share routed to an analyst queue before resolution — an operational-cost signal. | ~**4%** of submissions |
| **Flagged-fraud rate** | Share of activated accounts with a confirmed fraud signal (first-party default intent, synthetic identity, account-takeover, mule activity) **within the first 30 days**. | ~**1.2%** of activated accounts |
| **Chargeback / dispute rate** | Card disputes per 1,000 card transactions in the first 30 days. | context only |

Fraud signals come from the risk system (rules + model score + confirmed-loss backfill) and
are timestamped in **UTC** while every other system is `America/Sao_Paulo` — a deliberate
data-quality issue (§ architecture doc). The risk system is a **source of a guardrail
metric**; this project does not build or tune a fraud model (§16).

---

## 7. The analytics window — why 21 months

| Anchor | Value |
|---|---|
| Window length | 21 complete months: **month 1 = Jan 2025**, month 21 = Sep 2026 |
| Pre-experiment baseline | months 1–17 (Jan 2025 – May 2026) — the activation trend before any test |
| Original experiment | month 19 → **2026-07-06 → 2026-08-16** (6 weeks planned; stopped day 11) |
| Clean re-run | months 20–21 → **2026-08-24 → 2026-09-20** (4 weeks) |
| Outcome tail | to **2026-09-30** — needed to close the Day-7 window for re-run users assigned as late as 2026-09-20 (outcomes through 2026-09-27) |

**Why 21 months.** It is LumaBank's entire operating history — there is no earlier
comparable data. The window also gives a long, clean pre-period so the experiment's control
arm can be sense-checked against the platform's established activation rate.

**Near-future caveat.** The build ("today") is **2026-09-10**; the last ~3 weeks of the
window are dated after it and exist only to let the re-run's Day-7 outcomes complete. No
analysis treats them as observed history.

---

## 8. The onboarding experiment

### 8.1 Design (as pre-registered, before the break)

| Element | Decision |
|---|---|
| **Unit of randomization** | **User**, at signup start. The feature-flag service hashes a stable pre-account user id → arm; the assignment and the serving app version are logged. |
| **Split** | **50/50**, treatment (new flow, §3.3) vs control (old flow, §3.2). |
| **Eligible population** | Every new signup entering onboarding during the window, on a supported app version (≥ the version that ships the new flow behind the flag). Existing users are never re-onboarded and are out of frame. |
| **Assignment integrity** | Set once at signup start; no re-randomization; no mid-flight flow changes for either arm. *(This is precisely the invariant the production bug violates.)* |
| **Window** | 6 weeks: **2026-07-06 → 2026-08-16**. Chosen partly because July is a lower-volume winter-holiday stretch and 6 weeks were needed to accrue the target sample. |
| **Expected sample** | ~**13,500** users (~2,250/week) → ~**6,750 per arm**. |

### 8.2 Hypotheses

- **Business hypothesis.** Creating the account *before* the document upload, and deferring
  KYC to a limits-gate, raises the share of new users who complete a first transaction
  within 7 days — **without** worsening KYC rejection or fraud, and without a material rise
  in onboarding support load.
- **Statistical hypothesis (primary).** H₀: Day-7 Activation is equal in the two arms.
  H₁: treatment > control. Tested one-sided at α = 0.05; a two-sided 95% CI on the
  difference is always reported.

### 8.3 Metrics

| Role | Metric | Definition | Decision rule |
|---|---|---|---|
| **Primary** | **Day-7 Activation rate** | §4. Share of assigned users with account created **and** ≥1 transaction within 7 days of assignment. | Ship if the lift is **positive, significant (α = 0.05) and ≥ the MDE**. |
| **Guardrail — non-negotiable** | **KYC rejection rate** | Rejected ÷ KYC submissions, by arm. | **Non-inferiority:** treatment must not exceed control by more than **1.5 pp** (95% one-sided). A breach fails the experiment regardless of the activation lift. |
| **Guardrail — non-negotiable** | **Flagged-fraud rate (first 30 days)** | Confirmed fraud signals ÷ activated accounts, by arm. Uses only the fraud window observable within the data. | **Non-inferiority:** treatment must not exceed control by more than **0.5 pp** (95% one-sided). A breach fails the experiment. |
| Guardrail — secondary | **Onboarding support tickets per 1,000 signups** | Onboarding-category tickets ÷ signups × 1,000, by arm. | Directional; flag if treatment is materially worse (operational cost). |
| Health / context | **TTFT (median, p90)**, Day-1 & Day-30 Activation, limited-state-never-verified share (treatment only) | §4. | Context for whether a Day-7 lift is durable and verified, not just deferred paperwork. |

### 8.4 Power & minimum detectable effect — the 6-week design

| Assumption | Value |
|---|---|
| Control Day-7 Activation (planning value) | **48%** |
| Target effect (MDE), absolute | **+3 pp** (48% → 51%) |
| α (two-sided) / power | 0.05 / 0.80 |
| Required n per arm at the MDE (two-proportion) | **≈ 4,450** |
| Expected n per arm | **≈ 6,750** → power ≈ **0.93** at +3 pp; ~0.80 power for an effect as small as **+2.4 pp** |
| Per-channel cells (per arm, expected) | paid social ~2,570 · organic ~1,485 · ASO ~1,215 · referral ~1,010 · influencer ~475 → well powered for paid social/organic, directional for referral/influencer |

The power calculation is re-run from realized pre-period rates and reproduced in code in
Phase 10; these are the planning basis. **These numbers do not carry over to the re-run**
— §11 recomputes them for the shorter window and smaller sample.

### 8.5 Threats to validity the read-out must address

| Threat | How it is handled |
|---|---|
| **Sample-ratio mismatch (SRM)** | **Continuously monitored**, not checked once — see the runbook, §9. χ² goodness-of-fit on arm counts, daily, overall and by segment. *This is the monitor that caught the break.* |
| **Assignment integrity failure** | The variant **snapshot** table is reconciled against the assignment **event log** every day; disagreements (arm switches) are surfaced as a data-quality failure, not silently resolved. |
| **Covariate imbalance** | Standardized mean differences on channel, region, app version, OS, signup hour, device age; Love plot. Especially important **after** the break, where the fallback biases composition. |
| **Novelty effect** | Daily treatment Day-7 Activation across the window; test for a decaying trend; report the settled lift. |
| **Seasonality** | Concurrent control arm differences out calendar effects; both arms' daily series still reported. |
| **Interference between arms** | Referral links can put an inviter and invitee in different arms; assumed second-order, stated as a bounded limitation. |
| **Multiple comparisons** | One primary metric fixed in advance; the two hard guardrails are one-sided NI tests; the channel heterogeneity cut is secondary and CI-reported with a family-wise-error note. |
| **Peeking** | The **integrity** monitor runs daily by design; the **effect** analysis is a single fixed read at window close. Daily SRM looks never estimate the treatment effect. |

### 8.6 Heterogeneity analysis (required)

Effect on Day-7 Activation estimated **within each acquisition channel**, with per-channel
CIs and a formal **arm × channel interaction test** (likelihood-ratio). The business
decision — full rollout vs rollout scoped to specific channels — depends on this cut.

---

## 9. Runbook — continuous SRM & assignment-integrity monitoring

> This is a **standing operational process**, documented here because it is part of how
> LumaBank runs *every* experiment — not a one-off analysis step. It is what detected the
> break on 2026-07-17. It is owned by the Experimentation Platform team; the on-call
> rotation carries the pager.

### 9.1 Purpose

Detect, within one day, any failure of the randomization to deliver the intended
allocation (SRM) or the intended **stable** per-user assignment (integrity), for the full
life of a running experiment.

### 9.2 Cadence & inputs

- Runs **daily at 07:00 BRT** as a batch job, for every experiment in `running` state.
- Reads: the prior day's `variant_assignments` events, the cumulative assignment log, the
  `variant_snapshot` current-state table, `app_releases`, and a backend deploy/flag-config
  changelog.

### 9.3 Tests

| # | Test | Grain |
|---|---|---|
| T1 | Pearson **χ² goodness-of-fit** vs expected 50/50 | cumulative assignments to date |
| T2 | Pearson χ² vs 50/50 | trailing-7-day assignments |
| T3 | χ² vs 50/50, broken down | by `assignment_source` (normal / fallback), region, timezone, app version, OS |
| T4 | Snapshot-vs-log reconciliation: count users whose current snapshot arm ≠ their first logged assignment arm | per user, aggregated |
| T5 | First-assignment vs effective-assignment drift: count users with ≥2 assignment events | per user, aggregated |

### 9.4 Alert logic

- **WARN** — T1 or T2 p **< 0.01** on a single day, or T4/T5 count above a small fixed
  threshold. Logged, digested to the experiment owner; no pause.
- **ALERT** — T1 p **< 0.001**, or T2 p **< 0.001 on two consecutive days**, or T4/T5
  rising day-over-day. Thresholds are deliberately tighter than 0.05 because the test runs
  every day for weeks (a naïve 0.05 would false-alarm on most experiments).

### 9.5 On ALERT

1. **Auto-pause new enrollment** into the experiment (existing assignments keep serving).
2. **Page** the experiment owner and the Experimentation Platform on-call.
3. **Freeze** an analysis snapshot as of the last day that passed all tests ("last clean
   day").
4. Open an incident doc; begin triage (§9.6).

### 9.6 Triage checklist (in order)

1. **Release diff.** Any app release, backend deploy, or flag-config change in the 48 h
   before drift onset? Cross-reference `app_releases` and the deploy changelog. *(In this
   incident: the 2026-07-16 mobile release.)*
2. **Source split.** Break SRM by `assignment_source`. Is `fallback` non-zero or rising?
   When did the first fallback assignment appear?
3. **Segment split.** Is the imbalance concentrated by region / timezone / app version /
   OS? A geographic concentration points to a biased fallback, not random drift.
4. **Integrity.** Quantify T4/T5 — how many users have switched arms, and were they
   assigned before or after the onset?
5. **Population partition.** Count users assigned **before** onset (candidate-clean, but
   check for cache-reset), users assigned **after** onset (candidate-biased), and the
   overlap that experienced a reset.

### 9.7 Outputs the runbook hands to the decision

Contaminated-vs-clean user counts with an auditable rule; number of usable clean days and
the sample they contain; whether the defect is **still active** or already fixed by a
hotfix; the covariate-imbalance profile of the post-onset population. These feed directly
into the three-option decision analysis (§ scope doc §4.4, and Phase 10 block 4).

---

## 10. The break (summary — full treatment in Phase 10)

On **2026-07-16** (experiment day 11) a routine mobile app release reset the on-device
variant-assignment cache for a subset of users. The 07:00 run on **2026-07-17** raised a
WARN on T2; **2026-07-18** confirmed it to an ALERT and enrollment auto-paused. Two
distinct effects, which the investigation must separate:

1. **Contamination** — users **already assigned before 2026-07-16** whose cache was reset
   (`cache_reset_flag = 1`); a fraction were re-assigned on next app open, some to the
   **opposite arm**, so they experienced a mix of both flows mid-journey.
2. **Post-deploy attribution bias** — signups **after 2026-07-16** fell into an assignment
   **fallback** (`assignment_source = 'fallback'`) whose arm is a deterministic function of
   **region / timezone**, not random. The post-deploy arms differ in **composition**, not
   only in count. The fallback share decays as the **2026-07-22 hotfix** rolls out.

The magnitudes (reset share, arm-switch fraction, fallback share and its geographic skew)
are set in Phase 3 and recovered by the analysis, not read off.

---

## 11. The re-run

| Element | Decision |
|---|---|
| Preconditions | Cache-reset handling fixed (a reset no longer triggers re-assignment); the biased fallback removed (fallback, if ever hit, now uses the same hash as the primary path). Verified in staging before restart. |
| Fresh randomization | All users re-hashed; no carry-over of arms from the aborted run; aborted-run users entering again are re-randomized and flagged. |
| **Window** | **4 weeks: 2026-08-24 → 2026-09-20.** The business could not wait another full 6 weeks; 4 weeks was the agreed cap. |
| Expected sample | ~**9,000** users (~4,500/arm) — a slightly higher late-window run-rate plus modest pent-up demand. |
| **Power / MDE — recomputed** | At ~4,500/arm, α = 0.05, power = 0.80 → **MDE ≈ 3.0 pp** (vs 2.4 pp for the 6-week design). |
| **Stated cost of the deadline** | A true effect in the **+2 to +3 pp** range — a plausible real size for this change, and detectable under the original design — will now likely come back **non-significant**. The deep dive states this explicitly rather than treating a null as "no effect". |
| Guardrails & heterogeneity | Unchanged from §8.3 / §8.6, re-powered for the smaller sample (guardrail NI tests lose power too — noted). |

---

## 12. Seasonality and patterns embedded in the data

| Pattern | Where it shows |
|---|---|
| **January** "organize my finances" surge | Signup volume peaks; paid-social CAC falls |
| **Carnaval** (Feb) | Signups and support contacts dip for ~1 week |
| **Feb–Mar** back-to-school | Secondary signup lift |
| **Black Friday / November** | Card-acquisition marketing push → signup spike; card-transaction spike |
| **December** 13th-salary | Transaction volume and first-transaction rate rise; more Day-7 activations per signup |
| **Jun–Jul** winter holidays | Lower signup volume — the original experiment sits here, which is why 6 weeks were planned |
| **Late Aug–Sep** | Volume recovers — the re-run runs into a rising-volume stretch |
| **Paid-social volume** | Tracks quarter-end marketing pushes; creative refreshes cause week-to-week swings |
| **App releases** | ~2–4 per platform per month; the 2026-07-16 release was routine and not flagged as risky at the time |
| **Weekly cycle** | Signups skew to evenings and Sun–Tue; first transactions cluster on the assignment day and the following weekend |

---

## 13. Stakeholder personas → report pages

Four personas, one standing question each — those four questions are the Phase-8 report
pages (the dashboard is the secondary deliverable, kept lean).

| # | Persona | Standing question | Page |
|---|---|---|---|
| 1 | **VP Growth / GM** | Is new-user activation healthy and trending up, and did the onboarding redesign work well enough to roll out? | **Executive Overview** |
| 2 | **Product Lead, Onboarding** | Where exactly do new users drop between signup, KYC and first transaction — and how does the new flow reshape that funnel? | **Onboarding & Activation Funnel** |
| 3 | **Experimentation / Data Science Lead** | Can the experiment be trusted — allocation over time, SRM, contamination — and once it is clean, what is the effect? | **Experiment Integrity Monitor** |
| 4 | **Head of Risk & Compliance** | Did faster activation cost anything on KYC rejection or fraud? Are the guardrails intact? | **Experiment Readout** (guardrail section) |

---

## 14. KPI framework

Benchmark ranges are **directional**, drawn from public Brazilian-fintech and neobank
commentary and payments-industry notes, adapted to a young single-country neobank. They set
targets; they are not claims about named competitors.

### 14.1 Platform health & scale

| KPI | Definition | Benchmark | Target |
|---|---|---|---|
| Cumulative signups | Distinct users who ever started onboarding | — | on plan curve |
| **Active users** | ≥1 transaction in trailing 30 days | — | ≥ 60k by window end |
| Active rate % | Active ÷ (accounts created) | 45%–65% | ≥ 55% |
| New signups / week | Signups starting in the week | — | ≥ plan |
| Account-creation rate % | Accounts created ÷ signups started | 60%–80% | ≥ 75% |
| MAU / signup cohort retention | Share of a weekly signup cohort active at week n | M1 ≥ 55% | context |

### 14.2 Acquisition

| KPI | Definition | Benchmark | Target |
|---|---|---|---|
| Signups by channel | Count by first-touch channel | — | mix on plan |
| Channel mix % | Channel share of signups | ~38/22/18/15/7 | context |
| Day-7 Activation by channel | Primary metric split by channel | 40%–58% | context / heterogeneity input |
| Blended Day-7 Activation | All channels, all signups | 45%–52% | ≥ 50% |

### 14.3 Onboarding funnel

| KPI | Definition | Benchmark | Target |
|---|---|---|---|
| Step conversion | Share advancing signup → KYC submit → KYC decision → account → first txn | — | raise the KYC-submit step |
| **KYC-submit rate %** | KYC submitted ÷ signups started | 70%–88% | ≥ 85% (the redesign's job) |
| Account-creation rate % | §14.1 | 60%–80% | ≥ 75% |
| Median time in onboarding | Signup start → account created (minutes) | 4–15 | ≤ 8 |
| Limited-state-never-verified % *(treatment only)* | Accounts still limited (no KYC) 14 days after creation | — | ≤ 15% |

### 14.4 Activation

| KPI | Definition | Benchmark | Target |
|---|---|---|---|
| **Day-7 Activation rate %** *(primary)* | §4 | 40%–55% | ≥ 52% |
| Day-1 / Day-30 Activation rate % | §4 | — | context |
| Median / p90 TTFT | Hours from assignment to first transaction (activated users) | median 12–48 h | ↓ |
| First-transaction type mix | Pix / card / boleto / transfer share of first transactions | Pix-led | context |
| Activation by signup week | Day-7 Activation of each weekly cohort | — | trend up |

### 14.5 KYC & risk — guardrails

| KPI | Definition | Benchmark | Target |
|---|---|---|---|
| **KYC rejection rate %** | Rejected ÷ KYC submissions | 5%–12% | ≤ 10% and **not worsened by the experiment** |
| KYC manual-review rate % | Manual-review ÷ submissions | 3%–8% | ≤ 6% |
| **Flagged-fraud rate % (30d)** | Confirmed fraud signals ÷ activated accounts, first 30 days | 0.5%–2.0% | ≤ 1.5% and **not worsened by the experiment** |
| Chargeback rate (30d) | Card disputes per 1,000 first-30-day card transactions | — | context |
| Fraud-loss BRL per activated account | Confirmed loss ÷ activated accounts | — | context |

### 14.6 Support & operating cost

| KPI | Definition | Benchmark | Target |
|---|---|---|---|
| **Onboarding tickets per 1,000 signups** | Onboarding-category tickets ÷ signups × 1,000 | 60–120 | ≤ 85 |
| Onboarding contact rate % | Signups with ≥1 onboarding ticket | 4%–12% | ≤ 8% |
| KYC-appeal rate % | Rejected users who contest the decision | — | context |

### 14.7 Experiment scorecard (Integrity Monitor + Readout pages)

| KPI | Definition |
|---|---|
| Day-7 Activation by arm (+ lift, 95% CI, p) | Primary metric, §8.3 |
| Daily Day-7 Activation by arm | Novelty-effect diagnostic |
| Daily allocation by arm + **cumulative SRM χ² p-value** | Integrity monitor, §9 — the break story |
| SRM χ² by `assignment_source` / region / app version | Root-cause diagnostic |
| Snapshot-vs-log arm-switch count over time | Contamination diagnostic |
| Contaminated vs clean user counts | Auditable-rule output, §9.7 |
| KYC rejection rate by arm (+ non-inferiority test) | Non-negotiable guardrail |
| Flagged-fraud rate by arm (+ non-inferiority test) | Non-negotiable guardrail |
| Onboarding tickets / 1k by arm | Secondary guardrail |
| Day-7 Activation effect by channel (+ arm × channel interaction test) | Heterogeneity, §8.6 |
| Re-run power / MDE vs original | §11 — the cost of the deadline |

---

## 15. Targets and plan

- The plan is built on the **same basis as the actuals** (same activation definition, same
  KYC-rejection and fraud-window definitions).
- **Plan Day-7 Activation:** rising to **≥ 52%** by window end (the redesign is the lever
  meant to get it there).
- **Plan active users:** ramp to **60k** by month 21.
- **Plan KYC-submit rate:** **≥ 85%**.
- **Plan KYC rejection rate:** hold **≤ 10%** — a ceiling, not a target to optimise down at
  the cost of legitimate approvals.
- **Plan flagged-fraud rate:** hold **≤ 1.5%**.
- **Plan onboarding tickets:** **≤ 85 / 1,000 signups**.
- "vs Target %" measures exist per KPI; **KYC rejection rate, flagged-fraud rate, manual-
  review rate, tickets per 1,000 and TTFT are scored lower-is-better**.

---

## 16. Out of scope (explicit)

- A second country, region expansion, multi-currency / FX (covered by VoltEdge).
- Credit / lending — underwriting, limits as a credit decision, interest income. The
  account here is a checking account + debit card; "limits" are a KYC gate, not credit.
- A **fraud-detection model** — the flagged-fraud rate is a guardrail **input**, produced
  by the existing risk system; this project does not build or tune it.
- Customer-LTV, contribution-margin or unit-economics modelling — activation is the outcome;
  downstream revenue (interchange, float) is not modelled.
- Marketing-attribution modelling beyond a **first-touch channel** label; no CAC/ROAS.
- App clickstream / screen-level telemetry beyond the defined onboarding-step events.
- Real-time / streaming data; everything is daily batch.
- Real personal data — every user, account, transaction, KYC decision and fraud signal is
  synthetic and seed-generated.
- The **true treatment effect** and the **exact production-bug magnitudes** — set in
  Phase 3, detected blind in Phase 10.

---

## 17. Resolved-assumptions log

| # | Decision | Resolution |
|---|---|---|
| A1 | Window length & anchor | 21 months, Jan 2025 – Sep 2026; data-gen date 2026-09-10; = LumaBank's life to date. |
| A2 | Near-future tail | The last ~3 weeks (after 2026-09-10) exist only to close the re-run's Day-7 windows; not treated as observed history. |
| A3 | Product | Free digital checking account + Mastercard debit. No credit/lending in frame. |
| A4 | Primary metric | Day-7 Activation = account created **and** ≥1 transaction within 7 days of the randomization timestamp. |
| A5 | Randomization point | Signup start (feature-flag exposure), logged with timestamp + app version. |
| A6 | "Active user" | ≥1 transaction in the trailing 30 days (platform-health metric, not the experiment metric). |
| A7 | Control vs treatment flow | Control = document upload before account creation; treatment = account created in limited state, KYC deferred to a limits gate. |
| A8 | Unit / split | User-level, 50/50, feature-flag hash. |
| A9 | Original experiment window | 6 weeks, 2026-07-06 → 2026-08-16; terminated on day 11 by the SRM ALERT. |
| A10 | Expected sample (original) | ~13,500 users, ~6,750/arm. |
| A11 | Guardrails | KYC rejection rate (NI, +1.5 pp bound) and flagged-fraud rate (NI, +0.5 pp bound) = non-negotiable; onboarding tickets / 1k = secondary. |
| A12 | Power / MDE (original) | Control Day-7 ≈ 48%; MDE +3 pp; α 0.05, power 0.80; ~4,450/arm required, ~6,750 expected. |
| A13 | Heterogeneity | By acquisition channel, with a formal arm × channel interaction test. |
| A14 | SRM monitoring | Continuous daily χ² (cumulative + trailing-7d + segment splits) with WARN at p<0.01, ALERT at p<0.001; runbook in §9. |
| A15 | The break | Mobile release 2026-07-16 resets the variant cache; two effects (contamination + region/timezone-biased fallback); hotfix 2026-07-22. |
| A16 | The decision | Restart, not truncate or exclude-contaminated (trade-off table in scope §4.4 / Phase 10 block 4). |
| A17 | Re-run window & power | 4 weeks, 2026-08-24 → 2026-09-20; ~9,000 users; **power/MDE recomputed** → MDE ≈ 3.0 pp; deadline cost stated. |
| A18 | Currency | BRL only; no FX in scope. |
| A19 | True effect & bug magnitudes | **Not** decided here — set in ETL (Phase 3), detected blind in Phase 10. |

---

*End of Phase 1 deliverable. Next gate: **Phase 2** — `docs/02_data_architecture.md`
(medallion pipeline, the 6 simulated source systems, the curated star schema, and the
data-quality + bug-specific injection catalog).*
