# 01 — Anchor: the experiment frame and the naive numbers

**Question.** What is the analysis frame, and what do the raw treated-vs-control
differences look like before any modelling?

**Method (both tracks).** Load `fact_experiment_zone_day` (one row per randomised
zone-day, peak block) joined to `fact_incentive_assignment` (design + frozen
pre-period covariates) and `dim_zone` (baseline supply-stress tier). Group by arm;
group by tier × arm. DuckDB reproduces the headline differences on the same parquet.

**Evidence.**

| | Control (n=420) | Treatment (n=420) |
|---|---|---|
| Fulfillment rate | 95.75% | 97.61% |
| ETA p50 / p90 (min) | 36.8 / 46.2 | 33.9 / 40.1 |
| No-courier cancel rate | 1.16% | 0.80% |
| Courier earnings / active hr | R$ 33.0 | R$ 41.2 |
| Incentive spend | R$ 0 | R$ 35,820 |

Naive fulfillment lift **+1.87 pp**; ETA p90 **−6.06 min**; no-courier **−0.36 pp**.

Naive fulfillment lift by tier: short **+2.29 pp**, balanced **+2.43 pp**, long
**+0.94 pp**.

**Conclusion.** 840 zone-days, exactly 420/arm, spread over 12 zones (6 short / 2
balanced / 4 long) and 70 dates. Every treated-vs-control gap points the same way —
more orders delivered, faster, fewer no-courier cancels, more courier earnings — and
the gap is visibly larger in the supply-short and balanced zones than in the long
(well-supplied) zones. The rest of the read-out establishes whether those gaps are
causal (`03`), safe on the guardrails (`04`), stable over time (`05`), genuinely
heterogeneous (`06`), and not just supply pulled from neighbouring zones (`07`).

**Limitations.** The naive by-arm means ignore the clustering of zone-days within
zones — they are a description, not an estimate. Standard errors and inference start
in `03`.
