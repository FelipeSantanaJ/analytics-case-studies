"""
Stage 01 — generate the raw / bronze layer.

Writes messy, multi-source "system exports" to data/raw/. Everything is derived
deterministically from config.SEED. Downstream stages never write here.

Outputs
-------
fx_rates.csv                       Finance      daily USD-per-unit rates
suppliers.csv                      Procurement  supplier master + payment terms
erp_products.xlsx                  ERP          products / cost_history / price_history sheets
crm_customers.csv                  CRM          customer master (messy)
oms_orders.csv                     Storefront   order headers (messy)
oms_order_lines.csv                Storefront   order lines (messy)
psp_transactions.csv               PSP          one auth per order (+ unmatched noise)
procurement_purchase_orders.csv    Procurement  PO lines with receipt & payment dates
wms_inventory_movements.csv        WMS          receipt / sale / return / adjustment ledger
wms_inventory_snapshots.csv        WMS          month-end snapshots (+ injected variance)
returns.csv                        Storefront   return lines
web_analytics_daily.csv            GA4-style    sessions / funnel by market·channel·device
google_ads_report.csv              Google Ads   paid search + display, daily
meta_ads_export.csv                Meta Ads     paid social, daily (different schema)
other_marketing_spend.csv          Finance      affiliate commission + email tooling
support_tickets.csv                Support      tickets with CSAT
carrier_tracking.json              Carrier      nested shipment + tracking events (sample)
finance_targets.csv                Finance      monthly plan by market
"""

from __future__ import annotations

import datetime as dt
import math
from collections import defaultdict, deque

import numpy as np
import pandas as pd
from faker import Faker

import config as C
import utils as U


# =====================================================================================
# 1. FX
# =====================================================================================

def gen_fx():
    U.section("1/13  FX rates")
    fx = U.build_fx_series()
    # raw file: only the trading window, USD row omitted (a real export would)
    raw = fx[(fx["date"] >= C.WINDOW_START - dt.timedelta(days=40)) &
             (fx["date"] <= C.WINDOW_END) & (fx["currency_code"] != "USD")].copy()
    raw["date"] = raw["date"].map(lambda d: d.strftime("%d/%m/%Y"))          # EU-style dates
    raw = raw.rename(columns={"currency_code": "ccy", "rate_to_usd": "usd_per_unit"})
    U.write_csv(raw, C.RAW_DIR / "fx_rates.csv")
    return fx, U.fx_lookup(fx)


# =====================================================================================
# 2. Suppliers
# =====================================================================================

def gen_suppliers():
    U.section("2/13  Suppliers")
    g = U.rng(2)
    names = ["Shenzhen ", "Pacific ", "Nordic ", "Atlas ", "Meridian ", "Everest ",
             "BlueCircuit ", "Copperline ", "Kingfisher ", "Toroko ", "Vega ", "Halcyon ",
             "Ironwood ", "Silverpath ", "Brightforge "]
    suffix = ["Components", "Trading", "Electronics", "Manufacturing", "Distribution",
              "Supply Co", "Industries", "Tech", "Global", "Partners"]
    rows = []
    for i in range(C.N_SUPPLIERS):
        rows.append({
            "supplier_id": f"SUP-{i+1:03d}",
            "supplier_name": names[i].strip() + " " + suffix[i % len(suffix)],
            "country": g.choice(C.SUPPLIER_COUNTRIES),
            "payment_terms_days": int(g.choice(C.SUPPLIER_TERMS_DAYS, p=C.SUPPLIER_TERMS_WEIGHTS)),
            "lead_time_days": int(g.integers(*C.SUPPLIER_LEAD_TIME_RANGE)),
            "on_time_rate": round(float(g.uniform(*C.SUPPLIER_ONTIME_RANGE)), 3),
        })
    df = pd.DataFrame(rows)
    U.write_csv(df, C.RAW_DIR / "suppliers.csv")
    return df


# =====================================================================================
# 3. Product catalog  (ERP)
# =====================================================================================

def gen_products(suppliers: pd.DataFrame):
    U.section("3/13  Product catalog")
    g = U.rng(3)
    cat_names = list(C.CATEGORIES.keys())
    cat_share = np.array([C.CATEGORIES[c]["share"] for c in cat_names])
    cat_share = cat_share / cat_share.sum()
    n_by_cat = np.random.default_rng(C.SEED + 33).multinomial(C.N_PRODUCTS, cat_share)

    prods, cost_hist, price_hist = [], [], []
    sku_i = 0
    for cat, n in zip(cat_names, n_by_cat):
        meta = C.CATEGORIES[cat]
        lo, hi = meta["price_usd"]
        for _ in range(int(n)):
            sku_i += 1
            sku = f"SKU-{sku_i:05d}"
            sub = g.choice(meta["subcategories"])
            brand = g.choice(meta["brands"])
            # price skewed toward the low end: few flagships, many cheap models
            skew = g.beta(*C.PRICE_SKEW_BETA)
            price = U.psychological_price(lo * (hi / lo) ** skew)
            gm = U.clamp(g.normal(meta["gross_margin"], 0.03), 0.05, 0.55)
            base_cost = round(price * (1 - gm), 2)

            launch = C.DIM_DATE_START + dt.timedelta(days=int(g.integers(0, 600)))
            if g.random() < 0.35:                       # a third pre-date the buffer
                launch = dt.date(2022, 1, 1) + dt.timedelta(days=int(g.integers(0, 900)))
            disc = pd.NaT
            if g.random() < C.PRODUCT_DISCONTINUE_RATE:
                disc = C.WINDOW_START + dt.timedelta(days=int(g.integers(120, 660)))

            sup = suppliers.sample(1, random_state=C.SEED + sku_i).iloc[0]["supplier_id"]
            prods.append({
                "sku_id": sku,
                "product_name": f"{brand} {sub} {cat.split()[0]} {g.integers(100, 999)}",
                "category": cat,
                "subcategory": sub,
                "brand": brand,
                "list_price_usd": price,
                "unit_cost_usd": base_cost,
                "launch_date": launch,
                "discontinue_date": disc,
                "is_warranty_eligible": meta["warranty_eligible"],
                "weight_kg": round(float(U.clamp(g.lognormal(-0.5, 0.7), 0.02, 12)), 3),
                "warranty_months": int(g.choice([12, 12, 24, 36])),
                "supplier_id": sup,
                "return_rate": meta["return_rate"],
            })

            # monthly cost: mean-reverting walk around a slowly declining base (scale
            # economies in procurement), plus occasional price step
            months = U.month_starts(max(launch, C.DIM_DATE_START), C.DIM_DATE_END)
            c_cur, p_cur = base_cost, price
            for m in months:
                mi = max(0, (m.year - C.WINDOW_START.year) * 12 + m.month - C.WINDOW_START.month)
                base_m = base_cost * (1 - C.COST_SCALE_IMPROVEMENT_MONTHLY) ** mi
                c_cur = c_cur * (1 + g.normal(0, C.COST_DRIFT_MONTHLY_STD)) \
                    + C.COST_MEAN_REVERSION * (base_m - c_cur)
                cost_hist.append({"sku_id": sku, "effective_date": m,
                                  "unit_cost_usd": round(max(0.5, c_cur), 2)})
                if g.random() < 0.06:
                    p_cur = U.psychological_price(p_cur * g.uniform(0.95, 1.08))
                price_hist.append({"sku_id": sku, "effective_date": m, "list_price_usd": p_cur})

    products = pd.DataFrame(prods)
    cost_history = pd.DataFrame(cost_hist)
    price_history = pd.DataFrame(price_hist)

    # ---- write ERP xlsx with category-spelling noise on a share of rows ----------
    disp = products.copy()
    typo_mask = g.random(len(disp)) < C.DQ["product_category_typo_rate"]
    disp["category"] = [
        (g.choice(C.CATEGORY_TYPOS[c]) if m and c in C.CATEGORY_TYPOS else c)
        for c, m in zip(disp["category"], typo_mask)
    ]
    disp["brand"] = [b.lower() if g.random() < 0.15 else b for b in disp["brand"]]
    # a few SKUs never made it into the ERP master (discontinued/legacy) but still sell
    n_missing = int(len(disp) * C.DQ["sku_missing_from_master_rate"])
    missing_skus = disp.sample(n=n_missing, random_state=C.SEED + 99)["sku_id"].tolist()
    disp = disp[~disp["sku_id"].isin(missing_skus)]
    U.log(f"  {n_missing} SKUs deliberately omitted from the ERP master")
    disp = disp.drop(columns=["return_rate"])
    disp["list_price_usd"] = disp["list_price_usd"].map(lambda x: f"$ {x:,.2f}")
    disp["launch_date"] = disp["launch_date"].map(lambda d: d.strftime("%m/%d/%Y"))
    disp["discontinue_date"] = disp["discontinue_date"].map(
        lambda d: "" if pd.isna(d) else d.strftime("%m/%d/%Y"))

    xlsx_path = C.RAW_DIR / "erp_products.xlsx"
    with pd.ExcelWriter(xlsx_path, engine="openpyxl") as xw:
        disp.rename(columns={"sku_id": "SKU", "product_name": "Description"}).to_excel(
            xw, sheet_name="products", index=False)
        ch = cost_history.copy()
        ch["effective_date"] = ch["effective_date"].map(lambda d: d.strftime("%Y-%m-%d"))
        ch.to_excel(xw, sheet_name="cost_history", index=False)
        ph = price_history.copy()
        ph["effective_date"] = ph["effective_date"].map(lambda d: d.strftime("%Y-%m-%d"))
        ph.to_excel(xw, sheet_name="price_history", index=False)
    U.log(f"  wrote {xlsx_path.relative_to(C.PROJECT_DIR)}  (3 sheets, {len(disp):,} products)")

    return products, cost_history, price_history


