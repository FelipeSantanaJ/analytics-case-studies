# AeroVanti SkyPoints — Deep Dive (index)

The exhaustive record behind the board summary. Audience: analysts / managers who will act
on it. Every number is computed on **both tracks** (pandas + DuckDB over the same curated
parquet) with a parity assertion; run `python data_analysis/parity/run_all.py` to reproduce.

## The two business problems

| # | Problem | Deep-dive file | Findings |
|---|---|---|---|
| **A** | **Flash Redemption A/B test — should it roll out, and to whom?** | [`deep_dive_A_ab_test_readout.md`](deep_dive_A_ab_test_readout.md) | 01–06 |
| **B** | **Why members hoard points, and what it costs** | [`deep_dive_B_program_health.md`](deep_dive_B_program_health.md) | 07–08 |

Each finding also stands alone under [`../findings/`](../findings/) with its own
context · question · hypothesis · both-track method · evidence · limitations · recommendation.

## Headline

Flash Redemption **works** — it lifts the 12-week redemption rate by **+2.7 pp pooled**
(**+3.2 pp** re-weighted to the member base; p ≈ 2×10⁻⁶) — but the effect is **concentrated
in Blue and Silver** (arm×tier interaction p = 0.0007; nothing measurable for Gold/Platinum),
and **roughly half the headline is a launch bump that decays** (durable ≈ +1.5 pp).
Guardrails: disengagement improves (−2.0 pp, p = 0.001); flight revenue is unharmed but the
test is too small to *prove* non-inferiority; redemptions get **shallower** (−R$19 per
redeeming member). **Recommendation: roll out to Blue + Silver, hold Gold/Platinum, keep a
revenue and a redemption-depth guardrail live.**

## Data & method notes

- Analysis surface: `data/curated/*.parquet` (Kimball star, 18 tables). See
  [`../00_START_HERE.md`](../00_START_HERE.md) and `docs/05_data_model.md`.
- The experiment's true effect is **not** in any doc — it lives only in
  `etl/config.py::FLASH_EFFECT`; this read-out detects it from the data.
- Randomisation used blocked (pair-matched) assignment within tier strata, so the balance
  check passes by construction (finding 02).
- Post-window horizon is ~14 weeks: lapse guardrails are **90-day proxies**, not 12-month
  outcomes.
