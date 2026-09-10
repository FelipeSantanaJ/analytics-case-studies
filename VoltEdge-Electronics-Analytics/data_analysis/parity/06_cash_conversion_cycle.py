"""Finding 06 - Cash Conversion Cycle and the cash cost of Brazilian installments.

docs/06 section 11:
  DSO (days) = SUMX(fps, gross_amount_usd * settlement_lag_days) / SUM(gross_amount_usd)
  Avg Inventory Value = AVERAGEX(VALUES(snapshot_date_key), SUM(inventory_value_usd))
  COGS Trailing 12M   = COGS over the last 12 months (window ends 2026-06-30 -> = CY COGS)
  DIO (days) = Avg Inventory Value * 365 / COGS Trailing 12M
  Accounts Payable Open (USD) = SUM(po_value_usd) where actual_receipt_date_key <= asOf
                                                     AND supplier_paid_date_key   > asOf
  DPO (days) = AP Open * 365 / COGS Trailing 12M
  CCC (days) = DIO + DSO - DPO
asOf = max dim_date key in window = 20260630.
Both tracks; parity asserted.
"""
from __future__ import annotations

import sys
import pathlib

import pandas as pd

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from utils import assert_close, duck, load_sql, t  # noqa: E402

ASOF = 20260630
CY = (20250701, 20260630)

# ---------------- Python ----------------
fps = t("fact_payment_schedule")
mkt = t("dim_market")[["market_key", "market_name"]]
fps = fps.merge(mkt, on="market_key", how="left")

dso_all = (fps["gross_amount_usd"] * fps["settlement_lag_days"]).sum() / fps["gross_amount_usd"].sum()
dso_by_mkt = fps.groupby("market_name").apply(
    lambda x: (x["gross_amount_usd"] * x["settlement_lag_days"]).sum() / x["gross_amount_usd"].sum(),
    include_groups=False,
)
dso_by_plan = fps.groupby("installment_plan").apply(
    lambda x: (x["gross_amount_usd"] * x["settlement_lag_days"]).sum() / x["gross_amount_usd"].sum(),
    include_groups=False,
)

snap = t("fact_inventory_snapshot")
inv_by_date = snap.groupby("snapshot_date_key")["inventory_value_usd"].sum()
avg_inv_24 = inv_by_date.mean()
avg_inv_12 = inv_by_date.sort_index().iloc[-12:].mean()

ol = t("fact_order_lines")
cogs_12m = ol.loc[(ol["order_status"] != "cancelled") & ol["order_date_key"].between(*CY), "cogs_usd"].sum()

po = t("fact_purchase_orders")
ap_open = po.loc[(po["actual_receipt_date_key"] <= ASOF) & (po["supplier_paid_date_key"] > ASOF),
                 "po_value_usd"].sum()

# DPO measured three ways (the DAX point-in-time snapshot is noisy month-to-month)
import numpy as np  # noqa: E402
ddate = t("dim_date")[["date_key", "date"]]
month_ends = ddate.loc[ddate["date"].dt.is_month_end, "date_key"].tolist()
ap_series = pd.Series(
    {k: po.loc[(po["actual_receipt_date_key"] <= k) & (po["supplier_paid_date_key"] > k),
               "po_value_usd"].sum() for k in month_ends}
).sort_index()
ap_open_mean_12 = ap_series[ap_series.index <= ASOF].iloc[-12:].mean()
# receipt -> paid days (the real DPO behaviour). `days_to_pay` column = days PAST DUE (~1).
_po = po.merge(ddate.rename(columns={"date_key": "actual_receipt_date_key", "date": "_recv"}),
               on="actual_receipt_date_key", how="left") \
        .merge(ddate.rename(columns={"date_key": "supplier_paid_date_key", "date": "_paid"}),
               on="supplier_paid_date_key", how="left")
_po["recv_to_paid"] = (_po["_paid"] - _po["_recv"]).dt.days
wtd_recv_to_paid = float(np.average(_po["recv_to_paid"], weights=_po["po_value_usd"]))
wtd_past_due = float(np.average(po["days_to_pay"], weights=po["po_value_usd"]))
wtd_terms = float(np.average(po["payment_terms_days"], weights=po["po_value_usd"]))

dio_12 = avg_inv_12 * 365 / cogs_12m
dio_24 = avg_inv_24 * 365 / cogs_12m
dpo_pit = ap_open * 365 / cogs_12m                 # DAX-literal, point-in-time asOf
dpo_mean = ap_open_mean_12 * 365 / cogs_12m        # mean month-end AP, last 12
dpo_behav = wtd_recv_to_paid                       # value-weighted receipt -> paid days
dpo = dpo_mean                                     # primary
ccc_12 = dio_12 + dso_all - dpo
ccc_24 = dio_24 + dso_all - dpo