# =====================================================================================
# helpers for as-of lookups
# =====================================================================================

class AsOf:
    """Fast as-of value lookup keyed by sku, over a monthly history frame."""

    def __init__(self, hist: pd.DataFrame, value_col: str):
        self.map = {}
        for sku, grp in hist.sort_values("effective_date").groupby("sku_id"):
            self.map[sku] = (
                [d if isinstance(d, dt.date) else d.date() for d in grp["effective_date"]],
                grp[value_col].to_numpy(),
            )

    def get(self, sku: str, d: dt.date) -> float:
        dates, vals = self.map[sku]
        i = np.searchsorted(dates, d, side="right") - 1
        return float(vals[max(0, i)])


# =====================================================================================
# 4. Orders + customers + downstream seeds
# =====================================================================================

POOL_W: dict = {}


def gen_orders(products: pd.DataFrame, price_history: pd.DataFrame, fxl: dict):
    U.section("4/13  Orders, order lines, customers")
    g = U.rng(4)
    fake = {m: Faker(C.MARKETS[m]["locale"]) for m in C.MARKETS}
    for m in fake:
        fake[m].seed_instance(C.SEED + hash(m) % 1000)

    price_asof = AsOf(price_history, "list_price_usd")

    # index products by category for basket building, with popularity weights ~ 1/price
    by_cat = {c: products[products["category"] == c].reset_index(drop=True)
              for c in C.CATEGORIES}
    acc_pool = products[products["category"] == "Accessories"].reset_index(drop=True)
    global POOL_W
    POOL_W = {}
    for c, pool in list(by_cat.items()) + [("Accessories", acc_pool)]:
        wgt = (1.0 / pool["list_price_usd"].to_numpy()) ** C.SKU_POPULARITY_EXP
        POOL_W[c] = wgt / wgt.sum()

    # ---- customer store -------------------------------------------------------------
    customers: dict[str, dict] = {}
    by_market_ids: dict[str, list[str]] = defaultdict(list)
    cust_last_day: dict[str, int] = {}
    cust_orders: dict[str, int] = defaultdict(int)
    cust_i = 0

    def new_customer(market: str, acq_date: dt.date, channel: str) -> str:
        nonlocal cust_i
        cust_i += 1
        cid = f"CUST-{cust_i:06d}"
        f = fake[market]
        customers[cid] = {
            "customer_id": cid,
            "market": market,
            "signup_date": acq_date,
            "acquisition_channel": channel,
            "acquired_before_window": acq_date < C.WINDOW_START,
            "full_name": f.name(),
            "email": None,               # filled at write time (with noise)
            "city": f.city(),
            "state_region": _region_for(market, f),
            "postal_code": f.postcode(),
            "segment": U.weighted_choice(g, C.SEGMENTS),
            "birth_year": int(U.clamp(g.normal(1986, 13), 1945, 2007)),
            "marketing_consent": bool(g.random() < C.MARKETING_CONSENT_RATE),
        }
        by_market_ids[market].append(cid)
        cust_orders[cid] = 0
        return cid

    # ---- seed US pre-window customers so month 1 has realistic repeat & cohorts ----
    for _ in range(6000):
        acq = dt.date(2023, 6, 1) + dt.timedelta(days=int(g.integers(0, 395)))
        cid = new_customer("US", acq, U.weighted_choice(g, C.ACQUISITION_CHANNEL_SHARE))
        cust_last_day[cid] = (acq - C.DIM_DATE_START).days
        cust_orders[cid] = 1

    # ---- accumulators -------------------------------------------------------------
    orders, lines, returns_rows = [], [], []
    support_seeds, carrier_seeds = [], []
    web_cell = defaultdict(int)            # (date, market, channel, device) -> orders
    newcust_cell = defaultdict(int)        # (month, market, channel) -> new customers
    rev_cell = defaultdict(float)          # (month, market) -> net revenue usd
    sales_sku_month = defaultdict(int)     # (sku, market, month) -> units
    sales_movements = []                   # per line: for inventory ledger

    months = U.month_starts(C.WINDOW_START, C.WINDOW_END)
    n_months = len(months)
    promo_lookup = _promo_lookup()
    order_i = 0
    line_i = 0

    for mi, mstart in enumerate(months):
        prog = mi / (n_months - 1)
        ret_share = (C.RETURNING_ORDER_SHARE_START
                     + prog * (C.RETURNING_ORDER_SHARE_END - C.RETURNING_ORDER_SHARE_START)
                     + C.RETURNING_SHARE_WAVE_AMP
                       * math.sin(2 * math.pi * mi / C.RETURNING_SHARE_WAVE_PERIOD_M)
                     + g.normal(0, 0.03))
        ret_share = U.clamp(ret_share, 0.15, 0.75)
        acq_mix = _acq_mix(prog)
        mdays = U.date_range(mstart, U.month_end(mstart))

        for market, mk in C.MARKETS.items():
            if mstart < dt.date(mk["live_date"].year, mk["live_date"].month, 1):
                continue
            ramp = _market_month_orders(market, mstart, mi, n_months, g)
            if ramp <= 0:
                continue

            # spread orders across the month's days
            day_w = np.array([_day_weight(d, market, promo_lookup) for d in mdays])
            day_w = day_w / day_w.sum()
            per_day = g.multinomial(ramp, day_w)

            # sample this month's customers (returning vs new) in bulk
            n_ret = int(round(ramp * ret_share))
            n_new = ramp - n_ret
            ret_ids = _sample_returning(market, by_market_ids, cust_last_day,
                                        cust_orders, mstart, n_ret, g)
            new_channels = U.weighted_choice(g, acq_mix, size=n_new)
            new_ids = []
            for ch in new_channels:
                day = mdays[int(g.integers(0, len(mdays)))]
                new_ids.append(new_customer(market, day, ch))
                newcust_cell[(mstart, market, ch)] += 1
            cust_queue = deque(_interleave(new_ids, list(ret_ids), g))

            for di, d in enumerate(mdays):
                for _ in range(int(per_day[di])):
                    if not cust_queue:
                        break
                    cid = cust_queue.popleft()
                    order_i += 1
                    line_i = _emit_order(
                        order_i, line_i, cid, customers[cid], market, mk, d, prog,
                        by_cat, acc_pool, price_asof, fxl, promo_lookup, g,
                        orders, lines, returns_rows, support_seeds, carrier_seeds,
                        web_cell, rev_cell, sales_sku_month, sales_movements)
                    cust_orders[cid] += 1
                    cust_last_day[cid] = (d - C.DIM_DATE_START).days

        U.log(f"  {mstart:%Y-%m}: cum orders {order_i:,}  cum customers {cust_i:,}")

    orders_df = pd.DataFrame(orders)
    lines_df = pd.DataFrame(lines)
    returns_df = pd.DataFrame(returns_rows)
    U.log(f"  totals: {len(orders_df):,} orders  {len(lines_df):,} lines  "
          f"{len(returns_df):,} returns  {cust_i:,} customers")

    seeds = dict(customers=customers, support=support_seeds, carrier=carrier_seeds,
                 web_cell=web_cell, newcust_cell=newcust_cell, rev_cell=rev_cell,
                 sales_sku_month=sales_sku_month, sales_movements=sales_movements,
                 months=months)
    return orders_df, lines_df, returns_df, seeds


