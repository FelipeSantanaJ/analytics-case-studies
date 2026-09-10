"""Finding 08 - Retention: repeat rate, cohort curves, and why returning revenue is only 16%.

docs/06 section 12:
  Repeat Purchase Rate % = (customers with >1 non-cancelled order) / (customers with >=1)
  Customers with Orders  = DISTINCTCOUNT(fact_orders.customer_key), is_cancelled = FALSE
Also: month-offset cohort retention (share of an acquisition-month cohort that orders again
n months later) and the new-vs-returning revenue split by calendar month.
Both tracks; parity asserted on the headline rates.
"""
from __future__ import annotations

import sys
import pathlib

import numpy as np
import pandas as pd

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from utils import assert_close, duck, load_sql, t  # noqa: E402

CY = (20250701, 20260630)

# ---------------- Python ----------------
fo = t("fact_orders")
fo = fo[~fo["is_cancelled"]].copy()
dd = t("dim_date")[["date_key", "date"]]
fo = fo.merge(dd, left_on="order_date_key", right_on="date_key", how="left")
fo["ym"] = fo["date"].dt.to_period("M")
mkt = t("dim_market")[["market_key", "market_name"]]
fo = fo.merge(mkt, on="market_key", how="left")

orders_per_cust = fo.groupby("customer_key")["order_id"].nunique()
repeat_rate_all = (orders_per_cust > 1).sum() / (orders_per_cust >= 1).sum()

# by market
rr_mkt = {}
for m, g in fo.groupby("market_name"):
    opc = g.groupby("customer_key")["order_id"].nunique()
    rr_mkt[m] = (opc > 1).sum() / len(opc)

# repeat rate within CY (customers with >1 CY order / customers with >=1 CY order)
cy_fo = fo[fo["order_date_key"].between(*CY)]
opc_cy = cy_fo.groupby("customer_key")["order_id"].nunique()
repeat_rate_cy = (opc_cy > 1).sum() / (opc_cy >= 1).sum()

# ---- cohort retention: acquisition month -> months later ----
first = fo.groupby("customer_key")["date"].min().rename("first_dt")
fo = fo.merge(first, on="customer_key", how="left")
fo["cohort"] = fo["first_dt"].dt.to_period("M")
fo["mo_offset"] = (fo["date"].dt.to_period("M") - fo["cohort"]).apply(lambda x: x.n)
cohort_sizes = fo.groupby("cohort")["customer_key"].nunique()
active = fo.groupby(["cohort", "mo_offset"])["customer_key"].nunique().unstack(fill_value=0)
retention = active.div(cohort_sizes, axis=0)
# average retention curve across cohorts with >=6 months of maturity
mature = retention.loc[retention.index <= pd.Period("2025-12", "M")]
avg_curve = mature.mean(axis=0)

# ---- new vs returning revenue by calendar month ----
ol = t("fact_order_lines")
ol = ol[ol["order_status"] != "cancelled"].copy()
ol["nr"] = ol["net_amount_usd"] - ol["refund_amount_usd"]
ol = ol.merge(dd, left_on="order_date_key", right_on="date_key", how="left")
ol["ym"] = ol["date"].dt.to_period("M")
# per (customer, month) is this the customer's first-ever order month?
firstmonth = fo.groupby("customer_key")["cohort"].first()
ol = ol.merge(firstmonth.rename("cohort"), on="customer_key", how="left")
ol["is_new_month"] = ol["ym"] == ol["cohort"]
rev_split = ol.groupby(["ym", "is_new_month"])["nr"].sum().unstack(fill_value=0.0)
rev_split.columns = ["returning", "new"]
rev_split["returning_pct"] = rev_split["returning"] / (rev_split["new"] + rev_split["returning"])

# ---------------- SQL ----------------
con = duck()
Q = load_sql("08_retention_cohorts")
s_rr = con.execute(Q["repeat_rate_full"]).fetchone()[0]
s_rr_cy = con.execute(Q["repeat_rate_cy"]).fetchone()[0]
s_cust_orders = con.execute(Q["customers_with_orders"]).fetchone()[0]

# ---------------- parity ----------------
print("=== Finding 08 - retention: parity ===")
assert_close(repeat_rate_all, s_rr, abs_=1e-9, label="Repeat Purchase Rate % (full window)")
assert_close(repeat_rate_cy, s_rr_cy, abs_=1e-9, label="Repeat Purchase Rate % (CY)")
assert_close((orders_per_cust >= 1).sum(), s_cust_orders, abs_=0, label="Customers with Orders")

# ---------------- report ----------------
print(f"\nCustomers with >=1 order      : {(orders_per_cust>=1).sum():,}")
print(f"Repeat Purchase Rate (full)   : {repeat_rate_all:.1%}   (benchmark 25-35%)")
print(f"Repeat Purchase Rate (CY only): {repeat_rate_cy:.1%}")
print(f"Avg orders per customer       : {orders_per_cust.mean():.2f}")
print("\nRepeat rate by market (full window):")
for m, v in sorted(rr_mkt.items(), key=lambda kv: -kv[1]):
    print(f"  {m:<16} {v:.1%}")
print("\nAvg cohort retention curve (share of acquisition cohort ordering again, by month offset):")
for k in [1, 2, 3, 4, 5, 6, 9, 12]:
    if k in avg_curve.index:
        print(f"  +{k:>2} mo : {avg_curve[k]:.1%}")
print("\nReturning-revenue share by calendar month (first & last 3, plus CY avg):")
print(rev_split["returning_pct"].head(3).to_string())
print("  ...")
print(rev_split["returning_pct"].tail(3).to_string())
cy_rows = rev_split.loc[rev_split.index >= pd.Period("2025-07", "M")]
print(f"\nCY returning-revenue share (avg of monthly): {cy_rows['returning_pct'].mean():.1%}")
print(f"CY returning revenue $ / total $          : "
      f"{cy_rows['returning'].sum()/(cy_rows['new'].sum()+cy_rows['returning'].sum()):.1%}")

out = pathlib.Path(__file__).resolve().parents[1] / "outputs" / "tables"
retention.round(4).to_csv(out / "08_cohort_retention_matrix.csv")
rev_split.round(2).to_csv(out / "08_new_vs_returning_revenue_monthly.csv")
avg_curve.round(4).to_csv(out / "08_avg_retention_curve.csv")
print(f"\nBacking tables -> {out}\nALL PARITY CHECKS PASSED")
