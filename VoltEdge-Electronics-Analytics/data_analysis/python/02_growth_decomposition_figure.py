"""Headline chart for Finding 02 - where the YoY Net Revenue gain came from.
Re-runs the Python track numbers (kept in sync with parity/02) and draws one waterfall.
"""
from __future__ import annotations

import sys
import pathlib

import matplotlib.pyplot as plt
import matplotlib.ticker as mtick
import pandas as pd

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from utils import OUT_FIGS, t  # noqa: E402

NAVY, BLUE, AMBER, GREY = "#12305B", "#2E6FB2", "#E8A33D", "#9AA5B1"

CY_START, CY_END = 20250701, 20260630
PY_START, PY_END = 20240701, 20250630

ol = t("fact_order_lines")
ol = ol[ol["order_status"] != "cancelled"].copy()
ol["nr"] = ol["net_amount_usd"] - ol["refund_amount_usd"]
mkt = t("dim_market")[["market_key", "is_comparable_base"]]
ol = ol.merge(mkt, on="market_key", how="left")
ol["period"] = pd.NA
ol.loc[ol["order_date_key"].between(PY_START, PY_END), "period"] = "PY"
ol.loc[ol["order_date_key"].between(CY_START, CY_END), "period"] = "CY"

g = ol.groupby(["period", "is_comparable_base"])["nr"].sum()
comp_py, comp_cy = g["PY", True], g["CY", True]
exp_py, exp_cy = g["PY", False], g["CY", False]
total_py, total_cy = comp_py + exp_py, comp_cy + exp_cy

comp_growth = comp_cy - comp_py
exp_growth = exp_cy - exp_py

# waterfall: PY total -> +like-for-like -> +expansion -> CY total
labels = ["Prior year\n(all markets)", "US like-for-like\ngrowth", "New-market\nexpansion", "Current year\n(all markets)"]
vals = [total_py, comp_growth, exp_growth, total_cy]
fig, ax = plt.subplots(figsize=(9, 5.2))
running = 0.0
for i, (lab, v) in enumerate(zip(labels, vals)):
    if i in (0, 3):
        ax.bar(i, v, color=NAVY, width=0.6)
        ax.text(i, v + 4e5, f"${v/1e6:,.1f}M", ha="center", va="bottom", fontweight="bold")
    else:
        color = BLUE if i == 1 else AMBER
        ax.bar(i, v, bottom=running, color=color, width=0.6)
        ax.text(i, running + v + 4e5, f"+${v/1e6:,.1f}M", ha="center", va="bottom", fontweight="bold")
        ax.plot([i - 0.3, i + 0.3], [running, running], color=GREY, lw=1, ls="--")
    if i < 3:
        running = running + v if i > 0 else v

ax.set_xticks(range(4))
ax.set_xticklabels(labels)
ax.yaxis.set_major_formatter(mtick.FuncFormatter(lambda x, _: f"${x/1e6:,.0f}M"))
ax.set_ylabel("Net Revenue (USD)")
ax.set_title("Net Revenue +137% YoY — but 77% of the gain is new-market expansion\n"
             "US like-for-like grew +40%", loc="left", fontweight="bold")
ax.spines[["top", "right"]].set_visible(False)
share = exp_growth / (total_cy - total_py)
ax.text(0.99, -0.16, f"Like-for-like = US only. Expansion = UK+DE+BR. "
        f"Expansion = {share:.0%} of the YoY gain, {exp_cy/total_cy:.0%} of CY Net Revenue.",
        transform=ax.transAxes, ha="right", va="top", fontsize=8, color=GREY)
fig.tight_layout()
OUT_FIGS.mkdir(parents=True, exist_ok=True)
p = OUT_FIGS / "2026-09_02_yoy_growth_waterfall.png"
fig.savefig(p, dpi=150, bbox_inches="tight")
print(f"saved {p}")
