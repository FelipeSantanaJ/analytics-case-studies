"""
Stage 03 — build the curated / gold star schema from the staging layer.

Reads data/staging/*, produces conformed dimensions with surrogate keys and additive
fact tables, converts every monetary column to USD at the transaction-date rate,
computes moving-average COGS, derives the payment-settlement schedule and the
month-end inventory snapshot from the movement ledger, and flags the US comparable base.

Every curated table is written as both Parquet and CSV to data/curated/.
"""

from __future__ import annotations

import datetime as dt

import numpy as np
import pandas as pd

import config as C
import utils as U

S = C.STAGING_DIR


def rd(name: str) -> pd.DataFrame:
    return pd.read_parquet(S / f"{name}.parquet")


def dkey(s) -> "pd.Series":
    d = pd.to_datetime(s)
    return (d.dt.year * 10000 + d.dt.month * 100 + d.dt.day).astype("Int64")


# =====================================================================================
# FX helper
# =====================================================================================

class FX:
    def __init__(self, fx: pd.DataFrame):
        self.m = {(r.date.date(), r.currency_code): r.rate_to_usd
                  for r in fx.itertuples(index=False)}
        self.last = {}
        for (d, c), r in self.m.items():
            self.last.setdefault(c, (d, r))
            if d > self.last[c][0]:
                self.last[c] = (d, r)

    def rate(self, d, ccy) -> float:
        if ccy == "USD":
            return 1.0
        if isinstance(d, (pd.Timestamp, dt.datetime)):
            d = d.date()
        return self.m.get((d, ccy)) or self.last.get(ccy, (None, 1.0))[1]

    def to_usd(self, amount_series, date_series, ccy_series) -> pd.Series:
        rates = [self.rate(d, c) for d, c in zip(pd.to_datetime(date_series).dt.date, ccy_series)]
        return pd.Series(np.asarray(amount_series, dtype="float64") * np.asarray(rates), index=amount_series.index)


# =====================================================================================
# Dimensions
# =====================================================================================

def build_dim_date() -> pd.DataFrame:
    U.section("dim_date")
    days = pd.date_range(C.DIM_DATE_START, C.DIM_DATE_END, freq="D")
    df = pd.DataFrame({"date": days})
    df["date_key"] = dkey(df["date"])
    df["year"] = df["date"].dt.year
    df["quarter"] = df["date"].dt.quarter
    df["quarter_name"] = df["year"].astype(str) + "-Q" + df["quarter"].astype(str)
    df["month"] = df["date"].dt.month
    df["month_name"] = df["date"].dt.strftime("%b")
    df["month_year"] = df["date"].dt.strftime("%Y-%m")
    df["month_start_date"] = df["date"].values.astype("datetime64[M]")
    df["day_of_month"] = df["date"].dt.day
    df["day_of_week"] = df["date"].dt.weekday + 1
    df["day_name"] = df["date"].dt.strftime("%a")
    df["is_weekend"] = df["day_of_week"] >= 6
    df["iso_week"] = df["date"].dt.isocalendar().week.astype(int)
    df["day_of_year"] = df["date"].dt.dayofyear
    # fiscal year starts 1 July (so FY2025 = Jul-2024..Jun-2025 = the prior comparison year)
    df["fiscal_year"] = np.where(df["month"] >= 7, df["year"] + 1, df["year"])
    df["fiscal_quarter"] = ((df["month"] - 7) % 12) // 3 + 1
    df["fiscal_period"] = ((df["month"] - 7) % 12) + 1
    # promo periods
    df["is_promo_period"] = False
    df["promo_name"] = ""
    for s, e, name, _ in C.PROMO_PERIODS:
        m = (df["date"] >= pd.Timestamp(s)) & (df["date"] <= pd.Timestamp(e))
        df.loc[m, "is_promo_period"] = True
        df.loc[m, "promo_name"] = name
    df["is_black_friday_week"] = False
    for yr in df["year"].unique():
        bf = U.black_friday(int(yr))
        m = (df["date"] >= pd.Timestamp(bf)) & (df["date"] < pd.Timestamp(bf) + pd.Timedelta(days=C.BF_WINDOW_DAYS))
        df.loc[m, "is_black_friday_week"] = True
    # relative-period flags vs the fixed extract window
    df["in_extract_window"] = (df["date"] >= pd.Timestamp(C.WINDOW_START)) & (df["date"] <= pd.Timestamp(C.WINDOW_END))
    df["yoy_period"] = np.where(df["date"] >= pd.Timestamp(C.CY_START), "CY",
                        np.where(df["date"] >= pd.Timestamp(C.PY_START), "PY", ""))
    U.write_curated(df, "dim_date")
    return df


def build_dim_market() -> pd.DataFrame:
    U.section("dim_market")
    region = {"US": "North America", "UK": "Europe", "DE": "Europe", "BR": "South America"}
    rows = []
    for i, (mid, mk) in enumerate(C.MARKETS.items(), start=1):
        rows.append({"market_key": i, "market_id": mid, "market_name": mk["name"],
                     "region": region[mid], "currency_code": mk["currency"],
                     "live_date": pd.Timestamp(mk["live_date"]),
                     "is_comparable_base": mk["is_comparable_base"]})
    df = pd.DataFrame(rows)
    U.write_curated(df, "dim_market")
    return df


