# SwiftBite Delivery — Business Context & KPI Framework

**Document status:** Phase 1 deliverable · authored at project kickoff, before any analysis.
**Data generation date:** 2026-09-10 · **Marketplace-history window:** 2025-01-01 → 2026-08-31 (20 full months).
**Embedded experiment:** the zone-hour incentive test, 2026-04-06 → 2026-06-14 (10 weeks, window-months 16–18).
**Audience:** SwiftBite's Operations, Growth and Finance leads.

> This document frames the problem and defines the metrics. It deliberately does **not**
> state whether the zone-hour incentive worked, or by how much — that is the job of the
> read-out (Phase 10). Everything here was knowable *before* the analysis. The true
> underlying treatment effect — including the neighbour-zone cannibalisation term — is
> decided during ETL (Phase 3), baked into the synthetic data with noise and
> heterogeneity, and kept only in `etl/config.py`; Phase 10 must detect and quantify it
> as if blind.
>
> **PT — o que este documento é.** Enquadra o problema de negócio e define as métricas de
> um marketplace de delivery. **Não** diz se o incentivo por zona-horário funcionou —
> isso é a Fase 10. O efeito verdadeiro (e a canibalização entre zonas vizinhas) é
> plantado nos dados sintéticos na Fase 3 e fica só em `etl/config.py`; a análise tem
> que recuperá-lo "às cegas".

---

## 1. The situation

**PT.** SwiftBite é um marketplace de delivery de comida numa única cidade grande do
Brasil. Não emprega entregadores — eles entram no app e escolhem quando e onde rodar. Em
**pico de jantar de sexta e sábado**, e em algumas **zonas cronicamente com pouca
oferta**, a demanda passa da oferta: a fila de atribuição atrasa, o **ETA sobe**, uma
onda de pedidos é **cancelada**, e — a assinatura de liquidez ruim — há **entregadores
ociosos noutras zonas** ao mesmo tempo. Operações testou um **bônus dinâmico por
zona-horário** como experimento randomizado por **zona-dia**.

**SwiftBite Delivery** operates a food-delivery marketplace in one large Brazilian metro
(modelled on Belo Horizonte). It is a **two-sided marketplace**:

- **Demand** — consumers place orders in the SwiftBite app; each order belongs to a
  **delivery zone** (from the delivery address) and a **time block**.
- **Supply** — independent couriers log into the courier app and choose their hours and
  rough working area. SwiftBite does not roster them; it can only *influence* where supply
  goes — with information, with assignment logic, and with money.

Most of the week, the metro clears fine: a courier is assigned in a minute or two, ETA is
30–40 minutes, almost every order is delivered. The problem is **concentrated in time and
space**:

1. **Peak dinner on Friday and Saturday** (≈ 18:00–22:00) — order volume roughly triples
   over a weekday lunch, but courier supply rises far less.
2. **A handful of structurally supply-short zones** — outer-ring residential zones with
   long trips, poor return-load prospects and few couriers who live nearby.

When those overlap, three things happen together and define **poor marketplace liquidity**:

| Symptom | Metric it shows up in |
|---|---|
| Assignment slows / fails | Assignment latency ↑, **"no courier found"** cancellations ↑ |
| Customers wait, then bail | **ETA p90** ↑, customer-initiated **cancellation rate** ↑ |
| Supply is in the wrong place | **Idle-courier ratio** ↑ in *other* zones at the same minute |
| Orders never delivered | **Fulfillment rate** ↓ (the primary experiment metric) |

The Operations team's hypothesis: a **temporary, targeted per-delivery bonus** — announced
in-app for a **named zone during the peak block** — will pull enough nearby couriers into
that zone to lift fulfillment, at a bonus cost lower than the contribution margin of the
orders it saves. Growth's worry: the couriers who move are **taken from adjacent zones**,
so the local win is partly a transfer, not new supply. Finance's worry: the bonus is paid
on **every** delivered order in the zone-block, including the ones that would have happened
anyway. The experiment is designed to answer all three.

---

## 2. Company profile

