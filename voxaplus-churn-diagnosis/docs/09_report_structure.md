# Voxa+ — Report Structure

**Document status:** Phase 8 deliverable.
**Build:** `cd powerbi && bash build_report.sh` (regenerates assets → semantic model →
layout manifest → drives `pbir` to build `VoxaChurnDiagnosis.Report`).
**Layout source of truth:** `powerbi/gen_report_visuals.py` → `powerbi/_report_layout.json`.

The report is **7 pages, one business question each** — the seven stakeholder personas from
`docs/01` §12. Every page carries the same signature furniture, then two content rows on the
3-30-300 gradient (glance → scan → study).

---

## Signature element (every page)

1. **Page-background PNG** (`powerbi/assets/bg_<page>.png`): deep-violet band + **Voxa+**
   wordmark + a quiet "Subscriber Churn Diagnosis" label, an amber hairline, then the page
   **title + the business question** on the light body.
2. **Slicer row** (y ≈ 150): **Analysis period** (`dim_date[year_month]`) left; **Market**
   (`dim_subscriber[market]`) and **Currency** (`Reporting Currency[Currency]`) right.
3. **KPI band**: a white rounded frame `shape` (radius 20, no shadow) behind **six value
   cards**; KPIs with a plan target also carry a small **delta card** beneath, conditionally
   coloured green / red — **inverted for churn, CAC and payback** (lower is better).
4. Report-level filter `dim_date[in_analysis_window] = true` keeps every visual inside the
   36-month window.

Executive page height 900; the other six 720 (`powerbi/assets/_page_heights.json`).

---

## Page 1 — Executive Summary
*How bad is the churn spike, and is it still going?*

**KPIs:** Paid Subscribers (EoP) · Gross Monthly Churn % · Churn vs Baseline (×) ·
Net Adds · MRR · LTV : CAC — deltas vs plan target / YoY.

| Visual | Type | Fields |
|---|---|---|
| Gross monthly churn vs the pre-shift baseline | line | `Gross Monthly Churn %`, `Pre-Shift Baseline Churn %` by `year_month` |
| Read this | card | `Exec Insight` (dynamic narrative) |
| Gross monthly churn by market | clustered column | `Gross Monthly Churn %` by `year_month` × `market` |
| Voluntary vs involuntary churned subscribers | clustered column | `Voluntary / Involuntary Churned Subscribers` by `year_month` |
| Net subscriber adds by month | column | `Net Adds` by `year_month` |

## Page 2 — Subscriber Retention & Cohorts
*Which cohorts, tenures, plans and sources are churning?*

**KPIs:** Gross / Voluntary / Involuntary Churn % · M1 / M6 Retention % · Net MRR Retention %.

| Visual | Type | Fields |
|---|---|---|
| Cohort retention triangle | matrix | `Retention %` — rows `cohort_month`, cols `tenure_months` |
| Gross monthly churn by plan tier | bar | `Gross Monthly Churn %` by `current_tier` |
| Gross monthly churn by tenure (months) | line | `Gross Monthly Churn %` by `tenure_months` |
| Churned subscribers by acquisition channel | column | `Gross Churned Subscribers` by `acquisition_channel` |

## Page 3 — Content & Engagement
*Did viewing drop before people cancelled?*

**KPIs:** Monthly Active Rate % · Hours / Active Sub · % Below Healthy Engagement ·
Titles / Active Sub · % Days on CTV · Streamed Hours.

| Visual | Type | Fields |
|---|---|---|
| Viewing hours per active subscriber | line | `Viewing Hours per Active Sub` by `year_month` |
| Video-start-failure rate by device class | clustered column | `Video Start Failure Rate` by `year_month` × `device_class` |
| Share of subscribers below healthy engagement | line | `% Subs Below Healthy Engagement` by `year_month` |
| Streamed hours by device family | column | `Streamed Hours (by Device)` by `device_family` |

## Page 4 — Pricing & Plans
*Did a price or plan change trigger it?*

**KPIs:** ARPU · Gross Margin % · Gross Monthly Churn % · % Below Healthy Engagement ·
MRR · Net MRR Retention %.

| Visual | Type | Fields |
|---|---|---|
| Gross monthly churn by tier over time | clustered column | `Gross Monthly Churn %` by `year_month` × `current_tier` |
| Plan list-price history | table | `dim_price_history` tier / market / list price |
| ARPU by market | clustered column | `ARPU` by `year_month` × `market` |
| Churned subscribers by tier and month (filter market = BR) | clustered column | `Gross Churned Subscribers` by `year_month` × `current_tier` |

## Page 5 — Acquisition Quality & Channels
*Did the quality of who we acquire shift?*

**KPIs:** New Subscribers · % via Low-Q Channels · % Incentivised · M1 / M3 Retention % ·
Blended CAC.

| Visual | Type | Fields |
|---|---|---|
| New subscribers by acquisition channel | stacked column | `New Subscribers` by `year_month` × `acquisition_channel` |
| M3 retention by acquisition channel | bar | `M3 Retention %` by `acquisition_channel` |
| Share of new subscribers via low-quality channels | line | `% New via Low-Quality Channels` by `year_month` |
| Low-quality-channel share by market | clustered column | `% New via Low-Quality Channels` by `year_month` × `market` |

## Page 6 — Customer Experience, Billing & App Quality
*Payment failures or app problems forcing people out?*

**KPIs:** Payment Failure Rate % · Dunning Recovery % · Involuntary Churn % ·
Crash-Free Rate % · Tickets / 1k Subs · CSAT.

| Visual | Type | Fields |
|---|---|---|
| Crash-free session rate by device class | clustered column | `Crash-Free Session Rate %` by `year_month` × `device_class` |
| Payment failure rate and dunning recovery | line | `Payment Failure Rate %`, `Dunning Recovery Rate %` by `year_month` |
| Authorization rate by payment method | bar | `Authorization Rate %` by `method` |
| Support contacts per 1,000 subscribers by reason | clustered column | `Tickets per 1,000 Subs` by `year_month` × `reason_group` |

## Page 7 — Market Context
*Is this global, or concentrated in one market?*

**KPIs:** Gross Churn (Total / Comparable Base / Expansion) · Net Adds · MRR ·
Subscribers Lost vs Plan (since shift).

| Visual | Type | Fields |
|---|---|---|
| Gross monthly churn by market | clustered column | `Gross Monthly Churn %` by `year_month` × `market` |
| Net adds by market | clustered column | `Net Adds` by `year_month` × `market` |
| Comparable Base vs Expansion churn | clustered column | `Gross Monthly Churn % (Comparable Base / Expansion)` by `year_month` |
| Read this | card | `Exec Insight` |

---

## First open in Power BI Desktop (one time)

The `pbir` build validates structure and every field against the on-disk TMDL model, but it
cannot render. On first open:

1. **Transform data → `pDataFolder`** → point at `…/voxaplus-churn-diagnosis/data/curated`
   → **Close & Apply** (imports ~4 M fact rows; a minute or two).
2. **View → Themes → Browse for themes** → `powerbi/theme/theme.json`.
3. **Model view → `dim_date` → Mark as date table** (column `date`).
4. Walk the pages; iterate layout / formatting with `pbir` + `pbir desktop refresh` +
   `pbir desktop screenshot`. Known open items from `pbir validate --all`: KPI value/delta
   cards are intentionally compact and layered on the frame (`VISUAL_OVERLAP` /
   `VISUAL_UNDERSIZED` warnings are expected); a few pages run ~20 visuals
   (`TOO_MANY_VISUALS`).