def build_dim_currency() -> pd.DataFrame:
    U.section("dim_currency")
    meta = {"USD": ("US Dollar", "$"), "EUR": ("Euro", "€"),
            "GBP": ("Pound Sterling", "£"), "BRL": ("Brazilian Real", "R$")}
    df = pd.DataFrame([
        {"currency_key": i, "currency_code": c, "currency_name": meta[c][0],
         "currency_symbol": meta[c][1], "is_reporting_currency": c == C.REPORTING_CURRENCY}
        for i, c in enumerate(C.CURRENCIES, start=1)
    ])
    U.write_curated(df, "dim_currency")
    return df


def build_dim_channel() -> pd.DataFrame:
    U.section("dim_channel")
    grp = {"Paid Search": "Paid", "Paid Social": "Paid", "Display": "Paid",
           "Affiliate": "Paid", "Email": "Owned", "Direct": "Owned",
           "Organic Search": "Earned", "Referral": "Earned"}
    names = list(dict.fromkeys(list(C.ACQUISITION_CHANNEL_SHARE) + list(grp)))
    df = pd.DataFrame([
        {"channel_key": i, "channel_name": n, "channel_group": grp.get(n, "Other"),
         "is_paid": grp.get(n) == "Paid"}
        for i, n in enumerate(names, start=1)
    ])
    U.write_curated(df, "dim_channel")
    return df


def build_dim_payment_method() -> pd.DataFrame:
    U.section("dim_payment_method")
    rows = []
    for i, p in enumerate(C.PAYMENT_METHODS, start=1):
        rows.append({
            "payment_method_key": i, "method_name": p[0], "method_group": p[1],
            "card_scheme": p[2] or "n/a", "mdr_pct": p[3], "fixed_fee_local_nominal": p[4],
            "settlement_days": p[5], "installment_eligible": p[6], "max_installments": p[7],
            "available_markets": ",".join(p[8]),
        })
    rows.append({"payment_method_key": -1, "method_name": "Unknown", "method_group": "Unknown",
                 "card_scheme": "n/a", "mdr_pct": 0.0, "fixed_fee_local_nominal": 0.0,
                 "settlement_days": 2, "installment_eligible": False, "max_installments": 1,
                 "available_markets": ""})
    df = pd.DataFrame(rows)
    U.write_curated(df, "dim_payment_method")
    return df


def build_dim_carrier() -> pd.DataFrame:
    U.section("dim_carrier")
    rows, k = [], 0
    for mid, lst in C.CARRIERS.items():
        for name, days, ontime in lst:
            k += 1
            rows.append({"carrier_key": k, "carrier_name": name, "market_id": mid,
                         "baseline_transit_days": days, "baseline_on_time_rate": ontime})
    df = pd.DataFrame(rows)
    U.write_curated(df, "dim_carrier")
    return df


def build_dim_warehouse() -> pd.DataFrame:
    U.section("dim_warehouse")
    df = pd.DataFrame([
        {"warehouse_key": i, "warehouse_id": wid, "warehouse_name": w["name"],
         "market_id": w["market"], "region": w["region"]}
        for i, (wid, w) in enumerate(C.WAREHOUSES.items(), start=1)
    ])
    U.write_curated(df, "dim_warehouse")
    return df


def build_dim_supplier(stg_sup: pd.DataFrame) -> pd.DataFrame:
    U.section("dim_supplier")
    df = stg_sup.copy().reset_index(drop=True)
    df.insert(0, "supplier_key", np.arange(1, len(df) + 1))
    df["payment_terms_band"] = "Net " + df["payment_terms_days"].astype(str)
    df["reliability_band"] = pd.cut(df["on_time_rate"], [0, 0.88, 0.94, 1.01],
                                    labels=["Low", "Medium", "High"])
    U.write_curated(df, "dim_supplier")
    return df


def build_dim_product(stg_prod, stg_cost, dim_sup) -> pd.DataFrame:
    U.section("dim_product")
    df = stg_prod.copy().reset_index(drop=True)
    df.insert(0, "product_key", np.arange(1, len(df) + 1))
    df["is_active_at_window_end"] = df["discontinue_date"].isna() | \
        (df["discontinue_date"] > pd.Timestamp(C.WINDOW_END))
    df["price_tier"] = (df.groupby("category")["list_price_usd"]
                        .transform(lambda s: pd.qcut(s.rank(method="first"), 3,
                                                     labels=["Budget", "Mid", "Premium"])))
    df = df.merge(dim_sup[["supplier_key", "supplier_id"]], on="supplier_id", how="left")
    stub = {c: (None if df[c].dtype == object else np.nan) for c in df.columns}
    stub.update({"product_key": -1, "sku_id": "UNKNOWN", "product_name": "Unknown / late-arriving SKU",
                 "category": "Unknown", "subcategory": "Unknown", "brand": "Unknown",
                 "list_price_usd": 0.0, "is_warranty_eligible": False,
                 "is_active_at_window_end": False, "price_tier": "Unknown", "supplier_key": -1})
    df = pd.concat([df, pd.DataFrame([stub])], ignore_index=True)
    U.write_curated(df, "dim_product")
    return df


