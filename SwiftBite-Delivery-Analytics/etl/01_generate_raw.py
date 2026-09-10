"""
SwiftBite Delivery — 01_generate_raw.py

A seeded marketplace simulator. Builds zones / couriers / customers / restaurants,
simulates demand and courier supply per zone-hour, clears the marketplace through a
liquidity -> outcome model, applies the zone-hour incentive experiment (supply
response by baseline stress tier + neighbour-zone cannibalisation), and writes
source-faithful *messy* exports under data/raw/.

The true incentive effect lives only in config.INCENTIVE_EFFECT.

Everything is vectorised at the zone-hour grain; order-level attributes are drawn in
per-zone-hour batches and concatenated. One SEED -> byte-identical raw.
"""
from __future__ import annotations

import gzip
import json
from datetime import datetime, timedelta

import numpy as np
import pandas as pd

import config as C
from utils import (banner, date_key, daterange, fmt_dt, fmt_money_brl, mojibake,
                   rng, to_excel_serial, window_month_index, write_csv)

RAW = C.RAW_DIR
HOUR_FRAC = np.array(C.HOUR_SHAPE, float) / sum(C.HOUR_SHAPE)

# ZONE tuple: (id, name, macro_area, area_km2, cx, cy, dem_w, supply_attr)
ZONE_IDS = [z[0] for z in C.ZONES]
NZ = len(ZONE_IDS)
ZIDX = {z: i for i, z in enumerate(ZONE_IDS)}
ZMACRO = np.array([z[2] for z in C.ZONES])
ZAREA = np.array([z[3] for z in C.ZONES], float)
ZCX = np.array([z[4] for z in C.ZONES], float)
ZCY = np.array([z[5] for z in C.ZONES], float)
ZDEMW = np.array([z[6] for z in C.ZONES], float)
ZATTR = np.array([z[7] for z in C.ZONES], float)
SVC_MIN = np.array([C.SERVICE_MIN_BY_AREA[m] for m in ZMACRO], float)
TRIP_KM_BY_AREA = {"centre": 2.4, "inner_ring": 3.6, "outer_ring": 5.1}
ZTRIPKM = np.array([TRIP_KM_BY_AREA[m] for m in ZMACRO], float)
BH_LAT0, BH_LON0, CELL_DEG = -19.92, -43.94, 0.02

ADJ = {z: set() for z in ZONE_IDS}
for a, b in C.ZONE_ADJACENCY:
    ADJ[a].add(b); ADJ[b].add(a)
ADJ_IDX = [sorted(ZIDX[n] for n in ADJ[z]) for z in ZONE_IDS]

# demand share (flat-ish) and supply tilt (small, attractiveness-driven mismatch)
ZONE_SHARE = ZDEMW / ZDEMW.sum()                          # order-demand share
CHDEM_SHARE = (ZONE_SHARE * SVC_MIN) / (ZONE_SHARE * SVC_MIN).sum()   # courier-hour demand share
_attr_z = (ZATTR - ZATTR.mean()) / ZATTR.std()
SUPPLY_TILT = np.exp(0.20 * _attr_z)                      # small supply/demand mismatch by attractiveness
SUPPLY_W = CHDEM_SHARE * SUPPLY_TILT
SUPPLY_W = SUPPLY_W / SUPPLY_W.sum()
BASE_SUP_RATIO = 1.12                                     # metro-wide avg courier-hours / demanded


def cell_latlon(cx, cy, gen, n):
    lat = BH_LAT0 + (cy - 2) * CELL_DEG + gen.normal(0, CELL_DEG * 0.35, n)
    lon = BH_LON0 + (cx - 3) * CELL_DEG + gen.normal(0, CELL_DEG * 0.35, n)
    return np.round(lat, 6), np.round(lon, 6)


# --------------------------------------------------------------------------- #
# Dimensions / masters
# --------------------------------------------------------------------------- #
def gen_georef():
    banner("georef")
    rows = [dict(zone_id=z[0], zone_name=z[1], macro_area=z[2], area_km2=z[3],
                 centroid_lat=round(BH_LAT0 + (z[5] - 2) * CELL_DEG, 6),
                 centroid_lon=round(BH_LON0 + (z[4] - 3) * CELL_DEG, 6),
                 n_neighbours=len(ADJ[z[0]])) for z in C.ZONES]
    write_csv(pd.DataFrame(rows), RAW / "georef" / "georef__zones.csv")
    write_csv(pd.DataFrame(sorted({tuple(sorted(e)) for e in C.ZONE_ADJACENCY}),
                           columns=["zone_id_a", "zone_id_b"]),
              RAW / "georef" / "georef__zone_adjacency.csv")
    a, b = C.ZONE_REDRAW_PAIR
    hist = [dict(zone_id=a, valid_from="2025-01-01", valid_to="2025-08-31", note="pre-redraw polygon"),
            dict(zone_id=a, valid_from="2025-09-01", valid_to="", note=f"current polygon (strip moved to {b})"),
            dict(zone_id=b, valid_from="2025-01-01", valid_to="2025-08-31", note="pre-redraw polygon"),
            dict(zone_id=b, valid_from="2025-09-01", valid_to="", note=f"current polygon (gained strip from {a})")]
    write_csv(pd.DataFrame(hist), RAW / "georef" / "georef__zone_history.csv")