| | |
|---|---|
| Name | **SwiftBite Delivery** (legal entity *SwiftBite Tecnologia e Logística Ltda.*) |
| Headquarters | Belo Horizonte (MG), Brazil |
| Business | On-demand food-delivery marketplace — consumers ↔ restaurants ↔ independent couriers |
| Footprint in scope | **One metro, 12 delivery zones.** ~6,000 active restaurants. |
| Age | Founded 2022; this project's 20-month window is 2025-01 → 2026-08 (a mature, steady operation, not a launch ramp). |
| Currency | **BRL only.** Single-country, single-city; no FX in scope. |
| Reporting calendar | Calendar months for finance; **operations reporting is by day and by hour-block**; the experiment is analysed by zone-day. |
| Scale at window end | ~**3,500** couriers active over the window (~**900** in a typical week); ~**15,000 orders/day** metro-wide (~**7.5M** orders across the window); average basket ~**R$ 62**; average delivery fee ~**R$ 8.50**; SwiftBite take rate ~**22%** of basket + fee share. |

### Marketplace positioning
SwiftBite is the **#2 player** in this metro behind a national incumbent. It competes on
**ETA reliability** and **courier earnings** (couriers multi-app; the platform with better
peak earnings gets their hours). Restaurant commission is not a lever in this project —
it is treated as a fixed input to unit economics.

---

## 3. The two sides of the marketplace

**PT.** Os dois lados nunca devem ser misturados na análise: **oferta** = horas de
entregador disponíveis; **demanda** = pedidos (ou horas-entrega demandadas). Liquidez é a
razão entre os dois num dado par zona-hora.

### 3.1 Supply — couriers

| Concept | Definition |
|---|---|
| **Courier session** | A continuous logged-in period in the courier app (login → logout). |
| **Active minutes** | Session minutes assigned to an offer or en route (offer→accept→pickup→dropoff). |
| **Idle minutes** | Session minutes logged in but **not** on a run and **not** in cooldown. High idle = supply present but unproductive (often in the wrong zone). |
| **Available courier-hours** (a zone-hour) | Σ session-hours whose position is in the zone during the hour, net of cooldown. The **supply** quantity. |
| **Active courier** | ≥ 1 completed delivery in the trailing 7 days (weekly cut) / 28 days (monthly cut). |
| **Courier home zone** | Modal drop-off zone over the trailing 28 days — used only for descriptive supply geography, never for assignment. |
| **Multi-apping** | Assumed but not observed directly; shows up as couriers going idle-then-logout during a SwiftBite lull. A stated limitation. |

### 3.2 Demand — orders

| Concept | Definition |
|---|---|
| **Order** | A placed consumer order with a delivery address → **delivery zone** and a **time block**. |
| **Demanded delivery-hours** (a zone-hour) | Orders in the zone-hour × the period's average service time (pickup + drive + drop). The **demand** quantity, in the same unit as supply. |
| **Order outcome** | `delivered` · `cancelled_customer` · `cancelled_courier` · `cancelled_no_courier` · `cancelled_restaurant`. |
| **ETA** | Order-placed → delivered wall-clock minutes. Reported **p50** (typical) and **p90** (the customer-pain tail). |
| **Assignment latency** | Order-ready → courier-assigned seconds. |

### 3.3 Liquidity — where the two meet

| Metric | Definition | Read |
|---|---|---|
| **Liquidity ratio** | available courier-hours ÷ demanded delivery-hours, per **zone × hour** | < 1 → supply-short; the marketplace cannot clear without ETA blowing out or orders dropping |
| **Fulfillment rate** | orders delivered ÷ orders placed, same zone-hour | the headline outcome — and the experiment's **primary metric** |
| **Idle-courier ratio** | idle courier-hours ÷ available courier-hours, per zone × hour | high **and** low fulfillment in a *neighbouring* zone at the same time = a **spatial mismatch** the incentive is meant to fix |
| **Unmet demand** | placed − delivered, per zone-hour | the volume the incentive is trying to recover |

---

## 4. Zones & geography

**PT.** 12 zonas cobrindo a cidade; cada zona tem vizinhas (grafo de adjacência) e um
**tier de estresse de oferta** (curta / equilibrada / longa) fixado pelo comportamento
dos meses 1–15. O tier é usado para estratificar o experimento e para a análise de
heterogeneidade. A canibalização é justamente supor que o incentivo numa zona rouba
oferta das **zonas adjacentes**.