# ---- order emission ------------------------------------------------------------------

def _emit_order(oi, li, cid, cust, market, mk, d, prog, by_cat, acc_pool, price_asof,
                fxl, promo_lookup, g, orders, lines, returns_rows, support_seeds,
                carrier_seeds, web_cell, rev_cell, sales_sku_month, sales_movements):
    ccy = mk["currency"]
    fx = fxl[(d.isoformat(), ccy)]
    order_id = f"{market}-{d:%Y%m}-{oi:07d}"

    n_lines = int(U.weighted_choice(g, C.ORDER_LINES_WEIGHTS))
    primary_cat = U.weighted_choice(g, {c: C.CATEGORIES[c]["share"] for c in C.CATEGORIES})
    chosen_cats = [primary_cat]
    if g.random() < C.ACCESSORY_BASKET_PROB.get(primary_cat, 0.2):
        chosen_cats.append("Accessories")
    while len(chosen_cats) < n_lines:
        chosen_cats.append(U.weighted_choice(g, {c: C.CATEGORIES[c]["share"] for c in C.CATEGORIES}))
    chosen_cats = chosen_cats[:n_lines]

    promo = promo_lookup.get(d)
    order_gross_usd = order_net_usd = order_cogs_usd = 0.0
    order_units = 0
    warranty_added = False
    ship_wh = _fulfilling_warehouse(market, g)

    for cat in chosen_cats:
        pool = acc_pool if cat == "Accessories" else by_cat[cat]
        row = pool.iloc[int(g.choice(len(pool), p=POOL_W[cat]))]
        sku = row["sku_id"]
        # respect launch / discontinue
        if isinstance(row["launch_date"], dt.date) and row["launch_date"] > d:
            continue
        if not pd.isna(row["discontinue_date"]) and row["discontinue_date"] <= d:
            continue
        qty = int(U.weighted_choice(g, C.UNITS_PER_LINE_WEIGHTS))
        list_usd = price_asof.get(sku, d)
        unit_price_local = U.psychological_price(list_usd / fx * mk["price_index"])

        disc_rate = 0.0
        if promo is not None:
            disc_rate = max(0.0, g.normal(promo, 0.05))
        elif g.random() < C.DISCOUNT_ORDER_SHARE:
            disc_rate = max(0.0, g.normal(C.BASE_DISCOUNT_RATE, 0.03))
        disc_rate = min(disc_rate, 0.6)

        gross_local = round(unit_price_local * qty, 2)
        disc_local = round(gross_local * disc_rate, 2)
        net_local = gross_local - disc_local
        cost_local = round((list_usd * (1 - C.CATEGORIES[cat]["gross_margin"])) / fx
                           * mk["price_index"] * qty, 2)

        li += 1
        lines.append({
            "order_line_id": f"OL-{li:08d}",
            "order_id": order_id,
            "sku_id": sku,
            "line_type": "product",
            "quantity": qty,
            "unit_price_local": unit_price_local,
            "discount_amount_local": disc_local,
            "gross_amount_local": gross_local,
            "net_amount_local": net_local,
            "currency": ccy,
        })
        order_gross_usd += gross_local * fx
        order_net_usd += net_local * fx
        order_cogs_usd += cost_local * fx
        order_units += qty
        web_key = None
        sales_sku_month[(sku, market, dt.date(d.year, d.month, 1))] += qty
        sales_movements.append((sku, market, ship_wh, d, -qty))

        # returns
        if g.random() < row["return_rate"]:
            lag = int(g.integers(*C.RETURN_LAG_DAYS_RANGE))
            reason = U.weighted_choice(g, C.RETURN_REASONS)
            restock = g.random() < C.RETURN_RESTOCK_SHARE
            returns_rows.append({
                "return_id": f"RET-{len(returns_rows)+1:07d}",
                "order_id": order_id,
                "order_line_id": f"OL-{li:08d}",
                "sku_id": sku,
                "return_date": d + dt.timedelta(days=lag),
                "quantity": qty,
                "refund_amount_local": net_local,
                "currency": ccy,
                "reason": reason,
                "restocked": restock,
                "condition": "sellable" if restock else "quarantine",
            })

        # warranty attach
        if (not warranty_added and row["is_warranty_eligible"]
                and g.random() < C.WARRANTY_ATTACH_RATE):
            warranty_added = True
            w_price_local = U.psychological_price(unit_price_local * C.WARRANTY_PRICE_PCT)
            li += 1
            lines.append({
                "order_line_id": f"OL-{li:08d}",
                "order_id": order_id,
                "sku_id": sku,
                "line_type": "warranty",
                "quantity": 1,
                "unit_price_local": w_price_local,
                "discount_amount_local": 0.0,
                "gross_amount_local": w_price_local,
                "net_amount_local": w_price_local,
                "currency": ccy,
            })
            order_gross_usd += w_price_local * fx
            order_net_usd += w_price_local * fx
            order_cogs_usd += w_price_local * C.WARRANTY_COST_PCT * fx

    if order_units == 0:            # everything filtered out by launch/discontinue
        return li

    # ---- channel / device / logistics / payment --------------------------------
    channel = cust["acquisition_channel"] if g.random() < 0.55 else \
        U.weighted_choice(g, _acq_mix(prog))
    device = U.weighted_choice(g, C.DEVICE_SHARE)
    web_cell[(d, market, channel, device)] += 1

    carrier, base_days, ontime = _pick_carrier(market, g)
    peak = C.PEAK_DELAY_INFLATION if d.month in (11, 12) else 1.0
    stress = _log_stress(market, d)                       # smooth monthly logistics stress
    bulky = 1.0 + (g.uniform(0.10, 0.35) if g.random() < 0.14 else 0.0)  # heavy / oversized item
    ship_lag = int(U.clamp(g.poisson(1.0 * stress), 0, 4))
    transit = max(1, int(round(g.normal(base_days, 0.6) * peak * stress * bulky)))
    ship_date = d + dt.timedelta(days=ship_lag)
    promised_date = d + dt.timedelta(days=int(round(base_days)) + ship_lag + C.PROMISED_DAYS_BUFFER)
    delivered_date = ship_date + dt.timedelta(days=transit)
    # engineer a believable ~5% "slightly late" tail: pull this order's promise in so the
    # (unchanged) delivery lands 1-2 days past it. Keeps avg delivery days in the 4-5 band.
    if g.random() < C.SLIGHTLY_LATE_SHARE and delivered_date > d + dt.timedelta(days=2):
        promised_date = delivered_date - dt.timedelta(days=int(g.integers(1, 3)))
    late = delivered_date > promised_date

    free_ship = (order_net_usd / fx) >= mk["free_ship_threshold_local"]
    ship_fee_local = 0.0 if free_ship else round(g.uniform(4, 12), 2)
    ship_cost_usd = round(g.uniform(*C.SHIP_COST_PER_ORDER_USD) * (1.15 if peak > 1 else 1.0), 2)
    tax_rate = {"US": 0.07, "UK": 0.20, "DE": 0.19, "BR": 0.17}[market]

    pm = _pick_payment(market, prog, g)
    n_inst, plan = _pick_installments(market, pm, g)
    amount_local = round(order_net_usd / fx + ship_fee_local + (order_net_usd / fx) * tax_rate, 2)
    fee_local = round(amount_local * pm["mdr_pct"] + pm["fixed_fee_local"], 2)

    status = "delivered"
    if pm["method_name"] == "Boleto Bancario" and g.random() < C.BOLETO_UNPAID_RATE:
        status = "cancelled"
    elif g.random() < 0.006:
        status = "cancelled"

    orders.append({
        "order_id": order_id,
        "customer_id": cust["customer_id"],
        "market": market,
        "order_ts": dt.datetime.combine(d, dt.time(int(g.integers(0, 24)), int(g.integers(0, 60)))),
        "currency": mk["currency"],
        "channel": channel,
        "device": device,
        "warehouse": ship_wh,
        "carrier": carrier,
        "ship_date": ship_date,
        "promised_date": promised_date,
        "delivered_date": delivered_date if status == "delivered" else pd.NaT,
        "is_late": bool(late) if status == "delivered" else False,
        "order_status": status,
        "units": order_units,
        "gross_amount_local": round(order_gross_usd / fx, 2),
        "discount_amount_local": round((order_gross_usd - order_net_usd) / fx, 2),
        "net_amount_local": round(order_net_usd / fx, 2),
        "tax_amount_local": round((order_net_usd / fx) * tax_rate, 2),
        "shipping_fee_local": ship_fee_local,
        "shipping_cost_usd": ship_cost_usd,
        "cogs_usd_hint": round(order_cogs_usd, 2),     # helper; curated recomputes via moving avg
        "payment_method": pm["method_name"],
        "card_scheme": pm["card_scheme"] or "",
        "installments": n_inst,
        "installment_plan": plan,
        "payment_fee_local": fee_local,
    })
    if status != "cancelled":
        rev_cell[(dt.date(d.year, d.month, 1), market)] += order_net_usd

    # support seed
    if g.random() < C.SUPPORT_TICKET_PER_ORDER_RATE:
        created = d + dt.timedelta(days=int(g.integers(0, 21)))
        res_h = float(U.clamp(g.lognormal(2.6, 0.9), *C.SUPPORT_RES_HOURS_RANGE))
        created_ts = dt.datetime.combine(created, dt.time(int(g.integers(8, 20)), int(g.integers(0, 60))))
        support_seeds.append({
            "ticket_id": f"TCK-{len(support_seeds)+1:07d}",
            "order_id": order_id,
            "customer_id": cust["customer_id"],
            "market": market,
            "created_ts": created_ts,
            "resolved_ts": created_ts + dt.timedelta(hours=res_h),
            "category": U.weighted_choice(g, C.SUPPORT_CATEGORIES),
            "priority": U.weighted_choice(g, C.SUPPORT_PRIORITY),
            "first_contact_resolution": bool(g.random() < C.SUPPORT_FCR_RATE),
            "csat": int(U.clamp(round(g.normal(4.3, 0.9)), 1, 5)),
        })

    # carrier tracking seed (sample only)
    if status == "delivered" and g.random() < 0.09:
        carrier_seeds.append({
            "order_id": order_id, "market": market, "carrier": carrier,
            "ship_date": ship_date, "delivered_date": delivered_date, "late": late,
        })
    return li


