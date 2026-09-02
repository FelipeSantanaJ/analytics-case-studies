"""
AeroVanti SkyPoints — 03_build_curated.py

Reads data/staging/stg_*.parquet, writes the conformed Kimball star + the
pre-built experiment tables to data/curated/ (Parquet + CSV mirror), plus
curated DQ fragments.

Rules of the layer:
  - tier status is folded forward from the tier-change ledger, never the snapshot
  - all money is BRL
  - facts are never dropped for a missing dimension -> sentinel keys (-1/-2)
  - lapse is null (not False) until the 12-month rule is evaluable
"""

from __future__ import annotations

from collections import Counter

import numpy as np
import pandas as pd

import config as C
from utils import banner, month_key, rng, write_csv, write_dq_fragment, write_parquet

STG = C.STAGING_DIR
CUR = C.CURATED_DIR
TIERS = ["Blue", "Silver", "Gold", "Platinum"]
TIER_KEY = {t: i + 1 for i, t in enumerate(TIERS)}
TIER_KEY[None] = 1
MULT = {1: 1.0, 2: 1.25, 3: 1.5, 4: 2.0}


def L(name):
    return pd.read_parquet(STG / f"{name}.parquet")


def dkey(s: pd.Series) -> pd.Series:
    d = pd.to_datetime(s)
    return (d.dt.year * 10000 + d.dt.month * 100 + d.dt.day).astype("Int64")


def mkey(s: pd.Series) -> pd.Series:
    d = pd.to_datetime(s)
    return (d.dt.year * 100 + d.dt.month).astype("Int64")


def out(df: pd.DataFrame, name: str, ctr: Counter | None = None):
    CUR.mkdir(parents=True, exist_ok=True)
    write_parquet(df, CUR / f"{name}.parquet")
    if C.WRITE_CSV_MIRROR:
        if len(df) > C.CSV_MIRROR_MAX_ROWS:
            print(f"    [skip csv mirror] {name}: {len(df):,} rows > CSV_MIRROR_MAX_ROWS")
        elif len(df) > 400_000:
            write_csv(df, CUR / f"{name}.csv.gz", compression="gzip")
        else:
            write_csv(df, CUR / f"{name}.csv")
    write_dq_fragment(f"curated__{name}", dict(ctr or {}, rows=len(df)))
    print(f"  {name:34s} {len(df):>10,} rows")