def build_dim_small(name, values, key_col, val_col, extra=None) -> pd.DataFrame:
    rows = []
    for i, v in enumerate(values, start=1):
        r = {key_col: i, val_col: v}
        if extra:
            r.update(extra(v))
        rows.append(r)
    df = pd.DataFrame(rows)
    U.write_curated(df, name)
    return df


# =====================================================================================
# Moving-average COGS
# =====================================================================================

def build_cost_curves(stg_po, stg_cost, stg_mov):
    """Return {sku_id: (sorted_dates[np.datetime64], avg_cost[np.array])} from receipts."""
    opening_cost = (stg_cost.sort_values("effective_date")
                    .groupby("sku_id")["unit_cost_usd"].first().to_dict())
    events = {}
    # opening balances (adjustment) valued at earliest known cost
    op = stg_mov[stg_mov["movement_type"] == "adjustment"]
    for r in op.itertuples(index=False):
        events.setdefault(r.sku_id, []).append(
            (pd.Timestamp(r.movement_date), r.quantity, opening_cost.get(r.sku_id, 1.0)))
    # PO receipts at their PO unit cost
    for r in stg_po.itertuples(index=False):
        events.setdefault(r.sku_id, []).append(
            (pd.Timestamp(r.actual_receipt_date), int(r.qty_ordered), float(r.unit_cost_usd)))

    curves = {}
    for sku, evs in events.items():
        evs.sort(key=lambda x: x[0])
        tot_q = tot_v = 0.0
        ds, cs = [], []
        for d, q, c in evs:
            tot_q += q
            tot_v += q * c
            avg = tot_v / tot_q if tot_q else c
            ds.append(np.datetime64(d))
            cs.append(avg)
        curves[sku] = (np.array(ds), np.array(cs))
    return curves, opening_cost


def cost_asof(curves, opening_cost, cost_fallback, sku, when) -> float:
    w64 = np.datetime64(pd.Timestamp(when))
    if sku in curves:
        ds, cs = curves[sku]
        i = np.searchsorted(ds, w64, side="right") - 1
        if i >= 0:
            return float(cs[i])
        return float(cs[0])
    return float(opening_cost.get(sku, cost_fallback.get(sku, 1.0)))


# =====================================================================================
# Facts
# =====================================================================================