def gen_couriers():
    g = rng("couriers"); n = C.N_COURIERS_TOTAL
    df = pd.DataFrame(dict(
        courier_id=[f"C{100000+i}" for i in range(n)],
        vehicle_type=g.choice(list(C.COURIER_VEHICLE_MIX), n, p=list(C.COURIER_VEHICLE_MIX.values())),
        acquisition_channel=g.choice(list(C.COURIER_ACQ_CHANNEL_MIX), n, p=list(C.COURIER_ACQ_CHANNEL_MIX.values())),
        signup_date=[(C.WINDOW_START + timedelta(days=int(x))).isoformat()
                     for x in g.integers(-120, C.N_MONTHS * 30 - 30, n)],
        home_zone_hint=g.choice(ZONE_IDS, n, p=ZONE_SHARE)))
    m = g.random(n) < 0.05
    df.loc[m, "courier_id"] = df.loc[m, "courier_id"].str.lower()
    write_csv(df, RAW / "riderapp" / "riderapp__couriers.csv")
    return df


def gen_customers():
    g = rng("customers"); n = int(9000 * C.SCALE)
    df = pd.DataFrame(dict(customer_id=[f"U{200000+i}" for i in range(n)],
                           customer_segment=g.choice(["new", "casual", "regular", "heavy"], n,
                                                     p=[0.28, 0.4, 0.24, 0.08]),
                           home_zone_hint=g.choice(ZONE_IDS, n, p=ZONE_SHARE)))
    write_csv(df, RAW / "ordercore" / "ordercore__customers.csv")
    return df


def gen_restaurants():
    g = rng("restaurants"); n = int(1200 * C.SCALE)
    cuisine = g.choice(["brazilian", "pizza", "burger", "japanese", "healthy", "dessert", "arab"],
                       n, p=[0.28, 0.2, 0.16, 0.12, 0.1, 0.08, 0.06])
    names = [f"{c.title()} {s}" for c, s in zip(
        cuisine, g.choice(["Express", "Casa", "Refeições", "Grill", "Cantina", "Sabor & Cia",
                           "da Praça", "do Bairro"], n))]
    df = pd.DataFrame(dict(restaurant_id=[f"R{300000+i}" for i in range(n)], restaurant_name=names,
                           zone_id=g.choice(ZONE_IDS, n, p=ZONE_SHARE), cuisine=cuisine,
                           price_band=g.choice(["R$", "R$$", "R$$$"], n, p=[0.45, 0.42, 0.13])))
    m = g.random(n) < C.DQ["ordercore_latin1_rate"] * 0.3
    df.loc[m, "restaurant_name"] = df.loc[m, "restaurant_name"].map(mojibake)
    write_csv(df, RAW / "ordercore" / "ordercore__restaurants.csv")
    return df


# --------------------------------------------------------------------------- #
# Calendar factors
# --------------------------------------------------------------------------- #
def rainy_days():
    g = rng("rain")
    return {d: (g.random() < C.RAIN_DAY_PROB_IN_SEASON if d.month in C.RAINY_MONTHS else g.random() < 0.05)
            for d in daterange(C.WINDOW_START, C.WINDOW_END)}


def event_map():
    g = rng("events"); out = {}
    for d in daterange(C.WINDOW_START, C.WINDOW_END):
        if g.random() < C.EVENT_EVENINGS_PER_WEEK / 7.0:
            out[(d, int(g.choice(range(NZ), p=ZONE_SHARE)))] = C.EVENT_ZONE_DEMAND_MULT
    return out


def assign_experiment():
    """{(date, zone_idx): 'treatment'|'control'} for peak-eligible zone-days, 50/50
    within zone x weekday/weekend."""
    g = rng("assign"); out = {}
    days = list(daterange(C.EXPERIMENT_START, C.EXPERIMENT_END))
    for zi in range(NZ):
        for grp in ([d for d in days if d.weekday() < 5], [d for d in days if d.weekday() >= 5]):
            grp = list(grp); g.shuffle(grp)
            k = int(round(len(grp) * C.EXPERIMENT_ALLOCATION))
            for i, d in enumerate(grp):
                out[(d, zi)] = "treatment" if i < k else "control"
    return out


def piecewise(x, table):
    xs = np.array(sorted(table)); ys = np.array([table[k] for k in sorted(table)])
    return np.interp(x, xs, ys)


