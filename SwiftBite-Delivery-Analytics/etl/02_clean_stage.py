"""
SwiftBite Delivery — 02_clean_stage.py

Raw -> staging. One typed stg_<source>_<entity> per raw entity: datetime parsing,
timezone normalisation (local feeds localised from America/Sao_Paulo; PayHub/Boost
already UTC), money-string parsing, encoding repair, GPS sanitisation + 1-minute
courier-state reduction, de-duplication, category harmonisation. No cross-source
joins, no business logic. Every fix counted into a DQ fragment.
"""
from __future__ import annotations

import glob
import gzip
import json

import numpy as np
import pandas as pd

import config as C
from utils import (banner, from_excel_serial, haversine_km, read_parquet, rng,
                   write_dq_fragment, write_parquet)

try:
    from ftfy import fix_text
except Exception:                       # pragma: no cover
    def fix_text(s):
        return s

RAW, STG = C.RAW_DIR, C.STAGING_DIR
TZ = C.TIMEZONE
BBOX = (-20.20, -19.65, -44.20, -43.70)   # lat_lo, lat_hi, lon_lo, lon_hi (metro)


# --------------------------------------------------------------------------- #
def parse_money(s: pd.Series) -> tuple[pd.Series, dict]:
    raw = s.astype("string")
    txt = raw.str.strip()
    neg = txt.str.startswith("(") & txt.str.endswith(")")
    t = txt.str.replace(r"^\(|\)$", "", regex=True).str.replace("R$", "", regex=False).str.strip()
    both = t.str.contains(r"\.", regex=True) & t.str.contains(",", regex=True)
    t = t.mask(both, t.str.replace(".", "", regex=False))
    t = t.str.replace(",", ".", regex=False)
    val = pd.to_numeric(t, errors="coerce")
    val = val.mask(neg, -val)
    return val, {"money_strings_parsed": int(raw.str.contains(r"[R$,()]", regex=True).fillna(False).sum()),
                 "money_negatives_from_parens": int(neg.fillna(False).sum()),
                 "money_unparseable": int(val.isna().sum() - raw.isna().sum())}


def parse_dt_local(s: pd.Series) -> tuple[pd.Series, int]:
    """Fast split parser: ISO (`YYYY-...`) vs BR (`DD/MM/YYYY HH:MM`); localise -> UTC."""
    s = s.astype("string")
    iso = s.str.match(r"^\d{4}-")
    dt = pd.Series(pd.NaT, index=s.index, dtype="datetime64[ns]")
    dt.loc[iso] = pd.to_datetime(s[iso], format="ISO8601", errors="coerce")
    dt.loc[~iso] = pd.to_datetime(s[~iso], format="%d/%m/%Y %H:%M", errors="coerce")
    bad = int(dt.isna().sum())
    dt = (dt.dt.tz_localize(TZ, nonexistent="shift_forward", ambiguous=False).dt.tz_convert("UTC"))
    return dt, bad


def parse_dt_utc(s: pd.Series) -> tuple[pd.Series, int]:
    dt = pd.to_datetime(s, format="ISO8601", utc=True, errors="coerce")
    return dt, int(dt.isna().sum())


def dedup(df: pd.DataFrame, subset=None) -> tuple[pd.DataFrame, int]:
    before = len(df)
    out = df.drop_duplicates(subset=subset).reset_index(drop=True)
    return out, before - len(out)


def load_vocab(name: str) -> dict:
    v = pd.read_csv(C.VOCAB_DIR / name)
    return dict(zip(v["raw"].str.lower(), v["canonical"]))


def harmonise(s: pd.Series, vmap: dict) -> tuple[pd.Series, int]:
    low = s.astype("string").str.strip().str.lower()
    out = low.map(vmap)
    unknown = int(out.isna().sum() - s.isna().sum())
    return out.fillna("unknown"), unknown


# --------------------------------------------------------------------------- #
def stage_georef():
    banner("stage georef")
    z = pd.read_csv(RAW / "georef" / "georef__zones.csv")
    write_parquet(z, STG / "stg_georef_zones.parquet")
    a = pd.read_csv(RAW / "georef" / "georef__zone_adjacency.csv")
    write_parquet(a, STG / "stg_georef_zone_adjacency.parquet")
    h = pd.read_csv(RAW / "georef" / "georef__zone_history.csv")
    h["valid_from"] = pd.to_datetime(h["valid_from"], errors="coerce")
    h["valid_to"] = pd.to_datetime(h["valid_to"], errors="coerce")
    write_parquet(h, STG / "stg_georef_zone_history.parquet")
    write_dq_fragment("stg_georef", {"zones": len(z), "adjacency_edges": len(a)})


