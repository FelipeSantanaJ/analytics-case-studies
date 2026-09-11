# AeroVanti SkyPoints — Redemption & Retention Analysis

A data / BI portfolio project: diagnose why SkyPoints (AeroVanti's airline loyalty
program) members hoard miles instead of redeeming them, and read out the
**Flash Redemption** A/B test to decide on full rollout.

> Fictional company and synthetic data. Fully reproducible from a single random seed.

📄 [Visual case study (PDF)](portfolio/AeroVanti-SkyPoints-case-study.pdf) — 7-page carousel summary.

## Priority

1. **Data analysis + A/B test** (`data_analysis/`) — the primary deliverable.
2. Power BI report (`powerbi/`) — a lighter, 4-page secondary deliverable.

## The question

SkyPoints members accumulate miles but rarely redeem: ~40% of issued points sit unused
as breakage, and members who don't redeem within 12 months lapse at a much higher rate.
The loyalty team piloted **Flash Redemption** (lower minimum redemption threshold +
more low-cost reward options) as a randomized, member-level 50/50 A/B test on ~15,000
active members over 12 weeks. Does it work, is it safe on the guardrails, and should it
roll out to everyone?

## Scope at a glance

| | |
|---|---|
| Market | Brazil only, BRL only |
| Window | 24 months, 2024-09-01 → 2026-08-31 |
| Experiment | 12 weeks, 2026-03-02 → 2026-05-24 (program months 19–21) |
| Program size | ~120k enrolled members, ~65k active |
| Primary metric | Redemption rate (share redeeming ≥1 in the window) |
| Guardrails | Revenue / member, point-liability cost / member, lapse rate, avg redemption value |

## Layout

```
docs/            business context → architecture → data dictionary → model → DAX → DQ → walkthrough
etl/             config + pipeline (raw → staging → curated) + hard dq_checks
data/            raw / staging / curated (CSV + Parquet) / quality
data_analysis/   sql/  python/  findings/  parity/  deliverables/   ← primary deliverable
powerbi/         semantic model as code, lean theme, build_report.sh, 4-page report
assets/          logo + page-background generators
portfolio/       gallery images (diagram + screenshot sources)
```

See [docs/00_scope.md](docs/00_scope.md) for the full locked scope.

## Status

- [x] Phase 0 — Scope & scaffold
- [x] Phase 1 — Company story & KPI framework
- [x] Phase 2 — Data architecture
- [x] Phase 3 — ETL pipeline  (all DQ checks pass; curated star + experiment tables built)
- [x] Phase 4 — Data documentation  (03/04/05/08)
- [x] Phase 5 — Visual identity
- [x] Phase 6 — Semantic model as code  (TMDL, 21 tables)
- [x] Phase 7 — DAX measures  (62 measures → docs/06)
- [x] Phase 8 — Report build  (4 pages, pbir validate passes)
- [x] Phase 9 — Build log  (docs/walkthrough.md)
- [x] Phase 10 — Data analysis  ← PRIMARY  (8 analyses, dual-track, board summary + deep dive)
- [x] Phase 11 — Portfolio assets  (5 gallery images)
- [x] Phase 12 — Docs bundle  (docs/*.pdf — full 2.2 MB + summary 0.7 MB)

## Result

Flash Redemption lifts the 12-week redemption rate **+2.7 pp pooled / +3.2 pp re-weighted**
(p ≈ 2×10⁻⁶), concentrated in **Blue + Silver** (arm×tier interaction p = 0.0007); ≈ half
is a launch bump (durable ≈ +1.5 pp). Guardrails benign except redemptions get shallower.
**Roll out to Blue + Silver.** See `data_analysis/deliverables/`.
