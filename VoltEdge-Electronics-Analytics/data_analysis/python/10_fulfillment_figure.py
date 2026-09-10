"""Finding 10 figure - ops KPIs are fine; the shipping-cost recovery gap is the issue."""
from __future__ import annotations

import sys
import pathlib

import matplotlib.pyplot as plt
import matplotlib.ticker as mtick
import pandas as pd

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from utils import AMBER, BLUE, GREEN, GREY, NAVY, RED, OUT_FIGS, setup_mpl, t  # noqa: E402

setup_mpl()

fo = t("fact_orders")
fo = fo[~fo.is_cancelled].copy()
mk = t("dim_market")[["market_key", "market_name"]]
fo = fo.merge(mk, on="market_key", how="left")
g = fo.groupby("market_name").apply(lambda x: pd.Series({
    "orders": x.order_id.nunique(),
    "cost_po": x.shipping_cost_usd.sum() / x.order_id.nunique(),
    "fee_po": x.shipping_fee_usd.sum() / x.order_id.nunique(),
}), include_groups=False)
g["recovery"] = g.fee_po / g.cost_po
g = g.sort_values("recovery")
blended_cost = fo.shipping_cost_usd.sum() / fo.order_id.nunique()
blended_rec = fo.shipping_fee_usd.sum() / fo.shipping_cost_usd.sum()

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 5), gridspec_kw={"width_ratios": [1, 1.15]})

# left: ops KPIs vs benchmark
kpis = [
    ("On-time delivery %", 94.5, (92, 96), "%"),
    ("Avg delivery days", 4.5, (3, 6), "d"),
    ("Perfect order rate %", 82.9, (88, 93), "%"),
]
for i, (lab, val, bm, unit) in enumerate(kpis):
    lo, hi = bm
    norm = (val - lo) / (hi - lo)
    ax1.barh(i, 1, color=GREY, alpha=0.18)
    ax1.plot([0, 1], [i, i], color=GREY, lw=0.5)
    inbm = lo <= val <= hi
    ax1.scatter([min(max(norm, -0.15), 1.15)], [i], s=180, color=GREEN if inbm else RED, zorder=3)
    ax1.text(-0.05, i, lab, ha="right", va="center", fontsize=9.5)
    ax1.text(1.05, i, f"{val}{unit}  (bm {lo}–{hi})", va="center", fontsize=8.5,
             color=GREEN if inbm else RED)
ax1.set_xlim(-0.75, 2.0); ax1.set_ylim(-0.6, 2.6)
ax1.axvspan(0, 1, color=GREEN, alpha=0.08)
ax1.set_xticks([]); ax1.set_yticks([])
for s in ax1.spines.values():
    s.set_visible(False)
ax1.set_title("Service levels are on-benchmark — except perfect-order rate\n"
              "(83% vs 88–93%): the ~5.5% late + returns + cancels drag", loc="left",
              fontweight="bold", fontsize=10.5)

# right: shipping cost vs fee recovered, per order, by market
y = range(len(g))
ax2.barh(y, g.cost_po, color=GREY, alpha=0.55, label="Shipping cost / order")
ax2.barh(y, g.fee_po, color=BLUE, label="Fee revenue / order")
for i, (c, f, r) in enumerate(zip(g.cost_po, g.fee_po, g.recovery)):
    ax2.text(f + 0.2, i, f"{r:.0%} recovered", va="center", fontsize=9, color=NAVY, fontweight="bold")
ax2.set_yticks(list(y)); ax2.set_yticklabels(g.index)
ax2.set_xlim(0, 12.5)
ax2.set_xlabel("USD per order")
ax2.axvline(blended_cost, color=RED, ls="--", lw=1)
ax2.text(blended_cost - 0.15, -0.55, f"cost ${blended_cost:.2f}", color=RED, fontsize=8, ha="right")
ax2.legend(loc="lower right", fontsize=8, frameon=False)
ax2.set_title("Shipping cost is uniform (~$10.40/order); only 28% is recovered in fees\n"
              "Brazil recovers 5% — effectively free shipping. ~$1.25M/yr structural loss",
              loc="left", fontweight="bold", fontsize=10.5)
ax2.spines[["top", "right"]].set_visible(False)

fig.suptitle("Fulfilment runs well; the lever is shipping-fee recovery, not carrier performance",
             fontweight="bold", fontsize=12.5, x=0.01, ha="left")
fig.tight_layout(rect=[0, 0, 1, 0.94])
p = OUT_FIGS / "2026-09_10_fulfilment.png"
fig.savefig(p, dpi=150, bbox_inches="tight")
print("saved", p)
