# data_analysis/ — Phase 10 (primary deliverable)

Dual-track (pandas + DuckDB) analysis of the AeroVanti SkyPoints dataset. The headline is
the **Flash Redemption A/B test read-out**; findings 07–08 give the program-health context.

- Full method, analysis surface & docs reading order: [`00_START_HERE.md`](00_START_HERE.md)
- Run everything + confirm SQL/Python parity: `python parity/run_all.py`
- Standalone SQL track: `sql/*.sql` (`duckdb -c ".read data_analysis/sql/_prelude.sql"` first)
- Findings (one per business problem): [`findings/`](findings/)
- **Deliverables:**
  - [`deliverables/board_summary.pdf`](deliverables/board_summary.pdf) / `.html` — decision-first
  - [`deliverables/deep_dive.pdf`](deliverables/deep_dive.pdf) / `.html` — rendered from
    [`deep_dive_00_index.md`](deliverables/deep_dive_00_index.md) →
    `deep_dive_A_ab_test_readout.md` + `deep_dive_B_program_health.md`

## Result in one line

Flash Redemption lifts the 12-week redemption rate by **+2.7 pp pooled / +3.2 pp
re-weighted** (p ≈ 2×10⁻⁶), concentrated in **Blue + Silver** (arm×tier interaction
p = 0.0007), with **≈ half the headline a launch bump** that decays (durable ≈ +1.5 pp).
Guardrails: disengagement −2.0 pp (good), revenue unharmed but non-inferiority not proven,
redemptions **shallower** (−R$19/redeemer). **Roll out to Blue + Silver; hold Gold/Platinum.**
