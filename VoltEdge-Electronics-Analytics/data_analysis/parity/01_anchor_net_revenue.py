"""Parity runner for finding 01 - anchor on Net Revenue (USD).

Runs the SAME logic on both tracks and asserts they agree:
  * Python : pandas over data/curated/fact_order_lines.parquet
  * SQL    : DuckDB over the same parquet file

Net Revenue (USD) = SUM(net_amount_usd) - SUM(refund_amount_usd)
                    filtered to order_status <> 'cancelled'   (docs/06)
"""
from __future__ import annotations

import sys
import pathlib

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from utils import assert_close, curated_path, duck, t  # noqa: E402

# --------------------------------------------------------------------------- #
# Python track
# --------------------------------------------------------------------------- #
ol = t("fact_order_lines")
ol_nc = ol[ol["order_status"] != "cancelled"]

py = {
    "order_lines": len(ol_nc),
    "orders": ol_nc["order_id"].nunique(),
    "gross_sales_usd": ol_nc["net_amount_usd"].sum(),
    "returns_usd": ol_nc["refund_amount_usd"].sum(),
}
py["net_revenue_usd"] = py["gross_sales_usd"] - py["returns_usd"]

# by market
dmkt = t("dim_market")[["market_key", "market_name"]]
py_mkt = (
    ol_nc.merge(dmkt, on="market_key", how="left")
    .assign(net=lambda d: d["net_amount_usd"] - d["refund_amount_usd"])
    .groupby("market_name")["net"]
    .sum()
    .sort_values(ascending=False)
)

# --------------------------------------------------------------------------- #
# SQL track
# --------------------------------------------------------------------------- #
con = duck()
sql = con.execute(
    f"""
    SELECT COUNT(*)                                               AS order_lines,
           COUNT(DISTINCT order_id)                               AS orders,
           SUM(net_amount_usd)                                    AS gross_sales_usd,
           SUM(refund_amount_usd)                                 AS returns_usd,
           SUM(net_amount_usd) - SUM(refund_amount_usd)           AS net_revenue_usd
    FROM read_parquet('{curated_path("fact_order_lines")}')
    WHERE order_status <> 'cancelled'
    """
).df().iloc[0]

sql_mkt = con.execute(
    f"""
    SELECT m.market_name,
           SUM(ol.net_amount_usd) - SUM(ol.refund_amount_usd) AS net_revenue_usd
    FROM read_parquet('{curated_path("fact_order_lines")}') ol
    JOIN read_parquet('{curated_path("dim_market")}') m ON m.market_key = ol.market_key
    WHERE ol.order_status <> 'cancelled'
    GROUP BY 1 ORDER BY 2 DESC
    """
).df()

# --------------------------------------------------------------------------- #
# Parity assertions
# --------------------------------------------------------------------------- #
print("=== Finding 01 - anchor on Net Revenue (USD) ===")
assert_close(py["order_lines"], sql["order_lines"], abs_=0, label="order_lines (non-cancelled)")
assert_close(py["orders"], sql["orders"], abs_=0, label="orders (non-cancelled)")
assert_close(py["gross_sales_usd"], sql["gross_sales_usd"], label="Gross Sales (USD)")
assert_close(py["returns_usd"], sql["returns_usd"], label="Returns (USD)")
assert_close(py["net_revenue_usd"], sql["net_revenue_usd"], label="Net Revenue (USD)")

for name in py_mkt.index:
    a = py_mkt[name]
    b = float(sql_mkt.loc[sql_mkt["market_name"] == name, "net_revenue_usd"].iloc[0])
    assert_close(a, b, label=f"Net Revenue (USD) - {name}")

print()
print(f"Net Revenue (USD), full 24-month window : {py['net_revenue_usd']:,.2f}")
print(f"  Gross Sales (USD)                     : {py['gross_sales_usd']:,.2f}")
print(f"  Returns (USD)                         : {py['returns_usd']:,.2f}")
print(f"  Orders (non-cancelled)               : {py['orders']:,}")
print(f"  AOV = Net Revenue / Orders           : {py['net_revenue_usd'] / py['orders']:,.2f}")
print()
print("By market:")
for name, v in py_mkt.items():
    print(f"  {name:<16} {v:,.2f}")
print("\nALL PARITY CHECKS PASSED")
