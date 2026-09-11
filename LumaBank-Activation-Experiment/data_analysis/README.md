# data_analysis/ — Phase 10 (primary deliverable)

Dual-track (pandas + DuckDB) investigation of the **LumaBank onboarding activation
experiment** — pre-registered as a clean user-level A/B test, broken mid-flight by a
production bug on day 11, diagnosed, and re-run clean.

- Orientation & method: [`00_START_HERE.md`](00_START_HERE.md)
- Run everything + confirm SQL/Python parity: `python parity/run_all.py`
- Standalone SQL track: `sql/*.sql` (`duckdb -c ".read data_analysis/sql/_prelude.sql"` first)
- Findings (one per investigation block): [`findings/`](findings/)
- **Deliverables:** [`deliverables/board_summary.pdf`](deliverables/board_summary.pdf) /
  `.html` (decision-first) and [`deliverables/deep_dive.pdf`](deliverables/deep_dive.pdf) /
  `.html` (the exhaustive record, with a day-by-day incident timeline), built by
  [`deliverables/build_deliverables.py`](deliverables/build_deliverables.py).

## Result in one line

The redesigned onboarding **lifts Day-7 Activation +4.58 pp** (95% CI [+2.55, +6.62],
p ≈ 1×10⁻⁵) in a clean 4-week re-run — but only after a mobile deploy on day 11 of the
original 6-week test corrupted the randomisation (SRM ALERT fired within 2 days),
contaminating 191 users and biasing post-deploy signups by region through a broken
fallback. Truncating or excluding the contaminated users were both **too underpowered and
too residually biased** to trust; restarting clean, in a shorter window with the power
recomputed from scratch, was the only defensible option. On the clean re-run, the KYC
rejection guardrail holds; the **flagged-fraud guardrail does not establish
non-inferiority** — **recommend a monitored rollout with a fraud circuit-breaker, not an
unconditional launch.**
