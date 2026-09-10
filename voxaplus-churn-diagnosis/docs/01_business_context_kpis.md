# Voxa+ — Business Context & KPI Framework

**Document status:** Phase 1 deliverable · authored at project kickoff, before any analysis.
**Data generation date:** 2026-09-02 · **Analytics window:** 2023-09-01 → 2026-08-31 (36 full months).
**Audience:** the Voxa+ leadership team and the board.

> This document frames the problem and defines the metrics. It deliberately does **not**
> contain a conclusion about what caused the churn increase — that is the job of the
> investigation (Phase 10). Everything here was knowable *before* the diagnosis began.

---

## 1. The situation

Voxa+ is a subscription video-on-demand (SVOD) streaming service. For most of its history,
monthly subscriber churn has run in a stable band. **Starting in month 34 of this window
(June 2026), gross monthly churn nearly doubled and it has stayed elevated for the three
months since.** Net subscriber additions have turned negative in the home market for the
first time outside of a seasonal content gap.

Leadership has not been able to agree on a cause. Several things changed in the same broad
period — pricing, the app, the content slate, the acquisition mix, the international
footprint — and each function has a different theory. The board meets in five weeks and
wants a single, evidence-backed diagnosis rather than seven competing narratives.

This project builds the data foundation and the analysis to deliver that diagnosis.

---

## 2. Company profile

| | |
|---|---|
| Name | **Voxa+** (stylised "Voxa+"; legal entity *Voxa Mídia S.A.*) |
| Headquarters | São Paulo, Brazil |
| Business | Direct-to-consumer SVOD streaming — films, series, and a growing slate of originals |
| Age | Operating in Brazil for ~6 years; the last 3 years (this window) cover the international expansion |
| Employees | ~640 (not modelled below the level of allocated G&A) |
| Fiscal calendar | Calendar year; reporting is monthly |
| Scale at window end | ~70k paid active subscribers, ~120k cumulative sign-ups across the window, ~US$0.5M MRR (~US$6M ARR) |
| Devices | Mobile (iOS/Android), web, and connected-TV apps (Smart TV, streaming sticks, consoles) |

### Positioning
Voxa+ is a **mid-priced general-entertainment** service — cheaper than the global majors,
with a catalogue weighted toward Brazilian and Latin American content plus licensed
international titles. Its edge is local originals and locally relevant pricing and payment
methods (PIX and boleto in Brazil, OXXO and card in Mexico, card in the US).

---

## 3. The analytics window — why 36 months, and CY vs PY

| Anchor | Value |
|---|---|
| Window length | 36 complete months: **month 1 = Sep 2023**, month 36 = Aug 2026 |
| Current Year (CY) | months 25–36 → **Sep 2025 – Aug 2026** |
| Prior Year (PY) | months 13–24 → **Sep 2024 – Aug 2025** |
| Pre-shift baseline | months 1–33 (Sep 2023 – May 2026) |
| Churn shift | **begins month 34 (Jun 2026)**; elevated in months 34, 35, 36 |

**Why 36 months.** It is the shortest window that contains the *entire* international
expansion (both new markets launched inside it), gives a full CY-vs-PY comparison for the
home market, and still leaves a long stable baseline before the shift so "normal" is well
characterised. A shorter window would make the pre-shift band look like noise; a longer one
would drag in a platform migration that predates the current data pipeline.

**Comparability caveat.** Because two markets launched mid-window, raw company-wide YoY
mixes organic movement with expansion. Every time-series metric is therefore reported three
ways: **Total**, **Comparable Base**, and **Expansion** (see §7).

---

## 4. Market & expansion timeline

| Market | Currency | Enters window | Window-month | Notes |
|---|---|---|---|---|
| **Brazil** | BRL (R$) | present from month 1 | 1 (Sep 2023) | Home market. The only market present for the full window → the Comparable Base. |
| **Mexico** | MXN (MX$) | **Jun 2024** | 10 | Spanish-language localisation, OXXO cash payment, telco bundle partner from launch. |
| **United States** | USD (US$) | **Dec 2024** | 16 | English UI, card-only, positioned against incumbents on price; smallest base, highest ARPU. |

