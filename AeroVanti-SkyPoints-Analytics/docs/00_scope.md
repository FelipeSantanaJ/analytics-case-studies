# 00 — Scope & Scaffold (Phase 0)

**Project:** AeroVanti SkyPoints — Redemption & Retention Analysis
**Fictional company:** AeroVanti — a Brazilian domestic airline.
**Loyalty program:** SkyPoints (miles-based earn/burn, tiered).
**Date locked:** 2026-09-02

---

## 1. Premise

SkyPoints members accumulate miles but rarely redeem them: roughly 40% of issued
points sit unused as **breakage**, and members who do not redeem within 12 months
**lapse** at a materially higher rate. The loyalty team piloted **Flash Redemption** —
a lower minimum redemption threshold plus more low-cost reward options — as a
**randomized A/B test** on a subset of active members. This project builds the
read-out to decide on full rollout, plus a lighter dashboard on program health.

---

## 2. Locked scope decisions

| Dimension | Decision |
|---|---|
| Deliverable language | English (all docs, code, reports). Working chat in Portuguese. |
| Priority | **Phase 10 (data analysis + A/B test) is the primary deliverable.** Power BI track is secondary and scoped down. |
| PBI environment | `.pbip` / PBIR, built from code (`gen_semantic_model.py`), theme via `pbir` CLI. |
| Curated storage | CSV **and** Parquet in `data/curated/`. |
| Market / currency | Brazil only, BRL only. No multi-currency, no expansion modelling. |
| Data window | **24 months: 2024-09-01 → 2026-08-31.** CY = last 12 months (2025-09 → 2026-08), PY = prior 12. |
| Experiment window | **12 weeks in program months 19–21: 2026-03-02 → 2026-05-24.** Post-period Jun–Aug 2026 reserved for lapse/retention outcomes. |
| ETL / data-quality depth | **Reduced.** ~5–6 simulated source systems, ~6 core data-quality issue classes (see §5). |
| Program scale | **~120,000 enrolled members**, ~65,000 active (earn or flight in last 12 months). |
| Experiment scale | **~15,000 members in the pilot, 50/50 split (~7,500 per arm).** |
| Power BI track | **Playbook "lite":** semantic model as code + lean `theme.json` + build script, **4 pages**, few formatting passes. |

---

## 3. Phase-1 report pages (lean, 4 pages)

1. **Executive Summary** — program health + the A/B test headline result.
2. **Member Tiers & Value** — points earned / redeemed, tier movement, breakage.
3. **A/B Test Results** — Flash Redemption experiment, dedicated page.
4. **Redemption & Engagement Funnel** — catalog behaviour and lapse risk.

---

## 4. A/B test design (locked at Phase 0, detailed in Phase 1)

| Element | Decision |
|---|---|
| Unit of randomization | **Member.** |
| Split | **50/50**, treatment vs control. |
| Eligibility | Members with an **earn event or a flight in the trailing 12 months** and **not lapsed** as of the start of month 19 (2026-03-01). |
| Assignment | **Stratified by tier** (Blue / Silver / Gold / Platinum) so arms are balanced on tier. |
| Treatment | Flash Redemption: minimum redemption threshold lowered (e.g. 10,000 → 3,500 pts) **and** an expanded low-cost reward catalog (gift cards, seat selection, lounge passes, partner vouchers). |
| Control | Existing thresholds and catalog. |
| Primary metric | **Redemption rate** = share of members with ≥1 redemption during the 12-week window. |
| Guardrail metrics | Revenue per member (BRL), point-liability cost per member (BRL), churn / lapse rate (post-window), average redemption value. |
| Analyses required | SRM / randomization check; stated hypothesis + MDE / power rationale; significance test with effect size + CI; novelty-effect check across the window; heterogeneity by tier (top vs entry). |

**Underlying true effect:** deliberately decided during Phase 3 (ETL) and baked into
the generated data with plausible noise, novelty decay, and tier heterogeneity. The
true value lives only in `etl/config.py`; the Phase 10 analysis must detect and
quantify it as if blind.

---

## 5. Data-quality issues to inject (reduced set)

1. Multiple date formats + Excel serial numbers across source exports.
2. Money as strings (`"R$ 1.234,56"`, `"1234.56"`, thousands separators).
3. Mixed text encodings / mojibake in member names and city fields.
4. Duplicate rows in earn/redemption event exports.
5. Missing master rows (member dimension rows absent for some events → referential gap).
6. Snapshot-vs-ledger drift: a tier-status snapshot table that disagrees with the
   tier-movement ledger.

---

## 6. Out of scope (explicit)

- Multi-currency, FX, international routes, codeshare partners' own accrual.
- Fraud detection, points-trading abuse.
- Real-time / streaming data; all batch.
- Marketing-channel attribution beyond the experiment.
- Fare pricing / revenue management modelling (revenue is an input, not modelled).
- Mobile-app telemetry / clickstream.

---

## 7. Resolved-assumptions log

| # | Assumption | Resolution |
|---|---|---|
| A1 | "Active member" definition | Earn event or flight in trailing 12 months. |
| A2 | Program size | 120k enrolled; growth curve modelled over the 24 months (Phase 1). |
| A3 | Tiers | 4: Blue (entry), Silver, Gold, Platinum. Qualification by trailing-12m miles or segments (Phase 1). |
| A4 | Point value | ~BRL 0.025 per point redeemed value; liability booked at issuance (Phase 1 to finalize). |
| A5 | Breakage baseline | ~40% of issued points never redeemed (program-to-date). |
| A6 | Lapse definition | No earn and no redemption for 12 consecutive months. |
| A7 | Experiment enrollment | Stratified random by tier, 15k members, 50/50. |
| A8 | Currency formatting in report | pt-BR display acceptable? To confirm in Phase 5 (English portfolio → likely switch display units). |

---

## 8. Folder scaffold (created)

```
AeroVanti-SkyPoints-Analytics/
  docs/            business context, architecture, data dict, model, DAX, DQ, walkthrough
  etl/             config + pipeline (raw → staging → curated) + dq_checks
  data/
    raw/           source-faithful messy exports
    staging/       typed stg_* tables
    curated/       Kimball star, CSV + Parquet
    quality/       dq_report.md and fragments
  powerbi/         semantic model as code, theme, build_report.sh, .Report / .SemanticModel
  assets/          logo + page-background generators
  data_analysis/   sql/ python/ findings/ parity/ deliverables/ outputs/   ← PRIMARY
  portfolio/       gallery images (diagram + screenshot sources)
  README.md
```
