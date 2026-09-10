# Voxa+ — Subscriber Churn: Root-Cause Diagnosis

*Analyst deep-dive · prepared for the leadership team · all figures dual-computed in
DuckDB SQL and pandas with a parity check on every result
(`../parity/parity_report.md` — 14/14 pass).*

---

## 0. The question and the answer

**Question.** Gross monthly subscriber churn nearly doubled starting at window-month 34
(Jun 2026) and has stayed elevated. What caused it?

**Answer.** Three factors that overlapped in time. None explains the spike on its own.

| | Factor | Role | Markets |
|---|---|---|---|
| **1** | An app **"v3" connected-TV playback regression** (window-month 32) | acute trigger, biggest contributor | all; weakest in the US |
| **2** | The **Brazil Standard/Premium price increase** (window-month 32), landing on an already-disengaged base | amplifier | Brazil only |
| **3** | A **months-old Mexico cohort-quality drag** (newer Mexican subscribers retain ~8 pp worse) | pre-existing drain | Mexico only |

Payments and involuntary churn were tested and are **not** involved (`§6`).

---

## 1. The spike — size, persistence, shape  *(findings F01, F02)*

Gross monthly churn stepped from a **4.1 %** pre-shift baseline (window-months 25–33) to
**6.8 %** across the three elevated months — a **1.66×** increase, and **90 % of it is
voluntary**. It has not receded: the three months read 6.85 %, 6.58 %, 7.02 %.

Splitting by market shows the company-wide number is a composite of three different shapes:

| Market | Pre-shift | Peak | Behaviour |
|---|---|---|---|
| **Brazil** | 3.4 % | 7.0 % | flat, then a clean **+3.0 pp step** at window-month 34 — acute |
| **Mexico** | 5.4 % | 8.1 % | **drifting up from ~window-month 29** (+0.6 pp), then a further step — a problem that got worse |
| **United States** | 4.1 % | 4.4 % | essentially unchanged — the control |

A US that barely moves already rules out any explanation that would hit every market
equally.

---

## 2. Who is leaving, and why now  *(findings F03, F04)*

**The lift is broad, not narrow.** Peak-vs-baseline churn is up by a strikingly even
~+2.7 pp across almost every tenure band, plan tier and acquisition channel. Two exceptions
carry information:

- **Annual plans lifted only +1.9 pp** (vs +2.7 pp monthly) — locked-in subscribers were
  partly shielded.
- **Long-tenure subscribers (25+ months) were hit as hard as brand-new ones** (+3.2 pp) —
  a cause confined to weak new cohorts could not do that.

A single narrow cause does not produce an even cross-segment lift. This is the first
quantitative sign of **multiple overlapping factors**.

**The extra churn is engagement-led.** For subscribers who cancelled during the elevated
months, streamed hours were already sliding beforehand — ~37 h two months out, ~36 h the
month before — whereas pre-shift churners left from a flat ~43 h. Value erodes first, the
cancellation follows. That points at what suppressed viewing just before the spike (§3),
and it explains why a price change bites harder now (§4): people were already getting less.

---

## 3. Factor 1 — the connected-TV app regression  *(finding F05)*

The Voxa+ "v3" app shipped device-family by device-family, reaching connected-TV last.
Connected-TV streaming quality is flat through window-month 31, then:

| window-month | 31 | **32** | 33–36 |
|---|---|---|---|
| CTV video-start-failure rate | 1.1 % | **3.0 %** | ~3.4 % |
| CTV playback-error rate | 0.6 % | **1.4 %** | ~1.6 % |

Mobile and web are unchanged throughout. The connected-TV rates **triple at window-month
32 — one month before the churn step.**

The churn consequence is specific to the affected subscribers:

| | Pre-shift | Peak |
|---|---|---|
| Not CTV-heavy | 4.1 % | 5.6 % |
| **CTV-heavy** (primary device = smart-TV / stick / console) | 4.1 % | **8.4 %** |

Before the shift the two groups churned **identically**. After the CTV rollout, CTV-heavy
churn **doubled**. The one-month lag between the quality drop and the churn step is a
value → decision delay of roughly one billing cycle. This is the **acute trigger and the
largest single contributor**, and — because it touches every market — it is why the
company-wide number looks global.

---

## 4. Factor 2 — the Brazil price increase, and why it bit  *(finding F06)*

Brazil raised Standard and Premium list prices at window-month 32, migrating existing
members on their next renewal. Split Brazil Std/Prem subscribers by whether they were
engaged or disengaged (below the healthy-engagement line) in the month:

| Brazil Std/Prem | Churn before hike | Churn after hike | Lift |
|---|---|---|---|
| **Engaged** | ~0 % | ~0 % | **≈ 0 pp** |
| **Disengaged** | 23.9 % | **42.2 %** | **+18.3 pp** |