Launch dates are modelled explicitly. Like-for-like analysis uses Brazil (full history) as
the Comparable Base; Mexico gains its own 12-month YoY from month 22 (Jun 2025), the US from
month 28 (Dec 2025).

---

## 5. Product catalogue, pricing, and the margin structure

### 5.1 Plan line-up (per market, monthly billing)

| Tier | Description | Brazil (R$) | Mexico (MX$) | US (US$) |
|---|---|---|---|---|
| **Voxa Básico** | Ad-supported, 1080p, 1 stream, no downloads | 18.90 | 89 | 6.99 |
| **Voxa Standard** | Ad-free, 1080p, 2 streams, downloads | 29.90 | 139 | 12.99 |
| **Voxa Premium** | Ad-free, 4K HDR, 4 streams, downloads | 44.90 | 219 | 17.99 |

- **Annual plans** are offered at all tiers for the price of 10 months (~17% discount),
  billed once and recognised monthly.
- A **7-day free trial** is available on Standard and Premium via direct sign-up (not via
  most partner/bundle channels).
- Prices shown are the line-up **as of window end**. The list price has not been static for
  the full 36 months — see §8 (events).

### 5.2 Revenue streams

| Stream | ~Share of revenue | Mechanics |
|---|---|---|
| **Subscription** | ~86% | Recurring plan fees, reporting-currency converted; annual plans amortised straight-line over 12 months. |
| **Advertising** | ~10% | CPM-based, served against Básico-tier viewing. Revenue ≈ ad impressions × fill rate × eCPM. Seasonal (upfront-style H2 strength). |
| **Partner / bundle** | ~4% | Revenue-share and wholesale arrangements with telcos (carrier billing in BR/MX) and one retail bundle. Lower net price, near-zero acquisition cost. |

### 5.3 Cost structure

| Cost | Nature | Driver |
|---|---|---|
| **Content — amortisation** | Largest cost | Licensed titles amortised over licence term; originals over an accelerated useful-life curve. This is a CFO deep-dive thread (§9). |
| **Content — cash spend** | Cash, lumpy | Minimum guarantees and production milestones; diverges from amortisation month to month. |
| **Streaming delivery (CDN)** | Variable | ~per GB delivered; scales with viewing hours and bitrate (4K costs more per hour). |
| **Payment processing** | Variable | % + fixed fee per attempt, **varies sharply by method** (card vs PIX vs boleto vs OXXO vs carrier billing). Also drives involuntary churn via failed renewals — CFO thread (§9). |
| **Customer acquisition (marketing)** | Semi-variable | Performance media + brand + partner bounties. Basis for CAC. |
| **Customer support** | Variable | Cost per contact; contact rate per 1,000 subs. |
| **Cloud, platform & G&A** | Largely fixed | Allocated flat per subscriber for margin views. |

### 5.4 The core tension

For a subscription business the revenue-vs-profit tension is **growth vs. retention economics**:

- Cheaper tiers (Básico) and partner/bundle channels **add subscribers fast and cheap** but
  carry lower ARPU, lower engagement, and historically weaker retention.
- Premium tier and direct sign-ups **retain and monetise better** but cost more to acquire
  and are a smaller share of net adds.
- Content spend lifts engagement and retention, but with a lag, and it is the line most
  visible to the board when margin is under pressure.

A churn increase is therefore never "just a retention problem" — it moves LTV, which moves
the allowable CAC, which moves the growth plan. The investigation has to quantify the
**profit and LTV impact**, not only the rate.

---

## 6. Business model — financial definitions and the North Star

### 6.1 Subscriber & churn definitions (the spine of this project)

