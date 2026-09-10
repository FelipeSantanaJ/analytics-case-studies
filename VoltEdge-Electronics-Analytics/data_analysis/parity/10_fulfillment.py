"""Finding 10 - Fulfilment: delivery speed, on-time %, and the shipping-cost drag (esp. UK).

docs/06 section 10:
  On-Time Delivery %      = distinct on-time delivered orders / Orders Delivered
  Avg Delivery Days       = AVERAGE(delivery_days) where is_delivered
  Perfect Order Rate %    = distinct perfect orders / Orders
  Shipping Cost (USD)     = SUM(shipping_cost_usd), non-cancelled
  Shipping Cost per Order = Shipping Cost / Orders
  Shipping Cost Recovery %= Shipping Fee Revenue / Shipping Cost
Cuts: full/CY/PY, by market, by carrier, Q4 vs rest. Both tracks; parity asserted.
"""
from __future__ import annotations

import sys
import pathlib

import pandas as pd

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from utils import assert_close, duck, load_sql, t  # noqa: E402

CY = (20250701, 20260630)
PY = (20240701, 20250630)

# ---------------- Python ----------------
fo = t("fact_orders")
fo = fo[~fo["is_cancelled"]].copy()
mk = t("dim_market")[["market_key", "market_name"]]
ca = t("dim_carrier")[["carrier_key", "carrier_name"]]
dd = t("dim_date")[["date_key", "date", "quarter"]]
fo = fo.merge(mk, on="market_key", how="left").merge(ca, on="carrier_key", how="left") \
       .merge(dd, left_on="order_date_key", right_on="date_key", how="left")


def kpis(df):
    orders = df["order_id"].nunique()
    deliv = df.loc[df["is_delivered"], "order_id"].nunique()
    ontime = df.loc[df["is_delivered"] & df["is_on_time"], "order_id"].nunique()
    perfect = df.loc[df["is_perfect_order"], "order_id"].nunique()
    ship_cost = df["shipping_cost_usd"].sum()
    ship_fee = df["shipping_fee_usd"].sum()
    return dict(
        orders=orders,
        avg_delivery_days=df.loc[df["is_delivered"], "delivery_days"].mean(),
        on_time_pct=ontime / deliv,
        perfect_order_pct=perfect / orders,
        ship_cost=ship_cost,
        ship_cost_per_order=ship_cost / orders,
        ship_recovery_pct=ship_fee / ship_cost,
    )


full = kpis(fo)
cy = kpis(fo[fo["order_date_key"].between(*CY)])
py = kpis(fo[fo["order_date_key"].between(*PY)])
by_mkt = fo.groupby("market_name").apply(lambda x: pd.Series(kpis(x)), include_groups=False)
by_carrier = fo.groupby("carrier_name").apply(lambda x: pd.Series(kpis(x)), include_groups=False)
q4 = fo[fo["quarter"] == 4]
non_q4 = fo[fo["quarter"] != 4]
q4_kpi, non_q4_kpi = kpis(q4), kpis(non_q4)

# ---------------- SQL ----------------
con = duck()
Q = load_sql("10_fulfillment")
con.execute(Q["o_view"])
s = con.execute(Q["kpis"]).df().iloc[0]
s_mkt = con.execute(Q["by_market"]).df().set_index("market_name")

# ---------------- parity ----------------
print("=== Finding 10 - fulfilment: parity ===")
for k in ["orders", "avg_delivery_days", "on_time_pct", "perfect_order_pct",
          "ship_cost", "ship_cost_per_order", "ship_recovery_pct"]:
    assert_close(full[k], s[k], rel=1e-6, abs_=1e-6, label=f"full {k}")
for m in by_mkt.index:
    assert_close(by_mkt.loc[m, "ship_cost_per_order"], float(s_mkt.loc[m, "ship_cost_per_order"]),
                 label=f"ship $/order {m}")
    assert_close(by_mkt.loc[m, "on_time_pct"], float(s_mkt.loc[m, "on_time_pct"]),
                 abs_=1e-9, label=f"on-time % {m}")

# ---------------- report ----------------
def line(name, d):
    print(f"  {name:<14} deliv {d['avg_delivery_days']:.1f}d | on-time {d['on_time_pct']:.1%} | "
          f"perfect {d['perfect_order_pct']:.1%} | ship $/order ${d['ship_cost_per_order']:.2f} | "
          f"recovery {d['ship_recovery_pct']:.0%}")


print("\nOverall / CY / PY:")
line("full", full); line("CY", cy); line("PY", py)
print("\nBy market:")
for m in by_mkt.sort_values("ship_cost_per_order", ascending=False).index:
    line(m, by_mkt.loc[m].to_dict())
print("\nBy carrier (top/bottom on-time):")
bc = by_carrier.sort_values("on_time_pct")
for m in list(bc.index[:3]) + list(bc.index[-3:]):
    line(m, by_carrier.loc[m].to_dict())
print("\nQ4 vs rest of year:")
line("Q4", q4_kpi); line("non-Q4", non_q4_kpi)

# UK shipping drag vs blended
uk = by_mkt.loc["United Kingdom"]
blended_spo = full["ship_cost_per_order"]
uk_excess = (uk["ship_cost_per_order"] - blended_spo) * uk["orders"]
print(f"\nUK ship $/order ${uk['ship_cost_per_order']:.2f} vs blended ${blended_spo:.2f} "
      f"-> ${uk_excess:,.0f} excess shipping cost over 24m on UK volume")
print(f"UK shipping-cost recovery {uk['ship_recovery_pct']:.0%} "
      f"(blended {full['ship_recovery_pct']:.0%})")

out = pathlib.Path(__file__).resolve().parents[1] / "outputs" / "tables"
by_mkt.to_csv(out / "10_fulfilment_by_market.csv")
by_carrier.to_csv(out / "10_fulfilment_by_carrier.csv")
print(f"\nBacking tables -> {out}\nALL PARITY CHECKS PASSED")
