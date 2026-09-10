# F10 — Synthesis: the root cause is a combination of three factors

**Question.** Put `F02`–`F08` together. What actually caused the spike, and can any single
factor account for it?

**Method (both tracks).** Every **voluntary** churn in the three elevated months
(`month_idx` 33–35) tagged with three flags:

- `f1_ctv` — subscriber's primary device is connected-TV (exposed to the `F05` regression);
- `f2_price_diseng` — Brazil, Standard/Premium, and disengaged that month (exposed to the
  `F06` interaction);
- `f3_lowq_young` — acquired through a low-quality channel and ≤ 5 months tenure
  (the `F07` cohort-quality drag).

Share of peak voluntary churn carrying each flag, and the share carrying **none**, by
market. `q10_driver_decomposition`; SQL and pandas agree exactly.

**Evidence** (`results/q10_driver_decomposition.csv`).

| Market | Peak voluntary churn | has F1 (CTV) | has F2 (price×diseng) | has F3 (low-q young) | **has none of the three** |
|---|---|---|---|---|---|
| **Brazil** | 6,629 | 53.8 % | **63.4 %** | 12.0 % | **15.2 %** |
| **Mexico** | 4,017 | 52.6 % | 0 % | **22.8 %** | **36.0 %** |
| **United States** | 1,597 | 51.5 % | 0 % | 19.8 % | 38.6 % |

Read alongside the rate evidence:

- CTV-heavy churn 4.1 % → **8.4 %** vs non-CTV 4.1 % → 5.6 % (`F05`);
- disengaged Brazil Std/Prem churn **+18 pp** after the price hike, engaged **~0** (`F06`);
- Mexican post-shift cohorts **−8–9 pp** M3 retention (`F07`);
- payments and involuntary churn **unchanged** (`F08`).

**Conclusion — the diagnosis.**

> The near-doubling of monthly churn is **not one event**. It is three factors that
> overlapped in time:
>
> 1. **An app "v3" connected-TV playback regression** (window-month 32) — the acute
>    trigger. Video-start failures tripled on smart-TV / streaming-stick; the heaviest-
>    viewing subscribers lost value and churned a month later. Present in every market,
>    weakest in the US. This is the single biggest contributor and the reason the
>    company-wide number looks "global".
> 2. **The Brazil Standard/Premium price increase** (window-month 32) — the amplifier, and
>    **Brazil-only**. It did nothing to engaged subscribers; on subscribers already
>    disengaged — many of them pushed there by Factor 1 — it added ~18 pp of churn. This
>    is why Brazil *steps* rather than drifts.
> 3. **A months-old Mexico cohort-quality drag** — the pre-existing drain. Mexican
>    subscribers acquired since ~mid-2025 retain ~8 pp worse at month 3; this had already
>    lifted Mexican churn ~0.6 pp *before* window-month 33 and is still underneath the
>    spike. This is why Mexico was the highest market and *ramping* before anyone looked.
>
> **No single factor explains it.** Remove Factor 1 and Brazil's step is smaller and the US
> and Mexico barely move; remove Factor 2 and Brazil drifts instead of stepping; remove
> Factor 3 and Mexico looks fine. In Brazil, **85 % of the elevated churn carries Factor 1
> or Factor 2** (only 15 % carries neither); in Mexico, ~64 % carries Factor 1 or Factor 3.
> The US "38 % carries none" is simply its unchanged ~4 % baseline — the US is the control
> that shows the mechanism, not a fourth market with its own problem.

**Limitations.** The three flags overlap (a Brazil CTV-heavy disengaged Std/Prem subscriber
carries F1 and F2), so the shares do not sum to a clean attribution; the decomposition
establishes *coverage* ("almost none of the excess is unexplained"), not independent
percentages. The 52 % F1 share in every market partly reflects the CTV-heavy population
share, which is why the **rate** comparisons in `F05` (equal pre-shift, 8.4 % vs 5.6 % at
peak) carry the causal weight, not the flag share alone. Data is synthetic and seed-
generated (`docs/08`).

**Recommendation (priority order).**

1. **Fix the connected-TV player** (Sev-1). Roll back / hotfix v3 on smart-TV and
   streaming-stick; verify video-start-failure returns to ~1 %. Save-campaign the
   CTV-heavy subscribers whose viewing dropped after window-month 32.
2. **Pause the Brazil price migration for low-engagement Standard/Premium subscribers**;
   give them a retention path (hold price, downgrade, or pause) and re-test elasticity
   after the CTV fix.
3. **Audit Mexico acquisition and onboarding** since mid-2025; cap spend on the weakest
   sources until month-3 retention recovers toward ~82 %.
4. **Instrument** so this is visible next time: connected-TV QoE on the exec dashboard, a
   leading "engagement health" trend (`F04`), and price-change churn elasticity by
   engagement band.
