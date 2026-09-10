"""
03_build_curated.py — data/staging/stg_*  ->  data/curated/{dim,fact}_*.{parquet,csv}

Conformed Kimball star. Surrogate keys, snapshot folded from the movement ledger,
annual-plan monthly recognition, USD on every money column, is_comparable_base.
"""
from __future__ import annotations

import json
import sys
import datetime as _dt
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

import config as C
from utils import month_start, month_end, month_label, days_in_month, progress, write_parquet, dq_fragment

CNT = {}
def _c(k, n=1): CNT[k] = CNT.get(k, 0) + int(n)

CURRENCY = {k: v["currency"] for k, v in C.MARKETS.items()}


# Parquet is the source of truth for the model and the analysis. A CSV mirror is kept only
# for the compact tables (dims + small facts) — a convenient, diff-able preview. The
# multi-million-row facts would add ~370 MB of redundant text, so they are Parquet-only.
_CSV_MIRROR_MAX_ROWS = 200_000


def _save(df, name):
    write_parquet(df, C.CURATED / f"{name}.parquet")
    csv_path = C.CURATED / f"{name}.csv"
    if len(df) <= _CSV_MIRROR_MAX_ROWS:
        df.to_csv(csv_path, index=False)
    elif csv_path.exists():
        csv_path.unlink()


def sk(series):
    """surrogate keys 1..n for unique values, plus a {value: key} map (0 reserved)."""
    vals = pd.Index(pd.unique(series.dropna()))
    m = {v: i + 1 for i, v in enumerate(vals)}
    return m


# =========================================================================
def dim_date():
    d = pd.date_range(C.DIM_DATE_START, C.DIM_DATE_END, freq="D")
    df = pd.DataFrame({"date": d})
    df["date_key"] = df["date"].dt.year * 10000 + df["date"].dt.month * 100 + df["date"].dt.day
    df["year"] = df["date"].dt.year
    df["quarter"] = df["date"].dt.quarter
    df["month_num"] = df["date"].dt.month
    df["month_name"] = df["date"].dt.strftime("%b")
    df["year_month"] = df["date"].dt.strftime("%Y-%m")
    df["month_sort"] = df["year"] * 100 + df["month_num"]
    df["abs_month"] = df["year"] * 12 + df["month_num"]     # linear month index for time-intel DAX
    df["day_of_month"] = df["date"].dt.day
    df["is_month_end"] = df["date"].dt.is_month_end
    df["iso_week"] = df["date"].dt.isocalendar().week.astype(int)
    win0 = pd.Timestamp(month_start(0))
    df["window_month_idx"] = ((df["year"] - win0.year) * 12 + df["month_num"] - win0.month)
    df["in_analysis_window"] = df["window_month_idx"].between(0, C.N_MONTHS - 1)
    hol = pd.read_csv(C.VOCAB / "holidays.csv", parse_dates=["date"])
    for mk in C.MARKETS:
        hd = set(hol[hol["market"] == mk]["date"])
        df[f"is_holiday_{mk.lower()}"] = df["date"].isin(hd)
    m = df["month_num"]
    df["season_tag"] = np.select(
        [m.isin([12, 1]), m.isin([6, 7]), m.isin([2])],
        ["year_end_peak", "midyear", "carnaval"], default="regular")
    df["is_partial_period"] = df["window_month_idx"] == (C.N_MONTHS - 1)   # last window month
    _save(df, "dim_date")
    progress("curated: dim_date")


def dim_market():
    rows = []
    for mk, v in C.MARKETS.items():
        rows.append({"market_key": len(rows) + 1, "market_id": mk, "currency_code": v["currency"],
                     "market_active_from_date_key": int(pd.Timestamp(month_start(v["active_from_idx"]))
                                                        .strftime("%Y%m%d")),
                     "timezone": v["tz"], "is_comparable_base": mk == "BR"})
    df = pd.DataFrame(rows)
    _save(df, "dim_market")
    return {r.market_id: r.market_key for r in df.itertuples()}


def dim_channel():
    rows = [{"channel_key": i + 1, "channel": c,
             "channel_group": C.CHANNEL_GROUP.get(c, "unknown"),
             "is_low_quality": c in C.LOWQ_CHANNELS}
            for i, c in enumerate(C.CHANNELS + ["unknown"])]
    df = pd.DataFrame(rows)
    _save(df, "dim_channel")
    return {r.channel: r.channel_key for r in df.itertuples()}


def dim_device():
    rows = [{"device_key": i + 1, "device_family": d, "device_class": C.DEVICE_CLASS[d],
             "is_ctv": d in C.CTV_FAMILIES} for i, d in enumerate(C.DEVICE_FAMILIES)]
    rows.append({"device_key": len(rows) + 1, "device_family": "unknown",
                 "device_class": "unknown", "is_ctv": False})
    df = pd.DataFrame(rows)
    _save(df, "dim_device")
    return {r.device_family: r.device_key for r in df.itertuples()}