# ---- small helpers for gen_orders --------------------------------------------------

def _region_for(market: str, f: Faker) -> str:
    try:
        if market == "US":
            return f.state_abbr()
        if market == "BR":
            return f.estado_sigla()
        if market == "DE":
            return f.state()
        return f.county() if hasattr(f, "county") else f.city()
    except Exception:
        return ""


def _promo_lookup() -> dict:
    out = {}
    for s, e, name, depth in C.PROMO_PERIODS:
        sd, ed = dt.date.fromisoformat(s), dt.date.fromisoformat(e)
        for d in U.date_range(sd, ed):
            out[d] = depth
    return out


def _acq_mix(prog: float) -> dict:
    return {ch: max(0.01, base + prog * C.CHANNEL_MIX_DRIFT.get(ch, 0.0))
            for ch, base in C.ACQUISITION_CHANNEL_SHARE.items()}


def _market_month_orders(market, mstart, mi, n_months, g) -> int:
    mk = C.MARKETS[market]
    live_month = dt.date(mk["live_date"].year, mk["live_date"].month, 1)
    all_months = U.month_starts(live_month, C.WINDOW_END)
    if mstart not in all_months:
        return 0
    k = all_months.index(mstart)
    frac = k / max(1, len(all_months) - 1)
    base = mk["monthly_orders_start"] + frac * (mk["monthly_orders_end"] - mk["monthly_orders_start"])
    base *= C.SEASONALITY_BY_MONTH[mstart.month]
    # slow demand wave + month-to-month noise + occasional spike / soft month
    base *= 1 + C.DEMAND_WAVE_AMPLITUDE * math.sin(2 * math.pi * mi / C.DEMAND_WAVE_PERIOD_M
                                                   + hash(market) % 7)
    r = g.random()
    if r < C.DEMAND_HOT_MONTH_P:
        base *= g.uniform(1.25, 1.55)
    elif r < C.DEMAND_HOT_MONTH_P + C.DEMAND_SOFT_MONTH_P:
        base *= g.uniform(0.60, 0.80)
    base *= float(g.normal(1.0, C.DEMAND_MONTH_NOISE))
    return max(0, int(round(base)))


def _day_weight(d: dt.date, market: str, promo_lookup: dict) -> float:
    w = C.DOW_MULTIPLIER[d.weekday()]
    bf = U.black_friday(d.year)
    if 0 <= (d - bf).days < C.BF_WINDOW_DAYS:
        w *= C.BLACK_FRIDAY_MULT
    if d in promo_lookup:
        w *= 1.35
    return w


