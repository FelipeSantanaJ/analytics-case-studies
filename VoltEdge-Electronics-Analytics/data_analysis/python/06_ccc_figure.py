"""Finding 06 figure - CCC composition (DIO + DSO - DPO) and DSO by market."""
from __future__ import annotations

import sys
import pathlib

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from utils import AMBER, BLUE, GREEN, GREY, NAVY, RED, OUT_FIGS, setup_mpl, t  # noqa: E402

setup_mpl()
ASOF, CY = 20260630, (20250701, 20260630)

fps = t("fact_payment_schedule")
dso = (fps.gross_amount_usd * fps.settlement_lag_days).sum() / fps.gross_amount_usd.sum()
mk = t("dim_market")[["market_key", "market_name"]]
dso_mkt = fps.merge(mk, on="market_key").groupby("market_name").apply(
    lambda x: (x.gross_amount_usd * x.settlement_lag_days).sum() / x.gross_amount_usd.sum(),
    include_groups=False).sort_values()

snap = t("fact_inventory_snapshot")
inv = snap.groupby("snapshot_date_key").inventory_value_usd.sum().sort_index()
avg_inv_12 = inv.iloc[-12:].mean()
ol = t("fact_order_lines")
cogs = ol.loc[(ol.order_status != "cancelled") & ol.order_date_key.between(*CY), "cogs_usd"].sum()
po = t("fact_purchase_orders")
d = t("dim_date")[["date_key", "date"]]
mes = d.loc[d.date.dt.is_month_end, "date_key"].tolist()
ap = pd.Series({k: po.loc[(po.actual_receipt_date_key <= k) & (po.supplier_paid_date_key > k),
               "po_value_usd"].sum() for k in mes}).sort_index()
ap12 = ap[ap.index <= ASOF].iloc[-12:].mean()
dio = avg_inv_12 * 365 / cogs
dpo = ap12 * 365 / cogs
ccc = dio + dso - dpo

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 5), gridspec_kw={"width_ratios": [1.5, 1]})

# left: DIO / DSO / DPO / CCC as plain bars vs benchmark bands
items = [("DIO", dio, AMBER, (45, 75)), ("DSO", dso, BLUE, (2, 4)),
         ("DPO", dpo, GREEN, (30, 60)), ("CCC", ccc, NAVY, None)]
for i, (lab, v, c, bm) in enumerate(items):
    ax1.bar(i, v, color=c, width=0.62)
    ax1.text(i, v + 3, f"{v:.0f} d", ha="center", fontweight="bold")
    if bm:
        ax1.plot([i - .31, i + .31], [bm[1], bm[1]], color="black", lw=1.2)
        ax1.plot([i - .31, i + .31], [bm[0], bm[0]], color="black", lw=1.2)
        ax1.add_patch(plt.Rectangle((i - .31, bm[0]), .62, bm[1] - bm[0],
                                    color="black", alpha=0.10, zorder=0))
ax1.set_xticks(range(4))
ax1.set_xticklabels(["DIO\ninventory held", "DSO\norder → cash", "DPO\nsupplier terms", "CCC\n= DIO+DSO−DPO"])
ax1.set_ylabel("Days")
ax1.set_ylim(0, dio * 1.15)
ax1.set_title(f"CCC ≈ {ccc:.0f} days, and it is entirely inventory\n"
              f"DIO {dio:.0f}d is 2× the 45–75 benchmark; DSO & DPO are in range (grey bands)",
              loc="left", fontweight="bold", fontsize=11)
ax1.spines[["top", "right"]].set_visible(False)

# right: DSO by market
cols = [RED if m == "Brazil" else BLUE for m in dso_mkt.index]
ax2.barh(range(len(dso_mkt)), dso_mkt.values, color=cols)
ax2.set_yticks(range(len(dso_mkt))); ax2.set_yticklabels(dso_mkt.index)
for i, v in enumerate(dso_mkt.values):
    ax2.text(v + 0.5, i, f"{v:.1f} d", va="center", fontsize=9)
ax2.set_xlabel("DSO (amount-weighted settlement lag, days)")
ax2.set_title("Brazil DSO 3× the US — 12× installments\n(+ $114k/yr merchant-funded financing)",
              loc="left", fontweight="bold", fontsize=11)
ax2.spines[["top", "right"]].set_visible(False)

fig.suptitle("The working-capital problem is bigger than the P&L: ~$4.4M cash could be freed from inventory",
             fontweight="bold", fontsize=12.5, x=0.01, ha="left")
fig.tight_layout(rect=[0, 0, 1, 0.95])
p = OUT_FIGS / "2026-09_06_cash_conversion_cycle.png"
fig.savefig(p, dpi=150, bbox_inches="tight")
print("saved", p)
