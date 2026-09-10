"""Finding 05 - Discount leakage: how much margin goes to discounts, is it rising,
and do promo periods pay for themselves?

docs/06:
  Discounts (USD)     = SUM(fact_order_lines.discount_amount_usd)  order_status<>'cancelled'
  Gross Revenue (USD) = SUM(fact_order_lines.gross_amount_usd)     order_status<>'cancelled'
  Discount Rate %     = Discounts / Gross Revenue
Cuts: full/CY/PY, promo vs non-promo days (dim_date.is_promo_period), by promo_name,
by category, and monthly trend. Both tracks; parity asserted.
"""
from __future__ import annotations

import sys
import pathlib

import pandas as pd

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from utils import assert_close, duck, load_sql, t  # noqa: E402

CY = (20250701, 20260630)
PY = (20240701, 20250630)

# ---------- Python ----------
ol = t("fact_order_lines")
ol = ol[ol["order_status"] != "cancelled"].copy()
dd = t("dim_date")[["date_key", "date", "month_year", "is_promo_period", "promo_name", "yoy_period"]]
pr = t("dim_product")[["product_key", "category"]]
ol = ol.merge(dd, left_on="order_date_key", right_on="date_key", how="left").merge(pr, on="product_key", how="left")


def rate(df):
    g, d = df["gross_amount_usd"].sum(), df["discount_amount_usd"].sum()
    return g, d, d / g


full = rate(ol)
cy = rate(ol[ol["order_date_key"].between(*CY)])
py = rate(ol[ol["order_date_key"].between(*PY)])
promo = rate(ol[ol["is_promo_period"]])
nonpromo = rate(ol[~ol["is_promo_period"]])

by_promo_name = ol.groupby(ol["promo_name"].replace("", "(no promo)")).apply(
    lambda x: pd.Series(dict(zip(["gross", "disc", "rate"], rate(x)))), include_groups=False
).sort_values("gross", ascending=False)

by_cat = ol.groupby("category").apply(
    lambda x: pd.Series(dict(zip(["gross", "disc", "rate"], rate(x)))), include_groups=False
).sort_values("rate", ascending=False)

monthly = ol.groupby("month_year").apply(
    lambda x: pd.Series(dict(zip(["gross", "disc", "rate"], rate(x)))), include_groups=False
)

# promo lift: avg daily gross revenue & units, promo vs non-promo, per fiscal year
ol["net"] = ol["net_amount_usd"] - ol["refund_amount_usd"]
ol["gp"] = ol["net"] - ol["cogs_usd"]
daily = ol.groupby(["order_date_key", "is_promo_period"]).agg(
    gross=("gross_amount_usd", "sum"),
    units=("quantity", "sum"),
    disc=("discount_amount_usd", "sum"),
    net=("net", "sum"),
    gp=("gp", "sum"),
).reset_index()
lift = daily.groupby("is_promo_period").agg(
    days=("order_date_key", "nunique"),
    avg_daily_gross=("gross", "mean"),
    avg_daily_units=("units", "mean"),
    avg_daily_disc=("disc", "mean"),
    avg_daily_net=("net", "mean"),
    avg_daily_gp=("gp", "mean"),
)
n_promo_days = int(lift.loc[True, "days"])
gp_gap_per_day = lift.loc[True, "avg_daily_gp"] - lift.loc[False, "avg_daily_gp"]
promo_gp_impact = gp_gap_per_day * n_promo_days

# ---------- SQL ----------
con = duck()
Q = load_sql("05_discount_leakage")
con.execute(Q["base_view"])


def s_rate(key, params=None):
    r = con.execute(Q[key], params).df().iloc[0]
    return r.g, r.d, r.d / r.g


s_full = s_rate("rate_full")
s_cy = s_rate("rate_window", {"lo": CY[0], "hi": CY[1]})
s_py = s_rate("rate_window", {"lo": PY[0], "hi": PY[1]})
s_promo = s_rate("rate_promo")
s_nonpromo = s_rate("rate_nonpromo")
s_cat = con.execute(Q["by_cat"]).df()

# ---------- parity ----------
print("=== Finding 05 - discount leakage: parity ===")
for lbl, p, s in [("full", full, s_full), ("CY", cy, s_cy), ("PY", py, s_py),
                  ("promo days", promo, s_promo), ("non-promo days", nonpromo, s_nonpromo)]:
    assert_close(p[0], s[0], label=f"{lbl} gross")
    assert_close(p[1], s[1], label=f"{lbl} discounts")
    assert_close(p[2], s[2], rel=1e-6, abs_=1e-9, label=f"{lbl} discount rate")
for _, row in s_cat.iterrows():
    assert_close(float(by_cat.loc[row["category"], "rate"]), row["rate"], abs_=1e-9, label=f"cat rate {row['category']}")

# ---------- report ----------
pd.set_option("display.float_format", lambda x: f"{x:,.4f}")
print(f"\nDiscount rate  full {full[2]:.2%}   PY {py[2]:.2%}  ->  CY {cy[2]:.2%}")
print(f"Discounts $    full ${full[1]:,.0f}   PY ${py[1]:,.0f}  ->  CY ${cy[1]:,.0f}")
print(f"\nPromo days     rate {promo[2]:.2%}  on ${promo[0]:,.0f} gross  (${promo[1]:,.0f} discount)")
print(f"Non-promo days rate {nonpromo[2]:.2%} on ${nonpromo[0]:,.0f} gross")
print("\n--- by promo event ---")
print(by_promo_name)
print("\n--- by category ---")
print(by_cat)
print("\n--- promo vs non-promo daily averages ---")
print(lift)
lift_g = lift.loc[True, "avg_daily_gross"] / lift.loc[False, "avg_daily_gross"] - 1
lift_u = lift.loc[True, "avg_daily_units"] / lift.loc[False, "avg_daily_units"] - 1
print(f"\nPromo-day gross uplift vs baseline: {lift_g:+.1%}   units uplift: {lift_u:+.1%}")
print(f"Avg daily GROSS PROFIT  non-promo ${lift.loc[False,'avg_daily_gp']:,.0f}   promo ${lift.loc[True,'avg_daily_gp']:,.0f}")
print(f"GP gap per promo day: ${gp_gap_per_day:,.0f}   x {n_promo_days} promo days = ${promo_gp_impact:,.0f}")
print("  (naive counterfactual: promo days earned as if they were baseline days;")
print("   ignores pull-forward, new-customer acquisition and clearance value)")

out = pathlib.Path(__file__).resolve().parents[1] / "outputs" / "tables"
by_promo_name.to_csv(out / "05_discount_by_promo.csv")
by_cat.to_csv(out / "05_discount_by_category.csv")
monthly.to_csv(out / "05_discount_monthly.csv")
print(f"\nBacking tables -> {out}\nALL PARITY CHECKS PASSED")
