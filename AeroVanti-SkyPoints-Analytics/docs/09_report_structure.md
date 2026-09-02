# AeroVanti SkyPoints — Report Structure

**Document status:** Phase 8 deliverable. The Power BI report is the **secondary**
deliverable (Phase-0 decision) — 4 pages, lean formatting. One command rebuilds it:

```
cd powerbi && bash build_report.sh      # SKP_ALLOW_DESKTOP=1 if Desktop has another report open
```

Pipeline: `gen_logo.py` → `gen_semantic_model.py` (+ `pbi_measures.py`) →
`gen_dax_doc.py` → `gen_report_visuals.py` (emits `_report_layout.json`) →
`_drive_pbir.py` (drives `pbir`). Output: `powerbi/AeroVantiSkyPoints.pbip` +
`.Report` + `.SemanticModel`. `pbir validate --all` passes (cosmetic overlap /
undersize warnings only — the KPI frame deliberately sits behind the cards).

**First open in Power BI Desktop:** Transform data → set `pDataFolder` to
`data/curated` → Close & Apply · View ▸ Themes ▸ Browse → `powerbi/theme/theme.json`
· Model view → mark `dim_date` as a date table (`date`).

---

## Semantic model

19 imported curated tables + `dim_month` (month spine) + `Funnel Stage` +
`_Measures` (62 measures). Relationships per `docs/05_data_model.md`: day-grain
facts → `dim_date[date_key]`; month-grain facts → `dim_month[month_key]`; the
member hub → `dim_member`; the three experiment facts → `dim_experiment_arm` /
`dim_experiment_stratum`. Auto date/time off; implicit measures discouraged.

---

## The four pages

| # | Page | Question | KPI row (6 cards) | Content |
|---|---|---|---|---|
| 1 | **Executive Summary** | Program health, and did Flash Redemption work? | Active Members · Quarterly Redemption Rate (vs target) · Burn/Earn Ratio · Point Liability (adj) · Flash Redemption Lift · Engagement Lapse Rate | SkyPoints issued vs redeemed (line) · `Exec Insight` narrative card · effect-by-tier bar · liability trajectory (line) |
| 2 | **Member Tiers & Value** | Where is value concentrated, how big is the breakage liability? | Members · Active Rate · Elite Share · Revenue/Active Member · Card Penetration · Avg Points Balance | Active members by tier · revenue per member by tier · issued by earn source · tier upgrades vs downgrades · liability gross vs breakage-adjusted |
| 3 | **A/B Test Results** | Is the effect real, safe on guardrails, consistent? | Subjects · Control Rate · Treatment Rate · Lift (pp) · Significance · SRM (treatment share) | Redemption rate by arm × tier · treatment effect by tier (heterogeneity) · weekly redeemers by arm (novelty check) · guardrail table by arm |
| 4 | **Redemption & Engagement Funnel** | Where do members fall out, and who is about to lapse? | Ever-Redeemed Share · Quarterly Redemption Rate (vs target) · Redeeming Members · Account Lapse Rate · Engagement Lapse Rate · Reactivations | redemption funnel · redeemed by reward category · redemption rate vs plan (line) · engagement lapse rate by tier |

Slicers on every page: **Analysis period** (`dim_month[month_name]`), **Experiment
arm**, **Tier stratum**. KPI deltas are green > 0 / red ≤ 0, inverted for the
lower-is-better cards (breakage, lapse, liability, avg balance).

---

## Known lite-scope gaps (not polished)

- Visual overlap / undersize warnings from `pbir validate` — the generated layout
  stacks the KPI frame behind the cards; z-order is not pinned per visual.
- No screenshot-verification loop (needs a live Desktop session).
- Theme is applied manually on first open (`pbir` cannot apply an arbitrary theme
  file from the CLI in this version).
- `Exec Insight` is a dynamic text measure (no Smart Narrative visual).