| Term | Definition |
|---|---|
| **Paid active subscriber** | An account with an in-force paid subscription on the measurement date (trials excluded until they convert). |
| **New paid subscriber** | First paid billing in the period (trial conversion or direct paid start). |
| **Reactivation** | A previously-churned account starting a new paid subscription. |
| **Gross subscriber churn (logo churn)** | Paid subscriptions that ended in the month ÷ paid subscriptions active at the start of the month. **Primary watch metric.** Includes voluntary + involuntary. |
| **Voluntary churn** | Member-initiated cancellation (immediate or at period end). |
| **Involuntary churn** | Subscription ended because billing failed and the dunning sequence was exhausted. |
| **Net subscriber adds** | New + reactivations − gross churn. |
| **Net MRR retention (NRR)** | MRR from a starting cohort 12 months later (incl. upgrades, downgrades, churn, win-back) ÷ starting MRR. Secondary. |
| **Cohort** | All accounts with the same first-paid month. |
| **Mn retention** | Share of a cohort still paid-active n months after first paid billing. |
| **Trial-to-paid conversion** | Trials that convert to a first paid billing ÷ trials started. |

### 6.2 Revenue & margin definitions

| Term | Definition |
|---|---|
| **MRR** | Σ (active paid subscriptions × normalised monthly plan price), reporting currency. Annual plans counted at 1/12. |
| **ARPU** | Subscription revenue ÷ average paid active subscribers in the period. |
| **Total revenue** | Subscription + advertising + partner/bundle. |
| **Gross profit** | Total revenue − content amortisation − CDN − payment processing − support. |
| **Gross margin %** | Gross profit ÷ total revenue. |
| **Contribution margin** | Gross profit − marketing (acquisition + retention/lifecycle). |
| **CM % (T12M)** | Trailing-12-month contribution margin ÷ trailing-12-month revenue. |
| **Blended CAC** | Total marketing spend ÷ new paid subscribers (incl. trial conversions, excl. reactivations). Scored **lower-is-better**. |
| **LTV** | ARPU × gross margin % × expected lifetime, where expected lifetime = 1 ÷ monthly gross churn rate. |
| **LTV : CAC** | LTV ÷ blended CAC. |
| **CAC payback (months)** | Blended CAC ÷ (ARPU × gross margin %). |

### 6.3 North Star and watch metric

- **North Star: Paid Active Subscribers (end of period).** Everything the company does is in
  service of a growing, healthy paid base.
- **Watch metric: Gross Monthly Churn %.** The North Star cannot grow if the base leaks
  faster than acquisition can refill it. This is the metric that broke in month 34.

Supporting the North Star: NRR (value retention), engagement health (leading indicator of
churn), and LTV:CAC (whether growth is economic).

---

## 7. Total vs Comparable Base vs Expansion

| Cut | Definition | Use |
|---|---|---|
| **Total** | All markets, all subscribers. | Headline scale and the board number. |
| **Comparable Base** | **Brazil only** — the one market present for the entire window. | Like-for-like trend; strips expansion in/out of company-wide rates. |
| **Expansion** | Mexico + United States. | Isolates the contribution (and drag) of the new markets. |

`Expansion = Total − Comparable Base` for additive measures. Rates (churn %, ARPU, margin)
are computed within each cut, never subtracted. Each market also carries its own
`market_active_from` date so a per-market YoY only starts once 12 months of history exist.

An account-level flag `is_comparable_base` = (market = Brazil). A second flag
`is_l4l_cohort` = (first-paid month ≤ month 24) supports 12-month cohort comparisons that
are fully inside the pre-shift baseline.

---

## 8. Events in the window (neutral history)

These are things that happened. **None is asserted here to be a cause of the churn shift** —
they are the candidate context the investigation will test, confirm, or rule out. Dates are
approximate to the month.

