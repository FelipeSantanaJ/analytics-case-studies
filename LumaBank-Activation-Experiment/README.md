# LumaBank — New-User Activation & the Onboarding Experiment That Broke Mid-Flight

A data / BI portfolio project: read out a neobank's **onboarding
redesign A/B test** — except the test **breaks in production on day 11**, when an
unrelated mobile app deploy corrupts the experiment's randomization. The project is the
incident: catching it with continuous **SRM monitoring**, diagnosing the root cause,
choosing between three imperfect fixes under deadline, re-planning the statistics, and
re-running clean.

> Fictional company and synthetic data, fully reproducible from a single random seed.

📄 [Visual case study (PDF)](portfolio/LumaBank-Activation-case-study.pdf) — 7-page carousel summary.
> Every deliverable also explains each step in Portuguese.

## Priority

1. **Data analysis + the onboarding experiment** (`data_analysis/`) — the primary deliverable.
2. Power BI report (`powerbi/`) — a lighter, 4-page secondary deliverable.

## The story

LumaBank (a Brazilian neobank — digital account + card) redesigned onboarding: fewer
steps, and the identity-document upload **deferred to after** account creation. Launched
as a **user-level 50/50 A/B test**, primary metric **Day-7 Activation** (account created
**and** first transaction within 7 days), planned for 6 weeks.

Around **day 11**, the daily **sample-ratio-mismatch (SRM)** check fires: the arms are no
longer 50/50, and the drift started on the day of a **mobile app deploy**. The deploy
reset the on-device variant cache, which (1) **contaminated** users already in the test —
some switched arms mid-journey — and (2) pushed post-deploy signups into a **fallback
that assigns by region/timezone**, not at random. The read-out becomes: detect →
diagnose → decide (truncate / drop contaminated / restart) → re-plan power → re-run.

## Scope at a glance

| | |
|---|---|
| Domain | Brazilian neobank (digital account + card), BRL only |
| Window | 21 months, 2025-01-01 → 2026-09-30 |
| Original experiment | 6 weeks planned, 2026-07-06 → 2026-08-16 — terminated on day 11 |
| The break | Mobile deploy 2026-07-16 resets the variant cache; hotfix 2026-07-22 |
| Re-run | 4 weeks, 2026-08-24 → 2026-09-20, bug fixed, **power/MDE recomputed** |
| Unit of randomization | **User**, 50/50, feature-flag hash |
| Scale | ~130k signups over the window · ~13.5k in the original test · ~9k in the re-run |
| Primary metric | Day-7 Activation rate |
| Guardrails | KYC rejection rate · flagged-fraud rate (both non-negotiable) · onboarding support tickets / 1k signups |

## Layout

```
docs/            business context & KPIs (+ SRM runbook) → architecture → data dictionary →
                 ETL → model → DAX → visual identity → report structure → walkthrough →
                 docs bundle (PDF)
etl/             config (seed, true effect, bug magnitudes) + pipeline (raw → staging →
                 curated) + hard dq_checks (incl. an SRM data-quality check)
data/            raw / staging / curated (CSV + Parquet) / quality
data_analysis/   sql/  python/  findings/  parity/  deliverables/   ← primary deliverable
powerbi/         semantic model as code, theme, build script, 4-page report
assets/          logo + page-background generators
portfolio/       gallery images
```

See [docs/00_scope.md](docs/00_scope.md) for the full locked scope.

## Status

- [x] Phase 0 — Scope & scaffold
- [x] Phase 1 — Business context, KPIs & SRM monitoring runbook
- [x] Phase 2 — Data architecture
- [x] Phase 3 — ETL pipeline (the break, baked in deterministically)
- [x] Phase 4 — Data documentation
- [x] Phase 5 — Visual identity
- [x] Phase 6 — Semantic model as code (TMDL)
- [x] Phase 7 — DAX measures
- [x] Phase 8 — Report build (4 pages)
- [x] Phase 9 — Build log
- [x] Phase 10 — Data analysis  ← PRIMARY (5-block investigation narrative)
- [x] Phase 11 — Portfolio assets (5 gallery images)
- [x] Phase 12 — Docs bundle (`docs/*.pdf` — full 2.4 MB + summary 0.9 MB)

## Result

The redesigned onboarding **works**: on the clean re-run, Day-7 Activation lifts
**+4.58 pp** (95% CI [+2.55, +6.62], p ≈ 1.0×10⁻⁵), against a recomputed MDE of 2.92 pp.
It is not an unconditional pass — the KYC-rejection guardrail clears non-inferiority, but
the flagged-fraud guardrail's non-inferiority is **not established** at this sample size
(95% upper bound +0.89 pp vs a +0.5 pp margin). **Recommendation: a monitored rollout with
a fraud circuit-breaker**, not an unconditional launch. Getting there required catching a
real production bug mid-experiment (SRM ALERT 2 days after an unrelated mobile deploy),
diagnosing a two-part failure (contamination + a region-biased fallback), rejecting two
faster but under-powered fixes, and re-running clean with power recomputed for the smaller,
deadline-capped sample. See `data_analysis/deliverables/` for the full read-out.
