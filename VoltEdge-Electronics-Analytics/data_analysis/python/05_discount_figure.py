"""Finding 05 figure - discount depth by promo event, and the gross-profit hit on promo days."""
from __future__ import annotations

import sys
import pathlib

import matplotlib.pyplot as plt
import matplotlib.ticker as mtick
import pandas as pd

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from utils import AMBER, GREEN, GREY, NAVY, RED, OUT_FIGS, setup_mpl, t  # noqa: E402

setup_mpl()

ol = t("fact_order_lines")
ol = ol[ol.order_status != "cancelled"].copy()
dd = t("dim_date")[["date_key", "is_promo_period", "promo_name"]]
ol = ol.merge(dd, left_on="order_date_key", right_on="date_key", how="left")
ol["net"] = ol.net_amount_usd - ol.refund_amount_usd
ol["gp"] = ol.net - ol.cogs_usd

bp = ol.groupby(ol.promo_name.replace("", "(no promo)")).apply(
    lambda x: pd.Series({"gross": x.gross_amount_usd.sum(),
                         "rate": x.discount_amount_usd.sum() / x.gross_amount_usd.sum()}),
    include_groups=False).sort_values("rate")
bp = bp[bp.index != "(no promo)"]

daily = ol.groupby(["order_date_key", "is_promo_period"]).agg(gp=("gp", "sum"), net=("net", "sum")).reset_index()
lift = daily.groupby("is_promo_period").agg(gp=("gp", "mean"), net=("net", "mean"), days=("order_date_key", "nunique"))

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 5), gridspec_kw={"width_ratios": [1.6, 1]})

# left: discount rate by event
cols = [RED if "Black Friday" in n else AMBER for n in bp.index]
ax1.barh(range(len(bp)), bp.rate * 100, color=cols)
ax1.set_yticks(range(len(bp))); ax1.set_yticklabels(bp.index, fontsize=9)
for i, v in enumerate(bp.rate):
    ax1.text(v * 100 + 0.2, i, f"{v:.1%}", va="center", fontsize=9)
ax1.axvline(2.67, color=GREY, ls="--", lw=1)
ax1.text(2.9, -0.7, "non-promo baseline 2.7%", color=GREY, fontsize=8)
ax1.set_xlabel("Discount rate (discounts ÷ gross revenue)")
ax1.set_title("Promo events discount 11–19% of list; Black Friday the deepest",
              loc="left", fontweight="bold", fontsize=11)
ax1.spines[["top", "right"]].set_visible(False)

# right: avg daily gross profit promo vs non-promo
ax2.bar([0, 1], [lift.loc[False, "gp"], lift.loc[True, "gp"]], color=[GREEN, RED], width=0.6)
for i, k in enumerate([False, True]):
    ax2.text(i, lift.loc[k, "gp"] + 120, f"${lift.loc[k,'gp']:,.0f}", ha="center", fontweight="bold")
ax2.set_xticks([0, 1]); ax2.set_xticklabels([f"Non-promo day\n(n={lift.loc[False,'days']})",
                                             f"Promo day\n(n={lift.loc[True,'days']})"])
ax2.yaxis.set_major_formatter(mtick.FuncFormatter(lambda x, _: f"${x:,.0f}"))
ax2.set_ylabel("Avg gross profit per day (USD)")
gap = (lift.loc[True, "gp"] - lift.loc[False, "gp"]) * lift.loc[True, "days"]
ax2.set_title(f"Promo days earn almost no gross profit\n"
              f"~${abs(gap)/1e3:,.0f}k/yr below treating them as normal days", loc="left",
              fontweight="bold", fontsize=11)
ax2.spines[["top", "right"]].set_visible(False)

fig.suptitle("Discounting overall is modest (4.6%) — the problem is promo depth, not creep",
             fontweight="bold", fontsize=13, x=0.01, ha="left")
fig.tight_layout(rect=[0, 0, 1, 0.95])
p = OUT_FIGS / "2026-09_05_discount_leakage.png"
fig.savefig(p, dpi=150, bbox_inches="tight")
print("saved", p)
