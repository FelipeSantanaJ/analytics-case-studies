# AeroVanti SkyPoints — Business Context & KPI Framework

**Document status:** Phase 1 deliverable · authored at project kickoff, before any analysis.
**Data generation date:** 2026-09-02 · **Program-history window:** 2024-09-01 → 2026-08-31 (24 full months).
**Embedded experiment:** Flash Redemption A/B test, 2026-03-02 → 2026-05-24 (12 weeks, program months 19–21).
**Audience:** the AeroVanti loyalty leadership team and the CFO.

> This document frames the problem and defines the metrics. It deliberately does **not**
> state whether Flash Redemption worked, or by how much — that is the job of the read-out
> (Phase 10). Everything here was knowable *before* the analysis began. The true underlying
> treatment effect is decided during ETL (Phase 3), baked into the synthetic data with
> noise, novelty decay and tier heterogeneity, and kept only in `etl/config.py`; Phase 10
> must detect and quantify it as if blind.

---

## 1. The situation

**AeroVanti** is a mid-size Brazilian domestic airline. Its frequent-flyer program,
**SkyPoints**, was relaunched two years ago (Sep 2024) with a modern tier structure and a
co-branded credit card; this project's 24-month window is exactly the relaunched program's
life to date.

Two things are wrong with the program:

1. **Members hoard points.** Only about one active member in four has *ever* redeemed. Across
   the program to date, roughly **40% of issued points are expected to expire unredeemed**
   ("breakage"). A large, slow-growing **point liability** sits on the balance sheet, and
   the CFO wants it down.
2. **Non-redeemers leave.** Members who have never redeemed **lapse** (go 12 months with no
   earn and no redemption) at a materially higher rate than members who have redeemed at
   least once. Every lapsed member is lost forward flight revenue.

The loyalty team's hypothesis is that a **redemption threshold that is too high** is the
common cause: a member with 4,000 points can't do anything with them, never gets the
"I got something" moment, disengages, and eventually lapses — while their points age toward
expiry. In program months 19–21 the team ran **Flash Redemption** as a **randomized,
member-level A/B test**: a lower minimum redemption threshold plus an expanded catalog of
low-cost rewards. This project builds the read-out needed to decide on full
rollout, plus a lighter dashboard on overall program health.

---

## 2. Company profile

| | |
|---|---|
| Name | **AeroVanti** (legal entity *AeroVanti Linhas Aéreas S.A.*) |
| Headquarters | Campinas (VCP), São Paulo state, Brazil |
| Business | Domestic scheduled passenger airline — point-to-point + two-hub (VCP, Recife/REC) |
| Fleet & network | ~28 narrowbody aircraft; ~42 domestic routes; ~4.5M passengers/year |
| Age | Airline ~12 years; **SkyPoints relaunched Sep 2024** (legacy program folded in) |
| Currency | **BRL only.** Domestic operation, no international routes, no FX in scope. |
| Fiscal calendar | Calendar year; loyalty reporting is monthly, experiment reporting is weekly |
| Program scale at window end | ~150k cumulative enrolled members; **~65k active** (earn or flight in trailing 12 months); outstanding point liability ~R$14M |

### SkyPoints positioning
A **coalition-lite** airline program: points are earned on AeroVanti flights (with a tier
multiplier), on the **BancoAV SkyPoints Mastercard** co-branded card (the single largest
issuance source), and with a handful of hotel / car-rental / retail partners. Points are
redeemed mostly for **award flights**, plus a small ancillary catalog (seat selection, extra
bag, lounge passes). The relaunch's selling point was "a clear path to a free flight"; the
unsolved problem is that most members never get close.

---

## 3. Two point currencies

SkyPoints keeps the industry-standard split between a **spendable** currency and a
**status** currency. They must not be conflated in the analysis.