| ~Month | Date | Event |
|---|---|---|
| 6 | Feb 2024 | Cancellation flow redesigned (fewer steps, added a "pause subscription" option). |
| 10 | Jun 2024 | **Mexico launch** — OXXO payment, telco bundle partner live from day one. |
| 13 | Sep 2024 | Support platform migration (new ticketing tool; contact tagging taxonomy changes). |
| 16 | Dec 2024 | **US launch** — card-only, price-led positioning. |
| 18 | Feb 2025 | Ad-tier eCPM deal renegotiated upward; ad load per hour increased slightly. |
| 22 | Jun 2025 | Two long-running licensed international series expire from the Brazil catalogue. |
| 25 | Sep 2025 | Performance-marketing mix shifts toward lower-cost affiliate and paid-social inventory; a new telco bundle push begins in Brazil and Mexico. |
| 28 | Dec 2025 | Annual-plan discount deepened for a holiday promo (echoes into renewals ~12 months later). |
| 30–33 | Feb–May 2026 | **Voxa+ app "v3" rollout** — re-platformed player and navigation, shipped device-family by device-family (mobile first, connected-TV last). |
| 31 | Mar 2026 | **Brazil list-price increase** on Standard and Premium; Básico held flat. Existing members migrated on their next renewal. |
| 32 | Apr 2026 | Plan-lineup tweak: Básico stream quality and ad load adjusted; downloads removed from Básico. |
| 34 | Jun 2026 | **Churn steps up.** *(This row is the symptom, not an event.)* |

The investigation must weigh several of these against each other rather than seizing on the
one nearest to month 34.

---

## 9. CFO-grade deep-dive threads

Two threads get modelled with extra rigour because they carry the profit and cash story:

### 9.1 Content economics
- **Amortisation vs cash spend** tracked separately; a monthly bridge between them.
- **Content cost per viewing hour** and **per retained subscriber**, by market.
- **Content supply cadence**: releases per month, days since the last "tentpole" title,
  and a share-of-catalogue-refreshed metric — the supply side of engagement.

### 9.2 Payments, dunning, and involuntary churn
- Payment **method mix** (card / PIX / boleto / OXXO / carrier billing) with method-level
  **authorisation rates**, **processing cost**, and **failure → recovery** funnels.
- **Dunning**: retry schedule, recovery rate by attempt, days-to-recovery, and the
  involuntary-churn tail when dunning is exhausted.
- Effect of the payment-method mix on **effective net price** and on **cash conversion**
  (carrier-billing settlement lag, boleto float).

Working-capital framing: subscription cash is collected close to service, so the classic
cash-conversion-cycle story is thin; the cash levers here are **content cash timing** and
**payment settlement lag**, reported as a simplified cash bridge rather than a full CCC.

---

## 10. Multi-currency handling

