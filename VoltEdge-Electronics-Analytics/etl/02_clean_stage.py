"""
Stage 02 — clean & conform the raw layer into staging / silver.

Reads data/raw/*, applies parsing, typing, de-duplication, standardization and
identity resolution, and writes typed Parquet tables to data/staging/. Every fix is
counted and written as a Markdown fragment to data/quality/_fragments/ for the final
DQ report.

Staging outputs (Parquet)
-------------------------
stg_fx_rates · stg_suppliers · stg_products · stg_cost_history · stg_price_history
stg_customers · stg_orders · stg_order_lines · stg_order_line_rejects
stg_psp_transactions · stg_purchase_orders · stg_inventory_movements
stg_inventory_snapshots · stg_returns · stg_web_traffic · stg_marketing_spend
stg_support_tickets · stg_shipments · stg_carrier_events · stg_targets
"""

from __future__ import annotations

import datetime as dt
import json
import re

import numpy as np
import pandas as pd

import config as C
import utils as U

DQ: list[dict] = []


def flag(check: str, detail: str, count: int, severity: str = "info") -> None:
    DQ.append({"check": check, "detail": detail, "count": int(count), "severity": severity})
    U.log(f"  · {check}: {detail} = {count:,}")


# --------------------------------------------------------------------------------------
# parsing helpers
# --------------------------------------------------------------------------------------

_MONEY_RE = re.compile(r"[^\d,.\-]")

def parse_money(x) -> float:
    """Locale-tolerant money parser: '$ 1,299.00', '1.299,00', 'R$ 1.299,00', '', 12.5."""
    if x is None or (isinstance(x, float) and np.isnan(x)):
        return np.nan
    if isinstance(x, (int, float)):
        return float(x)
    s = _MONEY_RE.sub("", str(x)).strip()
    if not s or s in {"-", ".", ","}:
        return np.nan
    if "," in s and "." in s:
        # last separator is the decimal one
        if s.rfind(",") > s.rfind("."):
            s = s.replace(".", "").replace(",", ".")
        else:
            s = s.replace(",", "")
    elif "," in s:
        # comma only -> decimal if it looks like ",dd", else thousands
        s = s.replace(",", ".") if re.search(r",\d{1,2}$", s) else s.replace(",", "")
    try:
        return float(s)
    except ValueError:
        return np.nan


_DATE_FORMATS = ["%Y-%m-%d", "%m/%d/%Y", "%d/%m/%Y", "%d-%b-%Y", "%Y-%m-%dT%H:%M:%S",
                 "%Y-%m-%d %H:%M:%S", "%m/%d/%Y %H:%M", "%d-%b-%Y %H:%M"]
_EXCEL_EPOCH = pd.Timestamp("1899-12-30")

def parse_dt(x):
    """Parse the several date/time encodings the raw layer emits (incl. Excel serials)."""
    if x is None or x == "" or (isinstance(x, float) and np.isnan(x)):
        return pd.NaT
    if isinstance(x, (dt.date, dt.datetime, pd.Timestamp)):
        return pd.Timestamp(x)
    s = str(x).strip()
    for fmt in _DATE_FORMATS:
        try:
            return pd.Timestamp(dt.datetime.strptime(s, fmt))
        except ValueError:
            continue
    try:                                   # Excel serial number as string
        v = float(s)
        if 30000 < v < 80000:
            return _EXCEL_EPOCH + pd.Timedelta(days=v)
    except ValueError:
        pass
    return pd.to_datetime(s, errors="coerce", dayfirst=False)


def to_date(series):
    return pd.to_datetime(series.map(parse_dt)).dt.normalize()


def w(df: pd.DataFrame, name: str) -> None:
    U.write_parquet(df, C.STAGING_DIR / f"{name}.parquet")
    U.log(f"  staged {name}  ({len(df):,} rows, {len(df.columns)} cols)")


# --------------------------------------------------------------------------------------
# FX
# --------------------------------------------------------------------------------------