| Currency | Purpose | Earns on | Expires | Tier multiplier |
|---|---|---|---|---|
| **SkyPoints** | Spendable — redeemed for awards. Drives the **liability**. | Flights, co-brand card, partners | **24 months after the month earned**, per lot (FIFO burn) | Yes (see §4) |
| **Tier Points (TP)** | Status only — determine tier. Never redeemable, never a liability. | Flights only (base fare + 100 TP/segment) | Reset on the member's **tier anniversary** (rolling 12-month qualification) | No |

Because the program relaunched exactly 24 months before window end and SkyPoints lots live
24 months, **the first material wave of point expiry lands in the last ~3 months of the
window** — breakage becomes directly observable, not just forecast, right where the data
ends.

---

## 4. Tier structure

Four tiers. Qualification is on **trailing-12-month Tier Points or qualifying segments**,
re-evaluated monthly; a tier, once earned, is held for 12 months before it can be lost.

| Tier | Qualify (trailing 12m): TP **or** segments | SkyPoints earn multiplier (flights) | ~Share of active members | Key benefits |
|---|---|---|---|---|
| **Blue** | entry — any enrolled member | 1.0× | ~68% | Earn points; standard fees |
| **Silver** | 8,000 TP **or** 4 segments | 1.25× | ~20% | Free seat selection, priority check-in |
| **Gold** | 25,000 TP **or** 12 segments | 1.5× | ~9% | Free bag, lounge access, waived change fees |
| **Platinum** | 60,000 TP **or** 30 segments | 2.0× | ~3% | Upgrades, guaranteed availability, bonus redemption value |

**Tier movement** is tracked two ways, and the two are allowed to disagree (a deliberate
data-quality issue, §12 of the architecture doc): a monthly **tier-status snapshot** table
and a **tier-change event ledger**. The curated model rebuilds status *from* the ledger and
reconciles the drift.

---

## 5. Points economics — earn, burn, breakage, liability

### 5.1 Earn (SkyPoints issuance)

| Source | Rate | ~Share of SkyPoints issued | Notes |
|---|---|---|---|
| **AeroVanti flights** | 1.0 SkyPoint per R$1 **base fare** (excl. taxes/fees) × tier multiplier; +50% on flexible fare families | ~45% | The only source that also earns Tier Points |
| **BancoAV co-brand card** | 1 SkyPoint per R$2.50 card spend; large sign-up bonus on approval | ~42% | **Largest single issuance source**; no flight attached → pure liability with weak redemption pull |
| **Partners** (hotels, car rental, retail, fuel) | Varies by partner | ~8% | Small, irregular |
| **Promotions / service recovery / bonuses** | Ad hoc | ~5% | Double-points campaigns, IRROPS goodwill |

### 5.2 Burn (redemption)

| Option | Indicative price | Value per point | Available pre-Flash? |
|---|---|---|---|
| **Award flight** (dynamic pricing + "SkyCash" points-plus-cash) | from ~8,000 SkyPoints one-way short-haul | ~R$0.024 / pt | Yes |
| Seat selection | 1,500 pts | ~R$0.013 / pt | **No** — added by Flash |
| Extra checked bag | 2,500 pts | ~R$0.014 / pt | **No** — added by Flash |
| Lounge day pass | 5,000 pts | ~R$0.016 / pt | **No** — added by Flash |
| Partner gift card (R$25 / R$50) | 3,500 / 6,500 pts | ~R$0.008–0.010 / pt | **No** — added by Flash |
| Onboard Wi-Fi / bar voucher | 1,800 pts | ~R$0.012 / pt | **No** — added by Flash |

**Minimum redemption threshold** = the balance below which the redemption UI will not
transact at all. **Pre-Flash: 10,000 SkyPoints. Flash (treatment): 3,500 SkyPoints**, plus
the low-cost catalog above. A large block of Blue members hold 3,500–9,999 points and are
**structurally unable to redeem anything** pre-Flash — this is the segment the intervention
is aimed at.

Burn is **FIFO** across point lots (oldest first), so any redemption also directly reduces
near-term breakage.

### 5.3 Breakage & liability (CFO deep-dive thread #1)

