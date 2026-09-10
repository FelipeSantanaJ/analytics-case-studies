"""Finding 03 - How thin is the margin, and is contribution margin at break-even?

Walks Net Revenue -> Gross Profit -> Contribution Margin per docs/06:
  Gross Profit (USD)        = Net Revenue - COGS + Returns COGS Recovered
  Total Payment Cost (USD)  = Payment Fees + Financing Cost (Interest-Free)
  Contribution Margin (USD) = Gross Profit - Marketing Spend - Shipping Cost - Total Payment Cost

Split: full window, CY vs PY, and by market (CY). Both tracks (pandas + DuckDB), parity asserted.
CY = 2025-07..2026-06, PY = 2024-07..2025-06 (by order_date_key / date_key).
"""
from __future__ import annotations

import sys
import pathlib

import pandas as pd

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from utils import assert_close, duck, load_sql, t  # noqa: E402

CY = (20250701, 20260630)
PY = (20240701, 20250630)


# --------------------------------------------------------------------------- #
# Python track
# --------------------------------------------------------------------------- #
def pyk(lo, hi):
    ol = t("fact_order_lines")
    ol = ol[ol["order_status"] != "cancelled"]
    ol = ol[ol["order_date_key"].between(lo, hi)]
    nr = (ol["net_amount_usd"] - ol["refund_amount_usd"]).sum()
    cogs = ol["cogs_usd"].sum()

    ret = t("fact_returns")
    ret = ret[ret["return_date_key"].between(lo, hi)]
    cogs_rec = ret["cogs_recovered_usd"].sum()

    gp = nr - cogs + cogs_rec

    mk = t("fact_marketing_spend")
    mktg = mk.loc[mk["date_key"].between(lo, hi), "cost_usd"].sum()

    fo = t("fact_orders")
    fo = fo[(~fo["is_cancelled"]) & fo["order_date_key"].between(lo, hi)]
    ship = fo["shipping_cost_usd"].sum()
    payfee = fo["payment_fee_usd"].sum()

    ps = t("fact_payment_schedule")
    fin = ps.loc[
        (ps["installment_plan"] == "Interest-Free") & ps["order_date_key"].between(lo, hi),
        "financing_cost_usd",
    ].sum()

    tpc = payfee + fin
    cm = gp - mktg - ship - tpc
    return dict(
        net_revenue=nr, cogs=cogs, cogs_recovered=cogs_rec, gross_profit=gp,
        gross_margin_pct=gp / nr, marketing=mktg, shipping=ship, payment_fees=payfee,
        financing=fin, total_payment_cost=tpc, contribution_margin=cm,
        contribution_margin_pct=cm / nr,
    )


full = pyk(1, 99999999)
cy = pyk(*CY)
py = pyk(*PY)

# by market, CY
ol = t("fact_order_lines")
ol = ol[(ol["order_status"] != "cancelled") & ol["order_date_key"].between(*CY)]
mk = t("dim_market")[["market_key", "market_name"]]
ol = ol.merge(mk, on="market_key")
gp_mkt = ol.assign(nr=ol.net_amount_usd - ol.refund_amount_usd).groupby("market_name").agg(
    nr=("nr", "sum"), cogs=("cogs_usd", "sum")
)
ret = t("fact_returns")
ret = ret[ret["return_date_key"].between(*CY)].merge(mk, on="market_key")
gp_mkt["cogs_rec"] = ret.groupby("market_name")["cogs_recovered_usd"].sum().reindex(gp_mkt.index).fillna(0)
ms = t("fact_marketing_spend")
ms = ms[ms["date_key"].between(*CY)].merge(mk, on="market_key")
gp_mkt["marketing"] = ms.groupby("market_name")["cost_usd"].sum().reindex(gp_mkt.index).fillna(0)
fo = t("fact_orders")
fo = fo[(~fo["is_cancelled"]) & fo["order_date_key"].between(*CY)].merge(mk, on="market_key")
gp_mkt["shipping"] = fo.groupby("market_name")["shipping_cost_usd"].sum().reindex(gp_mkt.index).fillna(0)
gp_mkt["payfee"] = fo.groupby("market_name")["payment_fee_usd"].sum().reindex(gp_mkt.index).fillna(0)
ps = t("fact_payment_schedule")
ps = ps[(ps["installment_plan"] == "Interest-Free") & ps["order_date_key"].between(*CY)].merge(mk, on="market_key")
gp_mkt["financing"] = ps.groupby("market_name")["financing_cost_usd"].sum().reindex(gp_mkt.index).fillna(0)
gp_mkt["gross_profit"] = gp_mkt.nr - gp_mkt.cogs + gp_mkt.cogs_rec
gp_mkt["contribution_margin"] = (
    gp_mkt.gross_profit - gp_mkt.marketing - gp_mkt.shipping - gp_mkt.payfee - gp_mkt.financing
)
gp_mkt["gm_pct"] = gp_mkt.gross_profit / gp_mkt.nr
gp_mkt["cm_pct"] = gp_mkt.contribution_margin / gp_mkt.nr