def stage_fx() -> pd.DataFrame:
    U.section("FX rates")
    raw = pd.read_csv(C.RAW_DIR / "fx_rates.csv")
    raw["date"] = to_date(raw["date"])                            # d/m/Y in the raw export
    raw = raw.rename(columns={"ccy": "currency_code", "usd_per_unit": "rate_to_usd"})
    raw["rate_to_usd"] = raw["rate_to_usd"].map(parse_money)

    full_days = pd.DataFrame({"date": pd.date_range(C.DIM_DATE_START, C.DIM_DATE_END, freq="D")})
    frames = [full_days.assign(currency_code="USD", rate_to_usd=1.0)]
    for cur in [c for c in C.CURRENCIES if c != "USD"]:
        sub = raw[raw["currency_code"] == cur][["date", "rate_to_usd"]].sort_values("date")
        merged = full_days.merge(sub, on="date", how="left")
        merged["rate_to_usd"] = merged["rate_to_usd"].ffill().bfill()
        frames.append(merged.assign(currency_code=cur))
    fx = pd.concat(frames, ignore_index=True)[["date", "currency_code", "rate_to_usd"]]
    flag("fx", "rows after fill to full calendar", len(fx))
    w(fx, "stg_fx_rates")
    return fx


# --------------------------------------------------------------------------------------
# Suppliers + products
# --------------------------------------------------------------------------------------

def _canon_category_map() -> dict:
    m = {}
    for canon, variants in C.CATEGORY_TYPOS.items():
        m[canon.lower()] = canon
        for v in variants:
            m[v.lower().strip()] = canon
    return m


def stage_suppliers() -> pd.DataFrame:
    U.section("Suppliers")
    df = pd.read_csv(C.RAW_DIR / "suppliers.csv")
    df["supplier_name"] = df["supplier_name"].str.strip()
    w(df, "stg_suppliers")
    return df


def stage_products():
    U.section("Products (ERP xlsx)")
    prod = pd.read_excel(C.RAW_DIR / "erp_products.xlsx", sheet_name="products")
    prod = prod.rename(columns={"SKU": "sku_id", "Description": "product_name"})
    prod["sku_id"] = prod["sku_id"].str.strip()

    cmap = _canon_category_map()
    raw_cat = prod["category"].astype(str).str.strip()
    prod["category"] = raw_cat.str.lower().map(cmap)
    unmapped = prod["category"].isna().sum()
    prod["category"] = prod["category"].fillna(raw_cat)
    flag("products", "category spellings normalized to canonical",
         (raw_cat != prod["category"]).sum(), "info")
    flag("products", "category values left unmapped", unmapped, "warn" if unmapped else "info")

    prod["brand"] = prod["brand"].astype(str).str.strip().str.title()
    prod["list_price_usd"] = prod["list_price_usd"].map(parse_money)
    prod["launch_date"] = to_date(prod["launch_date"])
    prod["discontinue_date"] = to_date(prod["discontinue_date"])
    prod["is_warranty_eligible"] = prod["is_warranty_eligible"].astype(bool)
    dup = prod["sku_id"].duplicated().sum()
    prod = prod.drop_duplicates("sku_id")
    flag("products", "duplicate SKU rows dropped", dup)

    cost = pd.read_excel(C.RAW_DIR / "erp_products.xlsx", sheet_name="cost_history")
    cost["effective_date"] = to_date(cost["effective_date"])
    price = pd.read_excel(C.RAW_DIR / "erp_products.xlsx", sheet_name="price_history")
    price["effective_date"] = to_date(price["effective_date"])

    w(prod, "stg_products")
    w(cost.sort_values(["sku_id", "effective_date"]), "stg_cost_history")
    w(price.sort_values(["sku_id", "effective_date"]), "stg_price_history")
    return prod, cost, price


# --------------------------------------------------------------------------------------
# Customers  (utf-8 file + latin-1 regional file)
# --------------------------------------------------------------------------------------