| Term | Definition |
|---|---|
| **Points outstanding** | Σ (issued − redeemed − expired), all lots, at a date. |
| **Point liability (BRL)** | Points outstanding × unit cost, where **unit cost ≈ R$0.021 / pt** (weighted award value) **× (1 − expected breakage)** for the deferred-revenue portion. Reported both gross and breakage-adjusted. |
| **Breakage rate** | Of points issued in a cohort (issuance month), the share that expire unredeemed. Estimated **cohort-based** (preferred) and cross-checked against an aggregate roll-forward. |
| **Breakage-adjusted cost** | The P&L cost actually recognised; sensitive to the breakage assumption — a sensitivity table is a required Phase-10 artifact. |
| **Liability roll-forward** | Opening + issued − redeemed − expired − revaluation = closing, monthly. |

Program-to-date breakage is running near **40%**. The relaunch business case assumed it
would fall toward **30%** as members learned the program; it has not. Flash Redemption is
also a **liability-management** lever: more redemption draws the liability down and converts
"will expire" points into engagement — but the low-cost catalog is bought at **cash cost**
from partners, so the net financial effect is not obviously positive and must be quantified.

---

## 6. Lapse & retention (CFO deep-dive thread #2)

| Term | Definition |
|---|---|
| **Active member** | ≥ 1 earn event **or** ≥ 1 flight in the trailing 12 months. |
| **Lapsed member (account lapse)** | 12 consecutive months with **no earn and no redemption**. A state, re-evaluated monthly. Note: co-brand-card auto-earn keeps most card-holders' accounts "active" on this definition even when they never fly or redeem, so account lapse understates disengagement. |
| **Engagement lapse** | 12 consecutive months with **no flight and no redemption** (card-only earn does not count). The retention metric the program actually cares about — separates "still enrolled" from "still flying with us". |
| **Reactivation** | A lapsed member with a new earn or redemption. |
| **Redeemer** | A member with ≥ 1 completed redemption, ever (or in a stated window). |
| **Redeemer lapse gap** | Lapse rate of never-redeemers − lapse rate of redeemers, controlling for tenure, tier and earn activity. The program's core retention hypothesis: this gap is large and at least partly **causal**. |

The experiment is the clean causal test of that hypothesis: if randomly *enabling* more
redemption reduces downstream lapse, the lever is real. Because the experiment sits in
months 19–21 and the data ends at month 24, we observe **~14 weeks of post-window
behaviour** — enough for early-lapse proxies and a 90-day forward-activity read, not enough
for a full 12-month lapse outcome. Phase 10 states this horizon limit explicitly.

---

## 7. The Flash Redemption A/B test

### 7.1 Design

| Element | Decision |
|---|---|
| **Unit of randomization** | Member (single SkyPoints account). |
| **Eligible population** | Active (earn or flight in trailing 12m) **and** not lapsed as of **2026-03-01**. Frozen list; ~58k members. |
| **Sample & allocation** | **15,000 members**, **stratified by tier with mild oversampling of Gold/Platinum** so the heterogeneity cut has power: **Blue 8,000 · Silver 4,000 · Gold 2,200 · Platinum 800**. **50/50** treatment/control **within each stratum**. |
| **Why oversample** | Proportional allocation would leave ~450 Platinum members total — no power for a per-tier effect. Oversampling trades a little external validity for a usable heterogeneity read; the **overall effect is reported both pooled and post-stratified** back to the population tier mix. |
| **Treatment** | Minimum redemption threshold 10,000 → **3,500** SkyPoints; **low-cost reward catalog** (§5.2) switched on; one announcement email + in-app banner. |
| **Control** | No change: 10,000 threshold, flights-and-ancillaries-only catalog, no announcement. |
| **Window** | 12 weeks: **2026-03-02 → 2026-05-24**. Post-window observation to 2026-08-31. |
| **Assignment integrity** | Flag set once at enrolment; no re-randomization; no mid-flight changes to thresholds for either arm. |

### 7.2 Hypotheses

- **Business hypothesis.** Lowering the threshold and adding low-cost rewards raises the
  share of members who redeem, which (a) draws down the point liability and future breakage
  and (b) reduces downstream lapse, **without** a material loss of flight revenue.