def build_facts(dims):
    fx = FX(rd("stg_fx_rates"))
    orders = rd("stg_orders")
    lines = rd("stg_order_lines")
    products = rd("stg_products")
    customers = rd("stg_customers")
    returns = rd("stg_returns")
    stg_po = rd("stg_purchase_orders")
    stg_mov = rd("stg_inventory_movements")
    stg_cost = rd("stg_cost_history")

    dim_date = dims["dim_date"]; dim_market = dims["dim_market"]
    dim_cur = dims["dim_currency"]; dim_chan = dims["dim_channel"]
    dim_prod = dims["dim_product"]; dim_cust = dims["dim_customer"]
    dim_wh = dims["dim_warehouse"]; dim_pm = dims["dim_payment_method"]
    dim_carrier = dims["dim_carrier"]; dim_supplier = dims["dim_supplier"]

    mkey = dim_market.set_index("market_id")["market_key"].to_dict()
    ckey = dim_cur.set_index("currency_code")["currency_key"].to_dict()
    chkey = dim_chan.set_index("channel_name")["channel_key"].to_dict()
    pkey = dim_prod.set_index("sku_id")["product_key"].to_dict()
    cust_key = dim_cust.set_index("customer_id")["customer_key"].to_dict()
    whkey = dim_wh.set_index("warehouse_id")["warehouse_key"].to_dict()
    pmkey = dim_pm.set_index("method_name")["payment_method_key"].to_dict()
    carkey = {(r.carrier_name, r.market_id): r.carrier_key for r in dim_carrier.itertuples(index=False)}
    supkey = dim_supplier.set_index("supplier_id")["supplier_key"].to_dict()

    # ---- COGS curves -----------------------------------------------------------
    U.section("moving-average COGS curves")
    curves, opening_cost = build_cost_curves(stg_po, stg_cost, stg_mov)
    cost_fallback = dict(zip(products["sku_id"],
                             products["list_price_usd"] * 0.85))
    U.log(f"  cost curves for {len(curves):,} SKUs")

    # =============================== fact_orders ===============================
    U.section("fact_orders")
    o = orders.copy()
    o["market_key"] = o["market"].map(mkey)
    o["currency_key"] = o["currency"].map(ckey)
    o["channel_key"] = o["channel"].map(chkey).fillna(-1).astype(int)
    o["warehouse_key"] = o["warehouse"].map(whkey).fillna(-1).astype(int)
    o["payment_method_key"] = o["payment_method"].map(pmkey).fillna(-1).astype(int)
    o["customer_key"] = o["customer_id"].map(cust_key).fillna(-1).astype(int)
    o["carrier_key"] = [carkey.get((c, m), -1) for c, m in zip(o["carrier"], o["market"])]
    o["order_date_key"] = dkey(o["order_date"])
    o["ship_date_key"] = dkey(o["ship_date"])
    o["delivery_date_key"] = dkey(o["delivered_date"])

    for col in ["gross_amount", "discount_amount", "net_amount", "tax_amount",
                "shipping_fee", "payment_fee"]:
        o[f"{col}_usd"] = fx.to_usd(o[f"{col}_local"], o["order_date"], o["currency"])
    o["shipping_cost_usd"] = o["shipping_cost_usd"]

    o["ship_days"] = (o["ship_date"] - o["order_date"]).dt.days
    o["delivery_days"] = (o["delivered_date"] - o["order_date"]).dt.days
    o["is_delivered"] = o["order_status"].eq("delivered")
    o["is_cancelled"] = o["order_status"].eq("cancelled")
    o["is_on_time"] = o["is_delivered"] & ~o["is_late"]

    returned_orders = set(returns.loc[returns["line_known"], "order_id"])
    o["has_return"] = o["order_id"].isin(returned_orders)
    o["is_perfect_order"] = o["is_delivered"] & o["is_on_time"] & ~o["has_return"]

    fact_orders = o[[
        "order_id", "order_date_key", "ship_date_key", "delivery_date_key",
        "customer_key", "market_key", "currency_key", "channel_key", "warehouse_key",
        "carrier_key", "payment_method_key", "order_status", "device",
        "installments", "installment_plan", "units",
        "gross_amount_local", "discount_amount_local", "net_amount_local",
        "tax_amount_local", "shipping_fee_local", "payment_fee_local",
        "gross_amount_usd", "discount_amount_usd", "net_amount_usd", "tax_amount_usd",
        "shipping_fee_usd", "payment_fee_usd", "shipping_cost_usd",
        "ship_days", "delivery_days", "is_late", "is_on_time", "is_delivered",
        "is_cancelled", "has_return", "is_perfect_order",
    ]].copy()
    U.write_curated(fact_orders, "fact_orders")

    # ============================ fact_order_lines ============================
    U.section("fact_order_lines")
    ol = lines.merge(
        o[["order_id", "order_date", "ship_date", "delivered_date", "market",
           "customer_key", "market_key", "currency_key", "channel_key", "warehouse_key",
           "payment_method_key", "order_status", "order_date_key", "ship_date_key",
           "delivery_date_key"]],
        on="order_id", how="inner")
    ol["product_key"] = ol["sku_id"].map(pkey).fillna(-1).astype(int)

    ol["gross_amount_usd"] = fx.to_usd(ol["gross_amount_local"], ol["order_date"], ol["currency"])
    ol["discount_amount_usd"] = fx.to_usd(ol["discount_amount_local"], ol["order_date"], ol["currency"])
    ol["net_amount_usd"] = fx.to_usd(ol["net_amount_local"], ol["order_date"], ol["currency"])

    # COGS: product lines via moving-avg cost; warranty lines via cost ratio
    prod_mask = ol["line_type"].eq("product")
    cogs = np.zeros(len(ol))
    sku_arr = ol["sku_id"].to_numpy()
    dt_arr = ol["order_date"].to_numpy()
    qty_arr = ol["quantity"].to_numpy()
    mkt_arr = ol["market"].to_numpy()
    idx = np.where(prod_mask.to_numpy())[0]
    for j in idx:
        cogs[j] = (qty_arr[j]
                   * cost_asof(curves, opening_cost, cost_fallback, sku_arr[j], dt_arr[j])
                   * C.MARKET_COGS_FACTOR.get(mkt_arr[j], 1.0))
    war = np.where(ol["line_type"].eq("warranty").to_numpy())[0]
    cogs[war] = ol["net_amount_usd"].to_numpy()[war] * C.WARRANTY_COST_PCT
    ol["cogs_usd"] = np.round(cogs, 4)
    ol["gross_profit_usd"] = ol["net_amount_usd"] - ol["cogs_usd"]

    # returns rollup to the line
    ret_line = (returns[returns["line_known"]]
                .groupby("order_line_id")
                .agg(returned_qty=("quantity", "sum"),
                     refund_amount_local=("refund_amount_local", "sum"))
                .reset_index())
    ol = ol.merge(ret_line, on="order_line_id", how="left")
    ol["returned_qty"] = ol["returned_qty"].fillna(0).astype(int)
    ol["is_returned"] = ol["returned_qty"] > 0
    ol["refund_amount_usd"] = fx.to_usd(ol["refund_amount_local"].fillna(0),
                                        ol["order_date"], ol["currency"])

    fact_lines = ol[[
        "order_line_id", "order_id", "line_type", "order_date_key", "ship_date_key",
        "delivery_date_key", "product_key", "customer_key", "market_key", "currency_key",
        "channel_key", "warehouse_key", "payment_method_key", "order_status",
        "quantity", "unit_price_local", "gross_amount_local", "discount_amount_local",
        "net_amount_local", "gross_amount_usd", "discount_amount_usd", "net_amount_usd",
        "cogs_usd", "gross_profit_usd", "returned_qty", "is_returned",
        "refund_amount_local", "refund_amount_usd",
    ]].copy()
    U.write_curated(fact_lines, "fact_order_lines")

    # ========================= fact_payment_schedule =========================
    U.section("fact_payment_schedule")
    pm_meta = {p[0]: p for p in C.PAYMENT_METHODS}
    rows = []
    oo = o[~o["is_cancelled"]]
    RESERVE_PCT, RESERVE_DAYS = 0.14, 75        # processor rolling reserve on card volume
    for r in oo.itertuples(index=False):
        meta = pm_meta.get(r.payment_method)
        settle = meta[5] if meta else 2
        grp = meta[1] if meta else "Card"
        n = max(1, int(r.installments))
        plan = r.installment_plan
        total_local = r.net_amount_local + r.tax_amount_local + r.shipping_fee_local
        fee_total = r.payment_fee_local
        # a rolling reserve is held back on card / wallet / BNPL and released at +90d
        held = RESERVE_PCT if grp in ("Card", "Digital Wallet", "BNPL") else 0.0
        tranche = total_local * (1 - held) / n
        for k in range(1, n + 1):
            due = r.order_date + pd.Timedelta(days=settle) if n == 1 \
                else r.order_date + pd.Timedelta(days=settle) + pd.DateOffset(months=k - 1)
            fee_k = fee_total / n
            fin_k = 0.0
            if plan == "Interest-Free" and n > 1:
                remaining = total_local * (n - k + 1) / n
                fin_k = remaining * C.MERCHANT_FINANCING_MONTHLY_PCT
            rows.append((r.order_id, r.market, r.currency, r.order_date, n, k, plan,
                         pd.Timestamp(due), tranche, fee_k, fin_k, tranche - fee_k - fin_k))
        if held > 0:
            rel = total_local * held
            due = r.order_date + pd.Timedelta(days=RESERVE_DAYS)
            rows.append((r.order_id, r.market, r.currency, r.order_date, n, 99,
                         "Reserve Release", pd.Timestamp(due), rel, 0.0, 0.0, rel))
    ps = pd.DataFrame(rows, columns=[
        "order_id", "market", "currency", "order_date", "n_installments",
        "installment_number", "installment_plan", "due_date", "gross_amount_local",
        "fee_amount_local", "financing_cost_local", "net_amount_local"])
    ps["market_key"] = ps["market"].map(mkey)
    ps["currency_key"] = ps["currency"].map(ckey)
    ps["order_date_key"] = dkey(ps["order_date"])
    ps["due_date_key"] = dkey(ps["due_date"])
    ps["settlement_lag_days"] = (ps["due_date"] - ps["order_date"]).dt.days
    for c in ["gross_amount", "fee_amount", "financing_cost", "net_amount"]:
        ps[f"{c}_usd"] = fx.to_usd(ps[f"{c}_local"], ps["order_date"], ps["currency"])
    ps = ps.drop(columns=["market", "currency", "order_date", "due_date"])
    U.write_curated(ps, "fact_payment_schedule")

    # ============================ fact_returns ===============================
    U.section("fact_returns")
    r = returns[returns["line_known"]].merge(
        lines[["order_line_id", "sku_id", "order_id"]], on="order_line_id", how="left",
        suffixes=("", "_l"))
    r = r.merge(o[["order_id", "market", "customer_key", "market_key",
                   "currency_key"]], on="order_id", how="left")
    r["product_key"] = r["sku_id"].map(pkey).fillna(-1).astype(int)
    r["return_date_key"] = dkey(r["return_date"])
    r["refund_amount_usd"] = fx.to_usd(r["refund_amount_local"], r["return_date"], r["currency"])
    # COGS of returned units recovered: restocked -> full moving-avg cost back;
    # scrapped -> 25% salvage. Nets out the double-count of returns in gross profit.
    mkfac = r["market"].map(C.MARKET_COGS_FACTOR).fillna(1.0)
    unit_cost = np.array([cost_asof(curves, opening_cost, cost_fallback, s, d)
                          for s, d in zip(r["sku_id"], r["return_date"])]) * mkfac
    r["unit_cost_usd"] = np.round(unit_cost, 4)
    r["cogs_recovered_usd"] = np.round(
        r["quantity"] * unit_cost * np.where(r["restocked"], 1.0, 0.25), 2)
    fact_returns = r[["return_id", "order_id", "order_line_id", "return_date_key",
                      "product_key", "customer_key", "market_key", "currency_key",
                      "quantity", "refund_amount_local", "refund_amount_usd",
                      "unit_cost_usd", "cogs_recovered_usd",
                      "reason", "restocked", "condition"]].rename(
        columns={"quantity": "returned_qty"})
    U.write_curated(fact_returns, "fact_returns")

    # ======================== fact_marketing_spend ==========================
    U.section("fact_marketing_spend")
    mkt = rd("stg_marketing_spend")
    mkt["market_key"] = mkt["market"].map(mkey)
    mkt["channel_key"] = mkt["channel"].map(chkey).fillna(-1).astype(int)
    mkt["date_key"] = dkey(mkt["date"])
    ccy_by_market = {m: v["currency"] for m, v in C.MARKETS.items()}
    mkt["currency"] = mkt["market"].map(ccy_by_market)
    mkt["cost_usd"] = fx.to_usd(mkt["cost_local"], mkt["date"], mkt["currency"])
    # campaign dim
    camp = (mkt[["campaign", "market", "channel"]].drop_duplicates().reset_index(drop=True))
    camp.insert(0, "campaign_key", np.arange(1, len(camp) + 1))
    camp["campaign_theme"] = camp["campaign"].str.split("_").str[-1]
    U.write_curated(camp.rename(columns={"market": "market_id"}), "dim_campaign")
    ck = camp.set_index(["campaign", "market", "channel"])["campaign_key"].to_dict()
    mkt["campaign_key"] = [ck.get((a, b, c), -1) for a, b, c in
                           zip(mkt["campaign"], mkt["market"], mkt["channel"])]
    fact_mkt = mkt[["date_key", "market_key", "channel_key", "campaign_key",
                    "impressions", "clicks", "cost_local", "cost_usd"]].copy()
    U.write_curated(fact_mkt, "fact_marketing_spend")

    # ====================== fact_web_traffic_daily ==========================
    U.section("fact_web_traffic_daily")
    web = rd("stg_web_traffic")
    web["market_key"] = web["market"].map(mkey)
    web["channel_key"] = web["channel"].map(chkey).fillna(-1).astype(int)
    web["date_key"] = dkey(web["date"])
    fact_web = web[["date_key", "market_key", "channel_key", "device", "sessions",
                    "users", "pageviews", "bounces", "add_to_carts", "carts_created",
                    "transactions", "had_data_anomaly"]].copy()
    U.write_curated(fact_web, "fact_web_traffic_daily")

    # ========================= fact_purchase_orders =========================
    U.section("fact_purchase_orders")
    po = stg_po.copy()
    po["product_key"] = po["sku_id"].map(pkey).fillna(-1).astype(int)
    po["supplier_key"] = po["supplier_id"].map(supkey).fillna(-1).astype(int)
    po["warehouse_key"] = po["destination_warehouse"].map(whkey).fillna(-1).astype(int)
    po["market_key"] = po["market"].map(mkey)
    for c in ["order_date", "expected_receipt_date", "actual_receipt_date",
              "payment_due_date", "supplier_paid_date"]:
        po[f"{c}_key"] = dkey(po[c])
    po["days_to_pay"] = (po["supplier_paid_date"] - po["payment_due_date"]).dt.days
    fact_po = po[["po_number", "supplier_key", "product_key", "warehouse_key", "market_key",
                  "order_date_key", "expected_receipt_date_key", "actual_receipt_date_key",
                  "payment_due_date_key", "supplier_paid_date_key", "qty_ordered",
                  "unit_cost_usd", "po_value_usd", "payment_terms_days",
                  "late_receipt_days", "days_to_pay"]].copy()
    U.write_curated(fact_po, "fact_purchase_orders")

    # ======================= fact_inventory_movement ========================
    U.section("fact_inventory_movement")
    mv = stg_mov.copy()
    mv["product_key"] = mv["sku_id"].map(pkey).fillna(-1).astype(int)
    mv["warehouse_key"] = mv["warehouse"].map(whkey).fillna(-1).astype(int)
    mv["market_key"] = mv["market"].map(mkey)
    mv["movement_date_key"] = dkey(mv["movement_date"])
    mv["unit_cost_usd"] = [cost_asof(curves, opening_cost, cost_fallback, s, d)
                           * C.MARKET_COGS_FACTOR.get(m, 1.0)
                           for s, d, m in zip(mv["sku_id"], mv["movement_date"], mv["market"])]
    mv["value_usd"] = (mv["quantity"] * mv["unit_cost_usd"]).round(2)
    fact_mv = mv[["movement_id", "movement_date_key", "product_key", "warehouse_key",
                  "market_key", "movement_type", "quantity", "unit_cost_usd",
                  "value_usd"]].copy()
    U.write_curated(fact_mv, "fact_inventory_movement")

    # ======================= fact_inventory_snapshot ========================
    U.section("fact_inventory_snapshot (derived from the ledger)")
    led = mv.sort_values(["sku_id", "warehouse", "movement_date"], kind="stable").copy()
    led["running"] = led.groupby(["sku_id", "warehouse"])["quantity"].cumsum()
    month_ends = [U.month_end(m) for m in U.month_starts(C.WINDOW_START, C.WINDOW_END)]
    raw_snap = rd("stg_inventory_snapshots")[["snapshot_date", "sku_id", "warehouse", "units_on_hand"]]
    raw_map = {(pd.Timestamp(r.snapshot_date), r.sku_id, r.warehouse): r.units_on_hand
               for r in raw_snap.itertuples(index=False)}
    snaps = []
    for mend in month_ends:
        mend_ts = pd.Timestamp(mend)
        upto = led[led["movement_date"] <= mend_ts]
        bal = upto.groupby(["sku_id", "warehouse"]).agg(
            on_hand=("running", "last"), market=("market", "last")).reset_index()
        w8_start = mend_ts - pd.Timedelta(weeks=8)
        s8 = (led[(led["movement_type"] == "sale") & (led["movement_date"] > w8_start)
                  & (led["movement_date"] <= mend_ts)]
              .groupby(["sku_id", "warehouse"])["quantity"].sum().abs())
        in_transit = (stg_po[(pd.to_datetime(stg_po["order_date"]) <= mend_ts)
                             & (pd.to_datetime(stg_po["actual_receipt_date"]) > mend_ts)]
                      .groupby(["sku_id", "destination_warehouse"])["qty_ordered"].sum())
        for rr in bal.itertuples(index=False):
            oh = max(0, int(rr.on_hand)) if pd.notna(rr.on_hand) else 0
            avg_cost = (cost_asof(curves, opening_cost, cost_fallback, rr.sku_id, mend_ts)
                        * C.MARKET_COGS_FACTOR.get(rr.market, 1.0))
            wk = s8.get((rr.sku_id, rr.warehouse), 0) / 8.0
            snaps.append({
                "snapshot_date_key": U.date_key(mend), "month_year": mend.strftime("%Y-%m"),
                "sku_id": rr.sku_id, "product_key": pkey.get(rr.sku_id, -1),
                "warehouse_key": whkey.get(rr.warehouse, -1),
                "market_key": mkey.get(rr.market, None),
                "units_on_hand": oh,
                "moving_avg_cost_usd": round(avg_cost, 4),
                "inventory_value_usd": round(oh * avg_cost, 2),
                "units_in_transit": int(in_transit.get((rr.sku_id, rr.warehouse), 0)),
                "avg_weekly_units_sold": round(wk, 2),
                "weeks_of_cover": round(oh / wk, 1) if wk > 0 else None,
                "raw_snapshot_units": raw_map.get((mend_ts, rr.sku_id, rr.warehouse)),
            })
    fact_snap = pd.DataFrame(snaps)
    fact_snap["snapshot_variance_units"] = (
        fact_snap["raw_snapshot_units"] - fact_snap["units_on_hand"])
    U.write_curated(fact_snap, "fact_inventory_snapshot")

    # ========================= fact_support_tickets =========================
    U.section("fact_support_tickets")
    sup = rd("stg_support_tickets")
    sup["market_key"] = sup["market"].map(mkey)
    sup["customer_key"] = sup["customer_id"].map(cust_key).fillna(-1).astype(int)
    sup["created_date_key"] = dkey(pd.to_datetime(sup["created_ts"]).dt.normalize())
    sup["resolved_date_key"] = dkey(pd.to_datetime(sup["resolved_ts"]).dt.normalize())
    fact_sup = sup[["ticket_id", "order_id", "created_date_key", "resolved_date_key",
                    "market_key", "customer_key", "category", "priority",
                    "resolution_hours", "first_contact_resolution", "csat"]].copy()
    U.write_curated(fact_sup, "fact_support_tickets")

    # =========================== fact_exchange_rate =========================
    U.section("fact_exchange_rate")
    fxr = rd("stg_fx_rates").copy()
    fxr["date_key"] = dkey(fxr["date"])
    fxr["currency_key"] = fxr["currency_code"].map(ckey)
    fxr["rate_from_usd"] = 1.0 / fxr["rate_to_usd"]
    U.write_curated(fxr[["date_key", "currency_key", "currency_code", "rate_to_usd",
                         "rate_from_usd"]], "fact_exchange_rate")

    # =============================== fact_target ============================
    U.section("fact_target")
    tg = rd("stg_targets").copy()
    tg["market_key"] = tg["market"].map(mkey)
    tg["month_date_key"] = dkey(tg["month_date"])
    U.write_curated(tg[["month_date_key", "market_key", "metric", "target_value"]], "fact_target")

    return fact_orders, fact_lines