def dim_payment_method():
    rows = [{"method_key": i + 1, "method": m, "is_prepaid": m in ("boleto", "oxxo"),
             "settlement_lag_days_typical": C.SETTLEMENT_LAG_DAYS[m]}
            for i, m in enumerate(["card", "pix", "boleto", "oxxo", "carrier_billing"])]
    df = pd.DataFrame(rows)
    _save(df, "dim_payment_method")
    return {r.method: r.method_key for r in df.itertuples()}


def dim_plan_and_price(market_key):
    pc = pd.read_parquet(C.STAGING / "stg_ketch_plan_catalog.parquet")
    rows, prows = [], []
    pk = 0
    for tier in C.TIERS:
        for bp in C.BILLING_PERIODS:
            for mk in C.MARKETS:
                pk += 1
                f = C.PLAN_FEATURES[tier]
                rows.append({"plan_key": pk, "plan_id": f"{tier}-{bp}-{mk}", "tier": tier,
                             "billing_period": bp, "market_id": mk, "market_key": market_key[mk],
                             **f})
    plan = pd.DataFrame(rows)
    _save(plan, "dim_plan")
    plan_map = {(r.tier, r.billing_period, r.market_id): r.plan_key for r in plan.itertuples()}

    # price history: pre-hike + post-hike (BR Std/Prem); everyone else flat
    ph = 0
    for tier in C.TIERS:
        for mk in C.MARKETS:
            end_price = C.PRICE_LOCAL_END[tier][mk]
            if mk == "BR" and tier in ("Standard", "Premium"):
                pre = round(end_price / (1 + C.BR_PRICE_HIKE_PCT[tier]), 2)
                ph += 1
                prows.append({"price_key": ph, "tier": tier, "market_id": mk,
                              "effective_from_date_key": int(pd.Timestamp(month_start(0)).strftime("%Y%m%d")),
                              "effective_to_date_key": int(pd.Timestamp(month_start(C.BR_PRICE_HIKE_IDX)).strftime("%Y%m%d")) - 1,
                              "list_price_local": pre})
                ph += 1
                prows.append({"price_key": ph, "tier": tier, "market_id": mk,
                              "effective_from_date_key": int(pd.Timestamp(month_start(C.BR_PRICE_HIKE_IDX)).strftime("%Y%m%d")),
                              "effective_to_date_key": 20271231, "list_price_local": end_price})
            else:
                ph += 1
                prows.append({"price_key": ph, "tier": tier, "market_id": mk,
                              "effective_from_date_key": int(pd.Timestamp(month_start(0)).strftime("%Y%m%d")),
                              "effective_to_date_key": 20271231, "list_price_local": end_price})
    price = pd.DataFrame(prows)
    _save(price, "dim_price_history")
    return plan_map


def _price_local(tier, market, idx):
    end_price = C.PRICE_LOCAL_END[tier][market]
    if market == "BR" and tier in ("Standard", "Premium") and idx < C.BR_PRICE_HIKE_IDX:
        return round(end_price / (1 + C.BR_PRICE_HIKE_PCT[tier]), 2)
    return end_price


def dim_content():
    t = pd.read_parquet(C.STAGING / "stg_reelbase_titles.parquet").copy()
    t.insert(0, "content_key", range(1, len(t) + 1))
    t["release_date_key"] = pd.to_datetime(t["release_date"], errors="coerce").dt.strftime("%Y%m%d")
    t["release_date_key"] = pd.to_numeric(t["release_date_key"], errors="coerce").fillna(-1).astype(int)
    t["primary_genre"] = t["primary_genre"].fillna("Unknown")
    _save(t.drop(columns=["release_date"]), "dim_content")
    cmap = dict(zip(t["content_id"], t["content_key"]))

    rel = pd.read_parquet(C.STAGING / "stg_reelbase_licence_windows.parquet")
    # release schedule proxy: first licence window start per title/market flagged tentpole-ish
    # (curated keeps it simple: a release-calendar table for the Content page)
    try:
        rl = pd.read_parquet(C.STAGING / "stg_reelbase_licence_windows.parquet")
    except Exception:
        rl = pd.DataFrame()
    return cmap


def dim_support_reason():
    xw = pd.read_csv(C.VOCAB / "support_reason_crosswalk.csv")
    u = xw[["reason_category", "reason_group"]].drop_duplicates().reset_index(drop=True)
    u.insert(0, "support_reason_key", range(1, len(u) + 1))
    _save(u, "dim_support_reason")
    return {r.reason_category: r.support_reason_key for r in u.itertuples()}