- **Statistical hypothesis (primary).** H₀: redemption rate is equal in the two arms over
  the window. H₁: treatment > control. Tested one-sided at α = 0.05; a **two-sided 95% CI**
  on the difference is always reported.

### 7.3 Metrics

| Role | Metric | Definition | Decision rule |
|---|---|---|---|
| **Primary** | **Redemption rate** | Share of assigned members with ≥ 1 completed redemption (any type) during the 12-week window. | Ship if lift is **positive, significant (α = 0.05), and ≥ the MDE** on the pooled + post-stratified estimate. |
| Guardrail | **Revenue per member (BRL)** | Flown-flight revenue attributed to the member, window + 8 weeks post. | **Non-inferiority:** treatment not worse than control by > **3%** (one-sided). |
| Guardrail | **Point-liability cost per member (BRL)** | Δ liability drawn down + cash cost of low-cost rewards redeemed. | Net effect reported with CI; **flag if treatment cost per member is higher** than control with 95% confidence. |
| Guardrail | **Early-lapse / disengagement proxy** | Share with **no earn and no redemption in the 90 days after** the window. | Directional; **flag if treatment is worse.** |
| Guardrail | **Average redemption value & mix** | Mean BRL value per redeeming member; share of redemptions that are low-cost-catalog only. | Context for whether the lift is "real engagement" or trivial-redemption gaming. |

### 7.4 Power & minimum detectable effect

| Assumption | Value |
|---|---|
| Control redemption rate over 12 weeks (planning value) | **11.0%** |
| Target (MDE), relative | **+20%** → absolute **+2.2 pp** (11.0% → 13.2%) |
| α (two-sided) / power | 0.05 / 0.80 |
| Required n per arm at the MDE (two-proportion) | **≈ 3,450** |
| Actual n per arm | **≈ 7,500** → power **> 0.95** at the MDE; **~0.80** power for an effect as small as **+1.5 pp** |
| Per-tier cells (per arm) | Blue 4,000 · Silver 2,000 · Gold 1,100 · Platinum 400 → well powered for Blue/Silver, directional only for Gold, **underpowered for Platinum** (a Platinum null = "consistent with no effect", not "proven zero") |

The power calculation is re-run from the realized pre-period rates and reproduced in code in
Phase 10; the numbers above are the planning basis.

### 7.5 Threats to validity the read-out must address

| Threat | How it is handled |
|---|---|
| **Sample-ratio mismatch** | χ² goodness-of-fit on arm counts overall and per stratum; investigate if p < 0.01. |
| **Covariate imbalance** | Standardized mean differences on tier, tenure, pre-period earn, pre-period flights, pre-period balance, prior-redeemer flag; report a Love plot. |
| **Novelty effect** | Weekly treatment redemption rate across the 12 weeks; test for a decaying trend (weeks 1–4 vs 9–12); report the **settled** lift, not the peak. |
| **Seasonality** | Control arm is concurrent, so calendar seasonality differences out; still report both arms' weekly series. |
| **Contamination / spillover** | Household and referral links between arms assumed negligible; stated as a limitation with a rough bound. |
| **Multiple comparisons** | One primary metric fixed in advance; guardrails and the 4-way heterogeneity cut are treated as **secondary** and CI-reported, with a note on family-wise error. |
| **Post-window horizon** | Lapse is a 12-month construct; only 90-day forward proxies are available. Stated, not hidden. |
| **Peeking** | Single fixed analysis at window close; no interim looks drive the decision. |

### 7.6 Heterogeneity analysis (required)

Effect on the primary metric estimated **within each tier**, with per-tier CIs and a
formal **arm × tier interaction** test. The prior to test — not to assume — is that the
effect is largest for **Blue** (threshold-constrained) and smallest for **Platinum**
(already redeem freely). The business decision (full rollout vs rollout to lower tiers
only) hinges on this cut.

---

## 8. The analytics window — why 24 months, and CY vs PY