- Every monetary column is stored twice: `*_local` (transaction currency) and `*_usd`
  (converted at the month's average rate).
- A disconnected **Reporting Currency** table (BRL / MXN / USD) drives a slicer, with
  `FX Rate to Reporting Currency` (= 1 when reporting currency = USD) and a
  `Currency Symbol` measure (`R$` / `MX$` / `US$`).
- Leaf monetary measures are wrapped `× [FX Rate to Reporting Currency]`; **USD is the
  default** reporting currency for the portfolio.
- FX paths over the window are seeded with plausible drift: **BRL ≈ 4.9–5.5 / USD**,
  **MXN ≈ 17–20 / USD**. Rates move gradually; no single month swings enough to explain a
  churn step by itself, but FX is available as a control.

---

## 11. Seasonality and patterns embedded in the data

| Pattern | Where it shows |
|---|---|
| **Dec–Jan** Brazilian summer + year-end tentpoles | Acquisition and engagement peak; annual-plan sign-ups spike. |
| **Carnaval** (Feb) | Short engagement dip in Brazil, ~1–2 weeks. |
| **Jun–Jul** Festa Junina / winter | Engagement rises; a mid-year content push. |
| **Content gaps** (weeks between tentpoles) | Engagement troughs and a mild, *recurring, expected* churn uptick — the baseline seasonal churn rhythm. |
| **Annual-plan renewal echoes** | Sign-up peaks re-appear as renewal (and churn-decision) spikes ~12 months later. |
| **Payment cadence** | Boleto/PIX retries cluster at month start; carrier-billing subs bill and lapse on the partner's cycle. |
| **Mexico** | Semana Santa (Apr) and Día de Muertos (Nov/Dec) engagement bumps; December bundle promotions. |
| **US** | Post-holiday Q1 cancellations, a summer slump; short dip on Super Bowl weekend. |
| **FX drift** | Gradual BRL/MXN depreciation vs USD nudges USD-reported ARPU down even when local ARPU is flat. |

The month-34 shift sits **on top of** this seasonal structure and is larger than any
seasonal move in the baseline.

---

## 12. Stakeholder personas → report pages

Each persona brings one standing question. Those questions are the seven Phase-1 pages.

| # | Persona | Standing question | Page |
|---|---|---|---|
| 1 | **CEO / Board** | How bad is the spike, and is it still getting worse? | **Executive Summary** |
| 2 | **VP Retention & Lifecycle** | Which cohorts, tenures, plans, markets, and sign-up sources are actually churning? | **Subscriber Retention & Cohorts** |
| 3 | **VP Content & Programming** | Did people stop watching *before* they cancelled? Is there a content-supply gap? | **Content & Engagement** |
| 4 | **VP Pricing & Monetization** | Did a price increase or plan change push people out — and how price-sensitive is each segment? | **Pricing & Plans** |
| 5 | **VP Growth / Performance Marketing** | Did the *quality* of who we acquire drop — worse channels, worse early retention? | **Acquisition Quality & Channels** |
| 6 | **VP Customer Experience / CTO** | Are payment failures or app problems forcing people out — involuntary churn, crashes, playback errors, support surge? | **Customer Experience, Billing & App Quality** |
| 7 | **CFO / Head of Strategy** | Is this global or concentrated in one market — and what is the revenue and LTV hit? | **Market Context** |

No single page is expected to contain the whole answer; the diagnosis comes from reading
them together.

---

## 13. KPI framework

Benchmark ranges are **directional**, based on publicly disclosed SVOD metrics and analyst
commentary, adapted to a mid-priced Latin-America-led service. They set the targets; they
are not claims about competitors.

### 13.1 Growth & retention

| KPI | Definition | Benchmark range | Target |
|---|---|---|---|
| Paid Active Subscribers (EoP) | In-force paid accounts at period end | — | On plan curve (§14) |
| Net Subscriber Adds / month | New + reactivations − gross churn | > 0 ex-seasonal | ≥ plan |
| **Gross Monthly Churn %** | Ended paid subs ÷ start-of-month paid subs | 3.0%–6.0% | **≤ 4.0%** |
| Voluntary Churn % | Member-initiated share of churn | 2.2%–4.5% | ≤ 3.0% |
| Involuntary Churn % | Dunning-exhausted share of churn | 0.7%–1.6% | ≤ 1.0% |
| Net MRR Retention (12M) | Cohort MRR after 12M ÷ starting MRR | 92%–102% | ≥ 99% |
| M1 Retention | Cohort active after first renewal | 82%–90% | ≥ 88% |
| M6 Retention | Cohort active at month 6 | 52%–70% | ≥ 62% |
| M12 Retention | Cohort active at month 12 | 38%–55% | ≥ 48% |
| Trial-to-Paid Conversion % | Converting trials ÷ trials started | 45%–65% | ≥ 55% |
| Reactivation Rate % | Win-back within 12M ÷ churned base | 8%–16% | ≥ 12% |

### 13.2 Engagement (leading indicators of churn)

| KPI | Definition | Benchmark range | Target |
|---|---|---|---|
| Monthly Active Rate % | Paid subs who streamed ≥ 1 min in the month ÷ paid subs | 74%–88% | ≥ 85% |
| Viewing Hours / Active Sub / month | Streamed hours ÷ monthly active subs | 40–70 h | 45–65 h |
| % Subs Below Healthy Engagement | Paid subs with < 5 streamed hours in the month | 10%–20% | ≤ 15% |
| Titles Started / Active Sub / month | Distinct titles with a play start | 4–9 | ≥ 6 |
| Days Since Last Tentpole Release | Recency of a major release, by market | < 45 d | ≤ 30 d |
| Content Releases / month | Titles added to catalogue | — | ≥ plan |

### 13.3 Monetisation & unit economics

| KPI | Definition | Benchmark range | Target |
|---|---|---|---|
| ARPU (reporting currency) | Subscription revenue ÷ avg paid subs | BR ~US$5.5–7 · MX ~US$6–8 · US ~US$11–14 | ≥ plan |
| MRR | Normalised recurring subscription value | — | ≥ plan |
| Total Revenue YoY % | Total revenue vs prior year (per cut) | — | ≥ plan |
| Gross Margin % | Gross profit ÷ revenue | 28%–45% | ≥ 40% |
| Contribution Margin % (T12M) | (Gross profit − marketing) ÷ revenue | 6%–18% | ≥ 12% |
| Blended CAC | Marketing ÷ new paid subs (lower is better) | US$14–30 blended | ≤ US$22 |
| CAC Payback (months) | CAC ÷ (ARPU × gross margin %) | 12–20 | ≤ 16 |
| LTV : CAC | LTV ÷ blended CAC | ≥ 3.0 | ≥ 3.5 |
| % Revenue from Ads Tier | Advertising ÷ total revenue | 6%–14% | context |
| % New Subs via Partner/Bundle | Bundle sign-ups ÷ new subs | 10%–25% | context |

### 13.4 Acquisition quality

| KPI | Definition | Benchmark range | Target |
|---|---|---|---|
| New Subs by Channel | Direct / paid-search / paid-social / affiliate / partner-bundle / organic | — | mix on plan |
| Channel M1 Retention | M1 retention split by acquisition channel | direct highest, affiliate/bundle lowest | each ≥ its plan |
| Channel M3 Retention | M3 retention split by acquisition channel | — | each ≥ its plan |
| Trial Start Rate by Channel | Trials started ÷ sign-ups, by channel | — | context |
| Share of Adds from Low-Retention Channels | Affiliate + bundle share of new subs | 20%–40% | ≤ 35% |
| Incentivised Sign-up Share | Sign-ups with a promo/discount code | 25%–45% | ≤ 40% |

### 13.5 Customer experience, billing & app quality

| KPI | Definition | Benchmark range | Target |
|---|---|---|---|
| Payment Failure Rate % | Failed billing attempts ÷ attempts | 4%–9% | ≤ 6% |
| Auth Rate by Method | Approved ÷ attempted, per payment method | card 88–95% · PIX 95–99% · boleto 70–85% · OXXO 65–80% · carrier 90–97% | per-method plan |
| Dunning Recovery Rate % | Recovered ÷ entered dunning | 35%–55% | ≥ 45% |
| Days to Recovery | Mean days from failure to successful charge | 2–7 | ≤ 5 |
| App Crash-Free Session Rate % | Sessions with no fatal crash ÷ sessions | 99.2%–99.8% | ≥ 99.5% |
| Playback Error Rate % | Streams with a fatal playback error ÷ streams | 0.3%–1.2% | ≤ 0.7% |
| Video Start Failure % | Play attempts that never start ÷ attempts | 0.5%–2.0% | ≤ 1.2% |
| Support Contacts / 1,000 Subs | Tickets ÷ (subs / 1,000) per month | 40–90 | ≤ 70 |
| CSAT | Mean post-contact satisfaction (1–5) | 3.9–4.5 | ≥ 4.2 |

### 13.6 Market context

| KPI | Definition | Use |
|---|---|---|
| Churn % by Market | Gross monthly churn split BR / MX / US | Is the shift global or concentrated? |
| Net Adds by Market | Monthly net adds per market | Where the base is actually shrinking |
| Revenue & MRR by Market | Reporting-currency, with FX effect isolated | Size of the financial hit |
| Engagement & App Quality by Market | §13.2 / §13.5 metrics per market | Whether operational health differs by market |
| Cumulative Subscribers Lost vs Plan | (Plan base − actual base), by market, since month 34 | The board-level scoreboard of the gap |

---

## 14. Targets and plan

- The plan is built on the **same basis as the actuals** (net of involuntary churn where the
  actual measure is; local-currency plan then FX-converted, not the reverse).
- **Plan subscriber base**: `PY actual × (1 + planned growth)` per market per month, with
  planned growth set *before* the shift (Brazil mid-single-digit YoY, Mexico and US ramping
  from their launch curves).
- **Plan churn**: flat at the §13.1 targets (gross ≤ 4.0%, involuntary ≤ 1.0%).
- **Plan ARPU / MRR**: plan base × plan ARPU (local), then converted.
- **Plan marketing / CAC**: spend to hit plan net adds at CAC ≤ US$22 blended.
- Plan is monthly for the full window; the CY plan (months 25–36) is the one shown against
  actuals on the report. "vs Target %" measures exist per KPI, with CAC and churn scored
  **lower-is-better**.

---

## 15. Out of scope (explicit)

- Title-level recommendation / personalisation algorithm analysis.
- Ad-tech yield and programmatic optimisation beyond blended eCPM and fill rate.
- Device- or OS-level quality-of-experience beyond crash rate, playback-error rate, and
  video-start-failure rate.
- Tax, transfer pricing, and statutory / IFRS reporting detail.
- Headcount, payroll, and opex below allocated G&A.
- A churn-**prediction** model. This project is a **diagnosis**, not a forecast.
- External data: competitor pricing, market share, third-party panel data. The "Market
  Context" page is internal markets (BR/MX/US), not the competitive market.
- Real personal data. All subscribers, payments, and viewing events are synthetic and
  seed-generated.

---

## 16. Resolved-assumptions log

| # | Decision | Resolution |
|---|---|---|
| A1 | Window length & anchor | 36 months, Sep 2023 – Aug 2026; data-gen date 2026-09-02. |
| A2 | Market launch months | Brazil = pre-window; Mexico = month 10 (Jun 2024); US = month 16 (Dec 2024). |
| A3 | Churn-shift timing | Steps up at month 34 (Jun 2026); elevated for months 34–36. |
| A4 | Primary churn metric | Gross monthly logo churn; voluntary/involuntary split reported alongside. |
| A5 | North Star | Paid Active Subscribers (EoP); watch metric = gross monthly churn %. |
| A6 | Plan lineup | Three tiers (Básico ad-supported / Standard / Premium), monthly + annual, per-market local pricing. |
| A7 | Trial | 7-day free trial on Standard/Premium via direct sign-up only. |
| A8 | Comparable Base | Brazil only (sole full-window market); Expansion = Mexico + US. |
| A9 | Reporting currency | USD default; slicer for BRL/MXN/USD; `*_local` + `*_usd` on every money column. |
| A10 | FX method | Monthly average rates, seeded gradual drift; no single-month FX shock. |
| A11 | Content accounting | Amortisation and cash spend modelled separately, with a monthly bridge. |
| A12 | Payment scope | Method mix, auth rates, dunning funnel, involuntary-churn tail modelled; full CCC not. |
| A13 | Fiscal calendar | Calendar year; monthly reporting. |
| A14 | Benchmark ranges | Directional, from public SVOD disclosures/analyst ranges; used only to set targets. |
| A15 | Root cause | **Deliberately not decided in this document.** Determined during ETL (Phase 3), surfaced only through the data and the Phase 10 investigation. |

---

*End of Phase 1 deliverable.*