def stage_customers() -> pd.DataFrame:
    U.section("CRM customers")
    main = pd.read_csv(C.RAW_DIR / "crm_customers.csv", dtype=str, keep_default_na=False)
    # detect encoding of the regional file rather than assume
    br_path = C.RAW_DIR / "crm_customers_br.csv"
    enc = "utf-8"
    try:
        br_path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        enc = "latin-1"
    br = pd.read_csv(br_path, dtype=str, keep_default_na=False, encoding=enc)
    flag("customers", f"regional file decoded as {enc}", len(br))

    df = pd.concat([main, br], ignore_index=True)
    before = len(df)
    df = df.drop_duplicates()
    flag("customers", "exact duplicate rows dropped", before - len(df))
    dup_id = df["customer_id"].duplicated().sum()
    df = df.drop_duplicates("customer_id")
    flag("customers", "rows sharing customer_id dropped", dup_id)

    for col in ("full_name", "city", "state_region", "email", "segment", "acquisition_channel"):
        df[col] = df[col].astype(str).str.strip()
    df["full_name"] = df["full_name"].str.title()
    df["has_email"] = df["email"].str.contains("@", regex=False)
    flag("customers", "rows with no e-mail", (~df["has_email"]).sum(), "warn")
    df["signup_date"] = to_date(df["signup_date"])
    df["birth_year"] = pd.to_numeric(df["birth_year"], errors="coerce")
    df["marketing_consent"] = df["marketing_consent"].isin(["True", "true", "1", "TRUE"])
    df["acquired_before_window"] = df["signup_date"] < pd.Timestamp(C.WINDOW_START)
    w(df, "stg_customers")
    return df


# --------------------------------------------------------------------------------------
# Orders + order lines
# --------------------------------------------------------------------------------------

def stage_orders(customers: pd.DataFrame) -> pd.DataFrame:
    U.section("Orders (OMS)")
    df = pd.read_csv(C.RAW_DIR / "oms_orders.csv", dtype=str, keep_default_na=False)
    df["order_ts"] = df["order_ts"].map(parse_dt)
    bad_ts = df["order_ts"].isna().sum()
    df["order_date"] = pd.to_datetime(df["order_ts"]).dt.normalize()
    flag("orders", "unparseable order timestamps", bad_ts, "warn" if bad_ts else "info")

    for c in ("ship_date", "promised_date", "delivered_date"):
        df[c] = to_date(df[c])
    for c in ("gross_amount_local", "discount_amount_local", "net_amount_local",
              "tax_amount_local", "shipping_fee_local", "shipping_cost_usd",
              "payment_fee_local"):
        df[c] = df[c].map(parse_money)
    df["units"] = pd.to_numeric(df["units"], errors="coerce").fillna(0).astype(int)
    df["installments"] = pd.to_numeric(df["installments"], errors="coerce").fillna(1).astype(int)
    df["is_late"] = df["is_late"].isin(["True", "true", "1"])

    df["has_customer_id"] = df["customer_id"].str.len() > 0
    known = set(customers["customer_id"])
    df["customer_known"] = df["customer_id"].isin(known)
    flag("orders", "orders with blank customer_id", (~df["has_customer_id"]).sum(), "warn")
    flag("orders", "orders whose customer_id is not in CRM",
         (df["has_customer_id"] & ~df["customer_known"]).sum(), "warn")

    win = (df["order_date"] >= pd.Timestamp(C.WINDOW_START)) & \
          (df["order_date"] <= pd.Timestamp(C.WINDOW_END))
    flag("orders", "orders outside the extract window", (~win).sum(),
         "warn" if (~win).sum() else "info")
    w(df, "stg_orders")
    return df


def stage_order_lines(orders: pd.DataFrame, products: pd.DataFrame):
    U.section("Order lines (OMS)")
    df = pd.read_csv(C.RAW_DIR / "oms_order_lines.csv", dtype=str, keep_default_na=False)
    before = len(df)
    df = df.drop_duplicates()
    flag("order_lines", "exact duplicate lines dropped", before - len(df))

    df["quantity"] = pd.to_numeric(df["quantity"], errors="coerce")
    for c in ("unit_price_local", "discount_amount_local", "gross_amount_local", "net_amount_local"):
        df[c] = df[c].map(parse_money)

    neg = df["quantity"] <= 0
    rejects = df[neg].copy()
    rejects["reject_reason"] = "non-positive quantity"
    df = df[~neg].copy()
    flag("order_lines", "non-positive-qty lines moved to rejects", int(neg.sum()), "warn")

    df["order_known"] = df["order_id"].isin(set(orders["order_id"]))
    orphan = (~df["order_known"]).sum()
    flag("order_lines", "lines with no matching order", orphan, "warn" if orphan else "info")

    known_sku = set(products["sku_id"])
    df["sku_known"] = df["sku_id"].isin(known_sku)
    miss_sku = df.loc[~df["sku_known"], "sku_id"].nunique()
    flag("order_lines", "distinct SKUs missing from ERP master (late-arriving dim)",
         miss_sku, "warn" if miss_sku else "info")

    df["quantity"] = df["quantity"].astype(int)
    w(df, "stg_order_lines")
    w(rejects, "stg_order_line_rejects")
    return df