| Anchor | Value |
|---|---|
| Window length | 24 complete months: **month 1 = Sep 2024**, month 24 = Aug 2026 |
| Current Year (CY) | months 13–24 → **Sep 2025 – Aug 2026** |
| Prior Year (PY) | months 1–12 → **Sep 2024 – Aug 2025** — *the program's first, ramping year* |
| Experiment | months 19–21 → **Mar–May 2026** (12 weeks) |
| Post-window observation | 2026-05-25 → 2026-08-31 (~14 weeks) |

**Why 24 months.** It is the full life of the relaunched program — earlier data is on the
retired legacy scheme and not comparable. It is also exactly one SkyPoints lot lifetime, so
breakage becomes observable within the window.

**Comparability caveat.** PY is the relaunch ramp: enrolment, earn and redemption were all
climbing off a near-zero base, so **raw YoY overstates underlying growth**. Every YoY metric
is reported with a **steady-state cut** alongside it — restricted to members enrolled
**before month 4** (Dec 2024), whose behaviour is not dominated by onboarding. An
account-level flag `is_steady_state_cohort` carries this.

---

## 9. Seasonality and patterns embedded in the data

| Pattern | Where it shows |
|---|---|
| **Jan / Jul / Dec** Brazilian holiday travel peaks | Flight earn peaks; award-flight redemptions peak **1–2 months ahead** (booking Oct–Nov for Dec–Jan, Apr–May for Jul) |
| **Feb–Mar, May, Sep** shoulder season | Lower earn; the experiment sits in this calmer stretch |
| **Carnaval** (Feb) | Short travel spike then a lull |
| **Black Friday / Nov** | Enrolment spike (card acquisition push), co-brand spend spike |
| **Co-brand card earn** | Steadier than flight earn; mild Nov–Dec holiday-spend lift |
| **Point expiry wave** | First large lot expiries in **Jun–Aug 2026** (24 months after the relaunch surge) → breakage visibly steps up at window end |
| **Tier re-evaluation** | Monthly, but downgrades cluster ~12 months after the relaunch enrolment surge |
| **Redemption into the experiment window** | Naturally rising toward the Jul peak — handled by the concurrent control arm, not by de-seasonalising |

---

## 10. Stakeholder personas → report pages

Four personas, one standing question each. Those four questions are the Phase-1 pages
(dashboard is a secondary deliverable — kept lean).

| # | Persona | Standing question | Page |
|---|---|---|---|
| 1 | **Loyalty Director / CMO** | Is the program healthy, and did Flash Redemption work well enough to roll out? | **Executive Summary** |
| 2 | **Head of Loyalty Finance** (liability owner) | Where is member value concentrated, how large and how fast-growing is the breakage liability, and how are members moving between tiers? | **Member Tiers & Value** |
| 3 | **Experimentation / Product Lead** | Is the effect real, significant and safe on the guardrails — or is it novelty, or one segment carrying it? | **A/B Test Results** |
| 4 | **CRM / Retention Manager** | Where do members fall out of the redeem journey, and who is about to lapse? | **Redemption & Engagement Funnel** |

---

## 11. KPI framework

Benchmark ranges are **directional**, drawn from public airline-loyalty disclosures and
industry commentary (IdeaWorks/Switchfly breakage studies, IATA loyalty notes), adapted to a
young single-country program. They set targets; they are not claims about named competitors.

### 11.1 Program health & scale

| KPI | Definition | Benchmark | Target |
|---|---|---|---|
| Enrolled members (cumulative) | Distinct accounts ever enrolled | — | on relaunch curve |
| **Active members** | Earn or flight in trailing 12m | — | ≥ 80k by window end |
| Active rate % | Active ÷ enrolled | 45%–65% | ≥ 55% |
| New enrolments / month | First enrolment in the month | — | ≥ plan |
| Member tenure mix | Share by <6 / 6–12 / 12–24 months | — | context |
| Co-brand card penetration % | Active members holding the card | 12%–25% | ≥ 20% |

### 11.2 Earn & burn

