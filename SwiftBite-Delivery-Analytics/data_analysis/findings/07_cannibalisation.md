# 07 — Neighbour-zone cannibalisation: is the local win partly a transfer?

**Question.** Does arming the bonus in one zone pull couriers out of adjacent
(control) zones, so the metro-level gain is smaller than the sum of the local
lifts? (A SUTVA violation — spatial spillover.)

**Method (both tracks).**
- **A** — adjacent-control gap: fulfillment on control zone-days that *are* next to
  a treated zone that day vs control zone-days that are *not* (cluster-robust).
- **B** — spatial regression on control zone-days:
  `fulfillment_rate ~ n_adjacent_zones_treated + pre_fulfillment_rate + C(zone) + C(dow)`,
  cluster-robust — coefficient = per-treated-neighbour drag.
- **C** — clean-control bound: re-estimate the primary lift dropping control
  zone-days adjacent to any treated zone.
- **D** — implied cannibalised share and the metro net.
- **E** — supply elasticity: `available_courier_hours ~ treat`.

**Evidence** (`outputs/tables/07_cannibalisation.csv`).

| | Estimate | 95% CI / p |
|---|---|---|
| A. Adjacent-control fulfillment gap | **−0.26 pp** | p = 0.76 (not significant) |
| B. Per-treated-neighbour drag | **−0.19 pp** | p = 0.42 (not significant) |
| C. Primary lift: full-control vs clean-control | +1.87 pp → **+1.64 pp** | clean bound is *higher* |
| D. Implied cannibalised share | **≈ 17%** | metro net ≈ **83%** of summed local lift |
| E. Supply response | **+1.7 courier-hours / treated zone-day** (p < 0.001); +0.6 delivered orders | |

**Conclusion.** Cannibalisation is **present but small and not statistically
distinguishable from zero** at this scale. Point estimates line up — control zones
next to a treated zone fulfil ~0.2–0.3 pp lower, and the per-neighbour drag is
negative — implying roughly **one-sixth** of the local gain is supply pulled from
neighbours rather than net-new, so the metro-level effect is ~83% of the naive
sum. The clean-control bound (+1.64 pp) is *close* to the full estimate, so
depressed adjacent controls are not materially inflating the headline. The bonus
does add real supply (+1.7 courier-hours/zone-day), it is just mostly paying
couriers who were already there.

**Limitations.** 12 zones and a sparse adjacency graph give little power to resolve
a ~0.2 pp spatial effect; the ~17% share is a point estimate with a wide implicit
band. A denser design (more zones, an explicit "buffer" ring) would be needed to
pin it down.