# cash that better inventory discipline would release (payables are already ~on terms)
inv_at_75_dio = cogs_12m * 75 / 365
cash_from_inventory = avg_inv_12 - inv_at_75_dio

# financing cost of interest-free installments (BR "sem juros")
fin_if = fps.loc[fps["installment_plan"] == "Interest-Free", "financing_cost_usd"].sum()
fin_if_cy = fps.loc[(fps["installment_plan"] == "Interest-Free") & fps["order_date_key"].between(*CY),
                    "financing_cost_usd"].sum()

# ---------------- SQL ----------------
con = duck()
Q = load_sql("06_cash_conversion_cycle")
s_dso = con.execute(Q["dso"]).fetchone()[0]
s_dso_mkt = con.execute(Q["dso_by_market"]).df().set_index("market_name")["dso"]
s_avg_inv_24 = con.execute(Q["avg_inv_24"]).fetchone()[0]
s_avg_inv_12 = con.execute(Q["avg_inv_12"]).fetchone()[0]
s_cogs_12m = con.execute(Q["cogs_12m"]).fetchone()[0]
s_ap_open = con.execute(Q["ap_open"]).fetchone()[0]

# ---------------- parity ----------------
print("=== Finding 06 - CCC: parity ===")
assert_close(dso_all, s_dso, label="DSO (days), all")
for m in dso_by_mkt.index:
    assert_close(dso_by_mkt[m], float(s_dso_mkt[m]), label=f"DSO - {m}")
assert_close(avg_inv_24, s_avg_inv_24, label="Avg Inventory Value (24m)")
assert_close(avg_inv_12, s_avg_inv_12, label="Avg Inventory Value (last 12m)")
assert_close(cogs_12m, s_cogs_12m, label="COGS trailing 12M")
assert_close(ap_open, s_ap_open, label="Accounts Payable Open (point-in-time)")

s_wdp = con.execute(Q["wtd_pay"]).fetchone()
assert_close(wtd_past_due, s_wdp[0], label="value-wtd days past due")
assert_close(wtd_terms, s_wdp[1], label="value-wtd payment_terms_days")

# ---------------- report ----------------
print(f"""
COGS trailing 12M                 ${cogs_12m:,.0f}
Avg inventory value (last 12m)    ${avg_inv_12:,.0f}   (24m: ${avg_inv_24:,.0f})
AP open @ {ASOF} (point-in-time)  ${ap_open:,.0f}
AP open mean month-end (last 12)  ${ap_open_mean_12:,.0f}
Supplier terms available (val-wtd) {wtd_terms:.1f} days | receipt->paid {wtd_recv_to_paid:.1f} days | paid {wtd_past_due:+.1f} days vs due

DIO (days)  = {dio_12:5.1f}   (24m basis: {dio_24:.1f})   [benchmark 45-75]
DSO (days)  = {dso_all:5.1f}                              [US/EU ~2-4, BR higher]
DPO (days)  = {dpo_mean:5.1f}   (point-in-time {dpo_pit:.1f} | receipt->paid {dpo_behav:.1f})   [benchmark 30-60]
--------------------------------
CCC (days)  = {ccc_12:5.1f}   (24m basis: {ccc_24:.1f})

--- cash that better inventory discipline would release ---
Inventory at DIO 75 would be     ${inv_at_75_dio:,.0f}   -> frees ${cash_from_inventory:,.0f}
(Payables already run ~{dpo_mean:.0f} days, within the 30-60 benchmark - no easy release there)

DSO by market:
""" + dso_by_mkt.round(1).to_string() + f"""

DSO by installment plan:
""" + dso_by_plan.round(1).to_string() + f"""

Interest-Free (merchant-funded) financing cost:  full ${fin_if:,.0f}   CY ${fin_if_cy:,.0f}
""")

out = pathlib.Path(__file__).resolve().parents[1] / "outputs" / "tables"
pd.DataFrame({
    "metric": ["DIO", "DSO", "DPO", "CCC"],
    "days": [dio_12, dso_all, dpo, ccc_12],
}).to_csv(out / "06_ccc_components.csv", index=False)
dso_by_mkt.round(2).to_csv(out / "06_dso_by_market.csv")
print(f"Backing tables -> {out}\nALL PARITY CHECKS PASSED")