# =====================================================================================
# dim_customer needs fact aggregates -> built in two passes
# =====================================================================================

def build_dim_customer(stg_cust, dim_market) -> pd.DataFrame:
    U.section("dim_customer (pass 1)")
    df = stg_cust.copy().reset_index(drop=True)
    df.insert(0, "customer_key", np.arange(1, len(df) + 1))
    df = df.rename(columns={"market": "market_id"})
    df["acquisition_month"] = pd.to_datetime(df["signup_date"]).dt.strftime("%Y-%m")
    yr = pd.Timestamp.today().year
    df["age_band"] = pd.cut(yr - df["birth_year"],
                            [0, 25, 35, 45, 55, 200],
                            labels=["<25", "25-34", "35-44", "45-54", "55+"])
    df["country"] = df["market_id"].map(dim_market.set_index("market_id")["market_name"])
    stub = {c: (None if df[c].dtype == object else np.nan) for c in df.columns}
    stub.update({"customer_key": -1, "customer_id": "UNKNOWN", "full_name": "Unknown customer",
                 "market_id": None, "segment": "Unknown", "acquisition_channel": "Unknown",
                 "acquisition_month": None, "has_email": False, "marketing_consent": False,
                 "acquired_before_window": False})
    df = pd.concat([df, pd.DataFrame([stub])], ignore_index=True)
    return df


