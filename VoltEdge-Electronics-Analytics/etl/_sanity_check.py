"""Ad-hoc sanity check on the curated star schema (not part of the pipeline)."""
import pandas as pd

pd.set_option("display.width", 200)
pd.set_option("display.max_columns", 40)
C = "../data/curated/"


def L(p):
    return pd.read_parquet(C + p + ".parquet")


fl = L("fact_order_lines"); fo = L("fact_orders")
dd = L("dim_date")[["date_key", "month_year", "year", "yoy_period"]]
dm = L("dim_market")[["market_key", "market_id", "is_comparable_base"]]
fl = fl.merge(dd, left_on="order_date_key", right_on="date_key").merge(dm, on="market_key")
fo = fo.merge(dd, left_on="order_date_key", right_on="date_key").merge(dm, on="market_key")
flx = fl[fl.order_status != "cancelled"]
fox = fo[fo.order_status != "cancelled"]

print("\n=== Net revenue / gross margin by market (USD, full 24m) ===")
g = flx.groupby("market_id").agg(net_M=("net_amount_usd", lambda s: s.sum() / 1e6),
                                 gp_M=("gross_profit_usd", lambda s: s.sum() / 1e6),
                                 units_k=("quantity", lambda s: s.sum() / 1e3))
g["gm_pct"] = (flx.groupby("market_id").gross_profit_usd.sum()
               / flx.groupby("market_id").net_amount_usd.sum() * 100)
print(g.round(2))

print("\n=== Totals ===")
net = flx.net_amount_usd.sum()
orders = fox.order_id.nunique()
print(f"orders (non-cancelled)     {orders:,}")
print(f"net revenue USD            {net/1e6:,.2f} M")
print(f"AOV                        {net/orders:,.2f}")
print(f"units/order                {flx.quantity.sum()/orders:,.2f}")
print(f"blended gross margin       {flx.gross_profit_usd.sum()/net*100:,.1f} %")
print(f"discount rate              {flx.discount_amount_usd.sum()/flx.gross_amount_usd.sum()*100:,.1f} %")
print(f"return rate (units)        {fl.returned_qty.sum()/fl.quantity.sum()*100:,.1f} %")
print(f"warranty attach (lines)    {(fl.line_type=='warranty').sum()/fo.order_id.nunique()*100:,.1f} % of orders")

print("\n=== YoY: Total vs Comparable Base (US) — Net Revenue USD ===")
w = flx[flx.yoy_period.isin(["CY", "PY"])]
tot = w.groupby("yoy_period").net_amount_usd.sum()
cmp = w[w.is_comparable_base].groupby("yoy_period").net_amount_usd.sum()
print(f"TOTAL       PY {tot['PY']/1e6:6.2f}M  CY {tot['CY']/1e6:6.2f}M  YoY {(tot['CY']/tot['PY']-1)*100:+.1f}%")
print(f"COMPARABLE  PY {cmp['PY']/1e6:6.2f}M  CY {cmp['CY']/1e6:6.2f}M  YoY {(cmp['CY']/cmp['PY']-1)*100:+.1f}%")
print(f"expansion contribution CY  {(tot['CY']-cmp['CY'])/1e6:.2f}M")

print("\n=== Payments ===")
print(f"payment fee / gross        {fo.payment_fee_usd.sum()/fo.gross_amount_usd.sum()*100:.2f} %")
ps = L("fact_payment_schedule")
print(f"schedule rows              {len(ps):,}")
print(f"financing cost USD (total) {ps.financing_cost_usd.sum():,.0f}")
print(f"avg settlement lag (days)  {(ps.settlement_lag_days*ps.gross_amount_usd).sum()/ps.gross_amount_usd.sum():.1f}")
brps = ps.merge(dm, on="market_key")
brps = brps[brps.market_id == "BR"]
print(f"BR avg install#            {(brps.n_installments*brps.gross_amount_usd).sum()/brps.gross_amount_usd.sum():.1f}")

print("\n=== Marketing ===")
fm = L("fact_marketing_spend")
spend = fm.cost_usd.sum()
dc = L("dim_customer")
ncust = int((dc.lifetime_orders >= 1).sum())
print(f"total spend USD            {spend/1e6:,.2f} M")
print(f"MER (netrev/spend)         {net/spend:,.1f} x")
print(f"customers w/ >=1 order     {ncust:,}")
print(f"blended CAC (spend/cust)   {spend/ncust:,.1f}")
print(f"repeat rate                {(dc.lifetime_orders>=2).sum()/max(1,ncust)*100:,.1f} %")
print(f"avg orders / customer      {dc.lifetime_orders.sum()/max(1,ncust):,.2f}")

print("\n=== Inventory / working capital ===")
snap = L("fact_inventory_snapshot")
last_m = snap.month_year.max()
ls = snap[snap.month_year == last_m]
print(f"latest snapshot month      {last_m}")
print(f"inventory value USD        {ls.inventory_value_usd.sum()/1e6:,.2f} M")
print(f"snapshot rows w/ variance  {(snap.snapshot_variance_units.fillna(0).abs()>0).sum():,} / {len(snap):,}")
po = L("fact_purchase_orders")
print(f"PO value USD (all)         {po.po_value_usd.sum()/1e6:,.2f} M")
print(f"avg days_to_pay supplier   {po.days_to_pay.mean():,.1f}")

print("\n=== Monthly net revenue (USD M) ===")
print(flx.groupby("month_year").net_amount_usd.sum().div(1e6).round(3).to_string())

print("\n=== negative-margin lines? ===")
bad = flx[flx.line_type == "product"]
print(f"product lines with gross_profit_usd < 0: {(bad.gross_profit_usd<0).sum():,} "
      f"({(bad.gross_profit_usd<0).mean()*100:.1f}%)   min GM line: "
      f"{(bad.gross_profit_usd/bad.net_amount_usd).min():.2f}")