def stage_masters():
    banner("stage masters (couriers / customers / restaurants)")
    c = pd.read_csv(RAW / "riderapp" / "riderapp__couriers.csv")
    cnt_case = int((c["courier_id"] != c["courier_id"].str.upper()).sum())
    c["courier_id"] = c["courier_id"].str.upper().str.strip()
    c["signup_date"] = pd.to_datetime(c["signup_date"], errors="coerce")
    c, dup = dedup(c, ["courier_id"])
    write_parquet(c, STG / "stg_riderapp_couriers.parquet")
    write_dq_fragment("stg_riderapp_couriers", {"rows": len(c), "courier_id_case_normalised": cnt_case,
                                                "dupe_courier_dropped": dup})

    u = pd.read_csv(RAW / "ordercore" / "ordercore__customers.csv")
    write_parquet(u, STG / "stg_ordercore_customers.parquet")

    r = pd.read_csv(RAW / "ordercore" / "ordercore__restaurants.csv")
    moj = int(r["restaurant_name"].astype("string").str.contains(r"Ã|Â", regex=True).fillna(False).sum())
    r["restaurant_name"] = r["restaurant_name"].map(lambda x: fix_text(str(x)))
    write_parquet(r, STG / "stg_ordercore_restaurants.parquet")
    write_dq_fragment("stg_ordercore_restaurants", {"rows": len(r), "mojibake_repaired": moj})


def stage_orders():
    banner("stage ordercore orders / status / addresses")
    files = sorted(glob.glob(str(RAW / "ordercore" / "ordercore__orders__*.csv")))
    df = pd.concat((pd.read_csv(f, dtype={"basket_value": "string", "delivery_fee": "string"})
                    for f in files), ignore_index=True)
    n_raw = len(df)
    df, dup = dedup(df)                                  # exact retry dupes
    ts, bad = parse_dt_local(df["placed_at"])
    df["placed_ts"] = ts
    basket, mstat = parse_money(df["basket_value"])
    df["basket_value_brl"] = basket
    df["delivery_fee_brl"] = pd.to_numeric(df["delivery_fee"], errors="coerce")
    df["eta_min"] = pd.to_numeric(df["eta_min"], errors="coerce")
    df["dist_km"] = pd.to_numeric(df["dist_km"], errors="coerce")
    out = df[["order_id", "customer_id", "restaurant_id", "pickup_zone_id", "delivery_zone_label",
              "placed_ts", "basket_value_brl", "delivery_fee_brl", "outcome", "eta_min", "dist_km"]]
    write_parquet(out, STG / "stg_ordercore_orders.parquet")
    write_dq_fragment("stg_ordercore_orders",
                      {"rows_raw": n_raw, "rows": len(out), "retry_dupes_dropped": dup,
                       "datetimes_unparseable": bad, **mstat})

    smap = load_vocab("order_status_map.csv")
    ev_files = sorted(glob.glob(str(RAW / "ordercore" / "ordercore__order_status_events__*.csv")))
    ev = pd.concat((pd.read_csv(f) for f in ev_files), ignore_index=True)
    n_ev = len(ev)
    ev, edup = dedup(ev)
    ev["status_canonical"], unk = harmonise(ev["status"], smap)
    ev["event_ts"], ebad = parse_dt_local(ev["event_at"])
    write_parquet(ev[["order_id", "status_canonical", "event_ts"]], STG / "stg_ordercore_order_status_events.parquet")
    write_dq_fragment("stg_ordercore_order_status_events",
                      {"rows_raw": n_ev, "rows": len(ev), "dupe_events_dropped": edup,
                       "categories_normalised": len(ev) - unk, "category_unknowns": unk,
                       "datetimes_unparseable": ebad})

    ad_files = sorted(glob.glob(str(RAW / "ordercore" / "ordercore__addresses__*.csv")))
    ad = pd.concat((pd.read_csv(f) for f in ad_files), ignore_index=True)
    moj = int(ad["bairro"].astype("string").str.contains(r"Ã|Â", regex=True).fillna(False).sum())
    ad["bairro"] = ad["bairro"].map(lambda x: fix_text(str(x)))
    ad["logradouro"] = ad["logradouro"].map(lambda x: fix_text(str(x)))
    ad["lat"] = pd.to_numeric(ad["lat"], errors="coerce")
    ad["lon"] = pd.to_numeric(ad["lon"], errors="coerce")
    write_parquet(ad, STG / "stg_ordercore_addresses.parquet")
    write_dq_fragment("stg_ordercore_addresses", {"rows": len(ad), "mojibake_repaired": moj})


