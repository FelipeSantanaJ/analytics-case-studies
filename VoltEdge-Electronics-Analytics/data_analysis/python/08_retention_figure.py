"""Finding 08 figure - cohort retention curve + new vs returning revenue by month."""
from __future__ import annotations

import sys
import pathlib

import matplotlib.pyplot as plt
import matplotlib.ticker as mtick
import numpy as np
import pandas as pd

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from utils import AMBER, BLUE, GREY, NAVY, RED, OUT_FIGS, setup_mpl, t  # noqa: E402

setup_mpl()

fo = t("fact_orders")
fo = fo[~fo.is_cancelled].copy()
dd = t("dim_date")[["date_key", "date"]]
fo = fo.merge(dd, left_on="order_date_key", right_on="date_key", how="left")
first = fo.groupby("customer_key")["date"].min().rename("first_dt")
fo = fo.merge(first, on="customer_key", how="left")
fo["cohort"] = fo.first_dt.dt.to_period("M")
fo["mo"] = (fo.date.dt.to_period("M") - fo.cohort).apply(lambda x: x.n)
sizes = fo.groupby("cohort").customer_key.nunique()
act = fo.groupby(["cohort", "mo"]).customer_key.nunique().unstack(fill_value=0)
ret = act.div(sizes, axis=0)
mature = ret.loc[ret.index <= pd.Period("2025-12", "M")]
curve = mature.mean(axis=0)

ol = t("fact_order_lines")
ol = ol[ol.order_status != "cancelled"].copy()
ol["nr"] = ol.net_amount_usd - ol.refund_amount_usd
ol = ol.merge(dd, left_on="order_date_key", right_on="date_key", how="left")
ol["ym"] = ol.date.dt.to_period("M")
fm = fo.groupby("customer_key")["cohort"].first()
ol = ol.merge(fm.rename("cohort"), on="customer_key", how="left")
ol["is_new"] = ol.ym == ol.cohort
rs = ol.groupby(["ym", "is_new"]).nr.sum().unstack(fill_value=0.0)
rs.columns = ["returning", "new"]
rs["rpct"] = rs.returning / (rs.new + rs.returning)
rs.index = rs.index.to_timestamp()

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 5))

# left: retention curve
mos = [m for m in range(1, 13) if m in curve.index]
ax1.bar(mos, [curve[m] * 100 for m in mos], color=BLUE, width=0.62)
for m in mos:
    ax1.text(m, curve[m] * 100 + 0.3, f"{curve[m]:.0%}", ha="center", fontsize=8)
ax1.set_xlabel("Months after first order")
ax1.set_ylabel("% of acquisition cohort that orders that month")
ax1.set_xticks(mos)
ax1.set_title("Repeat demand decays fast: 16% order again at +1 month, 2% by +12\n"
              "Lifetime repeat rate 37.6% (above 25–35% benchmark); 1.67 orders/customer",
              loc="left", fontweight="bold", fontsize=10.5)
ax1.spines[["top", "right"]].set_visible(False)

# right: new vs returning revenue by month
ax2.stackplot(rs.index, rs["new"] / 1e6, rs["returning"] / 1e6,
              labels=["New-customer-month revenue", "Returning revenue"], colors=[GREY, NAVY], alpha=0.9)
ax2b = ax2.twinx()
ax2b.plot(rs.index, rs["rpct"] * 100, color=AMBER, lw=2.2, label="Returning %")
ax2b.set_ylim(0, 70)
ax2b.set_ylabel("Returning revenue share (%)", color="#9a6a12")
ax2.set_ylabel("Net Revenue (USD M)")
ax2.yaxis.set_major_formatter(mtick.FuncFormatter(lambda v, _: f"${v:.1f}M"))
ax2.set_title("Returning share of monthly revenue rose to ~45%\n"
              "(but 84% of CY revenue is still from customers in year 1)",
              loc="left", fontweight="bold", fontsize=10.5)
ax2.legend(loc="upper left", fontsize=8, frameon=False)
ax2.spines[["top"]].set_visible(False); ax2b.spines[["top"]].set_visible(False)

fig.suptitle("Repeat behaviour is healthy and improving — but not yet the revenue engine",
             fontweight="bold", fontsize=12.5, x=0.01, ha="left")
fig.tight_layout(rect=[0, 0, 1, 0.94])
p = OUT_FIGS / "2026-09_08_retention_cohorts.png"
fig.savefig(p, dpi=150, bbox_inches="tight")
print("saved", p)