| Property | Detail |
|---|---|
| **Zone count** | 12, tiling the metro; each is a group of neighbourhoods with one dispatch centroid. |
| **Adjacency graph** | Fixed in the geo reference; each zone has 2–5 neighbours. Cannibalisation is defined **against adjacent zones**. |
| **Baseline supply-stress tier** | Each zone tagged **short / balanced / long** from months 1–15 liquidity (4 short · 5 balanced · 3 long, indicative). Fixed pre-experiment; used for stratification and heterogeneity. |
| **Zone boundary redraw** | Two zone polygons were re-cut at window-month 9 (Sep 2025) — a deliberate data-quality issue: the **current** zone map disagrees with the **as-booked** zone on older orders (§ data-quality doc). |
| **Trip geography** | "short" zones have longer average trips and lower return-load probability — the structural reason supply avoids them. |

---

## 5. The zone-hour incentive experiment

### 5.1 Design

**PT.** Unidade de randomização = **zona-dia** (uma zona num dia). Em zona-dia tratado, o
bônus por entrega fica ligado no bloco de pico (18:00–22:00) daquela zona; em controle,
não. Split 50/50, **estratificado por zona e por tier de estresse de oferta**. Nada muda no
meio do dia; sem re-randomização.

| Element | Decision |
|---|---|
| **Unit of randomization** | **Zone-day** — one zone on one calendar date. Secondary analysis at **zone × hour-block**. |
| **Eligible units** | Peak-eligible zone-days: **every zone, every date** in the 10-week window, peak block **18:00–22:00** (the only time the incentive is ever offered). ≈ **840 zone-days** (12 × 70). |
| **Assignment** | **Stratified randomization**: within each **zone** and each **baseline supply-stress tier**, zone-days split **50/50** treated/control, balanced across day-of-week (so treated and control both get their share of Fri/Sat). Assignment fixed at 00:00 local; no mid-day switch; no re-randomization. |
| **Treatment** | A **flat per-delivery bonus** (R$ amount set in `etl/config.py`) for orders **completed in the treated zone during the peak block**, plus an in-app "surge zone" push to couriers within ~2 km. |
| **Control** | No bonus, no push — the normal marketplace. |
| **Blinding** | Couriers see the bonus (it must be visible to work); they do **not** see the experiment. Customers see nothing. |
| **Duration** | 10 weeks, 2026-04-06 → 2026-06-14. Post-window observation to 2026-08-31 for persistence. |

### 5.2 Hypotheses

- **Business hypothesis.** Arming a targeted peak-block bonus in a zone raises **fulfillment
  rate** in that zone-block (more couriers present → fewer no-courier cancellations, lower
  ETA, fewer customer bail-outs), at a **bonus cost per incremental delivered order below
  the contribution margin of a saved order**, and the effect is **largest in
  supply-short zones**. A secondary hypothesis is that some of the gained supply is
  **drawn from adjacent zones** (cannibalisation), so the metro-level net effect is smaller
  than the sum of local effects.
- **Statistical hypothesis (primary).** H₀: fulfillment rate is equal on treated and
  control zone-days over the window. H₁: treated > control. Tested one-sided at α = 0.05
  with **cluster-robust (zone) standard errors**; a two-sided 95% CI on the difference is
  always reported, alongside a **randomization-inference** p-value as a small-N cross-check.

### 5.3 Metrics

| Role | Metric | Definition | Decision rule |
|---|---|---|---|
| **Primary** | **Fulfillment rate** | Orders delivered ÷ orders placed, treated zone-days vs control zone-days, peak block. | Keep the incentive if lift is **positive, significant (α = 0.05, cluster-robust), ≥ the MDE**, **and** guardrail G1 passes. |
| Guardrail **G1** | **Incentive cost per incremental delivered order (BRL)** | Total bonus spend ÷ (incremental delivered orders vs control). | **Ship only if below the contribution margin of a delivered order** (planning value ≈ R$ 9–11). Reported with a CI. |
| Guardrail **G2** | **ETA p50 / p90 (min)** | Placed→delivered minutes, by arm. | Directional; **flag if treated is worse** (should improve or hold). |
| Guardrail **G3** | **Cancellation rate** | Cancelled ÷ placed, split by cause (customer / courier / no-courier). | **Flag if total or no-courier rate is worse** on treated. |
| Guardrail **G4** | **Courier earnings per active hour (BRL)** | Payout incl. bonus ÷ active hours, couriers working the zone-block. | Context + fairness; expected up on treated (that is the mechanism). |
| Guardrail **G5** | **Neighbour-zone spillover (cannibalisation)** | Δ fulfillment rate and Δ idle-courier ratio in **adjacent control zones** on treated zone-days vs non-treated-neighbour zone-days. | **Estimate sign and size**; flag if the metro-level net lift is < X% of the summed local lift. |