# =========================================================================
def dim_subscriber(market_key, channel_map):
    acc = pd.read_parquet(C.STAGING / "stg_voxaid_accounts.parquet")
    ev = pd.read_parquet(C.STAGING / "stg_entitlement_events.parquet")
    att = pd.read_parquet(C.STAGING / "stg_adbridge_attribution.parquet")
    crm = pd.read_parquet(C.STAGING / "stg_bonsai_crm_contacts.parquet")
    inv = pd.read_parquet(C.STAGING / "stg_ketch_invoices.parquet")

    first_paid = (ev[ev["kind"].isin(["paid_start"])].groupby("subject")["month_idx"].min()
                  .rename("first_paid_month_idx"))
    first_tier = (ev[ev["kind"] == "paid_start"].sort_values("occurred_at")
                  .groupby("subject")["to_tier"].first().rename("first_tier"))
    # current tier: last plan_change/paid_start/reactivate to_tier
    last_tier = (ev[ev["kind"].isin(["paid_start", "plan_change", "reactivate"])]
                 .dropna(subset=["to_tier"]).sort_values("occurred_at")
                 .groupby("subject")["to_tier"].last().rename("current_tier"))

    # billing period: annual if the subscriber has an invoice ~>= 6x a monthly plan price
    inv2 = inv.dropna(subset=["amount_local"]).copy()
    max_inv = inv2.groupby("account")["amount_local"].max().rename("max_invoice_local")
    med_inv = inv2.groupby("account")["amount_local"].median().rename("med_invoice_local")

    df = acc.rename(columns={"account_id": "subscriber_id"}).copy()
    df = df.join(first_paid, on="subscriber_id").join(first_tier, on="subscriber_id")
    df = df.join(last_tier, on="subscriber_id")
    df = df.join(max_inv, on="subscriber_id").join(med_inv, on="subscriber_id")
    df = df[df["first_paid_month_idx"].notna()].copy()
    df["first_paid_month_idx"] = df["first_paid_month_idx"].astype(int)

    df["first_tier"] = df["first_tier"].fillna("Standard")
    df["current_tier"] = df["current_tier"].fillna(df["first_tier"])
    df["billing_period"] = np.where(
        df["max_invoice_local"] >= 6 * df["med_invoice_local"].clip(lower=1), "annual", "monthly")
    _c("billing_period_detected_annual", int((df["billing_period"] == "annual").sum()))

    # acquisition channel/campaign via last-touch attribution; unmatched -> unknown
    att1 = att.sort_values("touch_date").groupby(att.index // 1).first() if False else att
    att_last = (att.assign(_r=att.groupby(["market", "channel", "campaign_id"]).cumcount())
                .sort_values("touch_date"))
    # attribution has no account key in this feed -> approximate by market+cohort share.
    # Simulate a per-subscriber channel by sampling from the market's monthly channel mix.
    rng = np.random.default_rng(C.SEED)
    mix_by = (att.groupby(["market", "channel"]).size().rename("n").reset_index())
    dfm = []
    for mk, g in df.groupby("market"):
        sub_mix = mix_by[mix_by["market"] == mk]
        if len(sub_mix) == 0:
            ch = np.array(["unknown"] * len(g))
        else:
            p = sub_mix["n"].to_numpy() / sub_mix["n"].sum()
            ch = rng.choice(sub_mix["channel"].to_numpy(), size=len(g), p=p)
        gg = g.copy()
        gg["acquisition_channel"] = ch
        dfm.append(gg)
    df = pd.concat(dfm)
    df["acquisition_channel"] = df["acquisition_channel"].fillna("unknown")

    df = df.join(crm.set_index("account_id")["lifecycle_stage"].rename("crm_lifecycle_stage"),
                 on="subscriber_id")
    df["crm_lifecycle_stage"] = df["crm_lifecycle_stage"].fillna("unknown")

    df.insert(0, "subscriber_key", range(1, len(df) + 1))
    df["market_key"] = df["market"].map(market_key).fillna(0).astype(int)
    df["channel_key"] = df["acquisition_channel"].map(channel_map).fillna(
        channel_map.get("unknown", 0)).astype(int)
    df["cohort_month"] = df["first_paid_month_idx"].map(lambda i: month_label(int(i)))
    df["signup_date_key"] = pd.to_datetime(df["created_date"], errors="coerce").dt.strftime("%Y%m%d")
    df["signup_date_key"] = pd.to_numeric(df["signup_date_key"], errors="coerce").fillna(-1).astype(int)
    df["is_comparable_base"] = df["market"] == "BR"
    df["is_l4l_cohort"] = df["first_paid_month_idx"] <= C.PY_END_IDX
    df["primary_device_family"] = df["primary_device"].fillna("unknown")
    # incentivised sign-up flag: sampled from the channel's promo-code rate (channel is
    # itself a sampled attribute — see docs/08 accepted limitations)
    _ri = np.random.default_rng(C.SEED + 17)
    df["is_incentivised"] = _ri.random(len(df)) < df["acquisition_channel"].map(
        C.INCENTIVISED_SIGNUP_RATE).fillna(0.2).to_numpy()

    keep = ["subscriber_key", "subscriber_id", "market", "market_key", "cohort_month",
            "first_paid_month_idx", "signup_date_key", "acquisition_channel", "channel_key",
            "first_tier", "current_tier", "billing_period", "primary_device_family",
            "crm_lifecycle_stage", "is_incentivised", "is_comparable_base", "is_l4l_cohort"]
    out = df[keep].reset_index(drop=True)
    _save(out, "dim_subscriber")
    progress(f"curated: dim_subscriber ({len(out):,})")
    return out


# =========================================================================
def fact_subscription_event(sub_df, market_key):
    ev = pd.read_parquet(C.STAGING / "stg_entitlement_events.parquet").copy()
    smap = dict(zip(sub_df["subscriber_id"], sub_df["subscriber_key"]))
    ev["subscriber_key"] = ev["subject"].map(smap).fillna(0).astype(int)
    ev["event_date_key"] = pd.to_datetime(ev["occurred_at"]).dt.strftime("%Y%m%d").astype(int)
    ev = ev.rename(columns={"kind": "event_type", "occurred_at": "event_ts_utc"})
    _c("orphan_event_rows_sentinel", int((ev["subscriber_key"] == 0).sum()))
    out = ev[["event_id", "subscriber_key", "subject", "event_type", "event_ts_utc",
              "event_date_key", "month_idx", "from_tier", "to_tier", "reason_code"]]
    _save(out, "fact_subscription_event")
    return ev


def fact_subscription_month(sub_df, ev):
    """Fold the movement ledger forward into a subscriber x month snapshot."""
    bp = dict(zip(sub_df["subscriber_id"], sub_df["billing_period"]))
    mkt = dict(zip(sub_df["subscriber_id"], sub_df["market"]))
    skey = dict(zip(sub_df["subscriber_id"], sub_df["subscriber_key"]))
    _prio = {"paid_start": 1, "reactivate": 1, "plan_change": 3, "resume": 4,
             "pause": 5, "cancel_request": 7, "churn": 9}
    ev = ev.copy()
    ev["_prio"] = ev["event_type"].map(_prio).fillna(5).astype(int)
    ev = ev.sort_values(["subject", "month_idx", "_prio", "event_ts_utc"])
    rows = []
    for subj, g in ev.groupby("subject", sort=False):
        if subj not in skey:
            continue
        market = mkt.get(subj, "BR")
        billing = bp.get(subj, "monthly")
        evs = list(g[["event_type", "month_idx", "to_tier", "reason_code"]].itertuples(index=False))
        # replay -> list of spells: [start_idx, end_idx|None, is_reactivation, tier, churn_kind|None]
        ever_active = False
        tier = "Standard"
        spells = []
        for etype, midx, to_tier, reason in evs:
            midx = int(midx) if pd.notna(midx) else 0
            midx = max(0, min(midx, C.N_MONTHS - 1))
            if etype in ("paid_start", "reactivate"):
                if pd.notna(to_tier):
                    tier = to_tier
                if spells and spells[-1][1] is None:      # unclosed prior spell -> close it
                    spells[-1][1] = midx
                spells.append([midx, None, ever_active, tier, None])
                ever_active = True
            elif etype == "plan_change" and pd.notna(to_tier):
                tier = to_tier
                if spells and spells[-1][1] is None:
                    spells[-1][3] = tier
            elif etype == "churn":
                if spells and spells[-1][1] is None:
                    spells[-1][1] = midx
                    spells[-1][4] = ("involuntary"
                                     if (isinstance(reason, str) and "involuntary" in reason)
                                     else "voluntary")
            # pause / resume / cancel_request: no effect on monthly subscribed state
        for sp in spells:
            s_idx, e_idx_raw, sp_react, sp_tier, ck = sp
            e_idx = e_idx_raw if e_idx_raw is not None else C.N_MONTHS - 1
            e_idx = max(e_idx, s_idx)
            sp = [s_idx, e_idx_raw, sp_react, sp_tier, ck]
            for m in range(max(s_idx, 0), min(e_idx, C.N_MONTHS - 1) + 1):
                is_churn_month = (sp[1] is not None) and (m == sp[1])
                status = "churned" if is_churn_month else "active"
                price = _price_local(sp_tier, market, m)
                mrr = price if billing == "monthly" else round(price * C.ANNUAL_MONTHS_CHARGED / 12.0, 2)
                rows.append((skey[subj], subj, m, status, sp_tier, billing, market,
                             mrr if status == "active" else 0.0,
                             m - s_idx,                                   # tenure_months
                             (m == s_idx) and not sp_react,              # is_new
                             (m == s_idx) and sp_react,                  # is_reactivation
                             is_churn_month and ck == "voluntary",
                             is_churn_month and ck == "involuntary"))
    cols = ["subscriber_key", "subscriber_id", "month_idx", "status", "tier", "billing_period",
            "market", "mrr_local", "tenure_months", "is_new", "is_reactivation",
            "is_voluntary_churn", "is_involuntary_churn"]
    sm = pd.DataFrame(rows, columns=cols)
    # FX -> USD
    fx = pd.read_parquet(C.STAGING / "stg_ledger_fx.parquet")
    fxm = {(r.month_idx, r.currency): r.avg_rate for r in fx.itertuples()}
    sm["fx_rate"] = [fxm.get((m, CURRENCY[mk]), 1.0) for m, mk in zip(sm["month_idx"], sm["market"])]
    sm["mrr_usd"] = (sm["mrr_local"] / sm["fx_rate"]).round(4)
    sm["date_key"] = sm["month_idx"].map(lambda i: int(pd.Timestamp(month_end(int(i))).strftime("%Y%m%d")))
    _save(sm.drop(columns=["fx_rate"]), "fact_subscription_month")
    progress(f"curated: fact_subscription_month ({len(sm):,})")
    return sm


# =========================================================================
def fact_billing_attempt(sub_df, method_map):
    txn = pd.read_parquet(C.STAGING / "stg_pagstream_transactions.parquet").copy()
    smap = dict(zip(sub_df["subscriber_id"], sub_df["subscriber_key"]))
    tiermap = dict(zip(sub_df["subscriber_id"], sub_df["current_tier"]))
    mktmap = dict(zip(sub_df["subscriber_id"], sub_df["market"]))
    txn["subscriber_key"] = txn["account_id"].map(smap).fillna(-1).astype(int)
    _c("null_or_orphan_billing_rows_sentinel", int((txn["subscriber_key"] <= 0).sum()))
    txn["market"] = txn["account_id"].map(mktmap)
    txn["tier"] = txn["account_id"].map(tiermap).fillna("Standard")
    # trusted amount from plan-price schedule (Q06 mislabel worked around)
    txn["amount_local"] = [
        _price_local(t, m if isinstance(m, str) else "BR", int(mi) if pd.notna(mi) else 0)
        for t, m, mi in zip(txn["tier"], txn["market"], txn["month_idx"])]
    txn["method_key"] = txn["method"].map(method_map).fillna(0).astype(int)
    txn["status"] = np.where(txn["type"].eq("refund"), "refunded",
                    np.where(txn["result"].eq("approved"), "approved", "failed"))
    fx = pd.read_parquet(C.STAGING / "stg_ledger_fx.parquet")
    fxm = {(r.month_idx, r.currency): r.avg_rate for r in fx.itertuples()}
    txn["fx_rate"] = [fxm.get((mi, CURRENCY.get(m, "USD")), 1.0)
                      for mi, m in zip(txn["month_idx"].fillna(0).astype(int), txn["market"])]
    txn["amount_usd"] = (txn["amount_local"] / txn["fx_rate"]).round(4)
    pc = txn["method"].map(lambda m: C.PROC_COST.get(m, {"pct": 0.02, "fixed": 0}))
    txn["processing_cost_local"] = [a * p["pct"] + p["fixed"] for a, p in zip(txn["amount_local"], pc)]
    txn["processing_cost_usd"] = (txn["processing_cost_local"] / txn["fx_rate"]).round(4)
    txn["date_key"] = txn["month_idx"].fillna(0).astype(int).map(
        lambda i: int(pd.Timestamp(month_end(int(min(max(i, 0), C.N_MONTHS - 1)))).strftime("%Y%m%d")))
    out = txn[["txn_id", "subscriber_key", "market", "month_idx", "date_key", "ts", "method",
               "method_key", "status", "type", "attempt_number", "is_dunning", "failure_reason",
               "amount_local", "amount_usd", "processing_cost_local", "processing_cost_usd"]]
    out = out.rename(columns={"ts": "attempt_ts_utc"})
    _save(out, "fact_billing_attempt")
    progress(f"curated: fact_billing_attempt ({len(out):,})")


# =========================================================================
def fact_viewing_and_engagement(sub_df, content_map, device_map):
    parts = sorted((C.STAGING / "stg_playlog").glob("*.parquet"))
    smap = dict(zip(sub_df["subscriber_id"], sub_df["subscriber_key"]))
    fx = pd.read_parquet(C.STAGING / "stg_ledger_fx.parquet")
    eng_rows = []
    dm_rows = []                                   # device x market x month rollup (small, for the model)
    mkt_by_sub = dict(zip(sub_df["subscriber_id"], sub_df["market"]))
    vd_dir = C.CURATED / "fact_viewing_daily"
    vd_dir.mkdir(parents=True, exist_ok=True)
    for f in parts:
        p = pd.read_parquet(f)
        idx = int(p["month_idx"].iloc[0])
        p["subscriber_key"] = p["account_ref"].map(smap).fillna(-1).astype(int)
        p["market"] = p["account_ref"].map(mkt_by_sub).fillna("BR")
        p["content_key"] = p["asset_id"].map(content_map).fillna(-1).astype(int)
        _c("orphan_content_rows_sentinel", int((p["content_key"] == -1).sum()))
        p["device_key"] = p["device_family"].map(device_map).fillna(device_map["unknown"]).astype(int)
        dm = (p.groupby(["market", "device_family", "device_key", "month_idx"])
                .agg(streamed_hours=("watch_minutes", lambda s: s.sum() / 60.0),
                     play_starts=("play_starts", "sum"),
                     video_start_failures=("video_start_failures", "sum"),
                     playback_errors=("playback_errors", "sum"),
                     rebuffer_ratio=("rebuffer_ratio", "mean"),
                     cdn_gb=("cdn_gb", "sum"),
                     viewing_subs=("subscriber_key", "nunique"))
                .reset_index())
        dm_rows.append(dm)
        g = (p.groupby(["subscriber_key", "account_ref", "local_date", "device_family",
                        "device_key", "month_idx"], dropna=False)
               .agg(streamed_minutes=("watch_minutes", "sum"),
                    play_starts=("play_starts", "sum"),
                    distinct_titles=("distinct_assets", "max"),
                    video_start_failures=("video_start_failures", "sum"),
                    playback_errors=("playback_errors", "sum"),
                    rebuffer_ratio=("rebuffer_ratio", "mean"),
                    cdn_gb=("cdn_gb", "sum"))
               .reset_index())
        g["date_key"] = pd.to_datetime(g["local_date"]).dt.strftime("%Y%m%d").astype(int)
        write_parquet(g, vd_dir / f"{month_label(idx)}.parquet")

        em = (g.groupby(["subscriber_key", "account_ref", "month_idx"])
                .agg(streamed_hours=("streamed_minutes", lambda s: s.sum() / 60.0),
                     active_days=("local_date", "nunique"),
                     distinct_titles=("distinct_titles", "sum"),
                     playback_errors=("playback_errors", "sum"),
                     video_start_failures=("video_start_failures", "sum"))
                .reset_index())
        ctv_days = (g[g["device_family"].isin(C.CTV_FAMILIES)]
                    .groupby(["subscriber_key"])["local_date"].nunique().rename("ctv_days"))
        em = em.join(ctv_days, on="subscriber_key")
        em["ctv_days"] = em["ctv_days"].fillna(0)
        em["pct_days_ctv"] = (em["ctv_days"] / em["active_days"].clip(lower=1)).round(3)
        em["below_healthy_engagement"] = em["streamed_hours"] < C.HEALTHY_ENGAGEMENT_HOURS
        eng_rows.append(em)
        progress(f"curated: viewing {month_label(idx)}  ({len(g):,} daily rows)")
    eng = pd.concat(eng_rows, ignore_index=True)
    eng["date_key"] = eng["month_idx"].map(lambda i: int(pd.Timestamp(month_end(int(i))).strftime("%Y%m%d")))
    _save(eng, "fact_engagement_month")
    progress(f"curated: fact_engagement_month ({len(eng):,})")

    dmf = pd.concat(dm_rows, ignore_index=True)
    dmf = (dmf.groupby(["market", "device_family", "device_key", "month_idx"], as_index=False)
              .agg(streamed_hours=("streamed_hours", "sum"), play_starts=("play_starts", "sum"),
                   video_start_failures=("video_start_failures", "sum"),
                   playback_errors=("playback_errors", "sum"),
                   rebuffer_ratio=("rebuffer_ratio", "mean"), cdn_gb=("cdn_gb", "sum"),
                   viewing_subs=("viewing_subs", "sum")))
    mk = pd.read_parquet(C.CURATED / "dim_market.parquet").set_index("market_id")["market_key"]
    dmf["market_key"] = dmf["market"].map(mk).fillna(0).astype(int)
    dmf["vsf_rate"] = (dmf["video_start_failures"] / dmf["play_starts"].clip(lower=1)).round(5)
    dmf["playback_error_rate"] = (dmf["playback_errors"] / dmf["play_starts"].clip(lower=1)).round(5)
    dmf["date_key"] = dmf["month_idx"].map(lambda i: int(pd.Timestamp(month_end(int(i))).strftime("%Y%m%d")))
    _save(dmf, "fact_engagement_device_month")
    progress(f"curated: fact_engagement_device_month ({len(dmf):,})")


def fact_app_performance_daily(sub_df, device_map):
    parts = sorted((C.STAGING / "stg_trackpad_app_events").glob("*.parquet"))
    smap = dict(zip(sub_df["subscriber_id"], sub_df["subscriber_key"]))
    mktmap = dict(zip(sub_df["subscriber_id"], sub_df["market"]))
    out = []
    versions = set()
    for f in parts:
        a = pd.read_parquet(f)
        a["market"] = a["user_ref"].map(mktmap).fillna("BR")
        a["device_key"] = a["device_family"].map(device_map).fillna(device_map["unknown"]).astype(int)
        versions |= set(a["app_version"].dropna().unique())
        g = (a.groupby(["market", "local_date", "device_family", "device_key", "app_version", "month_idx"])
               .agg(sessions=("session_count", "sum"), crashes=("crash_count", "sum"),
                    screen_views=("screen_views", "sum"))
               .reset_index())
        g["crash_free_rate"] = 1.0 - (g["crashes"] / g["sessions"].clip(lower=1))
        g["date_key"] = pd.to_datetime(g["local_date"]).dt.strftime("%Y%m%d").astype(int)
        out.append(g)
    perf = pd.concat(out, ignore_index=True)
    _save(perf, "fact_app_performance_daily")

    dv = pd.DataFrame({"app_version": sorted(versions)})
    dv.insert(0, "app_version_key", range(1, len(dv) + 1))
    dv["major"] = dv["app_version"].str.split(".").str[0].astype(int)
    dv["is_v3"] = dv["major"] >= 3
    dv["device_class_hint"] = "all"
    _save(dv, "dim_app_version")
    progress(f"curated: fact_app_performance_daily ({len(perf):,})")


# =========================================================================
def fact_marketing_and_ads(market_key, channel_map):
    sw = pd.read_parquet(C.STAGING / "stg_adbridge_spend_weekly.parquet").copy()
    sw = sw[~sw["is_test_campaign"]].copy()
    _c("test_campaign_rows_excluded", int(pd.read_parquet(C.STAGING / "stg_adbridge_spend_weekly.parquet")["is_test_campaign"].sum()))
    sw["market_key"] = sw["market"].map(market_key).fillna(0).astype(int)
    sw["channel_key"] = sw["channel"].map(channel_map).fillna(channel_map["unknown"]).astype(int)
    sw["week_date_key"] = pd.to_datetime(sw["week_start"], errors="coerce").dt.strftime("%Y%m%d")
    sw["week_date_key"] = pd.to_numeric(sw["week_date_key"], errors="coerce").fillna(-1).astype(int)
    sw["month_idx"] = pd.to_datetime(sw["week_start"], errors="coerce").apply(
        lambda d: (d.year - month_start(0).year) * 12 + d.month - month_start(0).month if pd.notna(d) else -1)
    _save(sw[["week_date_key", "month_idx", "market", "market_key", "channel", "channel_key",
              "campaign_id", "spend_usd", "spend_local", "impressions", "clicks", "signups_attributed"]],
          "fact_marketing_spend")

    ssp = pd.read_parquet(C.STAGING / "stg_voxaads_ssp_daily_revenue.parquet").copy()
    ssp["market_key"] = ssp["market"].map(market_key).fillna(0).astype(int)
    ssp["date_key"] = pd.to_datetime(ssp["date"], errors="coerce").dt.strftime("%Y%m%d")
    ssp["date_key"] = pd.to_numeric(ssp["date_key"], errors="coerce").fillna(-1).astype(int)
    ssp["month_idx"] = pd.to_datetime(ssp["date"], errors="coerce").apply(
        lambda d: (d.year - month_start(0).year) * 12 + d.month - month_start(0).month if pd.notna(d) else -1)
    _save(ssp[["date_key", "month_idx", "market", "market_key", "impressions_served",
               "fill_rate", "ecpm_usd", "ad_revenue_usd"]], "fact_ad_revenue")
    progress("curated: marketing + ads")


def fact_content_cost(content_map):
    am = pd.read_parquet(C.STAGING / "stg_contentfin_amort_schedule.parquet").copy()
    am["content_key"] = am["content_id"].map(content_map).fillna(-1).astype(int)
    cm = pd.read_parquet(C.STAGING / "stg_contentfin_cash_milestones.parquet").copy()
    cm["content_key"] = cm["content_id"].map(content_map).fillna(-1).astype(int)
    cm["month_idx"] = pd.to_datetime(cm["milestone_date"], errors="coerce").apply(
        lambda d: (d.year - month_start(0).year) * 12 + d.month - month_start(0).month if pd.notna(d) else -1)
    cash = cm.groupby(["content_key", "month_idx"])["amount_usd"].sum().rename("cash_spend_usd").reset_index()
    out = am.groupby(["content_key", "month_idx"])["amort_usd"].sum().reset_index()
    out = out.merge(cash, on=["content_key", "month_idx"], how="left")
    out["cash_spend_usd"] = out["cash_spend_usd"].fillna(0.0)
    out = out[(out["month_idx"] >= 0) & (out["month_idx"] < C.N_MONTHS)]
    out["date_key"] = out["month_idx"].map(lambda i: int(pd.Timestamp(month_end(int(i))).strftime("%Y%m%d")))
    _save(out, "fact_content_cost")
    progress("curated: fact_content_cost")


def fact_support(sub_df, reason_map):
    s = pd.read_parquet(C.STAGING / "stg_support_tickets.parquet").copy()
    smap = dict(zip(sub_df["subscriber_id"], sub_df["subscriber_key"]))
    mktmap = dict(zip(sub_df["subscriber_id"], sub_df["market"]))
    s["subscriber_key"] = s["account_id"].map(smap).fillna(-1).astype(int)
    s["market"] = s["account_id"].map(mktmap)
    s["support_reason_key"] = s["reason_category"].map(reason_map).fillna(0).astype(int)
    s["created_date_key"] = pd.to_datetime(s["created_ts"], errors="coerce").dt.strftime("%Y%m%d")
    s["created_date_key"] = pd.to_numeric(s["created_date_key"], errors="coerce").fillna(-1).astype(int)
    _save(s[["ticket_id", "subscriber_key", "market", "month_idx", "created_date_key",
             "contact_channel", "reason_category", "reason_group", "support_reason_key",
             "csat_score", "resolution_hours", "source_version"]], "fact_support_ticket")
    progress("curated: fact_support_ticket")


def fact_fx_and_finance(market_key):
    fx = pd.read_parquet(C.STAGING / "stg_ledger_fx.parquet").copy()
    fx["date_key"] = fx["month_idx"].map(lambda i: int(pd.Timestamp(month_end(int(i))).strftime("%Y%m%d")))
    _save(fx, "fact_fx_rate")
    gl = pd.read_parquet(C.STAGING / "stg_ledger_gl.parquet").copy()
    gl["market_key"] = gl["market"].map(market_key).fillna(0).astype(int)
    gl["date_key"] = gl["month_idx"].map(lambda i: int(pd.Timestamp(month_end(int(i))).strftime("%Y%m%d")))
    _save(gl, "fact_finance_month")
    progress("curated: fx + finance")


def fact_targets(market_key):
    """Plan = PY actual x (1+growth), local then FX-converted; flat target churn."""
    sm = pd.read_parquet(C.CURATED / "fact_subscription_month.parquet")
    act = sm[sm["status"] == "active"]
    base = act.groupby(["market", "month_idx"]).agg(
        active=("subscriber_key", "nunique"), mrr_usd=("mrr_usd", "sum")).reset_index()
    rows = []
    for mk in C.MARKETS:
        g = base[base["market"] == mk].set_index("month_idx")
        for idx in range(C.N_MONTHS):
            py = idx - 12
            if py in g.index:
                grow = {"BR": 1.06, "MX": 1.14, "US": 1.10}[mk] ** (1 / 12)
                tgt_active = g.loc[py, "active"] * grow ** 12
                tgt_mrr = g.loc[py, "mrr_usd"] * grow ** 12
            else:
                tgt_active = g.loc[idx, "active"] * 1.05 if idx in g.index else np.nan
                tgt_mrr = g.loc[idx, "mrr_usd"] * 1.05 if idx in g.index else np.nan
            rows.append({"market": mk, "market_key": market_key[mk], "month_idx": idx,
                         "kpi": "paid_active_subscribers", "target_value": round(float(tgt_active), 1) if pd.notna(tgt_active) else None})
            rows.append({"market": mk, "market_key": market_key[mk], "month_idx": idx,
                         "kpi": "mrr_usd", "target_value": round(float(tgt_mrr), 2) if pd.notna(tgt_mrr) else None})
            rows.append({"market": mk, "market_key": market_key[mk], "month_idx": idx,
                         "kpi": "gross_monthly_churn_pct", "target_value": 4.0})
            rows.append({"market": mk, "market_key": market_key[mk], "month_idx": idx,
                         "kpi": "involuntary_churn_pct", "target_value": 1.0})
    t = pd.DataFrame(rows)
    t["date_key"] = t["month_idx"].map(lambda i: int(pd.Timestamp(month_end(int(i))).strftime("%Y%m%d")))
    _save(t, "fact_targets_month")
    progress("curated: fact_targets_month")


# =========================================================================
def main():
    t0 = _dt.datetime.now()
    for p in list(C.CURATED.glob("*.parquet")) + list(C.CURATED.glob("*.csv")):
        p.unlink()
    progress("CURATED build")
    dim_date()
    mkey = dim_market()
    chmap = dim_channel()
    dvmap = dim_device()
    mmap = dim_payment_method()
    plan_map = dim_plan_and_price(mkey)
    cmap = dim_content()
    rmap = dim_support_reason()

    sub_df = dim_subscriber(mkey, chmap)
    ev = fact_subscription_event(sub_df, mkey)
    fact_subscription_month(sub_df, ev)
    fact_billing_attempt(sub_df, mmap)
    fact_viewing_and_engagement(sub_df, cmap, dvmap)
    fact_app_performance_daily(sub_df, dvmap)
    fact_marketing_and_ads(mkey, chmap)
    fact_content_cost(cmap)
    fact_support(sub_df, rmap)
    fact_fx_and_finance(mkey)
    fact_targets(mkey)

    dq_fragment("curated_build", CNT)
    progress(f"CURATED done in {(_dt.datetime.now()-t0).total_seconds():.0f}s")
    print(json.dumps(CNT, indent=2))


if __name__ == "__main__":
    main()