def _sample_returning(market, by_market_ids, last_day, orders_ct, mstart, n, g):
    ids = np.array(by_market_ids.get(market, []))
    if len(ids) == 0 or n <= 0:
        return []
    today = (mstart - C.DIM_DATE_START).days
    ld = np.array([last_day.get(i, today - 400) for i in ids])
    oc = np.array([orders_ct.get(i, 1) for i in ids])
    recency = 0.5 ** (np.clip(today - ld, 0, None) / 90.0)
    w = recency * (1 + 0.08 * np.clip(oc, 0, 6))
    w = w / w.sum()
    return list(g.choice(ids, size=n, p=w, replace=True))


def _interleave(a, b, g):
    out = a + b
    g.shuffle(out)
    return out


def _fulfilling_warehouse(market, g):
    whs = C.MARKETS[market]["warehouses"]
    if len(whs) == 1:
        return whs[0]
    return whs[0] if g.random() < 0.65 else whs[1]


def _pick_carrier(market, g):
    opts = C.CARRIERS[market]
    i = int(g.integers(0, len(opts)))
    return opts[i]


_LOG_STRESS: dict = {}

def _log_stress(market: str, d: dt.date) -> float:
    """Smooth AR(1) monthly logistics stress per market, with occasional carrier crises."""
    key = (market, d.year, d.month)
    if key in _LOG_STRESS:
        return _LOG_STRESS[key]
    gs = np.random.default_rng(C.SEED + 777 + hash(market) % 997)
    prev = _LOG_STRESS.get((market, *_prev_month(d.year, d.month)), 1.0)
    step = gs.normal(0, 0.035) + 0.40 * (1.0 - prev)      # mean-revert to 1.0, gentle
    val = U.clamp(prev + step, 0.94, 1.10)
    jg = np.random.default_rng(C.SEED + (d.year * 100 + d.month) * 13 + hash(market) % 101)
    val *= 1.0 + jg.normal(0, 0.02)
    if jg.random() < 0.03:
        val *= jg.uniform(1.05, 1.12)                     # a mildly stressed month
    val = U.clamp(val, 0.92, 1.14)
    _LOG_STRESS[key] = val
    return val


def _prev_month(y: int, m: int) -> tuple[int, int]:
    return (y - 1, 12) if m == 1 else (y, m - 1)


_PM_BY_MARKET = None

def _pick_payment(market, prog, g):
    global _PM_BY_MARKET
    if _PM_BY_MARKET is None:
        _PM_BY_MARKET = {}
        for m in C.MARKETS:
            avail = [p for p in C.PAYMENT_METHODS if m in p[8]]
            _PM_BY_MARKET[m] = avail
    avail = _PM_BY_MARKET[market]
    shares = np.array([max(0.001, p[9] + prog * p[10]) for p in avail])
    shares = shares / shares.sum()
    p = avail[int(g.choice(len(avail), p=shares))]
    return dict(method_name=p[0], method_group=p[1], card_scheme=p[2], mdr_pct=p[3],
                fixed_fee_local=p[4], settlement_days=p[5], installment_eligible=p[6],
                max_installments=p[7])


def _pick_installments(market, pm, g):
    if not pm["installment_eligible"]:
        return 1, "None"
    if pm["method_group"] == "BNPL":
        n = int(g.choice([3, 4]))
        return n, "Interest-Free"
    if market == "BR" and g.random() < C.BR_INSTALLMENT_ORDER_SHARE:
        n = int(U.weighted_choice(g, C.BR_INSTALLMENT_N_WEIGHTS))
        plan = "Interest-Free" if n <= C.INSTALLMENT_INTEREST_FREE_MAX else "With Interest"
        return n, plan
    return 1, "None"


# =====================================================================================
# 5. Write OMS + CRM (with injected mess)
# =====================================================================================

def write_oms_crm(orders_df, lines_df, seeds):
    U.section("5/13  Storefront (OMS) + CRM exports")
    g = U.rng(5)

    # ---- order lines: dup a few, flip a few to negative qty --------------------
    ol = lines_df.copy()
    dup = ol.sample(frac=C.DQ["order_line_dup_rate"], random_state=C.SEED)
    ol = pd.concat([ol, dup], ignore_index=True)
    neg_mask = g.random(len(ol)) < C.DQ["negative_qty_rate"]
    ol.loc[neg_mask, "quantity"] = -ol.loc[neg_mask, "quantity"].abs()
    ol = ol.sample(frac=1.0, random_state=C.SEED + 1).reset_index(drop=True)
    for col in ("unit_price_local", "gross_amount_local", "net_amount_local", "discount_amount_local"):
        ol[col] = ol[col].map(lambda x: f"{x:.2f}")
    U.write_csv(ol, C.RAW_DIR / "oms_order_lines.csv")

    # ---- order headers: drop customer_id on a few, mixed date formats ----------
    oh = orders_df.copy()
    miss = g.random(len(oh)) < C.DQ["order_missing_customer_rate"]
    oh.loc[miss, "customer_id"] = ""
    oh["order_ts"] = [
        _messy_ts(t, i, g) for i, t in enumerate(oh["order_ts"])
    ]
    for c in ("ship_date", "promised_date", "delivered_date"):
        oh[c] = oh[c].map(lambda d: "" if pd.isna(d) else pd.Timestamp(d).strftime("%Y-%m-%d"))
    oh = oh.drop(columns=["cogs_usd_hint"])
    for col in ("gross_amount_local", "discount_amount_local", "net_amount_local",
                "tax_amount_local", "shipping_fee_local", "payment_fee_local"):
        oh[col] = oh[col].map(lambda x: f"{x:.2f}")
    U.write_csv(oh, C.RAW_DIR / "oms_orders.csv")

    # ---- CRM customers: null emails, dup rows, casing, latin-1 file for BR -----
    cust = pd.DataFrame(seeds["customers"].values())
    emails = []
    for _, r in cust.iterrows():
        if g.random() < C.CUSTOMER_EMAIL_NULL_RATE:
            emails.append("")
        else:
            base = r["full_name"].lower().replace(" ", ".").replace("'", "")
            dom = g.choice(["gmail.com", "outlook.com", "yahoo.com", "proton.me", "icloud.com"])
            emails.append(f"{base}{g.integers(1, 999)}@{dom}")
    cust["email"] = emails
    cust["signup_date"] = cust["signup_date"].map(lambda d: pd.Timestamp(d).strftime("%Y-%m-%d"))
    cust["full_name"] = [n.upper() if g.random() < 0.12 else n for n in cust["full_name"]]
    cust.columns = [c.upper() if g.random() < 0.0 else c for c in cust.columns]  # keep stable
    # duplicate a fraction of rows verbatim
    dup_c = cust.sample(frac=C.CUSTOMER_DUP_ROW_RATE, random_state=C.SEED + 2)
    cust_out = pd.concat([cust, dup_c], ignore_index=True).sample(
        frac=1.0, random_state=C.SEED + 3).reset_index(drop=True)
    cust_out = cust_out.drop(columns=["acquired_before_window"])
    # trailing spaces on some city values
    cust_out["city"] = [c + "  " if g.random() < 0.08 else c for c in cust_out["city"]]

    br = cust_out[cust_out["market"] == "BR"]
    non_br = cust_out[cust_out["market"] != "BR"]
    non_br.to_csv(C.RAW_DIR / "crm_customers.csv", index=False, encoding="utf-8")
    # the Brazil regional CRM exports its whole file in Latin-1 (cp1252) — stage 02
    # must detect the encoding and convert, or "São Paulo" becomes mojibake.
    br.to_csv(C.RAW_DIR / "crm_customers_br.csv", index=False, encoding="latin-1")
    U.log(f"  wrote crm_customers.csv ({len(non_br):,}, utf-8) + "
          f"crm_customers_br.csv ({len(br):,}, latin-1)")
    return cust  # clean version for downstream stages that need it (not re-read from raw here)