### 5.4 Power & minimum detectable effect (zone-day unit)

**PT.** A unidade é **zona-dia**, então o N efetivo é pequeno (~420 por braço) e há
**correlação intra-zona** — o cálculo de poder tem que usar essa unidade, não o número de
pedidos. Erros-padrão com cluster por zona + inferência por randomização.

| Assumption | Value (planning) |
|---|---|
| Analysis unit | **zone-day** (peak block) |
| Zone-days per arm | ≈ **420** (≈ 840 eligible, 50/50) |
| Control fulfillment rate at peak, supply-short zones (planning value) | **≈ 0.86** |
| Between-zone-day SD of fulfillment rate (peak) | ≈ 0.07 (finalized from realized baseline in Phase 10) |
| Intra-zone correlation (ICC) | assumed ≈ 0.15 → **design effect ≈ 1.9** for ~35 days/zone/arm |
| α (two-sided) / power | 0.05 / 0.80 |
| **MDE on fulfillment rate**, all zones pooled | ≈ **+1.3 pp** |
| **MDE within the supply-short tier** (≈ 140 zone-days/arm) | ≈ **+2.2 pp** — the tier the decision hinges on; adequately but not generously powered |
| **MDE within a single zone** | ≈ +4–5 pp — **single-zone effects are directional only** |
| Secondary unit (zone × hour-block) | ~4× the rows, used for the novelty/decay and time-of-peak cut, not for the headline test |

The power calculation is re-run from realized pre-period variance and reproduced in code in
Phase 10; the values above are the planning basis.

### 5.5 Threats to validity the read-out must address

| Threat | How it is handled |
|---|---|
| **Assignment imbalance / SRM** | χ² on treated/control counts overall, per zone, per supply-stress tier and per day-of-week; investigate if p < 0.01. |
| **Covariate imbalance** | Standardized differences on pre-period fulfillment, ETA, order volume, liquidity ratio, weather flag, day-of-week; Love plot. |
| **Spatial spillover / cannibalisation (SUTVA violation)** | This is a *studied effect*, not just a nuisance: G5 estimates it directly by comparing adjacent-control zones on treated vs non-treated-neighbour days. The primary estimate is also reported **excluding** zone-days adjacent to a treated zone, as a bound. |
| **Novelty / courier learning** | Weekly treated-vs-control lift across the 10 weeks; test for a decaying trend (weeks 1–3 vs 8–10); report the **settled** lift. |
| **Weather & events** | Rain and city-event flags as covariates; control zone-days are concurrent so metro-wide shocks difference out, but zone-local rain does not — hence the covariate. |
| **Demand endogeneity** | The bonus could itself change customer behaviour (faster ETA → more orders). Fulfillment rate is a ratio, but order *volume* is also reported by arm so a demand response is visible, not hidden. |
| **Small number of clusters** | 12 zones → cluster-robust SEs are anti-conservative; a **randomization-inference** p-value and a wild-cluster bootstrap are reported alongside. |
| **Multiple comparisons** | One primary metric fixed in advance; 5 guardrails + the tier/zone heterogeneity cut are secondary and CI-reported with a family-wise-error note. |
| **Persistence** | The decision is on the in-window settled lift; the post-window weeks are reported as a persistence signal, not a second test. |

### 5.6 Heterogeneity analysis (required)

Effect on fulfillment rate estimated **within each baseline supply-stress tier**
(short / balanced / long) and **within each zone**, with per-cell CIs and a formal
**arm × tier interaction** test. The prior to test — not assume — is that the effect is
**largest in supply-short zones** (most unmet demand to recover) and **near zero in
supply-long zones** (already clearing; the bonus is pure cost there). The operational
decision — roll the incentive out everywhere, or only to short zones — hinges on this cut
and on G1 computed per tier.

---

## 6. The analytics window — why 20 months

