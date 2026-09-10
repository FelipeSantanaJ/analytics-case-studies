"""Finding 03 figures: (left) CY contribution-margin bridge, (right) CM% trajectory & by market.
Numbers mirror parity/03_margin_to_breakeven.py (CY track)."""
from __future__ import annotations

import sys
import pathlib

import matplotlib.pyplot as plt
import matplotlib.ticker as mtick

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from utils import OUT_FIGS, t  # noqa: E402

NAVY, BLUE, AMBER, RED, GREEN, GREY = "#12305B", "#2E6FB2", "#E8A33D", "#C0392B", "#2E8B57", "#9AA5B1"
CY, PY = (20250701, 20260630), (20240701, 20250630)


def walk(lo, hi):
    ol = t("fact_order_lines")
    ol = ol[(ol.order_status != "cancelled") & ol.order_date_key.between(lo, hi)]
    nr = (ol.net_amount_usd - ol.refund_amount_usd).sum()
    cogs = ol.cogs_usd.sum()
    rec = t("fact_returns")
    rec = rec[rec.return_date_key.between(lo, hi)].cogs_recovered_usd.sum()
    gp = nr - cogs + rec
    ms = t("fact_marketing_spend")
    mktg = ms[ms.date_key.between(lo, hi)].cost_usd.sum()
    fo = t("fact_orders")
    fo = fo[(~fo.is_cancelled) & fo.order_date_key.between(lo, hi)]
    ship, pay = fo.shipping_cost_usd.sum(), fo.payment_fee_usd.sum()
    ps = t("fact_payment_schedule")
    fin = ps[(ps.installment_plan == "Interest-Free") & ps.order_date_key.between(lo, hi)].financing_cost_usd.sum()
    cm = gp - mktg - ship - pay - fin
    return dict(nr=nr, gp=gp, mktg=mktg, ship=ship, pay=pay + fin, cm=cm)


cy, py = walk(*CY), walk(*PY)

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 5.4), gridspec_kw={"width_ratios": [1.5, 1]})

# ---- left: CY bridge ----
steps = [("Gross\nProfit", cy["gp"], NAVY),
         ("− Marketing", -cy["mktg"], AMBER),
         ("− Shipping", -cy["ship"], AMBER),
         ("− Payment\n& financing", -cy["pay"], AMBER),
         ("Contribution\nMargin", cy["cm"], GREEN if cy["cm"] > 0 else RED)]
run = 0.0
for i, (lab, v, c) in enumerate(steps):
    if i in (0, 4):
        ax1.bar(i, v, color=c, width=0.6)
        run = v
        ax1.text(i, v + 8e4, f"${v/1e6:.2f}M", ha="center", va="bottom", fontweight="bold")
    else:
        ax1.bar(i, v, bottom=run, color=c, width=0.6)
        ax1.plot([i - 0.3, i + 0.3], [run, run], color=GREY, lw=1, ls="--")
        run += v
        ax1.text(i, run - 1.2e5, f"−${abs(v)/1e6:.2f}M", ha="center", va="top", fontsize=9)
ax1.axhline(0, color="black", lw=0.8)
ax1.set_ylim(0, cy["gp"] * 1.28)
ax1.set_xticks(range(5)); ax1.set_xticklabels([s[0] for s in steps])
ax1.yaxis.set_major_formatter(mtick.FuncFormatter(lambda x, _: f"${x/1e6:.1f}M"))
ax1.set_title(f"Current Year: gross profit → contribution margin\n"
              f"CM = ${cy['cm']/1e3:,.0f}k  ({cy['cm']/cy['nr']:.1%} of Net Revenue) — barely above break-even",
              loc="left", fontweight="bold", fontsize=11, pad=14)
ax1.spines[["top", "right"]].set_visible(False)

# ---- right: CM% PY vs CY, then by market CY ----
ol = t("fact_order_lines")
olc = ol[(ol.order_status != "cancelled") & ol.order_date_key.between(*CY)].copy()
olc["nr"] = olc.net_amount_usd - olc.refund_amount_usd
mk = t("dim_market")[["market_key", "market_name"]]
olc = olc.merge(mk, on="market_key")
g = olc.groupby("market_name").agg(nr=("nr", "sum"), cogs=("cogs_usd", "sum"))
rec = t("fact_returns"); rec = rec[rec.return_date_key.between(*CY)].merge(mk, on="market_key")
g["rec"] = rec.groupby("market_name").cogs_recovered_usd.sum().reindex(g.index).fillna(0)
ms = t("fact_marketing_spend"); ms = ms[ms.date_key.between(*CY)].merge(mk, on="market_key")
g["mktg"] = ms.groupby("market_name").cost_usd.sum().reindex(g.index).fillna(0)
fo = t("fact_orders"); fo = fo[(~fo.is_cancelled) & fo.order_date_key.between(*CY)].merge(mk, on="market_key")
g["ship"] = fo.groupby("market_name").shipping_cost_usd.sum().reindex(g.index).fillna(0)
g["pay"] = fo.groupby("market_name").payment_fee_usd.sum().reindex(g.index).fillna(0)
ps = t("fact_payment_schedule")
ps = ps[(ps.installment_plan == "Interest-Free") & ps.order_date_key.between(*CY)].merge(mk, on="market_key")
g["fin"] = ps.groupby("market_name").financing_cost_usd.sum().reindex(g.index).fillna(0)
g["cm_pct"] = (g.nr - g.cogs + g.rec - g.mktg - g.ship - g.pay - g.fin) / g.nr
g = g.sort_values("cm_pct")

bars = ["Prior Yr\ntotal", "Current Yr\ntotal"] + [n.replace(" ", "\n") for n in g.index]
vals = [py["cm"] / py["nr"], cy["cm"] / cy["nr"]] + list(g.cm_pct)
cols = [RED, GREEN] + [GREEN if v > 0 else RED for v in g.cm_pct]
ax2.bar(range(len(bars)), [v * 100 for v in vals], color=cols, width=0.62)
for i, v in enumerate(vals):
    ax2.text(i, v * 100 + (0.15 if v >= 0 else -0.15), f"{v:.1%}", ha="center",
             va="bottom" if v >= 0 else "top", fontsize=9, fontweight="bold")
ax2.axhline(0, color="black", lw=0.8)
ax2.set_xticks(range(len(bars))); ax2.set_xticklabels(bars, fontsize=8)
ax2.set_ylabel("Contribution margin %")
ax2.set_title("CM% improving YoY (−3.9% → +1.5%)\nUK is the drag; Brazil the best", loc="left",
              fontweight="bold", fontsize=11)
ax2.spines[["top", "right"]].set_visible(False)

fig.suptitle("VoltEdge runs at break-even after marketing, shipping and payment costs",
             fontweight="bold", fontsize=13, x=0.01, ha="left")
fig.tight_layout(rect=[0, 0, 1, 0.95])
p = OUT_FIGS / "2026-09_03_contribution_margin.png"
fig.savefig(p, dpi=150, bbox_inches="tight")
print("saved", p)