def enrich_dim_customer(dim_cust, fact_lines, fact_orders):
    U.section("dim_customer (pass 2 — lifetime metrics)")
    od = fact_orders.merge(
        pd.read_parquet(C.CURATED_DIR / "dim_date.parquet")[["date_key", "date"]],
        left_on="order_date_key", right_on="date_key", how="left")
    agg = (od[~od["is_cancelled"]]
           .groupby("customer_key")
           .agg(first_order_date=("date", "min"), last_order_date=("date", "max"),
                lifetime_orders=("order_id", "nunique"),
                lifetime_net_revenue_usd=("net_amount_usd", "sum"),
                lifetime_gross_profit_usd=("net_amount_usd", "sum"))  # placeholder, refined below
           .reset_index())
    gp = fact_lines.groupby("customer_key")["gross_profit_usd"].sum().rename(
        "lifetime_gross_profit_usd").reset_index()
    agg = agg.drop(columns=["lifetime_gross_profit_usd"]).merge(gp, on="customer_key", how="left")

    df = dim_cust.merge(agg, on="customer_key", how="left")
    df["lifetime_orders"] = df["lifetime_orders"].fillna(0).astype(int)
    df["lifetime_net_revenue_usd"] = df["lifetime_net_revenue_usd"].fillna(0.0)
    df["is_repeat_customer"] = df["lifetime_orders"] >= 2
    we = pd.Timestamp(C.WINDOW_END)
    days_since = (we - pd.to_datetime(df["last_order_date"])).dt.days
    df["customer_status"] = np.select(
        [df["lifetime_orders"].eq(0), days_since <= 90, days_since <= 365],
        ["Prospect", "Active", "Lapsed"], default="Churned")
    valid = df.loc[df["lifetime_net_revenue_usd"] > 0, "lifetime_net_revenue_usd"]
    if len(valid) > 10:
        q = valid.quantile([0.6, 0.9]).tolist()
        df["loyalty_tier"] = np.select(
            [df["lifetime_net_revenue_usd"] <= 0,
             df["lifetime_net_revenue_usd"] <= q[0],
             df["lifetime_net_revenue_usd"] <= q[1]],
            ["Standard", "Standard", "Silver"], default="Gold")
    else:
        df["loyalty_tier"] = "Standard"
    U.write_curated(df, "dim_customer")
    return df