| KPI | Definition | Benchmark | Target |
|---|---|---|---|
| SkyPoints issued / month | Sum of earn events | — | ≥ plan |
| SkyPoints redeemed / month | Sum of redemption debits | — | ≥ plan |
| **Burn/earn ratio** | Points redeemed ÷ points issued (trailing 12m) | 0.55–0.80 | ≥ 0.65 |
| **Quarterly redemption rate %** | Active members with ≥1 redemption in the quarter | 8%–15% | ≥ 15% |
| Ever-redeemed % | Active members with ≥1 redemption ever | 30%–55% | ≥ 45% |
| Avg SkyPoints balance (active) | Mean outstanding balance | — | context |
| Median months-to-first-redemption | From enrolment to first redemption | 6–14 | ≤ 10 |

### 11.3 Breakage & liability

| KPI | Definition | Benchmark | Target |
|---|---|---|---|
| Point liability (BRL) | Points outstanding × unit cost (gross and breakage-adjusted) | — | ≤ plan |
| **Breakage rate %** | Cohort points issued that expire unredeemed | 10%–30% | ≤ 30% |
| Points expiring / month (BRL) | Value of lots reaching 24-month expiry | — | minimise |
| Liability per active member (BRL) | Liability ÷ active members | — | context |
| Liability coverage (months of redemptions) | Liability ÷ trailing-3m redemption value | — | context |

### 11.4 Tiers & value

| KPI | Definition | Benchmark | Target |
|---|---|---|---|
| Tier mix % | Active members by tier | ~68/20/9/3 | context |
| Upgrades / downgrades per month | Tier-change events by direction | — | net ≥ 0 |
| Tier retention rate % | Members holding tier at re-evaluation | Silver+ 60%–80% | ≥ 70% |
| Revenue per member by tier (BRL/yr) | Flown flight revenue ÷ members, by tier | rises steeply by tier | context |
| Share of flight revenue from Gold+Platinum | Top-tier revenue ÷ total member flight revenue | 25%–45% | context |

### 11.5 Retention & lapse

| KPI | Definition | Benchmark | Target |
|---|---|---|---|
| **12-month account lapse rate %** | Active members who hit *account* lapse within 12 months | 3%–8% | context |
| **12-month engagement lapse rate %** | Active members with no flight and no redemption for 12 months | 15%–30% | ≤ 22% |
| Active → lapsed / month | Monthly lapse count | — | minimise |
| Reactivation rate % | Lapsed members reactivating within 12m | 8%–18% | ≥ 12% |
| **Redeemer lapse gap (pp)** | Never-redeemer lapse rate − redeemer lapse rate (adjusted) | positive | quantify |
| Mn cohort retention | Share of an enrolment cohort still active at month n | M12 55%–75% | ≥ 65% |

### 11.6 Commercial value

| KPI | Definition | Benchmark | Target |
|---|---|---|---|
| Revenue per active member (BRL/yr) | Flown flight revenue ÷ active members | — | ≥ plan |
| Award-seat share % | Award-flight seats ÷ total seats | 5%–12% | 6%–10% (managed) |
| Points-plus-cash attach % | Bookings using SkyCash ÷ award bookings | — | context |
| Incremental flights from redeemers | Flights in 6m after first redemption vs matched non-redeemers | positive | quantify |

### 11.7 Experiment scorecard (A/B Test Results page)

| KPI | Definition |
|---|---|
| Redemption rate by arm (+ lift, CI, p) | Primary metric, §7.3 |
| Weekly redemption rate by arm | Novelty-effect diagnostic, §7.5 |
| SRM χ² (overall + per stratum) | Randomization check |
| Covariate balance (SMD / Love plot) | Randomization check |
| Revenue per member by arm (+ non-inferiority test) | Guardrail |
| Liability cost per member by arm (+ CI) | Guardrail |
| 90-day post-window disengagement by arm | Guardrail |
| Redemption value & low-cost-only share by arm | Guardrail / context |
| Effect by tier (+ interaction test) | Heterogeneity, §7.6 |

