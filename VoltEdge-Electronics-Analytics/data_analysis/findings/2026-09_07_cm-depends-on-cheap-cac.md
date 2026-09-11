# Finding 07 — Contribution margin turned positive on marketing efficiency — the least durable input

**Decision it informs:** how much confidence to place in the "we reached break-even" message,
and whether to hold or increase the marketing budget.
**Audience:** CFO, CMO.
**Time window:** CY 2025-07→2026-06 vs PY.

## Question
Finding 03 showed contribution margin went from −3.9% to +1.5% YoY. Gross margin only moved
+1.3pp, so most of the swing is on the cost side. **What moved it, and will it last?**

## Method (both tracks — `parity/07_marketing_efficiency.py`, all checks pass)
`docs/06 §08`: `Marketing Spend = SUM(fact_marketing_spend.cost_usd)`;
`New Customers` = customers whose **first-ever non-cancelled order** (`MIN(order_date_key)`
over `fact_orders`) falls in the period; `Blended CAC = Spend ÷ New Customers`;
`MER = Net Revenue ÷ Spend`. Sliced full/CY/PY, by `dim_channel.channel_group`, vs
`fact_target` (`metric = 'Blended CAC'`), plus a CM-sensitivity to CAC. SQL = DuckDB view on
first order + aggregates; Python = pandas. Parity exact on spend, new customers, NR,
new-customer NR, and on a 24-row monthly spend/new-customer panel. Significance: paired
t-test (calendar month PY vs CY) + bootstrap CI on the CAC change; a log-log OLS for the
spend→new-customers association.

## Evidence

| | PY | CY |
|---|---:|---:|
| Marketing spend | $1.10M | $1.72M |
| New customers | 36,419 | 63,862 (**+75%**) |
| **Blended CAC** | **$30.26** | **$26.91** (−11%) |
| Blended CAC target (`fact_target`) | — | $32.80 → **18% under plan** |
| MER (Net Rev ÷ spend) | 8.4× | **12.8×** (benchmark 6–10×) |
| **Marketing as % of Net Revenue** | **11.9%** | **7.8%** (−4.1pp) |
| CPC | $0.80 | $0.71 |

- The −4.1pp drop in marketing intensity ≈ the entire +5.4pp CM swing (Finding 03); gross
  margin (+1.3pp) and slightly higher shipping/payment ratios roughly net out.
- **Channel mix did *not* shift** — paid is 96.7% of *spend* in both years (email tooling is
  the only "owned" cost). What changed is **acquisition efficiency**: 41% of CY new customers
  arrive through **non-paid** channels (Organic, Direct, Email, Referral). CAC on *paid*
  acquisition alone is **$44.26** (benchmark $45–110, low end).
- New customers by market (CY): US 31.7k, BR 12.0k, UK 10.6k, DE 9.7k — expansion markets
  are **50%** of new-customer count.

### CY contribution margin is entirely a function of CAC

| Scenario | CY contribution margin |
|---|---:|
| Actual (blended CAC $26.91) | **+$325k** |
| If CAC reverted to PY ($30.26) | +$111k |
| If CAC hit plan ($32.80) | **−$51k (loss)** |

This sensitivity table is accounting, not statistics — it re-runs the known CY spend and
new-customer count at three different CAC values, so there's no sampling uncertainty to put
a confidence interval on. The question that *does* need a formal test is upstream of it:

### Is the PY→CY CAC improvement itself real, or just how the calendar fell?

Split into the 12 PY months and the 12 matching CY months (same calendar month each side —
July vs July, August vs August, ...) and compare CAC pairwise, so any month-of-year pattern
in acquisition cost (cheaper around Black Friday every year, say) cancels out of the
comparison rather than confounding it:

| | Value |
|---|---:|
| Mean CAC change (paired by month) | **−$1.18** |
| Paired t-test | t = −0.61, **p = 0.56** |
| 95% CI (bootstrap, 10,000 resamples) | **[−$4.64, +$2.61]** |