# ======================================================================== #
def build_dim_date():
    d = pd.date_range(C.DIM_DATE_START, C.DIM_DATE_END, freq="D")
    df = pd.DataFrame({"date": d})
    df["date_key"] = df["date"].dt.year * 10000 + df["date"].dt.month * 100 + df["date"].dt.day
    df["year"] = df["date"].dt.year
    df["quarter"] = df["date"].dt.quarter
    df["month"] = df["date"].dt.month
    df["month_key"] = df["year"] * 100 + df["month"]
    df["month_name"] = df["date"].dt.strftime("%b %Y")
    df["month_sort"] = df["year"] * 12 + df["month"]
    df["iso_week"] = df["date"].dt.isocalendar().week.astype(int)
    df["day_of_week"] = df["date"].dt.dayofweek
    df["is_month_end"] = df["date"].dt.is_month_end
    cal = pd.read_csv(C.VOCAB_DIR / "br_calendar.csv", parse_dates=["date"])
    df = df.merge(cal, on="date", how="left")
    df["is_holiday_br"] = df["is_holiday"].fillna(0).astype(int).astype(bool)
    df["is_school_break"] = df["is_school_break"].fillna(0).astype(int).astype(bool)
    df.drop(columns=["is_holiday", "holiday_name"], inplace=True, errors="ignore")
    m = df["month"]
    df["season_tag"] = np.select(
        [m.isin([12, 1, 2]), m.isin([3, 4, 5]), m.isin([6, 7, 8])],
        ["Summer peak", "Autumn shoulder", "Winter peak"], default="Spring shoulder")
    es, ee = pd.Timestamp(C.EXPERIMENT_START), pd.Timestamp(C.EXPERIMENT_END)
    win_s, win_e = pd.Timestamp(C.WINDOW_START), pd.Timestamp(C.WINDOW_END)
    df["experiment_phase"] = np.select(
        [df["date"] < es, (df["date"] >= es) & (df["date"] <= ee), df["date"] > ee],
        ["pre", "test", "post"], default="pre")
    df.loc[(df["date"] < win_s) | (df["date"] > win_e), "experiment_phase"] = "out_of_window"
    wk = ((df["date"] - es).dt.days // 7 + 1)
    df["experiment_week"] = wk.where((df["date"] >= es) & (df["date"] <= ee)).astype("Int64")
    out(df, "dim_date")
    return df


def build_small_dims():
    dt = pd.DataFrame({
        "tier_key": [1, 2, 3, 4],
        "tier_name": TIERS,
        "tier_rank": [1, 2, 3, 4],
        "earn_multiplier": [1.0, 1.25, 1.5, 2.0],
        "tp_threshold": [C.TIER_TP_THRESHOLD[t] for t in TIERS],
        "segment_threshold": [C.TIER_SEGMENT_THRESHOLD[t] for t in TIERS],
        "is_elite": [False, True, True, True],
    })
    out(dt, "dim_tier")

    srcs = ["flight", "cobrand_card", "partner_hotel", "partner_car", "partner_retail",
            "promo", "service_recovery", "legacy_migration"]
    grp = {"flight": "flight", "cobrand_card": "card", "partner_hotel": "partner",
           "partner_car": "partner", "partner_retail": "partner", "promo": "other",
           "service_recovery": "other", "legacy_migration": "other"}
    de = pd.DataFrame({
        "earn_source_key": list(range(1, len(srcs) + 1)),
        "source_name": srcs,
        "source_group": [grp[s] for s in srcs],
        "earns_tier_points": [s == "flight" for s in srcs],
    })
    de = pd.concat([pd.DataFrame([{"earn_source_key": -1, "source_name": "unknown",
                                   "source_group": "other", "earns_tier_points": False}]), de],
                   ignore_index=True)
    out(de, "dim_earn_source")

    rc = L("stg_skycore_reward_catalog").copy()
    rc.insert(0, "reward_type_key", range(1, len(rc) + 1))
    rc["is_low_cost_catalog"] = rc["reward_category"].isin(
        ["seat", "bag", "lounge", "gift_card", "voucher"])
    rc["available_from_date_key"] = dkey(rc["available_from"])
    rc = pd.concat([pd.DataFrame([{"reward_type_key": -1, "reward_name": "unknown",
                                   "reward_category": "unknown", "points_price": pd.NA,
                                   "value_per_point_brl": np.nan,
                                   "is_low_cost_catalog": False,
                                   "available_from_date_key": pd.NA}]), rc], ignore_index=True)
    out(rc, "dim_reward_type")

    out(pd.DataFrame({"arm_key": ["control", "treatment", "not_enrolled"]}), "dim_experiment_arm")
    out(pd.DataFrame({"stratum": TIERS}), "dim_experiment_stratum")
    return de, rc


# ======================================================================== #
def build_tier_change_and_status(members_ids: pd.Series):
    ev = L("stg_skycore_tier_change_events").copy()
    ev = ev.merge(members_ids, on="member_id", how="left")
    ev["member_key"] = ev["member_key"].fillna(-2).astype(int)
    ev["change_date_key"] = dkey(ev["change_date"])
    ev["change_month_key"] = mkey(ev["change_date"])
    ev["from_tier_key"] = ev["from_tier"].map(TIER_KEY).astype("Int64")
    ev["to_tier_key"] = ev["to_tier"].map(TIER_KEY).astype("Int64")
    fact = ev[["member_key", "member_id", "change_date_key", "change_month_key",
               "from_tier", "to_tier", "from_tier_key", "to_tier_key",
               "direction", "trigger"]].copy()
    out(fact, "fact_tier_change")
    return ev


def fold_forward_tier(ev: pd.DataFrame, mm_grid: pd.DataFrame) -> pd.Series:
    """Ledger-derived tier per (member_id, month_key). Blue at enrolment, then apply
    each tier-change event from its month onward."""
    chg = ev.dropna(subset=["change_month_key"])[["member_id", "change_month_key", "to_tier"]].copy()
    chg = chg.rename(columns={"change_month_key": "month_key", "to_tier": "chg_tier"})
    chg["month_key"] = chg["month_key"].astype("int64")
    chg = chg.sort_values(["month_key", "member_id"])
    g = mm_grid[["member_id", "month_key"]].copy()
    g["month_key"] = g["month_key"].astype("int64")
    g = g.sort_values(["month_key", "member_id"]).reset_index(drop=True)
    merged = pd.merge_asof(g, chg, on="month_key", by="member_id", direction="backward")
    merged["tier_name"] = merged["chg_tier"].fillna("Blue")
    return merged[["member_id", "month_key", "tier_name"]]


# ======================================================================== #
def build_members_and_facts():
    banner("curated: dims + facts")
    dim_date = build_dim_date()
    de, drt = build_small_dims()

    # ---------- dim_member ------------------------------------------------
    snap = L("stg_skycore_members")
    latest = (snap.sort_values("snapshot_month")
              .drop_duplicates("member_id", keep="last")
              .set_index("member_id"))
    members = pd.DataFrame(index=latest.index).reset_index()
    members = members.merge(
        snap.dropna(subset=["member_since"]).sort_values("snapshot_month")
        .drop_duplicates("member_id")[["member_id", "member_since"]],
        on="member_id", how="left")
    members["member_since"] = members["member_since"].fillna(
        members["member_id"].map(latest["member_since"]))
    members = members.sort_values("member_id").reset_index(drop=True)
    members.insert(0, "member_key", np.arange(1, len(members) + 1))
    members["enrollment_date"] = pd.to_datetime(members["member_since"])
    members["enrollment_date_key"] = dkey(members["enrollment_date"])
    members["enrollment_cohort_month"] = members["enrollment_date"].dt.to_period("M").astype(str)
    members["enrollment_channel"] = members["member_id"].map(latest["enrollment_channel"])
    members["home_city"] = members["member_id"].map(latest["home_city"])
    members["home_region"] = members["member_id"].map(latest["home_region"])
    members["is_steady_state_cohort"] = members["enrollment_date"] <= pd.Timestamp(
        C.STEADY_STATE_ENROLL_CUTOFF)
    members["is_test_account"] = False

    card = L("stg_bancoav_card_accounts")
    card_members = set(card["member_id"].dropna())
    members["has_cobrand_card"] = members["member_id"].isin(card_members)

    crm = L("stg_aurora_crm_contacts")
    members = members.merge(
        crm[["member_id", "lifecycle_stage", "birth_date", "birth_year_valid"]],
        on="member_id", how="left")
    members["crm_present"] = members["lifecycle_stage"].notna()
    members["crm_lifecycle_stage"] = members["lifecycle_stage"].fillna("unknown")
    by = pd.to_datetime(members["birth_date"]).dt.year
    age = 2026 - by
    members["age_band"] = pd.cut(age, [0, 25, 35, 45, 55, 200],
                                 labels=["<25", "25-34", "35-44", "45-54", "55+"]).astype("object")
    members.drop(columns=["lifecycle_stage", "birth_date"], inplace=True)

    mid_map = members[["member_id", "member_key"]]

    # ---------- fact_tier_change + folded status -----------------------
    ev = build_tier_change_and_status(mid_map)

    # ---------- month grid per member --------------------------------
    win_months = pd.period_range(C.WINDOW_START, C.WINDOW_END, freq="M")
    win_mkeys = np.array([p.year * 100 + p.month for p in win_months])
    enr_mkey = members["enrollment_date"].dt.to_period("M").astype("int64")  # not used directly
    rows = []
    enr = members["enrollment_date"].dt.to_period("M")
    for mk, p in zip(win_mkeys, win_months):
        active_cohort = members[enr <= p]
        rows.append(pd.DataFrame({"member_id": active_cohort["member_id"].to_numpy(),
                                  "member_key": active_cohort["member_key"].to_numpy(),
                                  "month_key": mk}))
    mm = pd.concat(rows, ignore_index=True)
    mm["ym"] = mm["month_key"].astype(str).str.slice(0, 4) + "-" + mm["month_key"].astype(str).str.slice(4, 6)

    # ---------- point transactions ----------------------------------
    tx = L("stg_skycore_point_transactions").copy()
    tx = tx.merge(mid_map, on="member_id", how="left")
    tx["member_key"] = tx["member_key"].fillna(-2).astype(int)
    tx["txn_date_key"] = dkey(tx["txn_date"])
    tx["month_key"] = mkey(tx["txn_date"])
    src_map = dict(zip(de["source_name"], de["earn_source_key"]))
    tx["earn_source_key"] = tx["earn_source"].map(src_map).fillna(-1).astype(int)
    rname_map = dict(zip(drt["reward_name"], drt["reward_type_key"]))
    tx["reward_type_key"] = tx["reward_name"].map(rname_map).fillna(-1).astype(int)
    tx.loc[tx["txn_type"].ne("redeem"), "reward_type_key"] = pd.NA
    tx.loc[tx["txn_type"].ne("earn"), "earn_source_key"] = pd.NA
    pv = tx["value_brl"].copy()
    need = pv.isna()
    pv[need] = (tx.loc[need, "points"].abs().astype(float) * C.POINT_UNIT_COST_BRL).round(2)
    tx["points_value_brl"] = pv
    tx["earn_month_key"] = tx["month_key"].where(tx["txn_type"].eq("earn"))
    fpt = tx[["member_key", "member_id", "txn_date_key", "month_key", "txn_type",
              "earn_source_key", "reward_type_key", "points", "points_value_brl",
              "earn_month_key"]].copy()
    fpt["txn_id"] = tx["txn_id"].to_numpy()
    out(fpt, "fact_point_transaction")

    # ---------- segments -> flight facts ----------------------------
    sg = L("stg_reserva_segments").copy()
    bk = L("stg_reserva_bookings")[["booking_id", "channel"]]
    sg = sg.merge(bk, on="booking_id", how="left")
    sg = sg.merge(mid_map.rename(columns={"member_id": "loyalty_member_id"}),
                  on="loyalty_member_id", how="left")
    sg["member_key"] = np.where(sg["loyalty_member_id"].isna(), -1,
                                sg["member_key"].fillna(-2)).astype(int)
    sg["flight_date_key"] = dkey(sg["flight_date"])
    sg["month_key"] = mkey(sg["flight_date"])
    # route dim
    routes = (sg[["origin", "dest"]].dropna().drop_duplicates().reset_index(drop=True))
    routes.insert(0, "route_key", np.arange(1, len(routes) + 1))
    rg = rng("route")
    routes["haul_band"] = rg.choice(["short", "medium"], len(routes), p=[0.62, 0.38])
    routes["region_pair"] = routes["origin"].str[:2] + "-" + routes["dest"].str[:2]
    routes = pd.concat([pd.DataFrame([{"route_key": -1, "origin": "?", "dest": "?",
                                       "haul_band": "unknown", "region_pair": "?"}]),
                        routes], ignore_index=True)
    out(routes, "dim_route")
    sg = sg.merge(routes[["route_key", "origin", "dest"]], on=["origin", "dest"], how="left")
    sg["route_key"] = sg["route_key"].fillna(-1).astype(int)

    # member tier that month (ledger-derived) for earn multiplier
    mm["month_key"] = mm["month_key"].astype("int64")
    status = fold_forward_tier(ev, mm)
    mm = mm.merge(status, on=["member_id", "month_key"], how="left")
    mm["tier_name"] = mm["tier_name"].fillna("Blue")
    mm["tier_key"] = mm["tier_name"].map(TIER_KEY).astype(int)

    lk = mm[["member_id", "month_key", "tier_key"]].rename(columns={"member_id": "loyalty_member_id"})
    sg["month_key"] = sg["month_key"].fillna(0).astype("int64")
    sg = sg.merge(lk, on=["loyalty_member_id", "month_key"], how="left")
    sg["tier_key"] = sg["tier_key"].fillna(1).astype(int)
    mult = sg["tier_key"].map(MULT).fillna(1.0)
    flex = sg["fare_family"].eq("FLEX")
    sg["skypoints_earned"] = np.where(
        sg["is_award"], 0,
        (sg["base_fare"].fillna(0) * C.SKYPOINTS_PER_BRL_BASE_FARE * mult
         * (1 + np.where(flex, C.FLEX_FARE_EARN_BONUS, 0))).round()).astype("int64")
    sg["tier_points_earned"] = np.where(
        sg["is_award"], 0,
        (sg["base_fare"].fillna(0) * C.TIER_POINTS_PER_BRL_BASE_FARE
         + C.TIER_POINTS_PER_SEGMENT).round()).astype("int64")
    fseg = sg[["member_key", "loyalty_member_id", "flight_date_key", "month_key", "route_key",
               "fare_family", "base_fare", "taxes", "channel", "is_award",
               "points_redeemed", "skypoints_earned", "tier_points_earned"]].rename(
        columns={"base_fare": "base_fare_brl", "taxes": "taxes_brl",
                 "channel": "booking_channel", "is_award": "is_award_redemption"})
    out(fseg, "fact_flight_segment")

    # ---------- card spend month ----------------------------------
    cs = L("stg_bancoav_card_spend").copy()
    cmap = card.dropna(subset=["member_id"])[["card_id", "member_id"]]
    cs = cs.merge(cmap, on="card_id", how="left").merge(mid_map, on="member_id", how="left")
    cs = cs.dropna(subset=["member_key", "competencia_month"])
    cs["member_key"] = cs["member_key"].astype(int)
    cs["month_key"] = cs["competencia_month"].str.replace("-", "").astype(int)
    fcs = cs.groupby(["member_key", "month_key"], as_index=False).agg(
        card_spend_brl=("valor_fatura", "sum"),
        skypoints_earned=("pontos_gerados", "sum"))
    fcs["is_card_active"] = fcs["card_spend_brl"] > 0
    out(fcs, "fact_card_spend_month")

    # ---------- fact_member_month -------------------------------
    pe = (fpt.assign(mk=fpt["month_key"])
          .pivot_table(index=["member_id", "mk"], columns="txn_type", values="points",
                       aggfunc="sum", fill_value=0).reset_index())
    for c in ("earn", "redeem", "expire", "adjust"):
        if c not in pe:
            pe[c] = 0
    pe = pe.rename(columns={"mk": "month_key", "earn": "points_earned_m",
                            "redeem": "points_redeemed_m_raw", "expire": "points_expired_m_raw"})
    pe["month_key"] = pe["month_key"].astype("int64")
    rc_cnt = (fpt[fpt["txn_type"].eq("redeem")].groupby(["member_id", "month_key"])
              .size().rename("redemptions_m").reset_index())
    rc_cnt["month_key"] = rc_cnt["month_key"].astype("int64")
    mm = mm.merge(pe[["member_id", "month_key", "points_earned_m",
                      "points_redeemed_m_raw", "points_expired_m_raw"]],
                  on=["member_id", "month_key"], how="left")
    mm = mm.merge(rc_cnt, on=["member_id", "month_key"], how="left")
    mm[["points_earned_m", "points_redeemed_m_raw", "points_expired_m_raw", "redemptions_m"]] = \
        mm[["points_earned_m", "points_redeemed_m_raw", "points_expired_m_raw", "redemptions_m"]].fillna(0)
    mm["points_redeemed_m"] = -mm["points_redeemed_m_raw"]
    mm["points_expired_m"] = -mm["points_expired_m_raw"]
    mm.drop(columns=["points_redeemed_m_raw", "points_expired_m_raw"], inplace=True)

    # flights + revenue
    fl = (fseg[fseg["member_key"] > 0].groupby(["loyalty_member_id", "month_key"])
          .agg(flights_m=("flight_date_key", "size"),
               flight_revenue_brl_m=("base_fare_brl", "sum")).reset_index()
          .rename(columns={"loyalty_member_id": "member_id"}))
    fl["month_key"] = fl["month_key"].astype("int64")
    mm = mm.merge(fl, on=["member_id", "month_key"], how="left")
    mm[["flights_m", "flight_revenue_brl_m"]] = mm[["flights_m", "flight_revenue_brl_m"]].fillna(0)

    # card spend on member-month
    cardmm = fcs.merge(mid_map, on="member_key", how="left")[["member_id", "month_key", "card_spend_brl"]]
    mm = mm.merge(cardmm.rename(columns={"card_spend_brl": "card_spend_brl_m"}),
                  on=["member_id", "month_key"], how="left")
    mm["card_spend_brl_m"] = mm["card_spend_brl_m"].fillna(0)

    # order, balance, activity, lapse
    mm["ym_sort"] = mm["month_key"]
    mm = mm.sort_values(["member_key", "ym_sort"]).reset_index(drop=True)
    grp = mm.groupby("member_key", sort=False)
    net = mm["points_earned_m"] - mm["points_redeemed_m"] - mm["points_expired_m"]
    mm["balance_pts_eom"] = net.groupby(mm["member_key"]).cumsum().round().astype("int64")
    mm["cum_redemptions"] = grp["redemptions_m"].cumsum()
    mm["has_redeemed_ever_eom"] = mm["cum_redemptions"] > 0
    mm["tenure_months"] = grp.cumcount()
    mm["is_new_enrollment"] = mm["tenure_months"] == 0

    activity = ((mm["points_earned_m"] > 0) | (mm["redemptions_m"] > 0) | (mm["flights_m"] > 0)).astype(int)
    mm["_act"] = activity
    # months since last activity (per member) — vectorized:
    # pos within the member's contiguous monthly panel; forward-fill the last
    # position where activity==1; the gap is the months-since count.
    mm["_pos"] = grp.cumcount()
    mm["_act_pos"] = mm["_pos"].where(activity == 1)
    last_act = mm.groupby("member_key")["_act_pos"].ffill()
    mm["months_since_last_activity"] = (mm["_pos"] - last_act).fillna(99).astype(np.int32)
    mm["is_active_eom"] = mm["months_since_last_activity"] < 12
    determinable = mm["tenure_months"] >= C.LAPSE_INACTIVITY_MONTHS
    is_lap = determinable & (mm["months_since_last_activity"] >= C.LAPSE_INACTIVITY_MONTHS)
    mm["is_lapsed_eom"] = np.where(determinable, is_lap, np.nan)  # NaN = undeterminable
    prev = grp["is_active_eom"].shift(1)
    prev_lap = grp.apply(lambda x: x["is_lapsed_eom"].shift(1)).reset_index(level=0, drop=True) \
        if False else mm.groupby("member_key")["is_lapsed_eom"].shift(1)
    mm["became_lapsed_this_month"] = (mm["is_lapsed_eom"] == 1) & (prev_lap != 1)
    mm["is_reactivation"] = (mm["_act"] == 1) & (prev_lap == 1)

    # experiment arm on member + member-month
    asg_raw = L("stg_flesk_ab_assignments")
    asg = asg_raw[asg_raw["eligible"]].merge(mid_map, on="member_id", how="left")
    arm_map = dict(zip(asg["member_id"], asg["arm"]))
    strat_map = dict(zip(asg["member_id"], asg["stratum"]))
    members["experiment_arm"] = members["member_id"].map(arm_map).fillna("not_enrolled")
    members["experiment_stratum"] = members["member_id"].map(strat_map).fillna("n/a")
    members["is_experiment_subject"] = members["experiment_arm"].isin(["control", "treatment"])
    mm["experiment_arm"] = mm["member_id"].map(arm_map).fillna("not_enrolled")

    # current tier on member (ledger status at last window month)
    last_status = (mm.sort_values("month_key").drop_duplicates("member_id", keep="last")
                   .set_index("member_id")["tier_key"])
    members["current_tier_key"] = members["member_id"].map(last_status).fillna(1).astype(int)
    members["current_tier_name"] = members["current_tier_key"].map({v: k for k, v in TIER_KEY.items() if k})

    members_out = members[[
        "member_key", "member_id", "enrollment_date_key", "enrollment_cohort_month",
        "enrollment_channel", "home_city", "home_region", "has_cobrand_card",
        "current_tier_key", "current_tier_name", "crm_present", "crm_lifecycle_stage",
        "age_band", "is_steady_state_cohort", "is_test_account",
        "experiment_arm", "experiment_stratum", "is_experiment_subject"]].copy()
    out(members_out, "dim_member")

    keep = ["member_key", "member_id", "month_key", "ym", "tier_key", "experiment_arm",
            "points_earned_m", "points_redeemed_m", "points_expired_m", "redemptions_m",
            "balance_pts_eom", "has_redeemed_ever_eom", "flights_m", "flight_revenue_brl_m",
            "card_spend_brl_m", "tenure_months", "is_new_enrollment", "months_since_last_activity",
            "is_active_eom", "is_lapsed_eom", "became_lapsed_this_month", "is_reactivation"]
    out(mm[keep].reset_index(drop=True), "fact_member_month")

    # snapshot-vs-ledger drift metric ---------------------------------
    ts = L("stg_skycore_tier_snapshots").copy()
    ts["month_key"] = ts["ym"].str.replace("-", "").astype(int)
    dcmp = mm[["member_id", "month_key", "tier_key"]].merge(
        ts[["member_id", "month_key", "tier"]], on=["member_id", "month_key"], how="inner")
    dcmp["snap_key"] = dcmp["tier"].map(TIER_KEY)
    drift = int((dcmp["snap_key"] != dcmp["tier_key"]).sum())
    write_dq_fragment("curated__tier_snapshot_drift", {
        "member_months_compared": len(dcmp), "drift_member_months": drift,
        "drift_rate": round(drift / max(1, len(dcmp)), 4)})
    print(f"  tier snapshot-vs-ledger drift: {drift:,}/{len(dcmp):,} "
          f"({drift/max(1,len(dcmp)):.1%})")

    return members, mm, dim_date


# ======================================================================== #
def build_liability(mm: pd.DataFrame):
    fpt = pd.read_parquet(CUR / "fact_point_transaction.parquet")
    roll = fpt.groupby(["month_key", "txn_type"])["points"].sum().unstack(fill_value=0)
    for c in ("earn", "redeem", "expire", "adjust"):
        if c not in roll:
            roll[c] = 0
    roll = roll.rename(columns={"earn": "points_issued_m", "redeem": "points_redeemed_m",
                                "expire": "points_expired_m"})
    roll["points_redeemed_m"] = -roll["points_redeemed_m"]
    roll["points_expired_m"] = -roll["points_expired_m"]
    roll = roll.reset_index().sort_values("month_key")
    roll = roll[(roll["month_key"] >= month_key(C.WINDOW_START)) &
                (roll["month_key"] <= month_key(C.WINDOW_END))]
    roll["points_outstanding_eop"] = (roll["points_issued_m"] - roll["points_redeemed_m"]
                                      - roll["points_expired_m"]).cumsum()
    roll["liability_brl_gross"] = (roll["points_outstanding_eop"] * C.POINT_UNIT_COST_BRL).round(2)
    roll["liability_brl_breakage_adj"] = (roll["liability_brl_gross"]
                                          * (1 - C.EXPECTED_BREAKAGE)).round(2)

    led = L("stg_ledger_liability_rollforward").copy()
    led["month_key"] = mkey(led["mes"])
    rcst = L("stg_ledger_reward_cost").copy()
    rcst["month_key"] = mkey(rcst["mes"])
    rcm = rcst.groupby("month_key", as_index=False)["custo_caixa_brl"].sum().rename(
        columns={"custo_caixa_brl": "reward_cash_cost_brl"})
    fli = roll.merge(led[["month_key", "pontos_emitidos", "pontos_resgatados",
                          "pontos_expirados", "provisao_breakage_brl"]],
                     on="month_key", how="left").merge(rcm, on="month_key", how="left")
    fli = fli.rename(columns={"pontos_emitidos": "points_issued_m_ledger",
                              "pontos_resgatados": "points_redeemed_m_ledger",
                              "pontos_expirados": "points_expired_m_ledger",
                              "provisao_breakage_brl": "breakage_provision_brl"})
    out(fli, "fact_liability_month")

    # tie-out DQ
    j = fli.dropna(subset=["points_issued_m_ledger"])
    err = ((j["points_issued_m"] - j["points_issued_m_ledger"]).abs()
           / j["points_issued_m"].replace(0, np.nan)).mean()
    write_dq_fragment("curated__liability_tie_out",
                      {"mean_rel_error_points_issued": round(float(err or 0), 5),
                       "months": len(j)})


def build_experiment_facts(members: pd.DataFrame):
    banner("curated: experiment tables")
    mid_map = members[["member_id", "member_key"]]
    TIER = {t: i + 1 for i, t in enumerate(TIERS)}

    asg_raw = L("stg_flesk_ab_assignments")
    asg = asg_raw[asg_raw["eligible"]].merge(mid_map, on="member_id", how="left")
    asg["member_key"] = asg["member_key"].fillna(-2).astype(int)
    asg["arm_key"] = asg["arm"]
    asg_out = asg[["member_key", "member_id", "arm_key", "stratum", "assigned_ts",
                   "pre_earn_12m_pts", "pre_flights_12m", "pre_redemptions_12m",
                   "pre_balance_pts", "prior_redeemer_flag", "pre_tenure_months"]].copy()
    ctr = Counter(dropped_ineligible=int((~asg_raw["eligible"]).sum()),
                  n_assigned=len(asg_out))
    out(asg_out, "fact_experiment_assignment", ctr)

    wk = L("stg_flesk_redemption_week").merge(mid_map, on="member_id", how="left")
    wk["member_key"] = wk["member_key"].fillna(-2).astype(int)
    wk = wk.rename(columns={"arm": "arm_key"})
    out(wk[["member_key", "member_id", "arm_key", "stratum", "week", "redeemed_w",
            "redemptions_w", "points_redeemed_w", "redemption_value_brl_w",
            "low_cost_only_w"]], "fact_experiment_member_week")

    oc = L("stg_flesk_outcome").merge(mid_map, on="member_id", how="left")
    oc["member_key"] = oc["member_key"].fillna(-2).astype(int)
    oc = oc.rename(columns={"arm": "arm_key"})
    cols = ["member_key", "member_id", "arm_key", "stratum", "redeemed_in_window",
            "redemptions_in_window", "redemption_value_brl", "points_redeemed_in_window",
            "low_cost_only", "revenue_brl_window_plus8w", "liability_drawdown_brl",
            "reward_cash_cost_brl", "net_liability_cost_brl", "disengaged_90d_post",
            "earn_in_window", "flights_in_window", "active_post_quarter"]
    out(oc[[c for c in cols if c in oc.columns]], "fact_experiment_outcome")


def build_targets():
    win = pd.period_range(C.WINDOW_START, C.WINDOW_END, freq="M")
    n = len(win)
    ramp = np.linspace(0, 1, n)
    rows = []
    for i, p in enumerate(win):
        mk = p.year * 100 + p.month
        rows += [
            (mk, "active_members", round(45000 + 35000 * ramp[i])),
            (mk, "breakage_rate", round(0.40 - 0.10 * ramp[i], 4)),
            (mk, "redemption_rate_quarterly", round(0.09 + 0.06 * ramp[i], 4)),
            (mk, "lapse_rate_12m", round(0.28 - 0.06 * ramp[i], 4)),
            (mk, "burn_earn_ratio", round(0.50 + 0.20 * ramp[i], 4)),
        ]
    out(pd.DataFrame(rows, columns=["month_key", "kpi", "target_value"]), "fact_targets_month")


def main():
    banner("AeroVanti SkyPoints — 03_build_curated")
    CUR.mkdir(parents=True, exist_ok=True)
    members, mm, dim_date = build_members_and_facts()
    build_liability(mm)
    build_experiment_facts(members)
    build_targets()
    banner("03_build_curated complete")


if __name__ == "__main__":
    main()