# --------------------------------------------------------------------------- #
# Core simulation — vectorised at zone-hour grain
# --------------------------------------------------------------------------- #
def simulate():
    banner("simulate marketplace (zone-hour) + experiment — vectorised")
    gd = rng("demand"); gs = rng("supply"); go = rng("outcome")
    rain = rainy_days(); events = event_map()
    all_days = list(daterange(C.WINDOW_START, C.WINDOW_END))

    def metro_day_orders(d):
        m = C.ORDERS_PER_DAY_METRO_BASE * C.DOW_MULT[d.weekday()] * C.MONTH_SEASONALITY[d.month]
        if d.month in C.RAINY_MONTHS:
            m *= C.RAINY_DEMAND_MULT
        if rain[d]:
            m *= C.RAIN_DAY_DEMAND_MULT
        return m

    def sup_ratio(d):
        r = BASE_SUP_RATIO
        if d.month in C.RAINY_MONTHS:
            r *= C.RAINY_SUPPLY_MULT
        if rain[d]:
            r *= C.RAIN_DAY_SUPPLY_MULT
        if d >= C.SUPPLY_DECLINE_PER_MONTH_FROM:
            r *= (1 - C.SUPPLY_DECLINE_PER_MONTH) ** ((d.year - 2026) * 12 + d.month)
        return r

    # ---- pass 1: baseline stress tiers (months 1-15) -----------------------
    L_sum = np.zeros(NZ); L_n = 0
    for d in daterange(C.WINDOW_START, C.BASELINE_END):
        mdo, sr = metro_day_orders(d), sup_ratio(d)
        for h in range(24):
            o = mdo * HOUR_FRAC[h] * ZONE_SHARE
            dem_ch = o * SVC_MIN / 60.0
            metro_ch = dem_ch.sum() * sr
            avail = metro_ch * SUPPLY_W
            good = dem_ch > 1e-6
            L_sum[good] += avail[good] / dem_ch[good]; L_n += 1
    base_L = L_sum / max(L_n, 1)
    tier = np.where(base_L < 0.93, "short", np.where(base_L > 1.13, "long", "balanced"))
    stress_tier = {ZONE_IDS[i]: tier[i] for i in range(NZ)}
    print("baseline mean L:", {ZONE_IDS[i]: round(float(base_L[i]), 2) for i in range(NZ)})
    print("tiers:", stress_tier,
          "| counts:", {t: int((tier == t).sum()) for t in ["short", "balanced", "long"]})

    exp_assign = assign_experiment()
    eff = C.INCENTIVE_EFFECT
    tier_mult = np.array([eff["supply_response_mult_by_tier"][t] for t in tier])

    # ---- pass 2: full sim, vectorised per (day, hour) across all 12 zones ----
    gc = rng("clear")
    CATS = np.array(["delivered", "cancelled_no_courier", "cancelled_customer",
                     "cancelled_courier", "cancelled_restaurant"])
    csp = np.array([C.CANCEL_SPLIT[k] for k in ("no_courier", "customer", "courier", "restaurant")], float)
    csp = csp / csp.sum()
    ev_by_day: dict = {}
    for (ed, ezi), mlt in events.items():
        ev_by_day.setdefault(ed, []).append((ezi, mlt))
    metro_ch_hour_const = (ZONE_SHARE * SVC_MIN / 60.0).sum()   # * mdo*HOUR_FRAC[h]*sr

    zh_rows = []
    oc_cols = ["date_key", "zone_idx", "hour", "is_peak", "outcome", "eta_min", "latency_s",
               "basket_brl", "fee_brl", "dist_km", "wmi", "arm", "exp_week"]
    o_chunks = {k: [] for k in oc_cols}

    for d in all_days:
        dk = date_key(d); wmi = window_month_index(d, C.WINDOW_START)
        mdo, sr = metro_day_orders(d), sup_ratio(d)
        in_exp = C.EXPERIMENT_START <= d <= C.EXPERIMENT_END
        exp_week = ((d - C.EXPERIMENT_START).days // 7 + 1) if in_exp else 0
        arm_vec = (np.array([exp_assign.get((d, zi), "") for zi in range(NZ)], object)
                   if in_exp else np.array([""] * NZ, object))
        day_events = ev_by_day.get(d, [])

        for h in range(24):
            is_peak = h in C.PEAK_HOURS
            o_lam = mdo * HOUR_FRAC[h] * ZONE_SHARE.copy()
            if is_peak:
                for ezi, mlt in day_events:
                    o_lam[ezi] *= mlt
            orders = gd.poisson(np.maximum(o_lam, 0)).astype(int)
            dem_ch = orders * SVC_MIN / 60.0
            metro_ch = mdo * HOUR_FRAC[h] * sr * metro_ch_hour_const
            avail = metro_ch * SUPPLY_W * np.exp(gs.normal(0, 0.06, NZ))

            if in_exp and is_peak:
                treated = (arm_vec == "treatment")
                nov = 1 + (eff["novelty_mult_week1"] - 1) * np.exp(-(exp_week - 1) / eff["novelty_decay_tau_weeks"])
                mult = np.where(treated,
                                1 + (tier_mult - 1) * nov * np.exp(go.normal(0, eff["supply_response_noise_sd"], NZ)),
                                1.0)
                delta = avail * (mult - 1.0)
                avail = avail * mult
                pull = np.zeros(NZ)
                for zi in np.where(treated & (delta > 0))[0]:
                    adj_ctrl = [j for j in ADJ_IDX[zi] if arm_vec[j] == "control"]
                    if adj_ctrl:
                        per = eff["cannibalisation_share"] * delta[zi] / len(adj_ctrl)
                        for j in adj_ctrl:
                            pull[j] += per
                avail = np.maximum(avail - pull, np.where(dem_ch > 0, 0.05 * dem_ch, 0.0))

            L = np.full(NZ, np.nan)
            np.divide(avail, dem_ch, out=L, where=dem_ch > 1e-6)
            Lf = np.where(np.isnan(L), 1.0, L)

            fr_z = np.clip(np.interp(Lf, sorted(C.FULFILL_AT_L), [C.FULFILL_AT_L[k] for k in sorted(C.FULFILL_AT_L)])
                           + gc.normal(0, 0.012, NZ), 0.5, 0.999)
            eta50_z = (np.interp(Lf, sorted(C.ETA_P50_AT_L), [C.ETA_P50_AT_L[k] for k in sorted(C.ETA_P50_AT_L)])
                       * (SVC_MIN / 34.0) ** 0.5)
            spread_z = np.interp(Lf, sorted(C.ETA_P90_SPREAD), [C.ETA_P90_SPREAD[k] for k in sorted(C.ETA_P90_SPREAD)])
            lat90_z = np.interp(Lf, sorted(C.ASSIGN_LATENCY_P90_AT_L),
                                [C.ASSIGN_LATENCY_P90_AT_L[k] for k in sorted(C.ASSIGN_LATENCY_P90_AT_L)])

            deliv_z = gc.binomial(orders, fr_z)
            nd = orders - deliv_z
            nc_z = gc.binomial(nd, csp[0])
            r1 = nd - nc_z
            cu_z = gc.binomial(r1, csp[1] / (csp[1] + csp[2] + csp[3]))
            r2 = r1 - cu_z
            co_z = gc.binomial(r2, csp[2] / (csp[2] + csp[3]))
            re_z = r2 - co_z

            tot = int(orders.sum())
            if tot:
                counts = np.stack([deliv_z, nc_z, cu_z, co_z, re_z], axis=1).reshape(-1)   # (12*5,)
                zrep = np.repeat(np.repeat(np.arange(NZ), 5), counts)
                outc = np.repeat(np.tile(CATS, NZ), counts)
                sig = np.maximum(np.log(spread_z) / 1.2815, 0.05)
                eta = np.full(tot, np.nan)
                dm = outc == "delivered"
                eta[dm] = np.round(gc.lognormal(np.log(np.maximum(eta50_z[zrep[dm]], 5)), sig[zrep[dm]]), 1)
                lat = np.round(gc.lognormal(np.log(np.maximum(lat90_z[zrep] / 2.2, 20)), 0.5), 0)
                o_chunks["date_key"].append(np.full(tot, dk))
                o_chunks["zone_idx"].append(zrep.astype(np.int16))
                o_chunks["hour"].append(np.full(tot, h, np.int8))
                o_chunks["is_peak"].append(np.full(tot, is_peak))
                o_chunks["outcome"].append(outc)
                o_chunks["eta_min"].append(eta)
                o_chunks["latency_s"].append(lat)
                o_chunks["basket_brl"].append(np.round(gc.lognormal(np.log(C.BASKET_VALUE_BRL_MEAN), C.BASKET_VALUE_BRL_CV, tot), 2))
                o_chunks["fee_brl"].append(np.round(np.clip(gc.normal(C.DELIVERY_FEE_BRL_MEAN, C.DELIVERY_FEE_BRL_SD, tot), 3, None), 2))
                o_chunks["dist_km"].append(np.round(np.clip(gc.normal(ZTRIPKM[zrep], 1.4), 0.4, None), 2))
                o_chunks["wmi"].append(np.full(tot, wmi, np.int16))
                o_chunks["arm"].append((arm_vec[zrep] if (in_exp and is_peak) else np.full(tot, "", object)))
                o_chunks["exp_week"].append(np.full(tot, exp_week, np.int8))

            ev_flag = np.zeros(NZ, np.int8)
            for ezi, _ in day_events:
                ev_flag[ezi] = 1
            for zi in np.where(orders > 0)[0]:
                zh_rows.append((dk, int(zi), h, bool(is_peak), int(orders[zi]), int(deliv_z[zi]),
                                int(nc_z[zi]), int(cu_z[zi]), int(co_z[zi]), int(re_z[zi]),
                                float(avail[zi]), float(dem_ch[zi]), float(Lf[zi]),
                                arm_vec[zi] if (in_exp and is_peak) else "",
                                int(rain[d]), int(ev_flag[zi])))

    orders_df = pd.DataFrame({k: np.concatenate(v) for k, v in o_chunks.items()})
    orders_df["order_id"] = np.arange(1, len(orders_df) + 1)
    orders_df["zone_id"] = np.array(ZONE_IDS)[orders_df["zone_idx"].to_numpy()]
    zh = pd.DataFrame(zh_rows, columns=[
        "date_key", "zone_idx", "hour", "is_peak", "orders_placed", "delivered", "canc_no_courier",
        "canc_customer", "canc_courier", "canc_restaurant", "avail_ch", "dem_ch", "L", "arm",
        "is_rain", "has_event"])
    zh["zone_id"] = np.array(ZONE_IDS)[zh["zone_idx"].to_numpy()]
    banner(f"orders simulated: {len(orders_df):,}  | zone-hours: {len(zh):,}")
    return orders_df, zh, stress_tier, exp_assign


# --------------------------------------------------------------------------- #
# Emit messy raw
# --------------------------------------------------------------------------- #
def emit_orders(df, customers, restaurants):
    banner("emit ordercore + dispatch + payhub(order)")
    g = rng("emit_orders")
    n = len(df)
    df = df.copy()
    df["order_code"] = "O" + (5_000_000 + df["order_id"].to_numpy()).astype(str)
    base_dt = pd.to_datetime(df["date_key"], format="%Y%m%d") + pd.to_timedelta(df["hour"], "h") \
        + pd.to_timedelta(g.integers(0, 3600, n), "s")
    df["ts"] = base_dt
    df["customer_id"] = g.choice(customers["customer_id"].to_numpy(), n)
    rest_by_zone = restaurants.groupby("zone_id")["restaurant_id"].apply(np.array).to_dict()
    all_rest = restaurants["restaurant_id"].to_numpy()
    df["restaurant_id"] = [rest_by_zone.get(z, all_rest)[g.integers(0, len(rest_by_zone.get(z, all_rest)))]
                           for z in df["zone_id"].to_numpy()]
    rzone = restaurants.set_index("restaurant_id")["zone_id"]
    df["pickup_zone_id"] = rzone.reindex(df["restaurant_id"].to_numpy()).fillna(df["zone_id"]).to_numpy()

    # Q07 as-booked label: pre-redraw, some border orders carry the swapped zone
    a, b = C.ZONE_REDRAW_PAIR
    lbl = df["zone_id"].to_numpy().copy()
    pre = (df["ts"].to_numpy() < np.datetime64(C.ZONE_REDRAW_DATE))
    swap = pre & np.isin(df["zone_id"], [a, b]) & (g.random(n) < C.ZONE_REDRAW_ASBOOKED_MISassign_RATE)
    lbl = np.where(swap & (df["zone_id"] == a).to_numpy(), b, lbl)
    lbl = np.where(swap & (df["zone_id"] == b).to_numpy(), a, lbl)
    df["delivery_zone_label"] = lbl

    # ---- orders monthly files
    ym = df["ts"].dt.strftime("%Y-%m")
    for period, part in df.groupby(ym, sort=True):
        p = part
        as_text = g.random(len(p)) < C.DQ["money_text_rate"]
        fmts = g.random(len(p)) < C.DQ["ordercore_date_format_mix"].get("br_datetime", 0.45)
        placed = np.where(fmts, p["ts"].dt.strftime("%d/%m/%Y %H:%M"),
                          p["ts"].dt.strftime("%Y-%m-%dT%H:%M:%S"))
        basket = np.where(as_text,
                          [fmt_money_brl(x, s) for x, s in zip(p["basket_brl"], g.choice(["symbol", "plain"], len(p)))],
                          p["basket_brl"].astype(str))
        out = pd.DataFrame(dict(order_id=p["order_code"], customer_id=p["customer_id"],
                                restaurant_id=p["restaurant_id"], pickup_zone_id=p["pickup_zone_id"],
                                delivery_zone_label=p["delivery_zone_label"], placed_at=placed,
                                basket_value=basket, delivery_fee=p["fee_brl"].astype(str),
                                outcome=p["outcome"], eta_min=p["eta_min"], dist_km=p["dist_km"]))
        dup = out.sample(frac=C.DQ["ordercore_retry_dupe_rate"], random_state=int(period.replace("-", "")))
        write_csv(pd.concat([out, dup], ignore_index=True),
                  RAW / "ordercore" / f"ordercore__orders__{period}.csv")

        # status events (vectorised per status)
        seg = []
        b0 = p["ts"]
        seg.append(pd.DataFrame(dict(order_id=p["order_code"], status="placed",
                                     event_at=b0.dt.strftime("%Y-%m-%dT%H:%M:%S"))))
        dl = p["outcome"] == "delivered"
        seg.append(pd.DataFrame(dict(order_id=p.loc[dl, "order_code"], status="assigned",
                                     event_at=(b0[dl] + pd.to_timedelta(p.loc[dl, "latency_s"], "s")).dt.strftime("%Y-%m-%dT%H:%M:%S"))))
        seg.append(pd.DataFrame(dict(order_id=p.loc[dl, "order_code"], status="delivered",
                                     event_at=(b0[dl] + pd.to_timedelta(p.loc[dl, "eta_min"], "m")).dt.strftime("%Y-%m-%dT%H:%M:%S"))))
        nc = p["outcome"] == "cancelled_no_courier"
        seg.append(pd.DataFrame(dict(order_id=p.loc[nc, "order_code"], status="no_courier_found",
                                     event_at=(b0[nc] + pd.to_timedelta(p.loc[nc, "latency_s"] + 300, "s")).dt.strftime("%Y-%m-%dT%H:%M:%S"))))
        cx = p["outcome"].str.startswith("cancelled")
        seg.append(pd.DataFrame(dict(order_id=p.loc[cx, "order_code"], status="cancelled",
                                     event_at=(b0[cx] + pd.to_timedelta(700, "s")).dt.strftime("%Y-%m-%dT%H:%M:%S"))))
        ev = pd.concat(seg, ignore_index=True)
        ev = pd.concat([ev, ev.sample(frac=C.DQ["event_at_least_once_rate"], random_state=7)], ignore_index=True)
        cap = g.random(len(ev)) < 0.08
        ev.loc[cap, "status"] = ev.loc[cap, "status"].str.upper()
        write_csv(ev, RAW / "ordercore" / f"ordercore__order_status_events__{period}.csv")

        # addresses
        lat, lon = cell_latlon(ZCX[p["zone_idx"].to_numpy()], ZCY[p["zone_idx"].to_numpy()], g, len(p))
        sw = g.random(len(p)) < 0.03
        lat2 = np.where(sw, lon, lat); lon2 = np.where(sw, lat, lon)
        moj = g.random(len(p)) < C.DQ["ordercore_latin1_rate"]
        _bnames = np.array(["Lourdes", "Funcionários", "Sion", "Savassi", "Cruzeiro",
                            "São Pedro", "Anchieta", "Coração Eucarístico"], object)
        bairro = np.array([f"{b} {k}" for b, k in zip(g.choice(_bnames, len(p)), g.integers(1, 40, len(p)))], object)
        log = g.choice(["Rua Antônio de Albuquerque", "Av. do Contorno", "Rua Pernambuco",
                        "Rua São Paulo", "Rua Ceará", "Av. Getúlio Vargas", "Rua Grão Mogol"], len(p))
        bairro = np.where(moj, [mojibake(x) for x in bairro], bairro)
        log = np.where(moj, [mojibake(str(x)) for x in log], log)
        write_csv(pd.DataFrame(dict(order_id=p["order_code"], bairro=bairro, logradouro=log,
                                    cep=[f"{c:05d}-{s:03d}" for c, s in zip(g.integers(30000, 32000, len(p)), g.integers(0, 999, len(p)))],
                                    lat=lat2, lon=lon2)),
                  RAW / "ordercore" / f"ordercore__addresses__{period}.csv")

    # ---- dispatch assignment events
    b0 = df["ts"]
    parts = [pd.DataFrame(dict(order_id=df["order_code"], event="order_ready",
                               event_at=(b0 + pd.to_timedelta(120, "s")).dt.strftime("%Y-%m-%dT%H:%M:%S"),
                               latency_ms_text=""))]
    dl = df["outcome"] == "delivered"
    parts.append(pd.DataFrame(dict(order_id=df.loc[dl, "order_code"], event="assigned",
                                   event_at=(b0[dl] + pd.to_timedelta(df.loc[dl, "latency_s"], "s")).dt.strftime("%Y-%m-%dT%H:%M:%S"),
                                   latency_ms_text=(df.loc[dl, "latency_s"] * 1000).astype(int).astype(str))))
    parts.append(pd.DataFrame(dict(order_id=df.loc[dl, "order_code"], event="delivered",
                                   event_at=(b0[dl] + pd.to_timedelta(df.loc[dl, "eta_min"], "m")).dt.strftime("%Y-%m-%dT%H:%M:%S"),
                                   latency_ms_text="")))
    nc = df["outcome"] == "cancelled_no_courier"
    parts.append(pd.DataFrame(dict(order_id=df.loc[nc, "order_code"], event="no_courier_found",
                                   event_at=(b0[nc] + pd.to_timedelta(df.loc[nc, "latency_s"] + 300, "s")).dt.strftime("%Y-%m-%dT%H:%M:%S"),
                                   latency_ms_text="")))
    cx = df["outcome"].str.startswith("cancelled") & ~nc
    parts.append(pd.DataFrame(dict(order_id=df.loc[cx, "order_code"], event=df.loc[cx, "outcome"],
                                   event_at=(b0[cx] + pd.to_timedelta(480, "s")).dt.strftime("%Y-%m-%dT%H:%M:%S"),
                                   latency_ms_text="")))
    de = pd.concat(parts, ignore_index=True)
    de = pd.concat([de, de.sample(frac=C.DQ["event_at_least_once_rate"], random_state=11)], ignore_index=True)
    write_csv(de, RAW / "dispatch" / "dispatch__assignment_events.csv")

    # ---- payhub order payments (UTC Z, text money, parens reversals, redelivered month)
    pd_ = df[df["outcome"] == "delivered"].copy()
    paid_utc = (pd_["ts"] + pd.to_timedelta(3, "h")).dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    amt = pd_["basket_brl"] + pd_["fee_brl"]
    rev = g.random(len(pd_)) < C.DQ["payhub_parens_reversal_rate"]
    amount = np.where(rev, [fmt_money_brl(-x, "parens") for x in (pd_["basket_brl"].to_numpy() * 0.1)],
                      [fmt_money_brl(x, "plain") for x in amt.to_numpy()])
    wk = (pd_["ts"] - pd.to_timedelta(pd_["ts"].dt.weekday, "D")).dt.date
    payout = pd.DataFrame(dict(order_id=pd_["order_code"], paid_at_utc=paid_utc, amount=amount,
                               settlement_week=[to_excel_serial(x) for x in wk]))
    write_csv(payout, RAW / "payhub" / "payhub__order_payments.csv")
    red = payout[pd_["ts"].dt.strftime("%Y-%m").to_numpy() == C.DQ["payhub_redelivered_month"]]
    if len(red):
        write_csv(red, RAW / "payhub" / "payhub__order_payments__2026-05_REDELIVERED.csv")
    return df


def emit_courier_layer(zh, couriers, exp_assign, stress_tier):
    banner("emit riderapp + trace + payhub(courier) + boost")
    g = rng("emit_courier")
    couriers = couriers.copy()
    couriers["cid"] = couriers["courier_id"].str.upper()
    pools = {z: couriers.loc[couriers["home_zone_hint"] == z, "cid"].to_numpy() for z in ZONE_IDS}
    allc = couriers["cid"].to_numpy()
    for z in ZONE_IDS:
        if len(pools[z]) < 30:
            pools[z] = allc[:60]

    act = zh[zh["avail_ch"] > 0.2].copy()
    act["n_slots"] = np.clip(act["avail_ch"].round().astype(int), 1, 300)
    act["util"] = np.clip((act["delivered"] * SVC_MIN[act["zone_idx"].to_numpy()])
                          / (act["avail_ch"] * 60.0).clip(lower=1), 0.05, 0.98)
    # explode to one row per courier-slot
    rep = act.loc[act.index.repeat(act["n_slots"])].reset_index(drop=True)
    m = len(rep)
    zi = rep["zone_idx"].to_numpy()
    rep["courier_id"] = [pools[ZONE_IDS[z]][g.integers(0, len(pools[ZONE_IDS[z]]))] for z in zi]
    li = np.clip(g.normal(52, 8, m), 15, 60)
    am = np.clip(g.normal(li * rep["util"].to_numpy(), 6), 0, li)
    cd = (li * C.COOLDOWN_SHARE).astype(int)
    idle = np.clip(li - am - cd, 0, None)
    per_slot = (rep["delivered"] / rep["n_slots"]).to_numpy()
    dl = g.poisson(np.maximum(per_slot, 0.01))
    trip_km = ZTRIPKM[zi]
    base_pay = dl * C.COURIER_BASE_PAYOUT_PER_DELIVERY_BRL + dl * C.COURIER_PAYOUT_PER_KM_BRL * trip_km
    tips = np.where(g.random(m) < C.TIP_RATE, g.normal(C.TIP_MEAN_BRL, 2, m), 0.0) * dl * C.TIP_RATE
    is_treat_peak = (rep["arm"].to_numpy() == "treatment") & rep["is_peak"].to_numpy()
    bonus = np.where(is_treat_peak, dl * C.INCENTIVE_BONUS_BRL_PER_DELIVERY, 0.0)

    blk = pd.DataFrame(dict(courier_id=rep["courier_id"], zone_id=rep["zone_id"], date_key=rep["date_key"],
                            hour=rep["hour"], logged_in_min=li.round().astype(int), active_min=am.round().astype(int),
                            idle_min=idle.round().astype(int), cooldown_min=cd, deliveries=dl,
                            base_payout=base_pay.round(2), tip=np.clip(tips, 0, None).round(2),
                            bonus=bonus.round(2)))

    # sessions
    sess = blk.groupby(["courier_id", "date_key"]).agg(h0=("hour", "min"), h1=("hour", "max"),
                                                       mins=("logged_in_min", "sum")).reset_index()
    d0 = pd.to_datetime(sess["date_key"], format="%Y%m%d")
    fmtbr = g.random(len(sess)) < 0.45
    sess["login_local"] = np.where(fmtbr, (d0 + pd.to_timedelta(sess["h0"], "h")).dt.strftime("%d/%m/%Y %H:%M"),
                                   (d0 + pd.to_timedelta(sess["h0"], "h")).dt.strftime("%Y-%m-%dT%H:%M:%S"))
    sess["logout_local"] = (d0 + pd.to_timedelta(np.minimum(sess["h1"] + 1, 23), "h")).dt.strftime("%Y-%m-%dT%H:%M:%S")
    write_csv(sess[["courier_id", "date_key", "login_local", "logout_local", "mins"]],
              RAW / "riderapp" / "riderapp__courier_sessions.csv")
    write_csv(blk.assign(planned_min=blk["logged_in_min"])[["courier_id", "zone_id", "date_key", "hour", "planned_min"]],
              RAW / "riderapp" / "riderapp__shift_zone_blocks.csv")

    # offers: ~1 accepted per delivery + ~0.4 rejected
    acc = blk.loc[blk.index.repeat(blk["deliveries"])].reset_index(drop=True)
    off_acc = pd.DataFrame(dict(offer_id=[f"OF{x}" for x in g.integers(10**9, 10**10, len(acc))],
                                courier_id=acc["courier_id"], zone_id=acc["zone_id"],
                                date_key=acc["date_key"], hour=acc["hour"], outcome="accepted"))
    nrej = int(len(off_acc) * 0.4)
    rj = off_acc.sample(n=nrej, random_state=1).copy()
    rj["offer_id"] = [f"OF{x}" for x in g.integers(10**9, 10**10, nrej)]
    rj["courier_id"] = g.choice(allc, nrej)
    rj["outcome"] = g.choice(["rejected", "timeout", "ignored"], nrej)
    off = pd.concat([off_acc, rj], ignore_index=True)
    orph = g.random(len(off)) < C.DQ["orphan_courier_id_rate"]
    off.loc[orph, "courier_id"] = "C" + g.integers(900000, 999999, int(orph.sum())).astype(str)
    off = pd.concat([off, off.sample(frac=C.DQ["event_at_least_once_rate"], random_state=5)], ignore_index=True)
    cap = g.random(len(off)) < 0.1
    off.loc[cap, "outcome"] = off.loc[cap, "outcome"].str.upper()
    write_csv(off, RAW / "riderapp" / "riderapp__offers.csv")

    # trace dwell rollup
    write_csv(blk.assign(present_min=blk["active_min"] + blk["idle_min"])[
        ["courier_id", "zone_id", "date_key", "hour", "present_min"]],
        RAW / "trace" / "trace__zone_dwell_minutes.csv")
    emit_ping_reference(blk, g)

    # payhub courier payouts
    pay = blk[blk["deliveries"] > 0].copy()
    pay["gross"] = pay["base_payout"] + pay["tip"] + pay["bonus"]
    rev = g.random(len(pay)) < C.DQ["payhub_parens_reversal_rate"]
    pay["amount"] = np.where(rev, [fmt_money_brl(-x, "parens") for x in (pay["base_payout"].to_numpy() * 0.2)],
                             [fmt_money_brl(x, "plain") for x in pay["gross"].to_numpy()])
    d0 = pd.to_datetime(pay["date_key"], format="%Y%m%d")
    pay["paid_at_utc"] = (d0 + pd.to_timedelta(pay["hour"] + 3, "h")).dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    pay["settlement_week"] = [to_excel_serial(x) for x in (d0 - pd.to_timedelta(d0.dt.weekday, "D")).dt.date]
    write_csv(pay[["courier_id", "date_key", "zone_id", "deliveries", "amount", "settlement_week", "paid_at_utc"]],
              RAW / "payhub" / "payhub__courier_payouts.csv")

    # bonus payouts + ledger
    bp = blk[blk["bonus"] > 0].copy()
    d0 = pd.to_datetime(bp["date_key"], format="%Y%m%d")
    bp["paid_at_utc"] = (d0 + pd.to_timedelta(bp["hour"] + 3, "h")).dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    bpay = bp[["courier_id", "zone_id", "date_key", "hour", "deliveries", "bonus", "paid_at_utc"]].rename(columns={"bonus": "bonus_brl"})
    bpay = pd.concat([bpay, bpay.sample(frac=C.DQ["event_at_least_once_rate"], random_state=9)], ignore_index=True)
    write_csv(bpay, RAW / "payhub" / "payhub__bonus_payouts.csv")
    led = bpay.groupby(["zone_id", "date_key"], as_index=False)["bonus_brl"].sum()
    write_csv(pd.concat([led, led.sample(frac=0.01, random_state=3)], ignore_index=True),
              RAW / "boost" / "boost__bonus_ledger.csv")

    # boost campaigns
    camp = []
    for (d, zi), arm in exp_assign.items():
        camp.append((f"CMP-{ZONE_IDS[zi]}-{date_key(d)}", ZONE_IDS[zi], date_key(d), arm,
                     C.INCENTIVE_BONUS_BRL_PER_DELIVERY if arm == "treatment" else 0.0,
                     C.INCENTIVE_PUSH_RADIUS_M, C.PEAK_BLOCK_START_HOUR, C.PEAK_BLOCK_END_HOUR,
                     (datetime(d.year, d.month, d.day) - timedelta(hours=3)).strftime("%Y-%m-%dT%H:%M:%SZ")))
    cdf = pd.DataFrame(camp, columns=["campaign_id", "zone_id", "date_key", "arm", "bonus_brl_per_delivery",
                                      "push_radius_m", "peak_start_hour", "peak_end_hour", "created_at_utc"])
    late = cdf.sample(n=min(20, len(cdf)), random_state=2).copy()
    late["arm"] = np.where(late["arm"] == "treatment", "control", "treatment")
    late["bonus_brl_per_delivery"] = np.where(late["arm"] == "treatment", C.INCENTIVE_BONUS_BRL_PER_DELIVERY, 0.0)
    late["created_at_utc"] = (pd.to_datetime(late["date_key"], format="%Y%m%d") + pd.to_timedelta(1, "h")).dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    write_csv(pd.concat([cdf, late], ignore_index=True), RAW / "boost" / "boost__incentive_campaigns.csv")


def emit_ping_reference(blk, g):
    """Full-fidelity GPS pings for the last 7 days only (Trace ages out raw pings)."""
    ref_from = date_key(C.WINDOW_END - timedelta(days=6))
    ref = blk[blk["date_key"] >= ref_from]
    rows = []
    for r in ref.itertuples():
        cx, cy = ZCX[ZIDX[r.zone_id]], ZCY[ZIDX[r.zone_id]]
        npings = max(int(r.logged_in_min / 1.2), 1)
        base = datetime.strptime(str(r.date_key), "%Y%m%d").replace(hour=int(r.hour))
        offs = np.sort(g.uniform(0, r.logged_in_min, npings))
        lat = BH_LAT0 + (cy - 2) * CELL_DEG + g.normal(0, 0.0006, npings)
        lon = BH_LON0 + (cx - 3) * CELL_DEG + g.normal(0, 0.0006, npings)
        far = g.random(npings) < C.DQ["gps_faraway_ping_rate"]
        lat = np.where(far, lat + g.choice([-1.0, 1.0], npings) * g.uniform(2, 6, npings), lat)
        nul = g.random(npings) < C.DQ["gps_null_island_rate"]
        lat = np.where(nul, 0.0, lat); lon = np.where(nul, 0.0, lon)
        for o, la, lo in zip(offs, lat, lon):
            rows.append(dict(courier_id=r.courier_id, ts=int((base + timedelta(minutes=float(o))).timestamp() * 1000),
                             lat=round(float(la), 6), lon=round(float(lo), 6)))
    path = RAW / "trace" / "trace__location_pings__REF.ndjson.gz"
    path.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(path, "wt", encoding="utf-8") as fh:
        for d in rows:
            fh.write(json.dumps(d) + "\n")
    print(f"  ref pings: {len(rows):,}")


# --------------------------------------------------------------------------- #
def main():
    banner("SwiftBite — 01_generate_raw")
    for sub in ["georef", "ordercore", "riderapp", "trace", "dispatch", "payhub", "boost"]:
        (RAW / sub).mkdir(parents=True, exist_ok=True)
    gen_georef()
    couriers = gen_couriers()
    customers = gen_customers()
    restaurants = gen_restaurants()
    orders_df, zh, stress_tier, exp_assign = simulate()
    emit_orders(orders_df, customers, restaurants)
    emit_courier_layer(zh, couriers, exp_assign, stress_tier)
    zh.to_parquet(RAW / "_sim_truth_zone_hour.parquet", index=False)
    pd.DataFrame([(z, t) for z, t in stress_tier.items()],
                 columns=["zone_id", "baseline_supply_stress_tier"]).to_parquet(
        RAW / "_sim_truth_zone_tier.parquet", index=False)
    banner("01_generate_raw done")


if __name__ == "__main__":
    main()
