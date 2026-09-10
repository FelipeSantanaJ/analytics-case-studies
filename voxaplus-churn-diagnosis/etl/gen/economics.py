"""Clean FX, marketing spend, ad revenue, support tickets, and a GL roll-up."""
from __future__ import annotations

import numpy as np
import pandas as pd

import config as C
from utils import rng, month_start, month_end, progress


# --------------------------------------------------------------------------
def build_fx() -> pd.DataFrame:
    rows = []
    for cur, p in C.FX.items():
        r = rng("econ", "fx", cur)
        lvl = p["start"]
        for idx in range(C.N_MONTHS):
            lvl = lvl + p["drift_per_month"] + r.normal(0, p["vol"])
            lvl = float(np.clip(lvl, p["lo"], p["hi"]))
            eop = float(np.clip(lvl + r.normal(0, p["vol"] * 0.5), p["lo"], p["hi"]))
            rows.append({"month_idx": idx, "currency": cur, "avg_rate": round(lvl, 4),
                         "eop_rate": round(eop, 4)})
    return pd.DataFrame(rows)


# --------------------------------------------------------------------------
def build_marketing(world: dict) -> dict:
    subs = world["subscribers"]
    r = rng("econ", "marketing")
    # sign-ups by month x market x channel x campaign
    g = (subs.groupby(["signup_idx", "market", "channel", "campaign_id"])
             .size().reset_index(name="signups"))
    rows, attr_rows = [], []
    for _, x in g.iterrows():
        idx, mk, ch, cmp_id, s = x["signup_idx"], x["market"], x["channel"], x["campaign_id"], x["signups"]
        cac = C.CAC_USD[ch] * float(r.uniform(0.8, 1.25))
        spend_usd = cac * s
        # test campaign with zero spend / inflated signups (DQ outlier)
        is_test = (ch == "paid_social" and idx == C.CHANNEL_SHIFT_IDX and mk == "BR"
                   and r.random() < 0.15)
        cpm = {"paid_search": 9, "paid_social": 5, "affiliate": 4,
               "partner_bundle": 2, "direct": 3, "organic": 1}[ch]
        impressions = int(spend_usd / cpm * 1000) if cpm else 0
        ctr = float(r.uniform(0.008, 0.03))
        clicks = int(impressions * ctr)
        d0 = pd.Timestamp(month_start(int(idx)))
        for wk in range(4):
            wd = d0 + pd.Timedelta(days=wk * 7)
            frac = [0.28, 0.26, 0.24, 0.22][wk]
            rows.append({
                "week_start": wd.date(), "month_idx": int(idx), "market": mk, "channel": ch,
                "campaign_id": cmp_id,
                "spend_usd": 0.0 if is_test else round(spend_usd * frac, 2),
                "spend_local": 0.0 if is_test else round(spend_usd * frac, 2),  # filled per-currency in messify
                "impressions": int(impressions * frac),
                "clicks": int(clicks * frac),
                "signups_attributed": 0,
                "is_test_campaign": bool(is_test),
            })
        # split the campaign's signups across its 4 weeks for attribution
        for _ in range(int(s)):
            attr_rows.append({"market": mk, "channel": ch, "campaign_id": cmp_id,
                              "signup_idx": int(idx)})
    spend_df = pd.DataFrame(rows)
    # distribute attributed signups back to weeks proportionally
    wk_counts = spend_df.groupby(["month_idx", "market", "channel", "campaign_id"]).cumcount()
    spend_df["signups_attributed"] = (
        spend_df.groupby(["month_idx", "market", "channel", "campaign_id"])["impressions"]
        .transform(lambda s: s))  # placeholder; real split below
    # simple even split
    tot = g.set_index(["signup_idx", "market", "channel", "campaign_id"])["signups"].to_dict()
    def _split(row):
        key = (row["month_idx"], row["market"], row["channel"], row["campaign_id"])
        return int(round(tot.get(key, 0) / 4.0))
    spend_df["signups_attributed"] = spend_df.apply(_split, axis=1)

    attr_df = pd.DataFrame(attr_rows)
    # ~7% of signups get no attribution row (become 'unknown' channel downstream)
    drop = attr_df.sample(frac=0.07, random_state=C.SEED % 7919).index
    attr_df = attr_df.drop(index=drop).reset_index(drop=True)
    return {"spend_weekly": spend_df, "attribution": attr_df}