The price increase had **no measurable effect on engaged subscribers** and a very large
effect on **already-disengaged** ones. Because Factor 1 pushed a wave of Brazil
subscribers into the disengaged bucket in window-months 32–33, the migration then landed
on a larger disengaged pool than it otherwise would have. Price alone did not move the
base; **price × prior disengagement produced the Brazil step**. Brazil-only.

---

## 5. Factor 3 — Mexico's pre-existing cohort-quality drag  *(finding F07)*

Month-3 retention by market and cohort era:

| Market | Pre-shift cohorts | Post-shift cohorts (acquired m24–30) |
|---|---|---|
| Brazil | ~82.8 % | ~80 % (−3 pp) |
| **Mexico** | ~81.8 % | **~73 % (−8–9 pp)** |
| United States | ~82.8 % | ~81 % (−2 pp) |

Every market's newer cohorts retain a little worse; **Mexico's are ~8–9 pp worse at
month 3** — three times the drop elsewhere. It is **not channel-specific** (within
post-shift Mexico, low-quality-channel cohorts retain about the same as the rest), so this
is not "the channel mix kept degrading" — it is **Mexican conditions for newly-acquired
subscribers deteriorating across the board** from ~window-month 24. This drag was already
lifting Mexican churn ~0.6 pp before the visible spike and is still underneath it.

---

## 6. What it is *not* — payments  *(finding F08)*

| Market | First-attempt payment-failure rate (pre → peak) | Dunning recovery (pre → peak) | Involuntary churn (pre → peak) |
|---|---|---|---|
| Brazil | 7.6 % → 7.7 % | 51 % → 52 % | 0.43 % → 0.41 % |
| Mexico | 18.8 % → 18.2 % | 37 % → 37 % | 1.25 % → 1.30 % |
| United States | 8.0 % → 7.8 % | 58 % → 57 % | 0.31 % → 0.32 % |

Nothing moved. Combined with the 90 % voluntary share (§1), payments are **ruled out** as a
driver of the spike. Mexico's payment economics are structurally poor but that is a
standing cost, not a new one.

---

## 7. Impact, and the decomposition  *(findings F09, F10)*

**Impact.** The churn step cuts the implied average subscriber lifetime from **~24 months
to ~15** — a **~40 % reduction in lifetime value**. In the three elevated months, **~5,400
subscribers left over and above the pre-shift rate**; at ~$7.5 ARPU that is on the order of
**$0.5–0.6 M of lifetime recurring revenue already forgone**, compounding monthly. A 40 %
lower LTV also cuts the allowable CAC by ~40 %, so the growth plan no longer pencils.

**Decomposition.** Tag every peak-month voluntary churn with the three factor flags:

| Market | Peak voluntary churn | F1 (CTV) | F2 (price×diseng) | F3 (low-q young) | **none** |
|---|---|---|---|---|---|
| Brazil | 6,629 | 54 % | **63 %** | 12 % | **15 %** |
| Mexico | 4,017 | 53 % | 0 % | **23 %** | 36 % |
| United States | 1,597 | 52 % | 0 % | 20 % | 39 % |

In Brazil, **85 % of the elevated churn carries Factor 1 or Factor 2**. In Mexico, ~64 %
carries Factor 1 or Factor 3. The US "39 % none" is just its unchanged ~4 % baseline —
the control. The flags overlap, so these are *coverage*, not an independent split; the
causal weight sits in the **rate** comparisons (§3–§5), which are clean.

---

## 8. Recommendations (priority order)

1. **Fix the connected-TV player (Sev-1).** Roll back / hotfix v3 on smart-TV and
   streaming-stick; verify video-start-failure returns to ~1 %. Save-campaign CTV-heavy
   subscribers whose viewing fell after window-month 32.
2. **Pause the Brazil price migration for low-engagement Standard/Premium subscribers.**
   Offer a retention path (hold price / downgrade / pause); re-test elasticity after the
   CTV fix.
3. **Audit Mexico acquisition and onboarding since mid-2025.** Cap spend on the weakest
   sources until month-3 retention recovers toward ~82 %.
4. **Instrument for next time.** Connected-TV QoE on the executive dashboard, a leading
   "engagement health" trend, and price-change elasticity by engagement band.

---

### How this was produced

`python data_analysis/run_analysis.py` runs all ten questions twice — DuckDB SQL over the
curated Parquet and pandas over the same files — and asserts the two agree within tolerance
before any number is used. SQL is saved under `data_analysis/sql/`, agreed results under
`data_analysis/results/`, and the parity log at `data_analysis/parity/parity_report.md`.
Per-problem method, evidence and limitations are in `data_analysis/findings/F01`–`F10`.