def stage_dispatch():
    banner("stage dispatch assignment events")
    df = pd.read_csv(RAW / "dispatch" / "dispatch__assignment_events.csv",
                     dtype={"latency_ms_text": "string"})
    n = len(df)
    df, dup = dedup(df)
    df["event_ts"], bad = parse_dt_local(df["event_at"])
    df["latency_s"] = pd.to_numeric(df["latency_ms_text"], errors="coerce") / 1000.0
    write_parquet(df[["order_id", "event", "event_ts", "latency_s"]],
                  STG / "stg_dispatch_assignment_events.parquet")
    write_dq_fragment("stg_dispatch_assignment_events",
                      {"rows_raw": n, "rows": len(df), "dupe_events_dropped": dup,
                       "latency_coerced": int(df["latency_s"].notna().sum()), "datetimes_unparseable": bad})


def stage_payhub():
    banner("stage payhub (order payments / courier payouts / bonus)")
    main = pd.read_csv(RAW / "payhub" / "payhub__order_payments.csv", dtype={"amount": "string"})
    redp = RAW / "payhub" / "payhub__order_payments__2026-05_REDELIVERED.csv"
    red_dropped = 0
    if redp.exists():
        r = pd.read_csv(redp, dtype={"amount": "string"})
        before = len(main) + len(r)
        main = pd.concat([main, r], ignore_index=True).drop_duplicates(subset=["order_id"]).reset_index(drop=True)
        red_dropped = before - len(main)
    amt, mstat = parse_money(main["amount"])
    main["amount_brl"] = amt
    main["paid_ts"], bad = parse_dt_utc(main["paid_at_utc"])
    main["settlement_week_date"] = [from_excel_serial(x) if pd.notna(x) else pd.NaT
                                    for x in pd.to_numeric(main["settlement_week"], errors="coerce")]
    write_parquet(main[["order_id", "paid_ts", "amount_brl", "settlement_week_date"]],
                  STG / "stg_payhub_order_payments.parquet")
    write_dq_fragment("stg_payhub_order_payments",
                      {"rows": len(main), "redelivered_rows_dropped": red_dropped,
                       "utc_datetimes_unparseable": bad, **mstat})

    cp = pd.read_csv(RAW / "payhub" / "payhub__courier_payouts.csv", dtype={"amount": "string"})
    cp["courier_id"] = cp["courier_id"].str.upper().str.strip()
    cpamt, cpstat = parse_money(cp["amount"])
    cp["amount_brl"] = cpamt
    cp["paid_ts"], cpbad = parse_dt_utc(cp["paid_at_utc"])
    cp["settlement_week_date"] = [from_excel_serial(x) if pd.notna(x) else pd.NaT
                                  for x in pd.to_numeric(cp["settlement_week"], errors="coerce")]
    write_parquet(cp[["courier_id", "date_key", "zone_id", "deliveries", "amount_brl",
                      "settlement_week_date", "paid_ts"]], STG / "stg_payhub_courier_payouts.parquet")
    write_dq_fragment("stg_payhub_courier_payouts", {"rows": len(cp), "utc_datetimes_unparseable": cpbad, **cpstat})

    bp = pd.read_csv(RAW / "payhub" / "payhub__bonus_payouts.csv")
    bp["courier_id"] = bp["courier_id"].str.upper().str.strip()
    n = len(bp)
    bp, dup = dedup(bp)
    bp["bonus_brl"] = pd.to_numeric(bp["bonus_brl"], errors="coerce")
    bp["paid_ts"], bbad = parse_dt_utc(bp["paid_at_utc"])
    write_parquet(bp[["courier_id", "zone_id", "date_key", "hour", "deliveries", "bonus_brl", "paid_ts"]],
                  STG / "stg_payhub_bonus_payouts.parquet")
    write_dq_fragment("stg_payhub_bonus_payouts", {"rows_raw": n, "rows": len(bp), "dupe_events_dropped": dup,
                                                   "utc_datetimes_unparseable": bbad})


def stage_riderapp():
    banner("stage riderapp (sessions / blocks / offers)")
    s = pd.read_csv(RAW / "riderapp" / "riderapp__courier_sessions.csv")
    s["courier_id"] = s["courier_id"].str.upper().str.strip()
    s["login_ts"], b1 = parse_dt_local(s["login_local"])
    s["logout_ts"], b2 = parse_dt_local(s["logout_local"])
    write_parquet(s[["courier_id", "date_key", "login_ts", "logout_ts", "mins"]],
                  STG / "stg_riderapp_courier_sessions.parquet")
    write_dq_fragment("stg_riderapp_courier_sessions", {"rows": len(s), "datetimes_unparseable": b1 + b2})

    b = pd.read_csv(RAW / "riderapp" / "riderapp__shift_zone_blocks.csv")
    b["courier_id"] = b["courier_id"].str.upper().str.strip()
    write_parquet(b, STG / "stg_riderapp_shift_zone_blocks.parquet")
    write_dq_fragment("stg_riderapp_shift_zone_blocks", {"rows": len(b)})

    omap = load_vocab("offer_outcome_map.csv")
    o = pd.read_csv(RAW / "riderapp" / "riderapp__offers.csv")
    n = len(o)
    o, dup = dedup(o)
    o["courier_id"] = o["courier_id"].str.upper().str.strip()
    o["outcome_canonical"], unk = harmonise(o["outcome"], omap)
    write_parquet(o[["offer_id", "courier_id", "zone_id", "date_key", "hour", "outcome_canonical"]],
                  STG / "stg_riderapp_offers.parquet")
    write_dq_fragment("stg_riderapp_offers", {"rows_raw": n, "rows": len(o), "dupe_events_dropped": dup,
                                              "category_unknowns": unk})


