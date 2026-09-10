"""Finding 04 figure - PVM waterfall for US like-for-like gross-revenue growth."""
from __future__ import annotations

import sys
import pathlib

import matplotlib.pyplot as plt
import matplotlib.ticker as mtick
import pandas as pd

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from utils import OUT_FIGS, setup_mpl, t  # noqa: E402

setup_mpl()
NAVY, GREEN, RED, GREY = "#12305B", "#2E8B57", "#C0392B", "#9AA5B1"
CY, PY = (20250701, 20260630), (20240701, 20250630)

ol = t("fact_order_lines")
mk = t("dim_market")[["market_key", "is_comparable_base"]]
pr = t("dim_product")[["product_key", "category"]]
ol = ol.merge(mk, on="market_key").merge(pr, on="product_key")
ol = ol[(ol.order_status != "cancelled") & ol.is_comparable_base]


def by_cat(lo, hi):
    d = ol[ol.order_date_key.between(lo, hi)]
    g = d.groupby("category").apply(lambda x: pd.Series({
        "gross": x.gross_amount_usd.sum(),
        "units": x.loc[x.line_type == "product", "quantity"].sum()}), include_groups=False)
    g["asp"] = g.gross / g.units
    return g


cy_c, py_c = by_cat(*CY), by_cat(*PY)
cats = sorted(set(cy_c.index) | set(py_c.index))
cy_c, py_c = cy_c.reindex(cats).fillna(0), py_c.reindex(cats).fillna(0)
g_cy, g_py = cy_c.gross.sum(), py_c.gross.sum()
u_cy, u_py = cy_c.units.sum(), py_c.units.sum()
price = ((cy_c.asp.replace([float("inf")], 0) - py_c.asp.replace([float("inf")], 0)) * py_c.units).sum()
volume = g_py * (u_cy - u_py) / u_py
mix = (g_cy - g_py) - price - volume

labels = ["US Gross Rev\nPY", "Volume\n(+44% units)", "Price\n(ASP within cat.)", "Category\nmix", "US Gross Rev\nCY"]
vals = [g_py, volume, price, mix, g_cy]
colors = [NAVY, GREEN, GREEN, RED, NAVY]
fig, ax = plt.subplots(figsize=(9.5, 5.2))
run = 0.0
for i, (lab, v, c) in enumerate(zip(labels, vals, colors)):
    if i in (0, 4):
        ax.bar(i, v, color=c, width=0.6); run = v
        ax.text(i, v + 1.2e5, f"${v/1e6:.2f}M", ha="center", fontweight="bold")
    else:
        ax.bar(i, v, bottom=run, color=c, width=0.6)
        ax.plot([i - .3, i + .3], [run, run], color=GREY, lw=1, ls="--")
        run += v
        off = 1.2e5 if v > 0 else -1.2e5
        ax.text(i, run + off, f"{'+' if v>0 else '−'}${abs(v)/1e6:.2f}M", ha="center",
                va="bottom" if v > 0 else "top", fontsize=9)
ax.yaxis.set_major_formatter(mtick.FuncFormatter(lambda x, _: f"${x/1e6:.0f}M"))
ax.set_ylim(0, g_cy * 1.15)
ax.set_xticks(range(5)); ax.set_xticklabels(labels)
ax.set_ylabel("Gross Revenue (USD)")
ax.set_title("US like-for-like growth is ~all volume — no pricing power, slight adverse mix\n"
             f"+$3.45M (+40%): volume +$3.79M, price +$0.26M, mix −$0.60M", loc="left", fontweight="bold")
ax.spines[["top", "right"]].set_visible(False)
fig.tight_layout()
p = OUT_FIGS / "2026-09_04_pvm_us_waterfall.png"
fig.savefig(p, dpi=150, bbox_inches="tight")
print("saved", p)