def _messy_ts(t, i, g):
    ts = pd.Timestamp(t)
    r = i % 5
    if r == 0:
        return ts.strftime("%Y-%m-%d %H:%M:%S")
    if r == 1:
        return ts.strftime("%m/%d/%Y %H:%M")
    if r == 2:
        return ts.strftime("%d-%b-%Y %H:%M")
    if r == 3:
        return ts.strftime("%Y-%m-%dT%H:%M:%S")
    return str(int((ts - pd.Timestamp("1899-12-30")).days) + round(
        (ts.hour * 3600 + ts.minute * 60) / 86400, 6))    # Excel serial


# =====================================================================================
# 6. PSP transactions
# =====================================================================================

def gen_psp(orders_df):
    U.section("6/13  Payment processor (PSP)")
    g = U.rng(6)
    o = orders_df
    keep = g.random(len(o)) >= C.DQ["order_without_psp_rate"]
    o = o[keep]
    rows = []
    for i, r in enumerate(o.itertuples(index=False)):
        rows.append({
            "psp_txn_id": f"TXN{C.SEED}{i:08d}",
            "order_ref": r.order_id,
            "method": r.payment_method,
            "scheme": r.card_scheme,
            "amount": f"{(r.net_amount_local + r.tax_amount_local + r.shipping_fee_local):.2f}",
            "ccy": r.currency,
            "mdr_pct": r.payment_fee_local,   # deliberately mislabeled: it's the fee amount, not a pct
            "installments": r.installments,
            "plan": r.installment_plan,
            "auth_ts": pd.Timestamp(r.order_ts).strftime("%Y-%m-%d %H:%M:%S")
            if not isinstance(r.order_ts, str) else r.order_ts,
            "status": "authorized" if r.order_status != "cancelled" else "voided",
        })
    # add unmatched junk transactions
    n_junk = int(len(rows) * C.DQ["psp_unmatched_rate"])
    for j in range(n_junk):
        rows.append({
            "psp_txn_id": f"TXN{C.SEED}{9000000 + j:08d}",
            "order_ref": f"UNKNOWN-{g.integers(10**6, 10**7)}",
            "method": "Visa Credit", "scheme": "Visa", "amount": f"{g.uniform(20, 900):.2f}",
            "ccy": g.choice(C.CURRENCIES), "mdr_pct": 0.0, "installments": 1,
            "plan": "None", "auth_ts": "2025-01-01 00:00:00", "status": "authorized",
        })
    df = pd.DataFrame(rows).sample(frac=1.0, random_state=C.SEED + 7).reset_index(drop=True)
    U.write_csv(df, C.RAW_DIR / "psp_transactions.csv")


# =====================================================================================
# 7. Procurement — purchase orders
# =====================================================================================

def gen_procurement(products, cost_history, suppliers, seeds):
    U.section("7/13  Procurement (purchase orders)")
    g = U.rng(8)
    cost_asof = AsOf(cost_history, "unit_cost_usd")
    sup = suppliers.set_index("supplier_id").to_dict("index")
    prod_sup = products.set_index("sku_id")["supplier_id"].to_dict()

    # demand per (sku, market, month)
    demand = defaultdict(int)
    for (sku, market, m), q in seeds["sales_sku_month"].items():
        demand[(sku, market)] += q
    # only stock sku/market pairs with real movement
    pairs = [(s, m) for (s, m), tot in demand.items() if tot >= C.PO_MIN_PAIR_DEMAND]

    months = U.month_starts(C.WINDOW_START - dt.timedelta(days=120), C.WINDOW_END)
    rows = []
    po_i = 0
    for (sku, market) in pairs:
        wh = C.MARKETS[market]["warehouses"][0]
        sid = prod_sup.get(sku)
        s = sup[sid]
        lead = int(s["lead_time_days"])
        terms = int(s["payment_terms_days"])
        # monthly demand estimate for this pair
        md = {m: seeds["sales_sku_month"].get((sku, market, m), 0)
              for m in U.month_starts(C.WINDOW_START, C.WINDOW_END)}
        avg_wk = max(1.0, (sum(md.values()) / max(1, len([v for v in md.values() if v > 0]))) / 4.33)
        on_hand = int(round(avg_wk * C.TARGET_WEEKS_OF_COVER))   # opening handled in inventory
        for m in months:
            fut = seeds["sales_sku_month"].get((sku, market, m), 0) \
                + seeds["sales_sku_month"].get((sku, market, U.add_months(m, 1)), 0)
            on_hand -= seeds["sales_sku_month"].get((sku, market, m), 0)
            target = max(int(round(avg_wk * C.TARGET_WEEKS_OF_COVER)), fut)
            if on_hand < target:
                qty = int(np.ceil((target - on_hand) / C.PO_CASE_PACK) * C.PO_CASE_PACK)
                order_date = m - dt.timedelta(days=lead + int(g.integers(0, 6)))
                unit_cost = round(cost_asof.get(sku, max(order_date, dt.date(2024, 1, 1))), 2)
                late_days = 0 if g.random() < s["on_time_rate"] else int(g.integers(2, 20))
                expected = order_date + dt.timedelta(days=lead)
                actual = expected + dt.timedelta(days=late_days)
                pay_due = actual + dt.timedelta(days=terms)
                paid = pay_due + dt.timedelta(days=int(g.integers(*C.PO_PAY_DELAY_RANGE)))
                po_i += 1
                rows.append({
                    "po_number": f"PO-{po_i:06d}",
                    "supplier_id": sid,
                    "sku_id": sku,
                    "destination_warehouse": wh,
                    "market": market,
                    "order_date": order_date,
                    "qty_ordered": qty,
                    "unit_cost_usd": unit_cost,
                    "po_value_usd": round(qty * unit_cost, 2),
                    "expected_receipt_date": expected,
                    "actual_receipt_date": actual,
                    "payment_terms_days": terms,
                    "payment_due_date": pay_due,
                    "supplier_paid_date": paid,
                })
                on_hand += qty
    df = pd.DataFrame(rows)
    for c in ("order_date", "expected_receipt_date", "actual_receipt_date",
              "payment_due_date", "supplier_paid_date"):
        df[c] = df[c].map(lambda d: pd.Timestamp(d).strftime("%Y-%m-%d"))
    U.write_csv(df, C.RAW_DIR / "procurement_purchase_orders.csv")
    return pd.DataFrame(rows)   # unformatted for inventory stage


# =====================================================================================
# 8. WMS — inventory movements + snapshots
# =====================================================================================