---

## 12. Targets and plan

- The plan is built on the **same basis as the actuals** (same lapse definition, same
  breakage-adjusted liability basis).
- **Plan active members:** relaunch business-case curve — ramp to **80k active** by month 24.
- **Plan breakage:** declining from ~40% at relaunch to **≤ 30%** by month 24.
- **Plan redemption rate:** rising to **≥ 15%** quarterly by month 24.
- **Plan 12-month lapse rate:** **≤ 22%**.
- **Plan liability:** issuance on the earn plan, redemptions on the burn plan → a planned
  liability trajectory; actual vs plan is the CFO scoreboard.
- "vs Target %" measures exist per KPI; **breakage rate, lapse rate and liability per member
  are scored lower-is-better**.

---

## 13. Multi-currency handling

Out of scope by design. All monetary values are **BRL**. No `*_local` / `*_usd` split, no FX
table, no reporting-currency slicer. This choice is deliberate — it keeps the project's
attention on the analysis and the experiment.

---

## 14. Out of scope (explicit)

- International routes, partner-airline accrual/redemption, Star/oneworld-style alliances.
- Fare pricing and revenue management (flight revenue is an input, not modelled).
- Fraud, points brokering, account-takeover.
- Crew, fuel, maintenance, aircraft economics — this is a **loyalty** project, not an
  airline-operations one.
- Real-time data; everything is monthly/weekly batch.
- A lapse-**prediction** model. Phase 10 quantifies drivers and the experiment effect; it
  does not ship a churn scorecard.
- Marketing-channel attribution beyond the experiment's own assignment.
- Real personal data. All members, flights, card spend, earn and redemption events are
  synthetic and seed-generated.
- The **true Flash Redemption effect size** — decided in Phase 3, not here.

---

## 15. Resolved-assumptions log

| # | Decision | Resolution |
|---|---|---|
| A1 | Window length & anchor | 24 months, Sep 2024 – Aug 2026; data-gen date 2026-09-02; = relaunched-program life. |
| A2 | Two point currencies | Spendable **SkyPoints** (24-month lot expiry, FIFO) + status **Tier Points** (reset on anniversary, non-redeemable). |
| A3 | Tiers | Blue / Silver / Gold / Platinum; trailing-12m TP-or-segments qualification; 12-month tier tenure guarantee. |
| A4 | Active member | Earn or flight in trailing 12 months. |
| A5 | Lapsed member | 12 consecutive months with no earn and no redemption. |
| A6 | Breakage | Cohort-based estimate, aggregate roll-forward cross-check; program-to-date ~40%; plan ≤ 30%. |
| A7 | Unit cost for liability | ≈ R$0.021 / pt weighted; reported gross and breakage-adjusted; sensitivity table required. |
| A8 | Experiment unit / split | Member; 50/50 within tier strata. |
| A9 | Experiment eligibility | Active & not lapsed at 2026-03-01; frozen list ~58k. |
| A10 | Experiment sample | 15,000; stratified with Gold/Platinum oversampling (8,000 / 4,000 / 2,200 / 800). |
| A11 | Primary metric | Redemption rate over the 12-week window. |
| A12 | Guardrails | Revenue/member (non-inferiority −3%), liability cost/member, 90-day post disengagement, redemption value & mix. |
| A13 | MDE / power | +20% relative (+2.2 pp on 11.0%); ~7,500/arm → >0.95 power at MDE. |
| A14 | Required diagnostics | SRM, covariate balance, novelty decay, tier heterogeneity + interaction test. |
| A15 | Post-window horizon | ~14 weeks; 90-day proxies only for lapse; stated as a limitation. |
| A16 | Currency | BRL only; no FX in scope. |
| A17 | YoY comparability | PY = relaunch ramp; every YoY paired with a steady-state-cohort cut (`is_steady_state_cohort`). |
| A18 | True treatment effect | Deliberately **not** decided here; set in ETL (Phase 3), detected blind in Phase 10. |

---

*End of Phase 1 deliverable.*
