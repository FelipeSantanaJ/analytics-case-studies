# Deep Dive B — Why members hoard points, and what it costs

**Business problem.** The SkyPoints relaunch business case assumed breakage would fall from
~40% toward 30% as members learned the program. It hasn't. A large, slow-moving
point-liability sits on the balance sheet, and members who never redeem lapse far more
often. This deep dive sizes the hoarding funnel, the liability and its estimate risk, and
the redeemer→retention link that makes redemption a retention lever — the context for the
Flash Redemption decision (Deep Dive A).

---

## 1. The redemption funnel (finding 07)

At 2026-08, of **109,458 active members**:

| stage | all | Blue | Silver | Gold | Platinum |
|---|---|---|---|---|---|
| balance ≥ Flash threshold (3,500) | 68% | 65% | 72% | 78% | 83% |
| **ever redeemed** | **32%** | 25% | 37% | 53% | 70% |
| redeemed in last 12m | 25% | 19% | 30% | 46% | 66% |
| **redeemed last quarter** | **9%** | 6% | 10% | 18% | 34% |

The drop-off is not "can't afford to" (two-thirds clear the threshold) — it's "never start".
**Blue is the problem**: a quarter have ever redeemed, 6% redeemed last quarter. This is
exactly the stage and segment Flash Redemption targets, and finding 06 shows it moves the
needle there.

---

## 2. Earn is dominated by the co-brand card (finding 07)

SkyPoints issued window-to-date, by source (M points):

| source | M pts | share |
|---|---|---|
| **BancoAV co-brand card** | **1,146** | **55%** |
| legacy migration | 397 | 19% |
| flights | 301 | 14% |
| promo / partners / service | 245 | 12% |

The card issues more than half of all points — to members earning **with no flight
attached**, who have the weakest reason to engage with the airline side of the program.
That is the population that accumulates and lets points expire.

---

## 3. Breakage and the liability (finding 07)

- Points: issued 2,089M · redeemed 636M (**burn/earn 30.4%**) · **expired 228M = 10.9% of
  issued** (the first legacy-lot expiry wave; most window lots have not reached their
  24-month expiry, so lifetime breakage is still trending toward ~40%).
- **Point liability at 2026-08: R$25.7M gross · R$15.4M breakage-adjusted (40%).**
- **Estimate risk:** the recognised liability moves **±R$2.6M per 10 pp** of breakage
  assumption:

  | assumed breakage | recognised liability |
  |---|---|
  | 20% | R$20.6M |
  | 30% | R$18.0M |
  | 40% (base) | R$15.4M |
  | 50% | R$12.9M |

Flash Redemption reduces the liability at the margin (finding 04, G2: net cost per member
−R$0.81, favourable direction) by converting "will expire" points into redemptions — but the
low-cost catalog is bought at cash cost, so the net is small, not a windfall.

**Figure:** `outputs/figures/07_hoarding.png` (reach by tier; liability trajectory).

---

## 4. Redeemers stay (finding 08) — observational, with the causal cross-check

12-month **engagement lapse** (no flight and no redemption for 12 months; plain "account
lapse" is only ~4% because card auto-earn keeps accounts nominally alive):

| | rate | n |
|---|---|---|
| prior redeemers | **10.6%** | 14,108 |
| never redeemed | **21.1%** | 42,447 |
| **raw gap** | **−10.5 pp** | |
| **adjusted** (logistic on tenure, tier, earn, flights, card-only) | **−6.0 pp** (p = 1e-31) | |

Forward 12-month flight revenue: redeemers **R$3,337**/member vs never-redeemers **R$1,596**
(+R$1,741 raw).

A large association survives adjustment, but a latent engagement trait plausibly drives both
redeeming and staying, so even −6 pp over-states causation. The clean causal signal is the
experiment's **90-day disengagement guardrail: −2.0 pp, p = 0.001** (Deep Dive A §6). The
true 12-month retention benefit is somewhere between the experiment's short-run −2 pp and
the observational −6 pp.

---

## 5. Limitations

- Realised breakage (11%) is window-to-date; lifetime breakage is a projection.
- No per-lot FIFO ledger in curated (docs/08 §4) — breakage is an aggregate roll-forward.
- Redeemer→retention is observational; confounded by latent engagement.
- Liability unit cost (R$0.021/pt) and the 40% breakage assumption are program inputs.

---

## 6. Recommendations

1. **Roll out Flash Redemption to Blue + Silver** (Deep Dive A) — it attacks the funnel
   stage and tier where hoarding is worst.
2. **Add a co-brand-card redemption nudge** — 55% of issuance goes to card-earn members with
   the weakest redemption pull; a targeted "you have enough for X" prompt is the highest-
   leverage adjacent move.
3. **Run a breakage cohort study** once a full 24-month lot lifetime of data exists — the
   recognised-liability uncertainty (±R$2.6M / 10 pp) is material for the CFO.
4. **Treat redemption enablement as a retention intervention**, sizing the benefit
   conservatively (closer to −2 pp than −6 pp) until a longer post-rollout window exists.