def gen_inventory(po_df, seeds, products):
    U.section("8/13  WMS (inventory movements + snapshots)")
    g = U.rng(9)
    mov = []

    # opening balances on 2024-06-30: ~5 weeks of each pair's early-window weekly demand
    early = defaultdict(int)
    for (sku, market, m), q in seeds["sales_sku_month"].items():
        if m <= dt.date(2024, 9, 1):
            early[(sku, market)] += q
    for (sku, market), q in early.items():
        wh = C.MARKETS[market]["warehouses"][0]
        weekly = q / 3 / 4.33
        opening = max(5, int(round(weekly * C.TARGET_WEEKS_OF_COVER)))
        mov.append((C.INVENTORY_OPENING_DATE, sku, wh, market, "adjustment", opening))

    # receipts from POs
    for r in po_df.itertuples(index=False):
        mov.append((pd.Timestamp(r.actual_receipt_date).date() if isinstance(r.actual_receipt_date, str)
                    else r.actual_receipt_date, r.sku_id, r.destination_warehouse, r.market,
                    "receipt", int(r.qty_ordered)))

    # sales
    for (sku, market, wh, d, dq) in seeds["sales_movements"]:
        mov.append((d, sku, wh, market, "sale", dq))

    mv = pd.DataFrame(mov, columns=["movement_date", "sku_id", "warehouse", "market",
                                    "movement_type", "quantity"])
    mv = mv.sort_values(["sku_id", "warehouse", "movement_date"]).reset_index(drop=True)
    mv["movement_id"] = [f"MOV-{i+1:09d}" for i in range(len(mv))]
    mv_out = mv[["movement_id", "movement_date", "sku_id", "warehouse", "market",
                 "movement_type", "quantity"]].copy()
    mv_out["movement_date"] = mv_out["movement_date"].map(lambda d: pd.Timestamp(d).strftime("%Y-%m-%d"))
    U.write_csv(mv_out, C.RAW_DIR / "wms_inventory_movements.csv")

    # month-end snapshots derived from the ledger, then perturbed for a few rows
    mv["running"] = mv.groupby(["sku_id", "warehouse"])["quantity"].cumsum()
    snaps = []
    for mend in [U.month_end(m) for m in U.month_starts(C.WINDOW_START, C.WINDOW_END)]:
        upto = mv[mv["movement_date"] <= mend]
        last = upto.groupby(["sku_id", "warehouse"]).agg(
            on_hand=("running", "last"), market=("market", "last")).reset_index()
        last = last[last["on_hand"].notna()]
        for rr in last.itertuples(index=False):
            oh = max(0, int(rr.on_hand))
            if g.random() < C.DQ["inventory_snapshot_variance_rate"]:
                oh = max(0, oh + int(g.integers(-8, 9)))
            snaps.append({"snapshot_date": mend, "sku_id": rr.sku_id,
                          "warehouse": rr.warehouse, "market": rr.market,
                          "units_on_hand": oh})
    sn = pd.DataFrame(snaps)
    sn["snapshot_date"] = sn["snapshot_date"].map(lambda d: pd.Timestamp(d).strftime("%Y-%m-%d"))
    U.write_csv(sn, C.RAW_DIR / "wms_inventory_snapshots.csv")


# =====================================================================================
# 9. Returns
# =====================================================================================

def write_returns(returns_df):
    U.section("9/13  Returns export")
    r = returns_df.copy()
    r["return_date"] = r["return_date"].map(lambda d: pd.Timestamp(d).strftime("%d/%m/%Y"))
    r["refund_amount_local"] = r["refund_amount_local"].map(lambda x: f"{x:.2f}")
    U.write_csv(r, C.RAW_DIR / "returns.csv")


# =====================================================================================
# 10. Web analytics daily
# =====================================================================================

def gen_web(seeds):
    U.section("10/13  Web analytics (daily)")
    g = U.rng(10)
    rows = []
    for (d, market, channel, device), n_orders in seeds["web_cell"].items():
        cr = (C.BASELINE_CONVERSION_RATE
              * C.CHANNEL_CR_MULT.get(channel, 1.0)
              * C.DEVICE_CR_MULT.get(device, 1.0)
              * float(g.normal(1.0, 0.12)))
        cr = U.clamp(cr, 0.002, 0.12)
        sessions = max(n_orders, int(round(n_orders / cr)))
        users = int(sessions * g.uniform(0.78, 0.92))
        bounce = U.clamp(g.uniform(*C.BOUNCE_RATE_RANGE), 0.2, 0.75)
        pps = g.uniform(*C.PAGES_PER_SESSION_RANGE)
        atc = U.clamp(g.uniform(*C.ADD_TO_CART_RATE_RANGE), 0.03, 0.25)
        add_to_carts = int(sessions * atc)
        carts = int(add_to_carts * g.uniform(0.55, 0.75))
        if g.random() < C.DQ["web_negative_sessions_rate"]:
            sessions = -sessions
        rows.append({
            "date": d.strftime("%Y-%m-%d"), "market": market, "channel": channel,
            "device": device, "sessions": sessions, "users": users,
            "pageviews": int(abs(sessions) * pps), "bounces": int(abs(sessions) * bounce),
            "add_to_carts": add_to_carts, "carts_created": carts,
            "transactions": n_orders,
        })
    df = pd.DataFrame(rows)
    # drop a fraction of dates entirely
    all_dates = sorted(df["date"].unique())
    drop_dates = set(pd.Series(all_dates).sample(
        frac=C.DQ["web_missing_day_rate"] if "web_missing_day_rate" in C.DQ else 0.015,
        random_state=C.SEED).tolist())
    df = df[~df["date"].isin(drop_dates)]
    df = df.sort_values(["date", "market", "channel", "device"]).reset_index(drop=True)
    U.write_csv(df, C.RAW_DIR / "web_analytics_daily.csv")


# =====================================================================================
# 11. Marketing spend  (Google Ads / Meta Ads / other)
# =====================================================================================

def gen_marketing(seeds, fxl):
    U.section("11/13  Marketing spend (Google / Meta / other)")
    g = U.rng(11)
    # monthly net revenue by market -> total paid budget via target MER
    rev_by_mm = defaultdict(float)
    for (m, market), v in seeds["rev_cell"].items():
        rev_by_mm[(m, market)] += v

    g_rows, m_rows, o_rows = [], [], []
    promo_months = {(dt.date.fromisoformat(s).year, dt.date.fromisoformat(s).month)
                    for s, *_ in C.PROMO_PERIODS}
    for (mo, market), rev in sorted(rev_by_mm.items()):
        frac = U.clamp(((mo.year - 2024) * 12 + mo.month - 7) / 23.0, 0, 1)
        # marketing efficiency improves over the window: MER ramps start -> end
        mer_t = C.TARGET_MER_START + frac * (C.TARGET_MER_END - C.TARGET_MER_START)
        # pull marketing back in promo months — demand is already there from the discount
        pullback = 0.68 if (mo.year, mo.month) in promo_months else 1.0
        budget = rev / mer_t * pullback
        ccy = C.MARKETS[market]["currency"]
        mdays = U.date_range(mo, U.month_end(mo))
        for ch, share in C.PAID_SPEND_SHARE.items():
            ch_budget = budget * share
            if ch == "Affiliate":
                o_rows.append({"month": mo.strftime("%Y-%m"), "market": market,
                               "channel": "Affiliate", "cost_type": "commission",
                               "amount_local": round(ch_budget / fxl[(mo.isoformat(), ccy)], 2),
                               "currency": ccy})
                continue
            daily = ch_budget / len(mdays)
            for d in mdays:
                spend_usd = max(0.0, daily * float(g.normal(1.0, 0.25)))
                # CPC eases a little as efficiency improves over the window
                cpc = g.uniform(*C.CPC_RANGE_USD[ch]) * (1.15 - 0.30 * frac)
                clicks = int(spend_usd / max(0.05, cpc))
                ctr = g.uniform(*C.CTR_RANGE[ch])
                impr = int(clicks / max(1e-4, ctr))
                fx = fxl[(d.isoformat(), ccy)]
                rec = {"date": d.strftime("%Y-%m-%d"), "market": market,
                       "campaign": _campaign_name(ch, market, mo, g),
                       "impressions": impr, "clicks": clicks}
                if ch == "Paid Search":
                    rec.update({"campaign_type": "Search", "cost": round(spend_usd / fx, 2),
                                "currency": ccy})
                    g_rows.append(rec)
                elif ch == "Display":
                    rec.update({"campaign_type": "Display", "cost": round(spend_usd / fx, 2),
                                "currency": ccy})
                    g_rows.append(rec)
                else:  # Paid Social -> Meta, different column names
                    m_rows.append({"day": d.strftime("%d/%m/%Y"), "country": market,
                                   "ad_campaign": _campaign_name("Paid Social", market, mo, g),
                                   "reach": int(impr * 0.7), "impressions": impr,
                                   "link_clicks": clicks,
                                   "spend": round(spend_usd / fx, 2), "currency": ccy})
        # email tooling flat monthly
        o_rows.append({"month": mo.strftime("%Y-%m"), "market": market, "channel": "Email",
                       "cost_type": "tooling",
                       "amount_local": round(C.EMAIL_TOOLING_MONTHLY_USD[market]
                                             / fxl[(mo.isoformat(), ccy)], 2), "currency": ccy})

    U.write_csv(pd.DataFrame(g_rows), C.RAW_DIR / "google_ads_report.csv")
    U.write_csv(pd.DataFrame(m_rows), C.RAW_DIR / "meta_ads_export.csv")
    U.write_csv(pd.DataFrame(o_rows), C.RAW_DIR / "other_marketing_spend.csv")