# =====================================================================================
# main
# =====================================================================================

def main():
    U.section("VoltEdge Electronics — Stage 03: build curated star schema")
    dims = {}
    dims["dim_date"] = build_dim_date()
    dims["dim_market"] = build_dim_market()
    dims["dim_currency"] = build_dim_currency()
    dims["dim_channel"] = build_dim_channel()
    dims["dim_payment_method"] = build_dim_payment_method()
    dims["dim_carrier"] = build_dim_carrier()
    dims["dim_warehouse"] = build_dim_warehouse()
    dims["dim_supplier"] = build_dim_supplier(rd("stg_suppliers"))
    dims["dim_product"] = build_dim_product(rd("stg_products"), rd("stg_cost_history"),
                                            dims["dim_supplier"])
    dims["dim_customer"] = build_dim_customer(rd("stg_customers"), dims["dim_market"])

    # small dims
    build_dim_small("dim_return_reason", list(C.RETURN_REASONS), "return_reason_key", "reason")
    build_dim_small("dim_ticket_category", list(C.SUPPORT_CATEGORIES),
                    "ticket_category_key", "category")
    build_dim_small("dim_device", list(C.DEVICE_SHARE), "device_key", "device")
    build_dim_small("dim_order_status", ["delivered", "cancelled", "in_transit", "processing"],
                    "order_status_key", "order_status")
    build_dim_small("dim_metric", C.TARGET_METRICS, "metric_key", "metric")

    fact_orders, fact_lines = build_facts(dims)
    enrich_dim_customer(dims["dim_customer"], fact_lines, fact_orders)

    U.section("Stage 03 complete")
    U.log(f"curated star schema in {C.CURATED_DIR}")


if __name__ == "__main__":
    main()