# --------------------------------------------------------------------------------------
# PSP
# --------------------------------------------------------------------------------------

def stage_psp(orders: pd.DataFrame):
    U.section("PSP transactions")
    df = pd.read_csv(C.RAW_DIR / "psp_transactions.csv", dtype=str, keep_default_na=False)
    df = df.rename(columns={"mdr_pct": "reported_fee_local", "ccy": "currency"})
    df["amount_local"] = df["amount"].map(parse_money)
    df["reported_fee_local"] = df["reported_fee_local"].map(parse_money)   # mislabeled column
    df["installments"] = pd.to_numeric(df["installments"], errors="coerce").fillna(1).astype(int)
    df["auth_ts"] = df["auth_ts"].map(parse_dt)
    df["order_matched"] = df["order_ref"].isin(set(orders["order_id"]))
    flag("psp", "transactions not matching any order", (~df["order_matched"]).sum(), "warn")
    orders_with_psp = orders["order_id"].isin(set(df["order_ref"]))
    flag("psp", "orders with no PSP transaction", int((~orders_with_psp).sum()), "warn")
    df = df.drop(columns=["amount"])
    w(df, "stg_psp_transactions")
    return df


# --------------------------------------------------------------------------------------
# Procurement + inventory
# --------------------------------------------------------------------------------------

def stage_purchase_orders():
    U.section("Purchase orders")
    df = pd.read_csv(C.RAW_DIR / "procurement_purchase_orders.csv")
    for c in ("order_date", "expected_receipt_date", "actual_receipt_date",
              "payment_due_date", "supplier_paid_date"):
        df[c] = to_date(df[c])
    df["late_receipt_days"] = (df["actual_receipt_date"] - df["expected_receipt_date"]).dt.days
    flag("purchase_orders", "PO lines received late", int((df["late_receipt_days"] > 0).sum()))
    w(df, "stg_purchase_orders")
    return df


def stage_inventory():
    U.section("Inventory (WMS)")
    mv = pd.read_csv(C.RAW_DIR / "wms_inventory_movements.csv")
    mv["movement_date"] = to_date(mv["movement_date"])
    w(mv, "stg_inventory_movements")

    sn = pd.read_csv(C.RAW_DIR / "wms_inventory_snapshots.csv")
    sn["snapshot_date"] = to_date(sn["snapshot_date"])
    # reconcile snapshot vs ledger running balance (stable sort so the running total
    # is deterministic when several movements share a date)
    led = mv.sort_values(["sku_id", "warehouse", "movement_date"], kind="stable").copy()
    led["running"] = led.groupby(["sku_id", "warehouse"])["quantity"].cumsum()
    recon = []
    for mend, grp in sn.groupby("snapshot_date"):
        upto = led[led["movement_date"] <= mend]
        bal = upto.groupby(["sku_id", "warehouse"])["running"].last().rename("ledger_qty")
        m = grp.merge(bal, on=["sku_id", "warehouse"], how="left")
        recon.append(m)
    rec = pd.concat(recon, ignore_index=True)
    rec["variance"] = rec["units_on_hand"] - rec["ledger_qty"].fillna(0)
    flag("inventory", "snapshot rows disagreeing with the movement ledger",
         int((rec["variance"].abs() > 0).sum()), "warn")
    w(rec, "stg_inventory_snapshots")
    return mv, rec


