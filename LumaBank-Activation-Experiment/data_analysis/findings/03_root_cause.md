# 03 — Root-cause investigation: what broke, and how do we know

**Decision it informs:** is this really a deploy-triggered bug and not coincidence, and
can we draw an auditable line between contaminated and clean users? **Audience:** the
experimentation platform team and whoever signs off on the restart decision.

## Question
What caused the SRM break, does the timing prove it was the deploy, who was contaminated,
and how biased is the post-deploy fallback?

## Grain
`dim_app_release` for the timing cross-reference; `fact_activation` (`contaminated_flag`,
`assignment_switch_flag`) for the contaminated-vs-clean split; `fact_variant_assignment`
joined to `dim_user` / `dim_region` for the fallback's geographic composition.

## Method (both tracks)
Exact-date cross-reference against the release calendar; contaminated-vs-clean counts and
Day-7 rates by cohort; fallback treatment-share by macro-region vs the primary path's
~50/50, with a χ² test on whether the fallback's regional *mix* itself differs from
primary's.

## Evidence
- **The release calendar confirms the trigger.** Exactly one release lands on 2026-07-16 —
  a routine-looking mobile update (`is_cache_reset_release`) — on both iOS and Android. No
  other release in the surrounding weeks coincides with the break's onset.
- **Contamination (pre-deploy users): 191 of 4,323 original-run subjects (4.4%).** Of
  those, 74 users' assignment log literally shows a second event with a **different** arm
  (the arm-switch rule); the remaining 117 are flagged because a cache-reset event landed
  inside their still-open Day-7 window, even without a logged switch. Contaminated and
  clean pre-deploy users show statistically indistinguishable Day-7 rates in this sample
  (47.8% clean vs 48.7% contaminated) — contamination is a **trust** problem, not
  necessarily a large *directional* one, which is exactly why it has to be handled by
  auditable exclusion rather than by eyeballing the outcome.
- **The fallback is not just imbalanced in proportion — it's biased in composition.**
  Post-deploy (2026-07-16 → 2026-07-21), the fallback path allocates **65.6% to
  treatment overall** (447 of 681, χ² p = 3×10⁻¹⁶ vs 50/50) — far more skewed than the
  primary path's post-deploy allocation, which stays close to 50/50. Broken down by macro
  region, the skew is geographic: **SE fallback users go 76.5% treatment**, while **N
  fallback users go only 35.3% treatment** — a 41-point spread that does not exist on the
  primary path (SE 48.9% vs N 55.6% there). The region-*mix* itself (which regions show up
  in the fallback at all) is not significantly different from primary (χ² p = 0.59) — the
  bug does not change *who* signs up, only *which arm a fallback-routed signup lands in*,
  and it does so as a function of region.

## Conclusion
The incident has a single, exactly-dated trigger (the 2026-07-16 release), and it produces
two genuinely different problems that the analysis has to keep separate: (1) a small
(4.4%) but real contamination of already-assigned users, auditable from the assignment
event log alone, and (2) a much larger compositional bias in whoever the broken fallback
routes, correlated with region/timezone exactly as the bug-catalogue predicted (doc 02
§9). Neither is a proportion-only sample-ratio problem — both change *who* ends up in
which arm, not just *how many*.

## Limitations
"Contaminated" is an auditable rule (doc 02 §7.3), not a certainty for every individual
user — a user whose cache reset silently landed exactly at their Day-7 boundary is a
judgment call the rule resolves conservatively (flag it), covered further in block 04.

## Recommendation
Any use of the original run's data (blocks 04) must treat `contaminated_flag` and
`assignment_source = 'fallback'` as two **separate** exclusion criteria, not one.
