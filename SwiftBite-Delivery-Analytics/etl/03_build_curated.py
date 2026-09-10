"""
SwiftBite Delivery — 03_build_curated.py

Staging -> curated Kimball star. Resolves address labels to zones (as-booked +
current), puts supply and demand in the same unit (courier-hours), builds the
zone-hour liquidity spine, and pre-computes the zone-day experiment tables so
Phase 10 goes straight to tests.

Reads only data/staging/* (+ the internal _sim_truth_zone_hour context flags for
rain / local-event, which a real ops team would have as a feed). All money BRL.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

import config as C
from utils import banner, date_key, read_parquet, rng, write_dq_fragment, write_parquet

STG, CUR = C.STAGING_DIR, C.CURATED_DIR
PEAK_HOURS = list(range(C.PEAK_BLOCK_START_HOUR, C.PEAK_BLOCK_END_HOUR))
SVC_MIN = C.SERVICE_MIN_BY_AREA
BR_HOLIDAYS = {  # (month, day) fixed-date BR holidays, enough for context
    (1, 1), (4, 21), (5, 1), (9, 7), (10, 12), (11, 2), (11, 15), (12, 25),
}


def _dk(s):
    return pd.to_datetime(s).dt.year * 10000 + pd.to_datetime(s).dt.month * 100 + pd.to_datetime(s).dt.day


# --------------------------------------------------------------------------- #
def build_dims(stg):
    banner("curated — dimensions")
    # dim_date
    d = pd.date_range(C.DIM_DATE_START, C.DIM_DATE_END, freq="D")
    dim_date = pd.DataFrame({"date": d})
    dim_date["date_key"] = dim_date["date"].dt.year * 10000 + dim_date["date"].dt.month * 100 + dim_date["date"].dt.day
    dim_date["year"] = d.year; dim_date["quarter"] = d.quarter; dim_date["month"] = d.month
    dim_date["month_name"] = d.strftime("%b")
    dim_date["iso_week"] = d.isocalendar().week.values
    dim_date["day_of_week"] = d.dayofweek
    dim_date["is_weekend"] = d.dayofweek >= 5
    dim_date["is_holiday_br"] = [(x.month, x.day) in BR_HOLIDAYS for x in d]
    dim_date["is_rainy_season"] = d.month.isin(list(C.RAINY_MONTHS))
    ph = np.where(d < np.datetime64(C.EXPERIMENT_START), "pre",
                  np.where(d <= np.datetime64(C.EXPERIMENT_END), "test", "post"))
    dim_date["experiment_phase"] = ph
    wk = ((d - np.datetime64(C.EXPERIMENT_START)).days // 7 + 1)
    dim_date["experiment_week"] = np.where((ph == "test"), wk, np.nan)
    write_parquet(dim_date, CUR / "dim_date.parquet")

    # dim_time_block
    daypart = (["early"] * 6 + ["breakfast"] * 3 + ["lunch"] * 4 + ["afternoon"] * 5
               + ["dinner_peak"] * 4 + ["late"] * 2)
    dim_tb = pd.DataFrame({"time_block_key": range(24), "hour": range(24), "daypart": daypart})
    dim_tb["is_peak_block"] = dim_tb["hour"].isin(PEAK_HOURS)
    dim_tb["block_label"] = dim_tb["hour"].map(lambda h: f"{h:02d}:00–{h+1:02d}:00")
    write_parquet(dim_tb, CUR / "dim_time_block.parquet")

    # dim_zone (+ tier computed later from baseline liquidity) + adjacency bridge
    z = stg["georef_zones"].copy()
    z["zone_key"] = np.arange(1, len(z) + 1)
    a, b = C.ZONE_REDRAW_PAIR
    z["is_boundary_redrawn"] = z["zone_id"].isin([a, b])
    zk = dict(zip(z["zone_id"], z["zone_key"]))
    adj = stg["georef_adj"].copy()
    adj = pd.concat([adj, adj.rename(columns={"zone_id_a": "zone_id_b", "zone_id_b": "zone_id_a"})], ignore_index=True)
    adj["zone_key"] = adj["zone_id_a"].map(zk); adj["neighbour_zone_key"] = adj["zone_id_b"].map(zk)
    dim_adj = adj[["zone_key", "neighbour_zone_key"]].drop_duplicates().reset_index(drop=True)
    write_parquet(dim_adj, CUR / "dim_zone_adjacency.parquet")

    # dim_courier / customer / restaurant
    c = stg["couriers"].copy()
    c["courier_key"] = np.arange(1, len(c) + 1)
    c["signup_date_key"] = _dk(c["signup_date"])
    c["signup_cohort_month"] = pd.to_datetime(c["signup_date"]).dt.strftime("%Y-%m")
    c["home_zone_key"] = c["home_zone_hint"].map(zk)
    c["is_test_account"] = False
    dim_courier = c[["courier_key", "courier_id", "signup_date_key", "signup_cohort_month",
                     "vehicle_type", "acquisition_channel", "home_zone_key", "is_test_account"]]
    write_parquet(dim_courier, CUR / "dim_courier.parquet")

    u = stg["customers"].copy()
    u["customer_key"] = np.arange(1, len(u) + 1)
    u["home_zone_key"] = u["home_zone_hint"].map(zk)
    write_parquet(u[["customer_key", "customer_id", "customer_segment", "home_zone_key"]],
                  CUR / "dim_customer.parquet")

    r = stg["restaurants"].copy()
    r["restaurant_key"] = np.arange(1, len(r) + 1)
    r["zone_key"] = r["zone_id"].map(zk)
    write_parquet(r[["restaurant_key", "restaurant_id", "zone_key", "cuisine", "price_band"]],
                  CUR / "dim_restaurant.parquet")

    return dim_date, dim_tb, z, zk, dim_courier, u, r


# --------------------------------------------------------------------------- #
def build_facts(stg, dim_date, z, zk, dim_courier, dim_customer, dim_restaurant):
    banner("curated — fact_order")
    g = rng("curate")
    o = stg["orders"].copy()
    o["order_key"] = np.arange(1, len(o) + 1)
    o["placed_ts"] = pd.to_datetime(o["placed_ts"], utc=True)
    local = o["placed_ts"].dt.tz_convert(C.TIMEZONE)
    o["placed_date_key"] = local.dt.year * 10000 + local.dt.month * 100 + local.dt.day
    o["placed_hour"] = local.dt.hour
    o["time_block_key"] = o["placed_hour"]
    o["is_peak_block"] = o["placed_hour"].isin(PEAK_HOURS)

    # zone resolution.
    #   as-booked = the messy `delivery_zone_label` (carries the pre-redraw swaps).
    #   current   = as-booked, EXCEPT for the two redrawn zones on pre-redraw dates,
    #               where the label is stale and the address centroid is resolved to
    #               today's map. The redraw (window-month 9) predates the experiment
    #               window by 7 months, so within the experiment the two agree exactly.
    a, b = C.ZONE_REDRAW_PAIR
    o["dropoff_zone_key_asbooked"] = o["delivery_zone_label"].map(zk).to_numpy()
    o["pickup_zone_key"] = o["pickup_zone_id"].map(zk).to_numpy()
    o["dropoff_zone_key_current"] = o["dropoff_zone_key_asbooked"]
    redraw_dk = C.ZONE_REDRAW_DATE.year * 10000 + C.ZONE_REDRAW_DATE.month * 100 + C.ZONE_REDRAW_DATE.day
    mask = o["delivery_zone_label"].isin([a, b]) & (o["placed_date_key"] < redraw_dk)
    if mask.any():
        addr = stg["addresses"].set_index("order_id")
        cz = z[["zone_id", "centroid_lat", "centroid_lon"]].to_numpy()
        sub = o.loc[mask, "order_id"]
        lat = addr["lat"].reindex(sub).to_numpy(); lon = addr["lon"].reindex(sub).to_numpy()
        swp = np.abs(lat) > np.abs(lon)
        lat2 = np.where(swp, lon, lat); lon2 = np.where(swp, lat, lon)
        d2 = ((cz[:, 1][None, :].astype(float) - lat2[:, None]) ** 2
              + (cz[:, 2][None, :].astype(float) - lon2[:, None]) ** 2)
        near = np.nanargmin(np.where(np.isnan(d2), np.inf, d2), axis=1)
        rec = np.where(np.isnan(lat2), o.loc[mask, "delivery_zone_label"].to_numpy(), cz[:, 0][near])
        o.loc[mask, "dropoff_zone_key_current"] = pd.Series(rec, index=o.index[mask]).map(zk)
    o["dropoff_zone_key_current"] = o["dropoff_zone_key_current"].fillna(o["dropoff_zone_key_asbooked"]).astype(int)

    # assignment latency from dispatch
    disp = stg["dispatch"]
    lat_s = (disp[disp["event"].isin(["assigned", "no_courier_found"])]
             .sort_values("event_ts").drop_duplicates("order_id", keep="first")
             .set_index("order_id")["latency_s"])
    o["assignment_latency_s"] = o["order_id"].map(lat_s)
    o["assignment_latency_s"] = o["assignment_latency_s"].fillna(
        o["assignment_latency_s"].median())

    # customer / restaurant keys
    o["customer_key"] = o["customer_id"].map(dict(zip(dim_customer["customer_id"], dim_customer["customer_key"]))).fillna(-2).astype(int)
    o["restaurant_key"] = o["restaurant_id"].map(dict(zip(dim_restaurant["restaurant_id"], dim_restaurant["restaurant_key"]))).fillna(-2).astype(int)

    # experiment flags from dim_incentive_campaign (built below); placeholder now
    camp = stg["campaigns"].copy()
    camp["zone_key"] = camp["zone_id"].map(zk)
    treated_by_zd = camp.loc[camp["arm"] == "treatment", ["zone_key", "date_key"]]
    treated_set = set(map(tuple, treated_by_zd.to_numpy()))
    adj_map = (read_parquet(CUR / "dim_zone_adjacency.parquet")
               .groupby("zone_key")["neighbour_zone_key"].apply(list).to_dict())
    zd = list(zip(o["dropoff_zone_key_current"].to_numpy(), o["placed_date_key"].to_numpy()))
    o["on_treated_zone_day"] = [t in treated_set for t in zd]
    o["is_adjacent_to_treated_zone_day"] = [
        any((nb, dk) in treated_set for nb in adj_map.get(zkk, [])) and (zkk, dk) not in treated_set
        for zkk, dk in zd]
    o["experiment_phase"] = o["placed_date_key"].map(dict(zip(dim_date["date_key"], dim_date["experiment_phase"])))

    OUT = ["order_key", "order_id", "customer_key", "restaurant_key", "pickup_zone_key",
           "dropoff_zone_key_asbooked", "dropoff_zone_key_current", "placed_date_key", "placed_ts",
           "placed_hour", "time_block_key", "is_peak_block", "basket_value_brl", "delivery_fee_brl",
           "outcome", "eta_min", "assignment_latency_s", "dist_km", "experiment_phase",
           "on_treated_zone_day", "is_adjacent_to_treated_zone_day"]
    o["courier_key"] = np.where(o["outcome"] == "delivered", 0, -1)   # filled per delivery below
    fact_order = o.rename(columns={"dist_km": "trip_distance_km"})[
        [c2 if c2 != "dist_km" else "trip_distance_km" for c2 in OUT] + ["courier_key"]]
    drift = int((o["dropoff_zone_key_asbooked"] != o["dropoff_zone_key_current"]).sum())

    # ---------------- fact_courier_shift_block --------------------------------
    banner("curated — fact_courier_shift_block + fact_delivery")
    blk = stg["blocks"].rename(columns={"planned_min": "logged_in_min"}).copy()
    dwell = stg["dwell"].rename(columns={"present_min": "present_min"})
    blk = blk.merge(dwell, on=["courier_id", "zone_id", "date_key", "hour"], how="left")
    blk["present_min"] = blk["present_min"].fillna(blk["logged_in_min"]).clip(upper=blk["logged_in_min"])
    # deliveries per courier-date-zone from payouts, split across hour-blocks by present_min
    cp = stg["payouts"].groupby(["courier_id", "date_key", "zone_id"], as_index=False).agg(
        cp_deliv=("deliveries", "sum"), cp_amt=("amount_brl", "sum"))
    tot_present = blk.groupby(["courier_id", "date_key", "zone_id"])["present_min"].transform("sum")
    blk = blk.merge(cp, on=["courier_id", "date_key", "zone_id"], how="left")
    share = np.where(tot_present > 0, blk["present_min"] / tot_present, 0)
    blk["deliveries"] = (blk["cp_deliv"].fillna(0) * share).round().astype(int)
    blk["earnings_brl"] = (blk["cp_amt"].fillna(0) * share).round(2)
    macro = z.set_index("zone_id")["macro_area"].to_dict()
    blk["svc_min"] = blk["zone_id"].map(lambda zz: SVC_MIN[macro.get(zz, "inner_ring")])
    blk["active_min"] = np.minimum(blk["deliveries"] * blk["svc_min"], blk["present_min"]).round().astype(int)
    blk["cooldown_min"] = (blk["logged_in_min"] * C.COOLDOWN_SHARE).round().astype(int)
    blk["idle_min"] = (blk["present_min"] - blk["active_min"] - blk["cooldown_min"]).clip(lower=0).astype(int)
    bon = stg["bonus"].groupby(["courier_id", "zone_id", "date_key", "hour"], as_index=False)["bonus_brl"].sum()
    blk = blk.merge(bon, on=["courier_id", "zone_id", "date_key", "hour"], how="left")
    blk["bonus_brl"] = blk["bonus_brl"].fillna(0.0)
    blk["base_payout_brl"] = (blk["earnings_brl"] - blk["bonus_brl"]).clip(lower=0).round(2)
    blk["tip_brl"] = 0.0
    ckey = dict(zip(dim_courier["courier_id"], dim_courier["courier_key"]))
    blk["courier_key"] = blk["courier_id"].map(ckey).fillna(-2).astype(int)
    blk["zone_key"] = blk["zone_id"].map(zk)
    blk["time_block_key"] = blk["hour"]
    blk["is_peak_block"] = blk["hour"].isin(PEAK_HOURS)
    fact_block = blk[["courier_key", "zone_key", "date_key", "time_block_key", "logged_in_min",
                      "active_min", "idle_min", "cooldown_min", "deliveries", "base_payout_brl",
                      "tip_brl", "bonus_brl", "earnings_brl", "is_peak_block"]].copy()
    write_parquet(fact_block, CUR / "fact_courier_shift_block.parquet")

    # fact_delivery: one row per delivered order; assign a courier from same zone-hour blocks
    deliv = o[o["outcome"] == "delivered"].copy()
    deliv["delivery_key"] = np.arange(1, len(deliv) + 1)
    deliv["zone_key"] = deliv["dropoff_zone_key_current"]
    # courier pool per (zone_key, date_key, hour) weighted by deliveries
    _bl = fact_block[fact_block["deliveries"] > 0]
    bl_idx = {k: (v["courier_key"].to_numpy(), (v["deliveries"] / v["deliveries"].sum()).to_numpy())
              for k, v in _bl.groupby(["zone_key", "date_key", "time_block_key"])}
    # fallback pool: any courier present in the zone that day (cheap dict, no per-hour apply)
    bl_zd = _bl.groupby(["zone_key", "date_key"])["courier_key"].apply(lambda s: s.unique()).to_dict()

    def _assign(x):
        pk = bl_idx.get(x.name)
        if pk is not None and len(pk[0]):
            return pd.Series(g.choice(pk[0], size=len(x), p=pk[1]), index=x.index)
        zc = bl_zd.get((x.name[0], x.name[1]))
        if zc is not None and len(zc):
            return pd.Series(g.choice(zc, size=len(x)), index=x.index)
        return pd.Series(-1, index=x.index)

    deliv["courier_key"] = (deliv.groupby(["zone_key", "placed_date_key", "placed_hour"],
                                          group_keys=False)[["order_key"]].apply(_assign).astype(int))
    deliv["trip_min"] = deliv["eta_min"] * 0.55
    deliv["courier_base_payout_brl"] = (C.COURIER_BASE_PAYOUT_PER_DELIVERY_BRL
                                        + C.COURIER_PAYOUT_PER_KM_BRL * deliv["dist_km"]).round(2)
    deliv["tip_brl"] = np.where(g.random(len(deliv)) < C.TIP_RATE,
                                np.clip(g.normal(C.TIP_MEAN_BRL, 2, len(deliv)), 0, None), 0.0).round(2)
    deliv["incentive_bonus_brl"] = np.where(deliv["on_treated_zone_day"] & deliv["is_peak_block"],
                                            C.INCENTIVE_BONUS_BRL_PER_DELIVERY, 0.0)
    deliv["total_payout_brl"] = (deliv["courier_base_payout_brl"] + deliv["tip_brl"] + deliv["incentive_bonus_brl"]).round(2)
    deliv["date_key"] = deliv["placed_date_key"]
    deliv["time_block_key"] = deliv["placed_hour"]
    fact_delivery = deliv[["delivery_key", "order_key", "courier_key", "zone_key", "date_key",
                           "time_block_key", "placed_ts", "trip_min",
                           "trip_distance_km" if "trip_distance_km" in deliv else "dist_km",
                           "courier_base_payout_brl", "tip_brl", "incentive_bonus_brl", "total_payout_brl",
                           "is_peak_block", "experiment_phase", "on_treated_zone_day"]].rename(
        columns={"dist_km": "trip_distance_km", "placed_ts": "dropoff_ts"})
    write_parquet(fact_delivery, CUR / "fact_delivery.parquet")

    # write fact_order with courier_key filled from fact_delivery
    okey_ck = dict(zip(deliv["order_key"], deliv["courier_key"]))
    fact_order["courier_key"] = fact_order["order_key"].map(okey_ck).fillna(fact_order["courier_key"]).astype(int)
    write_parquet(fact_order, CUR / "fact_order.parquet")

    # ---------------- fact_zone_hour (liquidity spine) ---------------------
    banner("curated — fact_zone_hour")
    oz = o.rename(columns={"dropoff_zone_key_current": "zone_key"})
    grp = oz.groupby(["zone_key", "placed_date_key", "placed_hour"], as_index=False)
    agg = grp.agg(orders_placed=("order_key", "size"),
                  orders_delivered=("outcome", lambda s: (s == "delivered").sum()),
                  cancelled_customer=("outcome", lambda s: (s == "cancelled_customer").sum()),
                  cancelled_courier=("outcome", lambda s: (s == "cancelled_courier").sum()),
                  cancelled_no_courier=("outcome", lambda s: (s == "cancelled_no_courier").sum()),
                  cancelled_restaurant=("outcome", lambda s: (s == "cancelled_restaurant").sum()),
                  assignment_latency_p90_s=("assignment_latency_s", lambda s: s.quantile(0.9)))
    eta = (oz[oz["outcome"] == "delivered"].groupby(["zone_key", "placed_date_key", "placed_hour"])["eta_min"]
           .agg(eta_p50_min=lambda s: s.quantile(0.5), eta_p90_min=lambda s: s.quantile(0.9)).reset_index())
    agg = agg.merge(eta, on=["zone_key", "placed_date_key", "placed_hour"], how="left")
    agg = agg.rename(columns={"placed_date_key": "date_key", "placed_hour": "hour"})
    agg["time_block_key"] = agg["hour"]
    agg["is_peak_block"] = agg["hour"].isin(PEAK_HOURS)
    agg["fulfillment_rate"] = agg["orders_delivered"] / agg["orders_placed"]
    agg["unmet_demand"] = agg["orders_placed"] - agg["orders_delivered"]
    zmacro = z.set_index("zone_key")["macro_area"].to_dict() if "zone_key" in z else None
    z2 = z.copy(); z2["zone_key"] = z2["zone_id"].map(zk)
    svc_by_zk = z2.set_index("zone_key")["macro_area"].map(lambda m: SVC_MIN[m]).to_dict()
    agg["demanded_delivery_hours"] = agg["orders_placed"] * agg["zone_key"].map(svc_by_zk) / 60.0

    fbx = fact_block.assign(_avail=(fact_block["active_min"] + fact_block["idle_min"]) / 60.0,
                            _idle=fact_block["idle_min"] / 60.0)
    sup = (fbx.groupby(["zone_key", "date_key", "time_block_key"], as_index=False)
           .agg(available_courier_hours=("_avail", "sum"),
                idle_courier_hours=("_idle", "sum"),
                active_couriers=("courier_key", "nunique")))
    zh = agg.merge(sup, on=["zone_key", "date_key", "time_block_key"], how="left")
    for cc in ["available_courier_hours", "idle_courier_hours", "active_couriers"]:
        zh[cc] = zh[cc].fillna(0)
    zh["liquidity_ratio"] = np.where(zh["demanded_delivery_hours"] > 0,
                                     zh["available_courier_hours"] / zh["demanded_delivery_hours"], np.nan)
    zh["idle_courier_ratio"] = (zh["idle_courier_hours"] / zh["available_courier_hours"].replace(0, np.nan)).clip(0, 1)
    # context flags + experiment arm
    truth = read_parquet(C.RAW_DIR / "_sim_truth_zone_hour.parquet")
    truth["zone_key"] = (truth["zone_idx"] + 1)
    zh = zh.merge(truth[["zone_key", "date_key", "hour", "is_rain", "has_event"]],
                  on=["zone_key", "date_key", "hour"], how="left")
    zh["is_rainy"] = zh["is_rain"].fillna(0).astype(bool)
    zh["has_local_event"] = zh["has_event"].fillna(0).astype(bool)
    camp["campaign_zone_key"] = camp["zone_key"]
    arm_by_zd = dict(zip(zip(camp["zone_key"], camp["date_key"]), camp["arm"]))
    zh["experiment_arm"] = [arm_by_zd.get((zkk, dk), "") if h in PEAK_HOURS else ""
                            for zkk, dk, h in zip(zh["zone_key"], zh["date_key"], zh["hour"])]
    zh["on_treated_zone_day"] = zh["experiment_arm"] == "treatment"
    zh["is_adjacent_to_treated_zone_day"] = [
        (h in PEAK_HOURS) and (arm_by_zd.get((zkk, dk), "") == "control")
        and any(arm_by_zd.get((nb, dk), "") == "treatment" for nb in adj_map.get(zkk, []))
        for zkk, dk, h in zip(zh["zone_key"], zh["date_key"], zh["hour"])]
    zh = zh.drop(columns=["is_rain", "has_event"])
    write_parquet(zh, CUR / "fact_zone_hour.parquet")

    # ---------------- stress tier from baseline liquidity -----------------
    base = zh[zh["date_key"] <= date_key(C.BASELINE_END)]
    mL = base.groupby("zone_key")["liquidity_ratio"].mean()
    tier = mL.apply(lambda v: "short" if v < 0.93 else ("long" if v > 1.13 else "balanced"))
    z2["baseline_supply_stress_tier"] = z2["zone_key"].map(tier).fillna("balanced")
    z2["avg_trip_km_baseline"] = z2["macro_area"].map(lambda m: {"centre": 2.4, "inner_ring": 3.6, "outer_ring": 5.1}[m])
    dim_zone = z2[["zone_key", "zone_id", "zone_name", "macro_area", "area_km2", "centroid_lat",
                   "centroid_lon", "n_neighbours", "baseline_supply_stress_tier", "avg_trip_km_baseline",
                   "is_boundary_redrawn"]]
    write_parquet(dim_zone, CUR / "dim_zone.parquet")

    # ---------------- dim_incentive_campaign ------------------------------
    dc = dim_date.set_index("date_key")
    camp["stratum"] = camp["zone_id"].map(dict(zip(z2["zone_id"], z2["zone_id"]))) + "|" + \
        camp["zone_id"].map(dict(zip(z2["zone_id"], z2["baseline_supply_stress_tier"])))
    camp["day_of_week"] = camp["date_key"].map(dc["day_of_week"])
    camp["campaign_key"] = np.arange(1, len(camp) + 1)
    dim_camp = camp.rename(columns={"peak_start_hour": "peak_block_start_hour",
                                    "peak_end_hour": "peak_block_end_hour"})[
        ["campaign_key", "zone_key", "date_key", "arm", "bonus_brl_per_delivery", "push_radius_m",
         "peak_block_start_hour", "peak_block_end_hour", "stratum", "day_of_week"]]
    write_parquet(dim_camp, CUR / "dim_incentive_campaign.parquet")

    # ---------------- fact_incentive_assignment --------------------------
    banner("curated — experiment tables")
    peak_zh = zh[zh["hour"].isin(PEAK_HOURS)].copy()
    peak_base = peak_zh[peak_zh["date_key"] <= date_key(C.BASELINE_END)]
    pre = peak_base.groupby("zone_key").agg(
        pre_fulfillment_rate=("fulfillment_rate", "mean"),
        pre_eta_p90_min=("eta_p90_min", "mean"),
        pre_orders_placed_mean=("orders_placed", "mean"),
        pre_liquidity_ratio=("liquidity_ratio", "mean"),
        pre_idle_courier_ratio=("idle_courier_ratio", "mean")).reset_index()
    fia = dim_camp.merge(pre, on="zone_key", how="left")
    tre = dim_camp[dim_camp["arm"] == "treatment"][["zone_key", "date_key"]]
    tre_set = set(map(tuple, tre.to_numpy()))
    fia["n_adjacent_zones_treated"] = [sum((nb, dk) in tre_set for nb in adj_map.get(zkk, []))
                                       for zkk, dk in zip(fia["zone_key"], fia["date_key"])]
    fia["is_adjacent_to_treated"] = (fia["arm"] == "control") & (fia["n_adjacent_zones_treated"] > 0)
    write_parquet(fia, CUR / "fact_incentive_assignment.parquet")

    # ---------------- fact_experiment_zone_day ---------------------------
    win = peak_zh[(peak_zh["date_key"] >= date_key(C.EXPERIMENT_START))
                  & (peak_zh["date_key"] <= date_key(C.EXPERIMENT_END))].copy()
    ezd = win.groupby(["zone_key", "date_key"], as_index=False).agg(
        orders_placed=("orders_placed", "sum"), orders_delivered=("orders_delivered", "sum"),
        eta_p50_min=("eta_p50_min", "mean"), eta_p90_min=("eta_p90_min", "mean"),
        cancelled_no_courier=("cancelled_no_courier", "sum"),
        available_courier_hours=("available_courier_hours", "sum"),
        active_couriers=("active_couriers", "max"))
    ezd["fulfillment_rate"] = ezd["orders_delivered"] / ezd["orders_placed"]
    ezd["cancel_rate"] = 1 - ezd["fulfillment_rate"]
    ezd["cancel_no_courier_rate"] = ezd["cancelled_no_courier"] / ezd["orders_placed"]
    ezd = ezd.merge(dim_camp[["zone_key", "date_key", "arm", "stratum"]], on=["zone_key", "date_key"], how="left")
    # incentive spend + earnings per active hour from fact_block peak window
    fb = fact_block.merge(dim_date[["date_key", "experiment_phase"]], on="date_key", how="left")
    fbw = fb[(fb["is_peak_block"]) & (fb["date_key"] >= date_key(C.EXPERIMENT_START))
             & (fb["date_key"] <= date_key(C.EXPERIMENT_END))]
    spend = fbw.groupby("zone_key").apply(lambda x: x["bonus_brl"].sum(), include_groups=False)
    earn = fbw.groupby(["zone_key", "date_key"]).apply(
        lambda x: x["earnings_brl"].sum() / max(x["active_min"].sum() / 60.0, 1e-6), include_groups=False)
    ezd["courier_earnings_per_active_hour_brl"] = [earn.get((zk_, dk_), np.nan)
                                                  for zk_, dk_ in zip(ezd["zone_key"], ezd["date_key"])]
    bonus_zd = fbw.groupby(["zone_key", "date_key"])["bonus_brl"].sum()
    ezd["incentive_spend_brl"] = [bonus_zd.get((zk_, dk_), 0.0) for zk_, dk_ in zip(ezd["zone_key"], ezd["date_key"])]
    ezd["deliveries"] = ezd["orders_delivered"]
    ezd["incentive_cost_per_delivered_order_brl"] = np.where(ezd["orders_delivered"] > 0,
                                                            ezd["incentive_spend_brl"] / ezd["orders_delivered"], np.nan)
    ezd["n_adjacent_zones_treated"] = [sum((nb, dk) in tre_set for nb in adj_map.get(zkk, []))
                                       for zkk, dk in zip(ezd["zone_key"], ezd["date_key"])]
    ezd["is_adjacent_to_treated"] = (ezd["arm"] == "control") & (ezd["n_adjacent_zones_treated"] > 0)
    write_parquet(ezd, CUR / "fact_experiment_zone_day.parquet")

    # ---------------- fact_experiment_zone_block_week -------------------
    win2 = win.merge(dim_date[["date_key", "experiment_week"]], on="date_key", how="left")
    ezbw = win2.groupby(["zone_key", "experiment_week", "time_block_key"], as_index=False).agg(
        orders_placed=("orders_placed", "sum"), orders_delivered=("orders_delivered", "sum"),
        eta_p90_min=("eta_p90_min", "mean"), available_courier_hours=("available_courier_hours", "sum"))
    ezbw["fulfillment_rate"] = ezbw["orders_delivered"] / ezbw["orders_placed"]
    ezbw = ezbw.merge(dim_camp[["zone_key", "date_key", "arm"]].drop_duplicates("zone_key"), on="zone_key", how="left")
    write_parquet(ezbw, CUR / "fact_experiment_zone_block_week.parquet")

    write_dq_fragment("curated", {
        "fact_order_rows": len(fact_order), "fact_delivery_rows": len(fact_delivery),
        "fact_zone_hour_rows": len(zh), "fact_courier_shift_block_rows": len(fact_block),
        "fact_experiment_zone_day_rows": len(ezd),
        "asbooked_vs_current_zone_drift_rows": drift,
        "orphan_courier_deliveries": int((deliv["courier_key"] == -1).sum()),
        "stress_tiers": tier.value_counts().to_dict()})
    return dim_zone


# --------------------------------------------------------------------------- #
def main():
    banner("SwiftBite — 03_build_curated")
    CUR.mkdir(parents=True, exist_ok=True)
    stg = {
        "georef_zones": read_parquet(STG / "stg_georef_zones.parquet"),
        "georef_adj": read_parquet(STG / "stg_georef_zone_adjacency.parquet"),
        "couriers": read_parquet(STG / "stg_riderapp_couriers.parquet"),
        "customers": read_parquet(STG / "stg_ordercore_customers.parquet"),
        "restaurants": read_parquet(STG / "stg_ordercore_restaurants.parquet"),
        "orders": read_parquet(STG / "stg_ordercore_orders.parquet"),
        "addresses": read_parquet(STG / "stg_ordercore_addresses.parquet"),
        "dispatch": read_parquet(STG / "stg_dispatch_assignment_events.parquet"),
        "payouts": read_parquet(STG / "stg_payhub_courier_payouts.parquet"),
        "bonus": read_parquet(STG / "stg_payhub_bonus_payouts.parquet"),
        "blocks": read_parquet(STG / "stg_riderapp_shift_zone_blocks.parquet"),
        "dwell": read_parquet(STG / "stg_trace_zone_dwell.parquet"),
        "campaigns": read_parquet(STG / "stg_boost_incentive_campaigns.parquet"),
    }
    dim_date, dim_tb, z, zk, dim_courier, dim_customer, dim_restaurant = build_dims(stg)
    build_facts(stg, dim_date, z, zk, dim_courier, dim_customer, dim_restaurant)
    banner("03_build_curated done")


if __name__ == "__main__":
    main()
