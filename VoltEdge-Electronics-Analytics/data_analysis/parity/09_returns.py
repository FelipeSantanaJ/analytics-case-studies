"""Finding 09 - Returns: rate, reasons, category concentration and the margin drag.

docs/06 section 13:
  Return Rate %  = SUM(fact_order_lines.returned_qty) / Units Sold
  Units Sold     = SUM(quantity) where order_status<>'cancelled' AND line_type='product'
  Return Value   = SUM(fact_returns.refund_amount_usd)
  Restock Rate % = SUM(returned_qty where restocked) / SUM(returned_qty)
Cuts: full/CY/PY, by category, by reason bucket, by market. Both tracks; parity asserted.
"""
from __future__ import annotations

import sys
import pathlib

import pandas as pd

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from utils import assert_close, duck, load_sql, t  # noqa: E402

CY = (20250701, 20260630)
PY = (20240701, 20250630)
CONTROLLABLE = {"Defective / not working", "Not as described", "Wrong item shipped",
                "Damaged in transit", "Arrived late"}  # ops/quality driven
CHOICE = {"Changed my mind", "Found better price"}      # customer-choice driven

# ---------------- Python ----------------
ol = t("fact_order_lines")
ol = ol[ol["order_status"] != "cancelled"].copy()
pr = t("dim_product")[["product_key", "category"]]
mk = t("dim_market")[["market_key", "market_name"]]
ol = ol.merge(pr, on="product_key", how="left").merge(mk, on="market_key", how="left")
prod = ol[ol["line_type"] == "product"]


def rr(df):
    u = df["quantity"].sum()
    rq = df["returned_qty"].sum()
    return u, rq, rq / u


units_full, rq_full, rate_full = rr(prod)
_, _, rate_cy = rr(prod[prod["order_date_key"].between(*CY)])
_, _, rate_py = rr(prod[prod["order_date_key"].between(*PY)])

by_cat = prod.groupby("category").apply(
    lambda x: pd.Series(dict(zip(["units", "ret_qty", "rate"], rr(x)))), include_groups=False
).sort_values("rate", ascending=False)
by_mkt = prod.groupby("market_name").apply(
    lambda x: pd.Series(dict(zip(["units", "ret_qty", "rate"], rr(x)))), include_groups=False
).sort_values("rate", ascending=False)

fr = t("fact_returns")
fr = fr.merge(pr, on="product_key", how="left").merge(mk, on="market_key", how="left")
refund_full = fr["refund_amount_usd"].sum()
cogs_rec_full = fr["cogs_recovered_usd"].sum()
restock_rate = fr.loc[fr["restocked"], "returned_qty"].sum() / fr["returned_qty"].sum()
by_reason = fr.groupby("reason").agg(returns=("return_id", "count"),
                                     qty=("returned_qty", "sum"),
                                     refund=("refund_amount_usd", "sum")).sort_values("refund", ascending=False)
ctrl_refund = fr.loc[fr["reason"].isin(CONTROLLABLE), "refund_amount_usd"].sum()
choice_refund = fr.loc[fr["reason"].isin(CHOICE), "refund_amount_usd"].sum()

# net margin drag = refund lost - cogs recovered  (returns reduce NR by refund; restock credits COGS)
net_drag_full = refund_full - cogs_rec_full

# ---------------- SQL ----------------
con = duck()
Q = load_sql("09_returns")
s_rate = con.execute(Q["return_rate_full"]).fetchone()[0]
s_refund, s_cogsrec = con.execute(Q["return_value"]).fetchone()
s_restock = con.execute(Q["restock_rate"]).fetchone()[0]
s_cat = con.execute(Q["by_cat"]).df()

# ---------------- parity ----------------
print("=== Finding 09 - returns: parity ===")
assert_close(rate_full, s_rate, abs_=1e-9, label="Return Rate % (full)")
assert_close(refund_full, s_refund, label="Return Value (USD)")
assert_close(cogs_rec_full, s_cogsrec, label="Returns COGS Recovered (USD)")
assert_close(restock_rate, s_restock, abs_=1e-9, label="Restock Rate %")
for _, row in s_cat.iterrows():
    assert_close(float(by_cat.loc[row["category"], "rate"]), row["rate"], abs_=1e-9,
                 label=f"return rate {row['category']}")

# ---------------- report ----------------
print(f"\nReturn Rate %   full {rate_full:.1%}   PY {rate_py:.1%}  ->  CY {rate_cy:.1%}   (benchmark 7-12%)")
print(f"Returned units  {rq_full:,.0f} of {units_full:,.0f} sold")
print(f"Refund value    ${refund_full:,.0f}   |  COGS recovered ${cogs_rec_full:,.0f}  |  net margin drag ${net_drag_full:,.0f}")
print(f"Restock rate     {restock_rate:.1%}   (the rest -> quarantine, written down)")
print("\n-- by category --"); print(by_cat.assign(rate=lambda d: (d["rate"]*100).round(1)))
print("\n-- by market --");   print(by_mkt.assign(rate=lambda d: (d["rate"]*100).round(1)))
print("\n-- by reason --");   print(by_reason)
print(f"\nOps/quality-driven refunds (controllable): ${ctrl_refund:,.0f} ({ctrl_refund/refund_full:.0%})")
print(f"Customer-choice refunds:                   ${choice_refund:,.0f} ({choice_refund/refund_full:.0%})")

out = pathlib.Path(__file__).resolve().parents[1] / "outputs" / "tables"
by_cat.to_csv(out / "09_return_rate_by_category.csv")
by_reason.to_csv(out / "09_returns_by_reason.csv")
by_mkt.to_csv(out / "09_return_rate_by_market.csv")
print(f"\nBacking tables -> {out}\nALL PARITY CHECKS PASSED")