# --------------------------------------------------------------------------------------
# Returns
# --------------------------------------------------------------------------------------

def stage_returns(order_lines: pd.DataFrame):
    U.section("Returns")
    df = pd.read_csv(C.RAW_DIR / "returns.csv", dtype=str, keep_default_na=False)
    df["return_date"] = to_date(df["return_date"])
    df["quantity"] = pd.to_numeric(df["quantity"], errors="coerce").fillna(0).astype(int)
    df["refund_amount_local"] = df["refund_amount_local"].map(parse_money)
    df["restocked"] = df["restocked"].isin(["True", "true", "1"])
    df["line_known"] = df["order_line_id"].isin(set(order_lines["order_line_id"]))
    flag("returns", "return rows with no matching order line",
         int((~df["line_known"]).sum()), "warn" if (~df["line_known"]).any() else "info")
    w(df, "stg_returns")
    return df


# --------------------------------------------------------------------------------------
# Web analytics
# --------------------------------------------------------------------------------------

def stage_web():
    U.section("Web analytics")
    df = pd.read_csv(C.RAW_DIR / "web_analytics_daily.csv")
    df["date"] = to_date(df["date"])
    neg = df["sessions"] < 0
    flag("web", "rows with negative sessions (abs-corrected)", int(neg.sum()), "warn")
    df.loc[neg, "sessions"] = df.loc[neg, "sessions"].abs()
    df["had_data_anomaly"] = neg.values

    present = set(zip(df["date"].dt.date, df["market"]))
    missing = 0
    for market, mk in C.MARKETS.items():
        for d in U.date_range(max(mk["live_date"], C.WINDOW_START), C.WINDOW_END):
            if (d, market) not in present:
                missing += 1
    flag("web", "market-days with no web analytics rows at all", missing, "warn")
    w(df, "stg_web_traffic")
    return df


# --------------------------------------------------------------------------------------
# Marketing — union Google + Meta + other
# --------------------------------------------------------------------------------------

def stage_marketing():
    U.section("Marketing spend (union of 3 sources)")
    g = pd.read_csv(C.RAW_DIR / "google_ads_report.csv")
    g["date"] = to_date(g["date"])
    g["channel"] = np.where(g["campaign_type"].eq("Search"), "Paid Search", "Display")
    g = g.rename(columns={"cost": "cost_local"})
    g["source_system"] = "google_ads"
    g = g[["date", "market", "channel", "campaign", "impressions", "clicks",
           "cost_local", "currency", "source_system"]]

    m = pd.read_csv(C.RAW_DIR / "meta_ads_export.csv")
    m = m.rename(columns={"day": "date", "country": "market", "ad_campaign": "campaign",
                          "link_clicks": "clicks", "spend": "cost_local"})
    m["date"] = to_date(m["date"])
    m["channel"] = "Paid Social"
    m["source_system"] = "meta_ads"
    m = m[["date", "market", "channel", "campaign", "impressions", "clicks",
           "cost_local", "currency", "source_system"]]

    o = pd.read_csv(C.RAW_DIR / "other_marketing_spend.csv")
    rows = []
    for r in o.itertuples(index=False):
        mstart = pd.Timestamp(r.month + "-01")
        days = pd.date_range(mstart, mstart + pd.offsets.MonthEnd(0), freq="D")
        for d in days:
            rows.append({"date": d, "market": r.market, "channel": r.channel,
                         "campaign": f"{r.market}_{r.channel}_{r.cost_type}",
                         "impressions": 0, "clicks": 0,
                         "cost_local": r.amount_local / len(days), "currency": r.currency,
                         "source_system": "other_marketing"})
    o2 = pd.DataFrame(rows)

    mkt = pd.concat([g, m, o2], ignore_index=True)
    flag("marketing", "unified spend rows (google+meta+other)", len(mkt))
    w(mkt, "stg_marketing_spend")
    return mkt


# --------------------------------------------------------------------------------------
# Support
# --------------------------------------------------------------------------------------

