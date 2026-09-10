"""Finding 07 figure - marketing efficiency drove CM positive, and CM's sensitivity to CAC."""
from __future__ import annotations

import sys
import pathlib

import matplotlib.pyplot as plt
import matplotlib.ticker as mtick
import pandas as pd

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from utils import AMBER, BLUE, GREEN, GREY, NAVY, RED, OUT_FIGS, setup_mpl, t  # noqa: E402

setup_mpl()
CY, PY = (20250701, 20260630), (20240701, 20250630)

fo = t("fact_orders")
fo_nc = fo[~fo.is_cancelled]
first = fo_nc.groupby("customer_key").order_date_key.min()
ms = t("fact_marketing_spend")
ol = t("fact_order_lines")
ol_nc = ol[ol.order_status != "cancelled"].copy()
ol_nc["nr"] = ol_nc.net_amount_usd - ol_nc.refund_amount_usd


def stats(lo, hi):
    spend = ms.loc[ms.date_key.between(lo, hi), "cost_usd"].sum()
    newc = fo_nc[fo_nc.order_date_key.between(lo, hi) &
                 fo_nc.customer_key.isin(first[first.between(lo, hi)].index)].customer_key.nunique()
    nr = ol_nc.loc[ol_nc.order_date_key.between(lo, hi), "nr"].sum()
    return spend, newc, nr


s_py, n_py, r_py = stats(*PY)
s_cy, n_cy, r_cy = stats(*CY)
cac_py, cac_cy = s_py / n_py, s_cy / n_cy
tgt = t("fact_target")
cac_tgt = tgt[(tgt.metric == "Blended CAC") & tgt.month_date_key.between(*CY)].target_value.mean()

CM = 325_498
cm_py_cac = CM - (cac_py * n_cy - s_cy)
cm_tgt_cac = CM - (cac_tgt * n_cy - s_cy)

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 5))

# left: marketing as % of net revenue + blended CAC, PY vs CY
x = [0, 1]
mkt_pct = [s_py / r_py * 100, s_cy / r_cy * 100]
ax1.bar([i - 0.19 for i in x], mkt_pct, width=0.36, color=BLUE, label="Marketing % of Net Rev")
ax1b = ax1.twinx()
ax1b.bar([i + 0.19 for i in x], [cac_py, cac_cy], width=0.36, color=AMBER, label="Blended CAC")
ax1b.axhline(cac_tgt, color=RED, ls="--", lw=1.2)
ax1b.text(1.35, cac_tgt + 0.4, f"CAC target ${cac_tgt:.0f}", color=RED, fontsize=8, ha="right")
for i, v in zip(x, mkt_pct):
    ax1.text(i - 0.19, v + 0.2, f"{v:.1f}%", ha="center", fontweight="bold", color=BLUE)
for i, v in zip(x, [cac_py, cac_cy]):
    ax1b.text(i + 0.19, v + 0.4, f"${v:.2f}", ha="center", fontweight="bold", color="#9a6a12")
ax1.set_xticks(x); ax1.set_xticklabels(["Prior Year", "Current Year"])
ax1.set_ylabel("Marketing spend as % of Net Revenue", color=BLUE)
ax1b.set_ylabel("Blended CAC (USD)", color="#9a6a12")
ax1.set_ylim(0, 14); ax1b.set_ylim(0, 40)
ax1.set_title("Marketing got cheaper: 11.9% → 7.8% of revenue, CAC 18% under plan\n"
              "41% of new customers now come via non-paid channels", loc="left",
              fontweight="bold", fontsize=10.5)
ax1.spines[["top"]].set_visible(False); ax1b.spines[["top"]].set_visible(False)

# right: CM sensitivity
bars = ["CM at actual\nCAC $26.91", "CM if CAC =\nPY $30.26", "CM if CAC =\nplan $32.80"]
vals = [CM, cm_py_cac, cm_tgt_cac]
cols = [GREEN, AMBER, RED]
ax2.bar(range(3), vals, color=cols, width=0.6)
for i, v in enumerate(vals):
    ax2.text(i, v + 14000 if v > 0 else 14000, f"${v/1e3:+,.0f}k", ha="center",
             va="bottom", fontweight="bold")
ax2.axhline(0, color="black", lw=0.9)
ax2.set_ylim(-90000, 360000)
ax2.set_xticks(range(3)); ax2.set_xticklabels(bars)
ax2.yaxis.set_major_formatter(mtick.FuncFormatter(lambda v, _: f"${v/1e3:,.0f}k"))
ax2.set_ylabel("CY contribution margin (USD)")
ax2.set_title("The positive CM depends entirely on cheap CAC\n"
              "revert to plan CAC and VoltEdge is loss-making again", loc="left",
              fontweight="bold", fontsize=10.5)
ax2.spines[["top", "right"]].set_visible(False)

fig.suptitle("Contribution margin turned positive on marketing efficiency — the least durable input",
             fontweight="bold", fontsize=12.5, x=0.01, ha="left")
fig.tight_layout(rect=[0, 0, 1, 0.94])
p = OUT_FIGS / "2026-09_07_marketing_efficiency.png"
fig.savefig(p, dpi=150, bbox_inches="tight")
print("saved", p)