| Anchor | Value |
|---|---|
| Window length | 20 complete months: **month 1 = Jan 2025**, month 20 = Aug 2026 |
| Baseline period | months 1–15 (Jan 2025 – Mar 2026) — defines each zone's supply-stress tier |
| Experiment | window-months 16–18 → **2026-04-06 → 2026-06-14** (10 weeks) |
| Post-window observation | 2026-06-15 → 2026-08-31 (~11 weeks) — persistence |
| Year-over-year | months 1–12 vs a trailing-12 ending at month 20, for the report's trend context only |

**Why 20 months.** Long enough for two full seasonal cycles of the parts that matter
(Carnaval, June festas, school holidays, rainy season) and a stable 15-month baseline
before the experiment; the operation is mature over the whole window, so there is **no
launch-ramp comparability caveat** (unlike AeroVanti). Shorter than VoltEdge's 24 because
there is no multi-year financial trend to establish — the value is in the experiment.

---

## 7. Seasonality & patterns embedded in the data

| Pattern | Where it shows |
|---|---|
| **Weekly** — Fri/Sat dinner peak | Order volume ~3× a weekday lunch; the peak block the experiment targets |
| **Daily** — lunch (11:30–14:00) and dinner (18:00–22:00) double peak | Dinner is longer, more supply-short |
| **Rainy season** (Oct–Mar in the Southeast) | Demand ↑ (people don't go out), courier supply ↓ (fewer want to ride) → the worst liquidity of the year; the experiment's first 2 weeks catch the tail of it |
| **Carnaval** (Feb/Mar) | Multi-day demand collapse then rebound — **outside** the experiment window by design |
| **June festas / school July holidays** | Elevated weekend demand; overlaps the experiment's back half — handled by the concurrent control arm |
| **Payday** (5th & 20th) | Mild order-volume and basket-size lift |
| **Big football matches / shows** | Zone-local demand spikes; flagged as an event covariate |
| **Courier supply drift** | Slow metro-wide decline in couriers/week across 2026 as a competitor raises pay — a backdrop trend, differenced out by the concurrent control |

---

## 8. Stakeholder personas → report pages

**PT.** Três personas, uma pergunta permanente cada — mais a pergunta executiva. As quatro
viram as quatro páginas do relatório.

| # | Persona | Standing question | Page |
|---|---|---|---|
| 1 | **Head of Operations** | Is the marketplace healthy this week, and did the zone-hour incentive earn its cost? | **Executive Overview** |
| 2 | **Marketplace / Liquidity Manager** | Exactly which zones and hours are supply-short, how bad is the ETA and cancellation damage, and where is idle supply sitting while that happens? | **Marketplace Health** |
| 3 | **Growth / Courier Supply Lead** *(and the experimentation partner)* | Is the incentive effect real, significant and safe on the guardrails — including cannibalisation of neighbour zones — or is one zone carrying it? | **Pricing & Incentive Experiment** |
| 4 | **Finance / Unit Economics** | What do couriers earn per hour, how utilised is supply, and how many reais of bonus buy one extra delivered order? | **Courier Economics** |

---

## 9. KPI framework

Benchmark ranges are **directional**, drawn from public delivery-marketplace disclosures and
industry commentary (gig-economy and last-mile studies), adapted to a single-metro #2
player. They set targets; they are not claims about named competitors.

### 9.1 Marketplace health & demand

| KPI | Definition | Benchmark | Target |
|---|---|---|---|
| Orders placed / day | Distinct placed orders | — | on plan |
| **Fulfillment rate %** | Delivered ÷ placed | 95%–99% | ≥ 98% metro; ≥ 95% in every zone-hour |
| **ETA p50 / p90 (min)** | Placed → delivered | p50 28–38 · p90 45–70 | p90 ≤ 55 |
| **Cancellation rate %** | Cancelled ÷ placed | 2%–6% | ≤ 3% |
| — of which **no-courier %** | `cancelled_no_courier` ÷ placed | 0.3%–2% | ≤ 0.5% |
| Assignment latency p90 (s) | Ready → assigned | 60–240 | ≤ 150 |
| Repeat-order rate % (28d) | Customers with ≥ 2 orders in 28d | — | context |

### 9.2 Supply — couriers

| KPI | Definition | Benchmark | Target |
|---|---|---|---|
| Active couriers / week | ≥ 1 delivery in trailing 7d | — | ≥ plan |
| New couriers / month | First delivery in the month | — | ≥ churn |
| **Courier CAC (BRL)** | Acquisition + onboarding-bonus spend ÷ new activated couriers | — | ≤ plan |
| Courier 4-week retention % | Active in week 4 after first delivery | 45%–70% | ≥ 60% |
| **Available courier-hours / zone-hour** | Σ session-hours in the zone-hour (net cooldown) | — | ≥ demanded hours |
| **Idle-courier ratio %** | Idle ÷ available courier-hours | 15%–35% | ≤ 25% (and not concentrated) |
| Deliveries per active hour | Completed deliveries ÷ active hours | 1.6–2.6 | ≥ 2.0 at peak |

### 9.3 Liquidity (zone × hour — the core of page 2)

| KPI | Definition | Benchmark | Target |
|---|---|---|---|
| **Liquidity ratio** | available courier-hours ÷ demanded delivery-hours | ≥ 1.0 | ≥ 1.1 at peak in every zone |
| Supply-short zone-hours % | Share of peak zone-hours with ratio < 1 | — | ≤ 10% |
| **Unmet demand / peak** | placed − delivered, peak blocks | — | minimise |
| Spatial-mismatch index | corr. of (idle ratio in zone A) with (unmet demand in adjacent zone B), same hour | — | monitor; the incentive should reduce it |
| ETA gap (short vs long zones) | ETA p90 short-tier − ETA p90 long-tier | — | narrowing |

### 9.4 Courier economics & unit economics (page 4)

| KPI | Definition | Benchmark | Target |
|---|---|---|---|
| **Courier earnings per active hour (BRL)** | Payout incl. tips & bonus ÷ active hours | R$ 22–34 | ≥ R$ 26 at peak |
| Utilisation % | Active ÷ logged-in minutes | 55%–80% | ≥ 70% at peak |
| Payout per delivery (BRL) | Total payout ÷ deliveries | — | context |
| **Contribution margin per delivered order (BRL)** | Take (commission + fee share) − payout − payment & support cost | R$ 6–14 | ≥ R$ 9 |
| **Incentive spend (BRL)** | Total dynamic-bonus payout | — | ≤ budget |
| **Incentive cost per incremental delivered order (BRL)** | Bonus spend ÷ incremental delivered orders | — | **< contribution margin** (≈ R$ 9–11) |
| Incentive spend as % of courier payout | Bonus ÷ total payout | — | ≤ 8% |
| Supply elasticity to incentive | % change in available courier-hours in a zone-block per R$1 of bonus | — | **quantify** (Phase 10) |

### 9.5 Experiment scorecard (Pricing & Incentive Experiment page)

| KPI | Definition |
|---|---|
| Fulfillment rate by arm (+ lift, cluster-robust CI, p, RI p) | Primary metric, §5.3 |
| Weekly fulfillment lift across the 10 weeks | Novelty / decay diagnostic, §5.5 |
| Balance check (SRM χ² + SMD / Love plot) | Randomization check |
| **Incentive cost per incremental delivered order (+ CI)** | Guardrail G1 — the go/no-go economic test |
| ETA p50 / p90 by arm | Guardrail G2 |
| Cancellation rate by arm and by cause | Guardrail G3 |
| Courier earnings per active hour by arm | Guardrail G4 |
| **Neighbour-zone spillover: Δ fulfillment & Δ idle ratio in adjacent control zones** | Guardrail G5 — cannibalisation |
| Effect by supply-stress tier and by zone (+ arm × tier interaction test) | Heterogeneity, §5.6 |
| Metro-level net lift vs summed local lift | Cannibalisation-adjusted bottom line |

---

## 10. Targets and plan

- The plan is built on the **same basis as the actuals** (same fulfillment, ETA, cancellation
  and contribution-margin definitions).
- **Plan fulfillment rate:** ≥ 98% metro-wide, ≥ 95% in every peak zone-hour.
- **Plan p90 ETA:** ≤ 55 min at peak in every zone.
- **Plan supply-short peak zone-hours:** ≤ 10%.
- **Plan incentive efficiency:** cost per incremental delivered order **below** the
  contribution margin of a delivered order.
- "vs Target" measures exist per KPI; **ETA, cancellation rate, idle ratio, no-courier rate,
  courier CAC and incentive cost per incremental order are scored lower-is-better**.

---

## 11. Multi-currency handling

Out of scope by design. All monetary values are **BRL**. No `*_local` / `*_usd` split, no FX
table, no reporting-currency slicer. Multi-currency was the VoltEdge project's job; repeating
it here would only distract from the marketplace analysis.

---

## 12. Out of scope (explicit)

- A second city, expansion modelling, multi-currency / FX.
- Restaurant-side economics (commission optimisation, menu pricing, prep-time SLAs) beyond
  a fixed input to demand and unit economics.
- Consumer-side pricing experiments (delivery fee, coupons, subscription) — this project's
  intervention is **supply-side only**.
- Dispatch / routing-algorithm design and real-time optimisation.
- A courier-churn or demand-forecast **model**. Phase 10 quantifies supply elasticity and
  the experiment effect; it does not ship a predictive scorecard.
- Fraud (GPS spoofing, incentive gaming, collusion) beyond a noted data-quality tail.
- Weather/traffic modelling — rain and events enter only as covariate flags.
- Real personal data. Every courier, customer, restaurant, order, GPS ping and payout is
  synthetic and seed-generated.
- The **true incentive effect size and the cannibalisation term** — decided in Phase 3,
  detected blind in Phase 10.

---

## 13. Resolved-assumptions log

| # | Decision | Resolution |
|---|---|---|
| A1 | Window length & anchor | 20 months, 2025-01-01 → 2026-08-31; data-gen date 2026-09-10; mature operation throughout (no launch ramp). |
| A2 | Geography | One metro (Belo Horizonte), 12 zones, fixed adjacency graph, one mid-window boundary redraw as a DQ issue. |
| A3 | Baseline supply-stress tier | short / balanced / long, fixed from months 1–15 liquidity; ~4 / 5 / 3 zones. |
| A4 | Two marketplace sides | Supply = available courier-hours; demand = demanded delivery-hours; never conflated. |
| A5 | Active courier | ≥ 1 completed delivery in trailing 7 days (weekly) / 28 days (monthly). |
| A6 | Liquidity ratio | available courier-hours ÷ demanded delivery-hours, per zone × hour. |
| A7 | Primary metric | Fulfillment rate = delivered ÷ placed, zone-day peak block. |
| A8 | ETA | Placed → delivered minutes; p50 and p90 both reported. |
| A9 | Cancellation taxonomy | customer · courier · no-courier · restaurant. |
| A10 | Experiment unit / split | **Zone-day**, 50/50, stratified by zone × supply-stress tier, balanced on day-of-week; peak block 18:00–22:00. |
| A11 | Experiment window | 10 weeks, 2026-04-06 → 2026-06-14 (window-months 16–18); post-window to 2026-08-31. |
| A12 | Treatment | Flat per-delivery bonus (R$, in `etl/config.py`) for peak-block deliveries in the treated zone + in-app surge-zone push. |
| A13 | Primary decision rule | Positive, significant (α = 0.05, cluster-robust), ≥ MDE, **and** guardrail G1 (cost per incremental order) below the delivered-order contribution margin. |
| A14 | Guardrails | G1 incentive cost / incremental order · G2 ETA p50/p90 · G3 cancellation rate by cause · G4 courier earnings / active hour · G5 neighbour-zone spillover. |
| A15 | MDE / power | Computed for the **zone-day** unit (~420/arm), ICC ≈ 0.15, design effect ≈ 1.9; pooled MDE ≈ +1.3 pp, supply-short-tier MDE ≈ +2.2 pp; RI + wild-cluster bootstrap cross-checks. Finalized in Phase 10 from realized variance. |
| A16 | Cannibalisation | A real, modest negative spillover to adjacent control zones baked into the data in Phase 3; Phase 10 estimates its sign and size and reports a cannibalisation-adjusted metro net lift. |
| A17 | Required diagnostics | SRM/balance, covariate Love plot, novelty decay, tier & zone heterogeneity + interaction test, spillover estimate, persistence. |
| A18 | Currency | BRL only; no FX in scope. |
| A19 | Seasonality | Rainy-season and June-festas overlap the window edges; Carnaval deliberately excluded; concurrent control arm handles metro-wide shocks. |
| A20 | True treatment effect | Deliberately **not** decided here; set in ETL (Phase 3), detected blind in Phase 10. |

---

*End of Phase 1 deliverable.*