def _campaign_name(channel, market, mo, g):
    quarter = f"Q{(mo.month - 1) // 3 + 1}"
    theme = g.choice(["Always-On", "Brand", "Prospecting", "Retargeting", "Seasonal",
                      "New-Arrivals", "Category-Audio", "Category-Mobile"])
    return f"{market}_{channel.replace(' ', '')}_{quarter}{mo.year}_{theme}"


# =====================================================================================
# 12. Support tickets
# =====================================================================================

def write_support(seeds):
    U.section("12/13  Support tickets")
    df = pd.DataFrame(seeds["support"])
    if df.empty:
        return
    df["created_ts"] = df["created_ts"].map(lambda t: pd.Timestamp(t).strftime("%Y-%m-%d %H:%M:%S"))
    df["resolved_ts"] = df["resolved_ts"].map(lambda t: pd.Timestamp(t).strftime("%Y-%m-%d %H:%M:%S"))
    U.write_csv(df, C.RAW_DIR / "support_tickets.csv")


# =====================================================================================
# 13. Carrier tracking JSON
# =====================================================================================

_STATUS_VOCAB = ["created", "in_transit", "out_for_delivery", "delivered"]
_STATUS_STYLE = [str.lower, str.upper, str.title]

def write_carrier_json(seeds):
    U.section("13/13  Carrier tracking JSON")
    g = U.rng(12)
    out = []
    for s in seeds["carrier"]:
        ship = pd.Timestamp(s["ship_date"])
        deliv = pd.Timestamp(s["delivered_date"])
        style = _STATUS_STYLE[int(g.integers(0, 3))]
        events = [
            {"status": style("created"), "ts": (ship - pd.Timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%SZ"),
             "location": s["market"]},
            {"status": style("in_transit"), "ts": ship.strftime("%Y-%m-%dT%H:%M:%SZ"),
             "location": s["market"]},
            {"status": style("out_for_delivery"), "ts": (deliv - pd.Timedelta(hours=6)).strftime("%Y-%m-%dT%H:%M:%SZ"),
             "location": s["market"]},
            {"status": g.choice(["delivered", "DELIVERED", "Delivery complete"]),
             "ts": deliv.strftime("%Y-%m-%dT%H:%M:%SZ"), "location": s["market"]},
        ]
        out.append({
            "order_id": s["order_id"], "carrier": s["carrier"],
            "tracking_number": f"{s['carrier'][:3].upper()}{g.integers(10**9, 10**10)}",
            "service_level": g.choice(["standard", "express", "economy"]),
            "events": events,
        })
    U.write_json({"generated_at": "2026-07-01", "shipments": out},
                 C.RAW_DIR / "carrier_tracking.json")


# =====================================================================================
# 14. Finance targets
# =====================================================================================

def gen_targets(orders_df, lines_df, returns_df, seeds):
    U.section("bonus  Finance targets")
    g = U.rng(13)
    o = orders_df[orders_df["order_status"] != "cancelled"].copy()
    o["month"] = o["order_ts"].map(lambda t: dt.date(pd.Timestamp(t).year, pd.Timestamp(t).month, 1))
    fx = U.build_fx_series()
    fxl = U.fx_lookup(fx)

    # refunds attributed back to the original order's market/month, so the plan is on the
    # SAME basis as the [Net Revenue (USD)] measure (gross sales - returns)
    refund_by_mm = defaultdict(float)
    if len(returns_df):
        omap = o.set_index("order_id")[["market", "month"]].to_dict("index")
        for r in returns_df.itertuples(index=False):
            key = omap.get(r.order_id)
            if key:
                ccy = C.MARKETS[key["market"]]["currency"]
                rate = fxl[(key["month"].isoformat(), ccy)]
                refund_by_mm[(key["market"], key["month"])] += r.refund_amount_local * rate

    # actual net revenue / orders / new customers per (market, month)
    actual = {}
    for (market, month), grp in o.groupby(["market", "month"]):
        ccy = C.MARKETS[market]["currency"]
        rate = fxl[(month.isoformat(), ccy)]
        new_cust = sum(v for (mo, mk, ch), v in seeds["newcust_cell"].items()
                       if mo == month and mk == market)
        actual[(market, month)] = {
            "Net Revenue": (grp["net_amount_local"] * rate).sum() - refund_by_mm[(market, month)],
            "Orders": float(len(grp)),
            "New Customers": float(new_cust),
        }

    rows = []
    for (market, month), act in actual.items():
        py = actual.get((market, dt.date(month.year - 1, month.month, 1)))
        for metric in ("Net Revenue", "Orders", "New Customers"):
            if py is not None and py[metric] > 0:
                # current-year month: plan = prior-year actual grown by the plan rate
                plan_val = py[metric] * (1 + C.PLAN_YOY_GROWTH) * g.uniform(
                    1 - C.PLAN_MONTH_NOISE, 1 + C.PLAN_MONTH_NOISE)
            else:
                # no in-window prior year: plan sits close to actual
                plan_val = act[metric] / g.uniform(*C.PRE_CY_ATTAINMENT_RANGE)
            rows.append({"month": month.strftime("%Y-%m"), "market": market,
                         "metric": metric, "target_value": round(plan_val, 2)})
        rows.append({"month": month.strftime("%Y-%m"), "market": market,
                     "metric": "Blended CAC", "target_value": round(g.uniform(24, 40), 2)})
        rows.append({"month": month.strftime("%Y-%m"), "market": market,
                     "metric": "Gross Margin %", "target_value": round(g.uniform(0.16, 0.21), 4)})
    U.write_csv(pd.DataFrame(rows), C.RAW_DIR / "finance_targets.csv")


# =====================================================================================
# main
# =====================================================================================

def main():
    U.section("VoltEdge Electronics — Stage 01: generate raw layer")
    fx, fxl = gen_fx()
    suppliers = gen_suppliers()
    products, cost_history, price_history = gen_products(suppliers)
    orders_df, lines_df, returns_df, seeds = gen_orders(products, price_history, fxl)
    write_oms_crm(orders_df, lines_df, seeds)
    gen_psp(orders_df)
    po_df = gen_procurement(products, cost_history, suppliers, seeds)
    gen_inventory(po_df, seeds, products)
    write_returns(returns_df)
    gen_web(seeds)
    gen_marketing(seeds, fxl)
    write_support(seeds)
    write_carrier_json(seeds)
    gen_targets(orders_df, lines_df, returns_df, seeds)
    U.section("Stage 01 complete")
    U.log(f"raw files in {C.RAW_DIR}")


if __name__ == "__main__":
    main()
