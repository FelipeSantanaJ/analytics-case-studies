"""Finding 09 figure - return rate by category, and refund value by reason (controllable vs choice)."""
from __future__ import annotations

import sys
import pathlib

import matplotlib.pyplot as plt
import matplotlib.ticker as mtick
import pandas as pd

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from utils import AMBER, BLUE, GREEN, GREY, NAVY, RED, OUT_FIGS, setup_mpl, t  # noqa: E402

setup_mpl()
CONTROLLABLE = {"Defective / not working", "Not as described", "Wrong item shipped",
                "Damaged in transit", "Arrived late"}

ol = t("fact_order_lines")
ol = ol[(ol.order_status != "cancelled") & (ol.line_type == "product")].copy()
pr = t("dim_product")[["product_key", "category"]]
ol = ol.merge(pr, on="product_key", how="left")
cat = ol.groupby("category").apply(lambda x: x.returned_qty.sum() / x.quantity.sum(),
                                   include_groups=False).sort_values()

fr = t("fact_returns")
by_reason = fr.groupby("reason").refund_amount_usd.sum().sort_values()
restock = fr.loc[fr.restocked, "returned_qty"].sum() / fr.returned_qty.sum()
refund_total = fr.refund_amount_usd.sum()
cogs_rec = fr.cogs_recovered_usd.sum()

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 5))

ax1.axhspan(7, 12, color=GREEN, alpha=0.12)
ax1.text(0.1, 12.3, "benchmark 7–12%", color=GREEN, fontsize=8)
cols = [RED if v >= 0.11 else BLUE for v in cat.values]
ax1.bar(range(len(cat)), cat.values * 100, color=cols, width=0.62)
for i, v in enumerate(cat.values):
    ax1.text(i, v * 100 + 0.25, f"{v:.1%}", ha="center", fontsize=8.5)
ax1.set_xticks(range(len(cat))); ax1.set_xticklabels(cat.index, rotation=30, ha="right", fontsize=8.5)
ax1.set_ylabel("Return rate (returned units ÷ units sold)")
ax1.set_title("Return rate 8.0% blended (flat YoY, flat by market)\n"
              "but Smartphones & Wearables run ~11–12% — the categories US is growing into",
              loc="left", fontweight="bold", fontsize=10.5)
ax1.spines[["top", "right"]].set_visible(False)

cc = [RED if r in CONTROLLABLE else GREY for r in by_reason.index]
ax2.barh(range(len(by_reason)), by_reason.values / 1e3, color=cc)
ax2.set_yticks(range(len(by_reason))); ax2.set_yticklabels(by_reason.index, fontsize=9)
for i, v in enumerate(by_reason.values):
    ax2.text(v / 1e3 + 8, i, f"${v/1e3:,.0f}k", va="center", fontsize=8.5)
ax2.set_xlabel("Refund value over 24 months (USD thousands)")
ax2.set_title("63% of the $3.5M refunds are ops/quality-driven (red) — fixable\n"
              f"Only {restock:.0%} of returned units are restocked; net margin drag "
              f"${(refund_total-cogs_rec)/1e6:.2f}M", loc="left", fontweight="bold", fontsize=10.5)
ax2.spines[["top", "right"]].set_visible(False)

fig.suptitle("Returns are not rising — but $1.65M of margin leaks, mostly for fixable reasons",
             fontweight="bold", fontsize=12.5, x=0.01, ha="left")
fig.tight_layout(rect=[0, 0, 1, 0.94])
p = OUT_FIGS / "2026-09_09_returns.png"
fig.savefig(p, dpi=150, bbox_inches="tight")
print("saved", p)