# --------------------------------------------------------------------------
def build_ad_revenue(world: dict) -> pd.DataFrame:
    sm = world["subscription_month"]
    r = rng("econ", "ads")
    basico = sm[(sm["tier"] == "Basico") & (sm["status"] == "active")]
    hrs = basico.groupby("month_idx")["streamed_hours"].sum().reset_index()
    subs = world["subscribers"].set_index("subscriber_id")
    basico2 = basico.join(subs["market"], on="subscriber_id")
    by_mk = basico2.groupby(["month_idx", "market"])["streamed_hours"].sum().reset_index()
    rows = []
    for _, x in by_mk.iterrows():
        idx, mk, h = int(x["month_idx"]), x["market"], x["streamed_hours"]
        d0, d1 = month_start(idx), month_end(idx)
        for day in pd.date_range(d0, d1):
            day_h = h / ((d1 - d0).days + 1) * float(r.uniform(0.8, 1.2))
            ads_per_hour = 8.0
            impressions = int(day_h * ads_per_hour)
            fill = float(np.clip(r.normal(0.82 + (0.05 if idx >= 17 else 0), 0.05), 0.55, 0.98))
            ecpm = float(np.clip(r.normal(9.5 + (1.5 if idx >= 17 else 0), 1.2), 4, 16))
            rev = impressions * fill * ecpm / 1000.0
            rows.append({"date": day.date(), "market": mk,
                         "impressions_served": int(impressions * fill),
                         "fill_rate": round(fill, 3), "ecpm_usd": round(ecpm, 2),
                         "ad_revenue_usd": round(rev, 2)})
    return pd.DataFrame(rows)


# --------------------------------------------------------------------------
def build_support(world: dict) -> pd.DataFrame:
    sm = world["subscription_month"]
    subs = world["subscribers"].set_index("subscriber_id")
    bill = world["billing_attempts"]
    r = rng("econ", "support")
    fails = bill[bill["status"] == "failed"].groupby(["subscriber_id", "month_idx"]).size()
    rows = []
    base_per_1000 = C.SUPPORT_CONTACTS_PER_1000_BASE
    active = sm[sm["status"] == "active"]
    by_mk_idx = active.groupby(["month_idx"]).size()
    reasons = list(C.SUPPORT_REASON_MIX)
    rp = np.array([C.SUPPORT_REASON_MIX[k] for k in reasons])
    for idx, cnt in by_mk_idx.items():
        n_tickets = int(cnt / 1000.0 * base_per_1000 * float(r.uniform(0.9, 1.15)))
        # CTV playback complaints rise after v3 CTV rollout
        ctv_v3 = idx >= min(C.APP_V3_ROLLOUT_IDX[f] for f in C.CTV_FAMILIES)
        rp_i = rp.copy()
        if ctv_v3:
            rp_i[reasons.index("app_playback")] *= 1.7
            rp_i[reasons.index("app_crash")] *= 1.4
            rp_i = rp_i / rp_i.sum()
            n_tickets = int(n_tickets * 1.18)
        pool = active[active["month_idx"] == idx]["subscriber_id"].to_numpy()
        if len(pool) == 0:
            continue
        picks = r.choice(pool, size=min(n_tickets, len(pool) * 2))
        for sidv in picks:
            rc = str(r.choice(reasons, p=rp_i))
            d = month_start(idx) + pd.Timedelta(days=int(r.integers(0, 27)),
                                                hours=int(r.integers(0, 24)))
            ver = "v1" if idx < C.SUPPORT_MIGRATION_IDX else "v2"
            csat = float(np.clip(r.normal(C.CSAT_MEAN_V1 if ver == "v1" else C.CSAT_MEAN_V2, 0.8), 1, 5))
            rows.append({
                "ticket_id": f"{ver}-{idx}-{r.integers(1, 10**8)}",
                "subscriber_id": sidv, "created_month_idx": int(idx),
                "created_ts": d.isoformat(), "contact_channel": str(r.choice(["chat", "email", "phone"], p=[0.55, 0.32, 0.13])),
                "reason_category": rc,
                "resolution_hours": round(float(np.clip(r.lognormal(1.6, 0.9), 0.2, 220)), 2),
                "csat_1_5": round(csat, 1), "source_version": ver,
                "is_reopened": bool(r.random() < 0.08),
            })
    return pd.DataFrame(rows)