def stage_support():
    U.section("Support tickets")
    df = pd.read_csv(C.RAW_DIR / "support_tickets.csv", dtype=str, keep_default_na=False)
    df["created_ts"] = df["created_ts"].map(parse_dt)
    df["resolved_ts"] = df["resolved_ts"].map(parse_dt)
    df["resolution_hours"] = (df["resolved_ts"] - df["created_ts"]).dt.total_seconds() / 3600
    df["first_contact_resolution"] = df["first_contact_resolution"].isin(["True", "true", "1"])
    df["csat"] = pd.to_numeric(df["csat"], errors="coerce")
    bad = (df["resolution_hours"] < 0).sum()
    flag("support", "tickets with negative resolution time", int(bad), "warn" if bad else "info")
    w(df, "stg_support_tickets")
    return df


# --------------------------------------------------------------------------------------
# Carrier tracking JSON -> events + shipment summary
# --------------------------------------------------------------------------------------

_STATUS_MAP = {
    "created": "created", "in_transit": "in_transit", "in transit": "in_transit",
    "out_for_delivery": "out_for_delivery", "out for delivery": "out_for_delivery",
    "delivered": "delivered", "delivery complete": "delivered",
}

def stage_carrier():
    U.section("Carrier tracking (JSON flatten)")
    obj = json.loads((C.RAW_DIR / "carrier_tracking.json").read_text(encoding="utf-8"))
    ev_rows, ship_rows = [], []
    vocab = set()
    for s in obj["shipments"]:
        norm_events = []
        for e in s["events"]:
            raw_status = str(e["status"]).strip()
            vocab.add(raw_status)
            st = _STATUS_MAP.get(raw_status.lower(), raw_status.lower().replace(" ", "_"))
            ts = parse_dt(e["ts"])
            norm_events.append((st, ts))
            ev_rows.append({"order_id": s["order_id"], "carrier": s["carrier"],
                            "status": st, "event_ts": ts, "location": e.get("location")})
        d = {st: ts for st, ts in norm_events}
        ship_rows.append({
            "order_id": s["order_id"], "carrier": s["carrier"],
            "tracking_number": s["tracking_number"], "service_level": s["service_level"],
            "created_ts": d.get("created"), "in_transit_ts": d.get("in_transit"),
            "out_for_delivery_ts": d.get("out_for_delivery"),
            "delivered_ts": d.get("delivered"),
            "n_events": len(norm_events),
        })
    flag("carrier", "distinct raw status strings collapsed to canonical vocab", len(vocab))
    w(pd.DataFrame(ev_rows), "stg_carrier_events")
    w(pd.DataFrame(ship_rows), "stg_shipments")


# --------------------------------------------------------------------------------------
# Targets
# --------------------------------------------------------------------------------------

def stage_targets():
    U.section("Finance targets")
    df = pd.read_csv(C.RAW_DIR / "finance_targets.csv")
    df["month_date"] = to_date(df["month"] + "-01")
    df["target_value"] = df["target_value"].map(parse_money)
    w(df, "stg_targets")
    return df


# --------------------------------------------------------------------------------------
# main
# --------------------------------------------------------------------------------------

def main():
    U.section("VoltEdge Electronics — Stage 02: clean & stage")
    stage_fx()
    stage_suppliers()
    products, _, _ = stage_products()
    customers = stage_customers()
    orders = stage_orders(customers)
    order_lines = stage_order_lines(orders, products)
    stage_psp(orders)
    stage_purchase_orders()
    stage_inventory()
    stage_returns(order_lines)
    stage_web()
    stage_marketing()
    stage_support()
    stage_carrier()
    stage_targets()

    dq = pd.DataFrame(DQ)
    U.dq_fragment("stage_02_cleaning", [
        "## Stage 02 — cleaning & conforming", "",
        f"_generated {dt.datetime.now():%Y-%m-%d %H:%M}_", "",
        "| check | detail | count | severity |",
        "|---|---|---:|---|",
        *[f"| {r.check} | {r.detail} | {r.count:,} | {r.severity} |"
          for r in dq.itertuples(index=False)],
    ])
    U.write_csv(dq, C.QUALITY_DIR / "stage_02_metrics.csv")
    U.section("Stage 02 complete")


if __name__ == "__main__":
    main()