def stage_trace():
    banner("stage trace (dwell rollup + ping-minute from the 7d reference)")
    d = pd.read_csv(RAW / "trace" / "trace__zone_dwell_minutes.csv")
    d["courier_id"] = d["courier_id"].str.upper().str.strip()
    write_parquet(d, STG / "stg_trace_zone_dwell.parquet")
    write_dq_fragment("stg_trace_zone_dwell", {"rows": len(d)})

    path = RAW / "trace" / "trace__location_pings__REF.ndjson.gz"
    recs = []
    with gzip.open(path, "rt", encoding="utf-8") as fh:
        for line in fh:
            recs.append(json.loads(line))
    p = pd.DataFrame(recs)
    n_raw = len(p)
    p["courier_id"] = p["courier_id"].str.upper().str.strip()
    null_island = ((p["lat"].abs() < 1e-6) & (p["lon"].abs() < 1e-6))
    oob = ~p["lat"].between(BBOX[0], BBOX[1]) | ~p["lon"].between(BBOX[2], BBOX[3])
    drop = null_island | oob
    p = p[~drop].copy()
    p["ts"] = pd.to_datetime(p["ts"].astype("int64"), unit="ms", utc=True)
    p["minute"] = p["ts"].dt.floor("min")
    p = p.sort_values(["courier_id", "ts"])
    p["dlat"] = p.groupby("courier_id")["lat"].diff()
    p["dlon"] = p.groupby("courier_id")["lon"].diff()
    p["step_km"] = haversine_km(p["lat"] - p["dlat"], p["lon"] - p["dlon"], p["lat"], p["lon"]).fillna(0)
    cm = (p.groupby(["courier_id", "minute"])
            .agg(step_km=("step_km", "sum"), pings=("ts", "size")).reset_index())
    cm["state"] = np.where(cm["step_km"] > 0.15, "moving", "idle")
    write_parquet(cm, STG / "stg_trace_ping_minute.parquet")
    write_dq_fragment("stg_trace_ping_minute",
                      {"pings_raw": n_raw, "gps_null_island_dropped": int(null_island.sum()),
                       "gps_out_of_area_dropped": int((oob & ~null_island).sum()),
                       "ping_minutes_materialised": len(cm)})


def stage_boost():
    banner("stage boost (incentive campaigns + bonus ledger)")
    c = pd.read_csv(RAW / "boost" / "boost__incentive_campaigns.csv")
    c["created_ts"], bad = parse_dt_utc(c["created_at_utc"])
    n = len(c)
    c = (c.sort_values("created_ts").drop_duplicates(subset=["zone_id", "date_key"], keep="first")
          .reset_index(drop=True))                       # earliest edit = the 00:00-fixed assignment
    write_parquet(c[["campaign_id", "zone_id", "date_key", "arm", "bonus_brl_per_delivery",
                     "push_radius_m", "peak_start_hour", "peak_end_hour", "created_ts"]],
                  STG / "stg_boost_incentive_campaigns.parquet")
    write_dq_fragment("stg_boost_incentive_campaigns",
                      {"rows_raw": n, "rows": len(c), "campaign_late_edits_reconciled": n - len(c),
                       "utc_datetimes_unparseable": bad})

    led = pd.read_csv(RAW / "boost" / "boost__bonus_ledger.csv")
    led["bonus_brl"] = pd.to_numeric(led["bonus_brl"], errors="coerce")
    led = led.groupby(["zone_id", "date_key"], as_index=False)["bonus_brl"].sum()
    write_parquet(led, STG / "stg_boost_bonus_ledger.parquet")
    write_dq_fragment("stg_boost_bonus_ledger", {"rows": len(led)})


def main():
    banner("SwiftBite — 02_clean_stage")
    STG.mkdir(parents=True, exist_ok=True)
    stage_georef()
    stage_masters()
    stage_orders()
    stage_dispatch()
    stage_payhub()
    stage_riderapp()
    stage_trace()
    stage_boost()
    banner("02_clean_stage done")


if __name__ == "__main__":
    main()
