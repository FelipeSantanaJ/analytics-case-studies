# 04 — Decision analysis: truncate, exclude-contaminated, or restart

**Decision it informs:** which of the three fixes to take, under real business deadline
pressure. **Audience:** Growth + Experimentation leadership — the call that has to be
defended afterwards.

## Question
Given the break (blocks 02–03), which of three imperfect options — truncate to the clean
pre-deploy days, exclude only the contaminated/biased users, or restart clean — gives a
defensible answer inside a reasonable timeline?

## Grain
`fact_activation` (cohort, `contaminated_flag`), `fact_variant_assignment`
(`assignment_source`) for how much each option keeps and how biased what's kept still is.

## Method (both tracks)
For each option: the usable sample, the achievable MDE at that sample (two-proportion
formula, control rate from block 01), and — for option 2 — a residual-bias check (regional
composition of what's kept vs. what's dropped).

## Evidence

| Option | n/arm | MDE (80% power) | Bias | Timeline |
|---|---:|---:|---|---|
| **1. Truncate** (pre-deploy only) | 1,324 | **5.44 pp** (6.55 pp in real time*) | still 7.2% contaminated — the last pre-deploy days' Day-7 windows reach into the post-deploy period | immediate |
| **2. Exclude contaminated + fallback-sourced** | 1,725 | **4.77 pp** | residual — max regional-mix gap between kept and excluded is 1.7 pp; cannot prove every contaminated user was caught | a few days, no new data |
| **3. Restart clean** | ~4,500 (block 05) | **2.92 pp** (block 05) | none — clean randomisation, bug fixed | worst, but capped at 4 weeks |

\* *In real time, at the actual decision point (a few days after the deploy), users
assigned in the final pre-deploy days would not yet have a closed Day-7 window — a live
analysis would have had even less usable data than the retrospective 1,324/arm shown here.*

- **Truncate's MDE (5.44 pp, worse in real time) is more than double the original design's
  MDE (2.41 pp)** and larger than the true effect this project independently recovers in
  block 05 (+4.58 pp) — truncating would very plausibly have returned a **false null**.
- **Excluding the contaminated users only modestly improves the picture** (MDE 4.77 pp) —
  still short of what would reliably detect a ~4–5 pp effect — while leaving a real,
  unquantifiable residual bias (the region-mix gap is small, 1.7 pp, but "small and
  unproven" is a different thing from "zero").
- **Restart is the only option with zero bias**, at the cost of the worst timeline — which
  the business capped at 4 weeks rather than the original 6.

## Conclusion
Neither truncate nor exclude-contaminated would have supported a trustworthy answer: both
carry an MDE too wide to reliably resolve the effect this project turns out to have (block
05), and both trade statistical power for residual, unquantified bias. **Restart, in a
shorter window with power/MDE recomputed from scratch, is the only option that does not
ask the business to accept an unresolved risk on a fintech guardrail decision (KYC
rejection, fraud) in exchange for speed.**

## Limitations
This is a retrospective comparison — the "in real time" truncate figure approximates what
would have been knowable at the actual decision point, but the exact triage timeline (how
many days of investigation preceded the restart decision) is itself a modelling choice
(doc 00 §4.4), not observed data.

## Recommendation
Restart in a 4-week window; recompute power/MDE for the smaller sample rather than
reusing the original design's numbers (block 05); state the resulting MDE explicitly as
the cost of the deadline.