# --------------------------------------------------------------------------- #
# SQL track
# --------------------------------------------------------------------------- #
con = duck()
Q = load_sql("03_margin_to_breakeven")


def sqlk(lo, hi):
    r = con.execute(Q["walk"], {"lo": lo, "hi": hi}).df().iloc[0]
    gpv = r.nr - r.cogs + r.cogs_rec
    tpc = r.payfee + r.financing
    cmv = gpv - r.mktg - r.ship - tpc
    return dict(net_revenue=r.nr, cogs=r.cogs, cogs_recovered=r.cogs_rec, gross_profit=gpv,
                marketing=r.mktg, shipping=r.ship, payment_fees=r.payfee, financing=r.financing,
                total_payment_cost=tpc, contribution_margin=cmv)


s_full, s_cy, s_py = sqlk(1, 99999999), sqlk(*CY), sqlk(*PY)

# --------------------------------------------------------------------------- #
# Parity
# --------------------------------------------------------------------------- #
print("=== Finding 03 - margin walk: parity ===")
for lbl, p, s in [("FULL", full, s_full), ("CY", cy, s_cy), ("PY", py, s_py)]:
    for k in ["net_revenue", "cogs", "cogs_recovered", "gross_profit", "marketing",
              "shipping", "payment_fees", "financing", "total_payment_cost", "contribution_margin"]:
        assert_close(p[k], s[k], label=f"{lbl} {k}")

# --------------------------------------------------------------------------- #
# Report
# --------------------------------------------------------------------------- #
def show(name, d):
    print(f"\n--- {name} ---")
    print(f"  Net Revenue          {d['net_revenue']:>14,.0f}")
    print(f"  - COGS               {d['cogs']:>14,.0f}")
    print(f"  + Returns COGS recov  {d['cogs_recovered']:>13,.0f}")
    print(f"  = Gross Profit       {d['gross_profit']:>14,.0f}   ({d['gross_profit']/d['net_revenue']:.1%} margin)")
    print(f"  - Marketing          {d['marketing']:>14,.0f}")
    print(f"  - Shipping cost      {d['shipping']:>14,.0f}")
    print(f"  - Payment fees       {d['payment_fees']:>14,.0f}")
    print(f"  - Financing (sem juros){d['financing']:>12,.0f}")
    print(f"  = Contribution Margin{d['contribution_margin']:>14,.0f}   ({d['contribution_margin']/d['net_revenue']:.1%})")


show("FULL 24 months", full)
show("Current Year", cy)
show("Prior Year", py)

pd.set_option("display.float_format", lambda x: f"{x:,.0f}")
print("\n--- Contribution margin by market (CY) ---")
print(gp_mkt[["nr", "gross_profit", "gm_pct", "marketing", "shipping", "payfee",
             "financing", "contribution_margin", "cm_pct"]].sort_values("nr", ascending=False))

out = pathlib.Path(__file__).resolve().parents[1] / "outputs" / "tables"
pd.DataFrame([dict(scope="full", **full), dict(scope="CY", **cy), dict(scope="PY", **py)]).to_csv(
    out / "03_margin_walk.csv", index=False)
gp_mkt.to_csv(out / "03_contribution_margin_by_market_cy.csv")
print(f"\nBacking tables -> {out}")
print("\nALL PARITY CHECKS PASSED")