# --------------------------------------------------------------------------
def build_gl(world: dict, content: dict, ads: pd.DataFrame, marketing: dict,
             support: pd.DataFrame, fx: pd.DataFrame) -> pd.DataFrame:
    """Monthly P&L by market x line, in USD (ties to operational aggregates)."""
    sm = world["subscription_month"]
    subs = world["subscribers"].set_index("subscriber_id")
    fxm = fx.set_index(["month_idx", "currency"])["avg_rate"].to_dict()
    smj = sm.join(subs["market"], on="subscriber_id")
    smj = smj[smj["status"] == "active"].copy()
    smj["cur"] = smj["market"].map({k: v["currency"] for k, v in C.MARKETS.items()})
    smj["rate"] = [fxm.get((i, c), 1.0) for i, c in zip(smj["month_idx"], smj["cur"])]
    smj["mrr_usd"] = smj["mrr_local"] / smj["rate"]
    sub_rev = smj.groupby(["month_idx", "market"])["mrr_usd"].sum().reset_index(name="amount_usd")
    sub_rev["pnl_line"] = "revenue_subscription"

    ad_rev = ads.copy()
    ad_rev["month_idx"] = ((pd.to_datetime(ad_rev["date"]).dt.year - month_start(0).year) * 12
                           + pd.to_datetime(ad_rev["date"]).dt.month - month_start(0).month)
    ad_rev = ad_rev.groupby(["month_idx", "market"])["ad_revenue_usd"].sum().reset_index(name="amount_usd")
    ad_rev["pnl_line"] = "revenue_advertising"

    partner = sub_rev.copy()
    partner["amount_usd"] = partner["amount_usd"] * 0.045
    partner["pnl_line"] = "revenue_partner"

    # costs
    hrs = smj.groupby(["month_idx", "market"])["streamed_hours"].sum().reset_index()
    cdn = hrs.copy()
    cdn["amount_usd"] = -(cdn["streamed_hours"] * 0.018)
    cdn["pnl_line"] = "cost_cdn"
    cdn = cdn.drop(columns="streamed_hours")

    bill = world["billing_attempts"]
    bj = bill[bill["status"] == "approved"].join(subs["market"], on="subscriber_id")
    bj["cur"] = bj["market"].map({k: v["currency"] for k, v in C.MARKETS.items()})
    bj["rate"] = [fxm.get((i, c), 1.0) for i, c in zip(bj["month_idx"], bj["cur"])]
    bj["fee_usd"] = [(-(a / rt) * C.PROC_COST[m]["pct"] - C.PROC_COST[m]["fixed"] / rt)
                     for a, rt, m in zip(bj["amount_local"], bj["rate"], bj["method"])]
    pay_cost = bj.groupby(["month_idx", "market"])["fee_usd"].sum().reset_index(name="amount_usd")
    pay_cost["pnl_line"] = "cost_payment"

    cc = content["content_cost_month"].groupby("month_idx")["amort_usd"].sum().reset_index()
    cc_rows = []
    mkt_w = {"BR": 0.55, "MX": 0.28, "US": 0.17}
    for _, x in cc.iterrows():
        for mk, w in mkt_w.items():
            cc_rows.append({"month_idx": int(x["month_idx"]), "market": mk,
                            "amount_usd": -x["amort_usd"] * w, "pnl_line": "cost_content_amort"})
    cc_df = pd.DataFrame(cc_rows)

    mk = marketing["spend_weekly"].groupby(["month_idx", "market"])["spend_usd"].sum().reset_index()
    mk["amount_usd"] = -mk["spend_usd"]
    mk["pnl_line"] = "cost_marketing"
    mk = mk.drop(columns="spend_usd")

    sp = support.copy()
    sp["amount_usd"] = -6.5
    sp = sp.join(subs["market"], on="subscriber_id")
    sp = sp.groupby(["created_month_idx", "market"])["amount_usd"].sum().reset_index()
    sp = sp.rename(columns={"created_month_idx": "month_idx"})
    sp["pnl_line"] = "cost_support"

    ga = sub_rev.copy()
    ga["amount_usd"] = -(ga["amount_usd"] * 0.16)
    ga["pnl_line"] = "cost_g_and_a"

    out = pd.concat([sub_rev, ad_rev, partner, cdn, pay_cost, cc_df, mk, sp, ga],
                    ignore_index=True)
    out["amount_usd"] = out["amount_usd"].round(2)
    return out[["month_idx", "market", "pnl_line", "amount_usd"]]