**The CI spans zero — a $1.18 average improvement across 12 paired months is not
distinguishable from typical month-to-month CAC noise.** The blended annual figures
($30.26 → $26.91) are exact, not estimates; what's uncertain is whether that gap reflects a
persistent efficiency gain or is disproportionately driven by a handful of unusually cheap
months. This doesn't overturn the finding — it **sharpens** it: the case for caution on the
break-even message gets stronger, not weaker, once the improvement funding it can't itself
be shown to be a durable trend.

**Companion check — does spend scale with new customers?** A log-log regression of monthly
new customers on monthly spend (n=24 months) gives an elasticity of **1.01
[95% CI: 0.53, 1.49], p < 0.001** — a 1% change in spend associates with roughly a 1%
change in new customers that month. This is observational, not causal (spend and organic
demand share the same seasonal calendar — Finding 05), but it's at least consistent with the
"there's room to scale paid spend" recommendation below: no sign yet of the sharply
diminishing returns that would show up as an elasticity well below 1.

Method: `parity/07_marketing_efficiency.py` — the monthly spend/new-customer panel behind
both tests is parity-checked SQL vs. pandas, row for row, before the paired test or the
regression runs on it.

## What the data says
1. VoltEdge is not more profitable because it got better at selling — it is more profitable
   because **customers currently come cheap**, helped by organic/direct pull as brand
   awareness compounds (exactly the pattern `docs/01 §7` anticipates).
2. `docs/01 §7` also says **"CAC rises over time."** It hasn't yet — CY CAC *fell*, though the
   paired-month test above says that fall isn't statistically distinguishable from noise
   either way. When CAC normalises toward the ~$44 paid CAC or the $33 plan, **the positive
   contribution margin disappears.** The break-even claim has a ~$375k cushion that sits
   entirely on this one line, and that line hasn't been shown to be a durable trend in either
   direction.
3. MER 12.8× (well above the 6–10× benchmark) is a **sign of under-investment**, not just
   efficiency: revenue grew +137% while spend grew +56%. There may be *profitable growth
   being left on the table* — or the organic tailwind is masking a paid channel that is
   already near its efficient frontier.

## Limitations & assumptions
- **Left-censoring:** the dataset starts 2024-07-01, so "first-ever order" for PY and the
  full window is bounded by the extract start → PY / full new-customer revenue shows as 100%.
  Only the **CY** new-vs-returning split (84% new / 16% returning) is meaningful, and even
  there some "returning" customers were acquired inside PY.
- The **16% returning** here is the DAX `New Revenue %` definition (a customer is "new" for
  the whole of their first year). At *order-month* grain, ~44% of CY revenue is repeat orders
  — see Finding 08 for the reconciliation. Both are correct; they answer different questions.
- ROAS/attribution is last-touch at channel level (`docs/01 §11`) — not a real MMM.
- CM-sensitivity holds new-customer *count* fixed and flexes only CAC; in reality a higher
  CAC might also come with more spend and more customers. It is a cushion estimate, not a forecast.
- `fact_marketing_spend` has no true "owned/earned" cost, so channel-group spend share is
  structurally ~97% paid; the acquisition-channel split uses `dim_customer.acquisition_channel`.

## Recommendation
- **Reframe the board message:** "contribution margin is positive *at current CAC*; it is
  break-even to slightly negative at planned CAC — and we can't yet show the CAC improvement
  itself is durable rather than a good few months." Do not present +1.5% CM as structural.
- **CMO:** test scaling paid spend deliberately — MER 12.8× and an elasticity near 1 both say
  there is likely profitable volume above the current budget, without yet showing
  diminishing returns. Set a marginal-CAC ceiling (e.g. ≤ $45) and spend up to it.
- **CFO:** treat the ~$375k CAC cushion as the single biggest risk to the break-even story;
  track marginal (not blended) CAC monthly against the paired-month baseline above, and
  stress-test the plan at CAC = $33 and $45.
- The real durable path to profit is **repeat revenue** (only 16% of CY) — Finding 08.
