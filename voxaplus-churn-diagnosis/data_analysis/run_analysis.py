"""
run_analysis.py — the Voxa+ churn diagnosis, computed twice (DuckDB SQL + pandas)
with a parity check on every result.

    python data_analysis/run_analysis.py

Writes results/qNN_*.csv and parity/parity_report.md. Reads only ../data/curated/.
"""
from __future__ import annotations
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from lib.io import (con, load, sm_py, PRE, PEAK, SHIFT_IDX, CHANNEL_SHIFT_IDX,
                    BR_PRICE_HIKE_IDX, APP_V3_CTV_IDX)
from lib import parity

RES = HERE / "results"
SQLDIR = HERE / "sql"
RES.mkdir(exist_ok=True)
SQLDIR.mkdir(exist_ok=True)
C = con()


def _sql(name: str, q: str) -> pd.DataFrame:
    (SQLDIR / f"{name}.sql").write_text(q.strip() + "\n", encoding="utf-8")
    return C.execute(q).df()


def save(name: str, df: pd.DataFrame):
    df.to_csv(RES / f"{name}.csv", index=False)


# =====================================================================
# Q1 — how large is the spike, and is it still going?
# =====================================================================
def q1():
    q = """
    WITH m AS (
      SELECT month_idx,
             COUNT(*) FILTER (WHERE status='active')                         AS active,
             SUM(CASE WHEN is_voluntary_churn   THEN 1 ELSE 0 END)           AS vol,
             SUM(CASE WHEN is_involuntary_churn THEN 1 ELSE 0 END)           AS invol
      FROM fact_subscription_month GROUP BY 1),
    w AS (
      SELECT *, LAG(active) OVER (ORDER BY month_idx) AS start_active FROM m)
    SELECT month_idx, active, vol, invol, start_active,
           ROUND((vol+invol)::DOUBLE / start_active, 5) AS gross_churn,
           ROUND(vol::DOUBLE   / start_active, 5)       AS vol_churn,
           ROUND(invol::DOUBLE / start_active, 5)       AS invol_churn
    FROM w WHERE month_idx BETWEEN 12 AND 35 ORDER BY month_idx
    """
    s = _sql("q1_churn_trend", q)

    f = load("fact_subscription_month")
    g = f.groupby("month_idx").agg(
        active=("status", lambda x: (x == "active").sum()),
        vol=("is_voluntary_churn", "sum"), invol=("is_involuntary_churn", "sum")).reset_index()
    g["start_active"] = g["active"].shift(1)
    g["gross_churn"] = ((g.vol + g.invol) / g.start_active).round(5)
    g["vol_churn"] = (g.vol / g.start_active).round(5)
    g["invol_churn"] = (g.invol / g.start_active).round(5)
    p = g[g.month_idx.between(12, 35)][s.columns.tolist()].reset_index(drop=True)

    r = parity.assert_parity("Q1 churn trend", s, p, ["month_idx"])
    save("q1_churn_trend", r)
    pre = r[r.month_idx.between(*PRE)].gross_churn.mean()
    peak = r[r.month_idx.between(*PEAK)].gross_churn.mean()
    summary = pd.DataFrame([{
        "pre_shift_gross_churn": round(pre, 4),
        "peak_gross_churn": round(peak, 4),
        "ratio": round(peak / pre, 2),
        "peak_vol_share": round(r[r.month_idx.between(*PEAK)].vol.sum()
                               / r[r.month_idx.between(*PEAK)][["vol", "invol"]].sum().sum(), 3),
        "m33": r.set_index("month_idx").loc[33, "gross_churn"],
        "m34": r.set_index("month_idx").loc[34, "gross_churn"],
        "m35": r.set_index("month_idx").loc[35, "gross_churn"],
    }])
    save("q1_summary", summary)
    return summary


# =====================================================================
# Q2 — global or one market?
# =====================================================================
def q2():
    q = """
    WITH m AS (
      SELECT sub_market AS market, month_idx,
             COUNT(*) FILTER (WHERE status='active')                    AS active,
             SUM(CASE WHEN is_voluntary_churn OR is_involuntary_churn THEN 1 ELSE 0 END) AS churned
      FROM sm GROUP BY 1,2),
    w AS (SELECT *, LAG(active) OVER (PARTITION BY market ORDER BY month_idx) AS start_active FROM m)
    SELECT market, month_idx, ROUND(churned::DOUBLE / start_active, 5) AS gross_churn
    FROM w WHERE month_idx BETWEEN 20 AND 35 ORDER BY market, month_idx
    """
    s = _sql("q2_churn_by_market", q)

    sm = sm_py()
    g = sm.groupby(["sub_market", "month_idx"]).agg(
        active=("status", lambda x: (x == "active").sum()),
        churned=("is_voluntary_churn", "sum")).reset_index()
    g["churned"] = (sm.groupby(["sub_market", "month_idx"])[["is_voluntary_churn", "is_involuntary_churn"]]
                    .sum().sum(axis=1).values)
    g["start"] = g.groupby("sub_market")["active"].shift(1)
    g["gross_churn"] = (g.churned / g.start).round(5)
    p = (g[g.month_idx.between(20, 35)].rename(columns={"sub_market": "market"})
         [["market", "month_idx", "gross_churn"]].reset_index(drop=True))

    r = parity.assert_parity("Q2 churn by market", s, p, ["market", "month_idx"])
    save("q2_churn_by_market", r)
    piv = r.pivot(index="month_idx", columns="market", values="gross_churn")
    out = pd.DataFrame([{
        "market": mk,
        "pre_shift": round(piv.loc[PRE[0]:PRE[1], mk].mean(), 4),
        "peak": round(piv.loc[PEAK[0]:PEAK[1], mk].mean(), 4),
        "m28_to_m32_drift": round(piv.loc[28:32, mk].mean() - piv.loc[24:27, mk].mean(), 4),
        "step_m32_to_m33": round(piv.loc[33, mk] - piv.loc[32, mk], 4),
    } for mk in ["BR", "MX", "US"]])
    save("q2_market_summary", out)
    return out


# =====================================================================
# Q3 — cohorts / tenure / tier / channel
# =====================================================================
def q3():
    cuts = {
        "tier": "sub_current_tier",
        "tenure_band": "CASE WHEN tenure_months<=1 THEN '0-1' WHEN tenure_months<=6 THEN '2-6' "
                       "WHEN tenure_months<=12 THEN '7-12' WHEN tenure_months<=24 THEN '13-24' "
                       "ELSE '25+' END",
        "channel": "acquisition_channel",
        "billing": "sub_billing",
    }
    frames = []
    for label, expr in cuts.items():
        q = f"""
        WITH m AS (
          SELECT {expr} AS grp, month_idx,
                 COUNT(*) FILTER (WHERE status='active') AS active,
                 SUM(CASE WHEN is_voluntary_churn OR is_involuntary_churn THEN 1 ELSE 0 END) AS churned
          FROM sm GROUP BY 1,2),
        r AS (SELECT grp, month_idx,
                     churned::DOUBLE / LAG(active) OVER (PARTITION BY grp ORDER BY month_idx) AS gc
              FROM m)
        SELECT '{label}' AS cut, grp,
               ROUND(AVG(gc) FILTER (WHERE month_idx BETWEEN {PRE[0]} AND {PRE[1]}), 5) AS pre_shift,
               ROUND(AVG(gc) FILTER (WHERE month_idx BETWEEN {PEAK[0]} AND {PEAK[1]}), 5) AS peak
        FROM r GROUP BY 1,2
        """
        frames.append(_sql(f"q3_{label}", q))
    s = pd.concat(frames, ignore_index=True)

    sm = sm_py()
    sm["tenure_band"] = pd.cut(sm.tenure_months, [-1, 1, 6, 12, 24, 999],
                               labels=["0-1", "2-6", "7-12", "13-24", "25+"]).astype(str)
    pcuts = {"tier": "current_tier", "tenure_band": "tenure_band",
             "channel": "acquisition_channel", "billing": "billing_period"}
    prows = []
    for label, col in pcuts.items():
        g = sm.groupby([col, "month_idx"]).agg(
            active=("status", lambda x: (x == "active").sum())).reset_index()
        g["churned"] = (sm.groupby([col, "month_idx"])[["is_voluntary_churn", "is_involuntary_churn"]]
                        .sum().sum(axis=1).values)
        g["start"] = g.groupby(col)["active"].shift(1)
        g["gc"] = g.churned / g.start
        for grp, gg in g.groupby(col):
            prows.append({"cut": label, "grp": str(grp),
                          "pre_shift": round(gg[gg.month_idx.between(*PRE)].gc.mean(), 5),
                          "peak": round(gg[gg.month_idx.between(*PEAK)].gc.mean(), 5)})
    p = pd.DataFrame(prows)

    r = parity.assert_parity("Q3 cohort cuts", s, p, ["cut", "grp"])
    r["delta_pp"] = (r.peak - r.pre_shift).round(4)
    save("q3_cohort_cuts", r.sort_values(["cut", "delta_pp"], ascending=[True, False]))
    return r


# =====================================================================
# Q4 — did engagement drop before cancellation?
# =====================================================================
def q4():
    q = """
    WITH e AS (SELECT subscriber_key, month_idx, streamed_hours, below_healthy_engagement
               FROM fact_engagement_month),
    churn AS (SELECT subscriber_key, month_idx AS cm
              FROM fact_subscription_month WHERE is_voluntary_churn),
    j AS (
      SELECT c.cm,
             MAX(CASE WHEN e.month_idx = c.cm     THEN e.streamed_hours END) AS h_m0,
             MAX(CASE WHEN e.month_idx = c.cm - 1 THEN e.streamed_hours END) AS h_m1,
             MAX(CASE WHEN e.month_idx = c.cm - 2 THEN e.streamed_hours END) AS h_m2,
             MAX(CASE WHEN e.month_idx = c.cm - 1 THEN e.below_healthy_engagement::INT END) AS bh_m1
      FROM churn c LEFT JOIN e ON e.subscriber_key = c.subscriber_key
      GROUP BY c.subscriber_key, c.cm)
    SELECT CASE WHEN cm BETWEEN 24 AND 32 THEN 'pre_shift'
                WHEN cm BETWEEN 33 AND 35 THEN 'peak' ELSE 'other' END AS period,
           COUNT(*)                          AS churners,
           ROUND(AVG(h_m2), 2)               AS avg_hours_m_minus_2,
           ROUND(AVG(h_m1), 2)               AS avg_hours_m_minus_1,
           ROUND(AVG(h_m0), 2)               AS avg_hours_m0,
           ROUND(AVG(bh_m1), 3)              AS share_below_healthy_prior_month
    FROM j WHERE cm BETWEEN 24 AND 35 GROUP BY 1 ORDER BY 1
    """
    s = _sql("q4_engagement_before_churn", q)

    e = load("fact_engagement_month")[["subscriber_key", "month_idx", "streamed_hours",
                                       "below_healthy_engagement"]]
    ch = load("fact_subscription_month")
    ch = ch[ch.is_voluntary_churn][["subscriber_key", "month_idx"]].rename(columns={"month_idx": "cm"})
    j = ch.copy()
    for k, col in [(0, "h_m0"), (-1, "h_m1"), (-2, "h_m2")]:
        et = e[["subscriber_key", "month_idx", "streamed_hours"]].copy()
        et["cm"] = et.month_idx - k
        j = j.merge(et[["subscriber_key", "cm", "streamed_hours"]].rename(columns={"streamed_hours": col}),
                    on=["subscriber_key", "cm"], how="left")
    eb = e[["subscriber_key", "month_idx", "below_healthy_engagement"]].copy()
    eb["cm"] = eb.month_idx + 1
    j = j.merge(eb[["subscriber_key", "cm", "below_healthy_engagement"]]
                .rename(columns={"below_healthy_engagement": "bh_m1"}),
                on=["subscriber_key", "cm"], how="left")
    j["bh_m1"] = j.bh_m1.astype("float")
    j["period"] = np.select([j.cm.between(24, 32), j.cm.between(33, 35)],
                            ["pre_shift", "peak"], "other")
    p = (j[j.cm.between(24, 35)].groupby("period")
         .agg(churners=("cm", "size"),
              avg_hours_m_minus_2=("h_m2", "mean"), avg_hours_m_minus_1=("h_m1", "mean"),
              avg_hours_m0=("h_m0", "mean"),
              share_below_healthy_prior_month=("bh_m1", "mean")).reset_index())
    for c in ["avg_hours_m_minus_2", "avg_hours_m_minus_1", "avg_hours_m0"]:
        p[c] = p[c].round(2)
    p["share_below_healthy_prior_month"] = p.share_below_healthy_prior_month.round(3)
    p = p[s.columns.tolist()]

    r = parity.assert_parity("Q4 engagement before churn", s, p, ["period"])
    save("q4_engagement_before_churn", r)
    return r


# =====================================================================
# Q5 — device / app-quality signal  (F1)
# =====================================================================
def q5():
    q = f"""
    SELECT d.device_class, e.month_idx,
           ROUND(SUM(e.video_start_failures)::DOUBLE / NULLIF(SUM(e.play_starts),0), 5) AS vsf_rate,
           ROUND(SUM(e.playback_errors)::DOUBLE     / NULLIF(SUM(e.play_starts),0), 5) AS pberr_rate
    FROM fact_engagement_device_month e JOIN dim_device d USING (device_key)
    WHERE e.month_idx BETWEEN 26 AND 35
    GROUP BY 1,2 ORDER BY 1,2
    """
    s = _sql("q5_qoe_by_device", q)

    e = load("fact_engagement_device_month")
    d = load("dim_device")[["device_key", "device_class"]]
    m = e.merge(d, on="device_key")
    g = (m[m.month_idx.between(26, 35)].groupby(["device_class", "month_idx"])
         .agg(vsf=("video_start_failures", "sum"), pb=("playback_errors", "sum"),
              ps=("play_starts", "sum")).reset_index())
    g["vsf_rate"] = (g.vsf / g.ps).round(5)
    g["pberr_rate"] = (g.pb / g.ps).round(5)
    p = g[["device_class", "month_idx", "vsf_rate", "pberr_rate"]].reset_index(drop=True)
    r = parity.assert_parity("Q5 QoE by device", s, p, ["device_class", "month_idx"])
    save("q5_qoe_by_device", r)

    # churn of CTV-heavy vs rest, pre vs peak  (CTV-heavy = >=35% of viewing days on CTV,
    # proxied by primary_device_family in the CTV set)
    q2 = f"""
    WITH tagged AS (
      SELECT s.*, (primary_device_family IN ('smart_tv','streaming_stick','console')) AS ctv_heavy
      FROM sm s),
    m AS (
      SELECT ctv_heavy, month_idx,
             COUNT(*) FILTER (WHERE status='active') AS active,
             SUM(CASE WHEN is_voluntary_churn OR is_involuntary_churn THEN 1 ELSE 0 END) AS churned
      FROM tagged GROUP BY 1,2),
    r AS (SELECT ctv_heavy, month_idx,
                 churned::DOUBLE / LAG(active) OVER (PARTITION BY ctv_heavy ORDER BY month_idx) AS gc
          FROM m)
    SELECT ctv_heavy,
           ROUND(AVG(gc) FILTER (WHERE month_idx BETWEEN {PRE[0]} AND {PRE[1]}),5) AS pre_shift,
           ROUND(AVG(gc) FILTER (WHERE month_idx BETWEEN {PEAK[0]} AND {PEAK[1]}),5) AS peak
    FROM r GROUP BY 1 ORDER BY 1
    """
    s2 = _sql("q5_ctv_heavy_churn", q2)
    sm = sm_py()
    sm["ctv_heavy"] = sm.primary_device_family.isin(["smart_tv", "streaming_stick", "console"])
    g2 = sm.groupby(["ctv_heavy", "month_idx"]).agg(
        active=("status", lambda x: (x == "active").sum())).reset_index()
    g2["churned"] = (sm.groupby(["ctv_heavy", "month_idx"])[["is_voluntary_churn", "is_involuntary_churn"]]
                     .sum().sum(axis=1).values)
    g2["start"] = g2.groupby("ctv_heavy")["active"].shift(1)
    g2["gc"] = g2.churned / g2.start
    p2 = (g2.groupby("ctv_heavy").apply(lambda x: pd.Series({
        "pre_shift": round(x[x.month_idx.between(*PRE)].gc.mean(), 5),
        "peak": round(x[x.month_idx.between(*PEAK)].gc.mean(), 5)}), include_groups=False)
        .reset_index())
    parity.assert_parity("Q5 CTV-heavy churn", s2, p2, ["ctv_heavy"])
    save("q5_ctv_heavy_churn", s2)
    return s, s2


# =====================================================================
# Q6 — Brazil price change  (F2)
# =====================================================================
def q6():
    # BR Std/Prem churn by month, engaged vs disengaged (below-healthy that month)
    q = f"""
    WITH br AS (
      SELECT sm.subscriber_key, sm.month_idx, sm.status, sm.sub_current_tier,
             (sm.is_voluntary_churn OR sm.is_involuntary_churn) AS churned,
             COALESCE(em.below_healthy_engagement, TRUE) AS disengaged
      FROM sm LEFT JOIN fact_engagement_month em
             ON em.subscriber_key = sm.subscriber_key AND em.month_idx = sm.month_idx
      WHERE sm.sub_market = 'BR' AND sm.sub_current_tier IN ('Standard','Premium')),
    m AS (
      SELECT disengaged, month_idx,
             COUNT(*) FILTER (WHERE status='active') AS active,
             SUM(CASE WHEN churned THEN 1 ELSE 0 END) AS churned
      FROM br GROUP BY 1,2),
    w AS (SELECT *, LAG(active) OVER (PARTITION BY disengaged ORDER BY month_idx) AS start_active FROM m)
    SELECT disengaged, month_idx, ROUND(churned::DOUBLE / start_active, 5) AS gc
    FROM w WHERE month_idx BETWEEN 26 AND 35 ORDER BY 1,2
    """
    s = _sql("q6_br_price_engaged_split", q)

    sm = sm_py()
    em = load("fact_engagement_month")[["subscriber_key", "month_idx", "below_healthy_engagement"]]
    br = sm[(sm.sub_market == "BR") & (sm.current_tier.isin(["Standard", "Premium"]))].copy()
    br = br.merge(em, on=["subscriber_key", "month_idx"], how="left")
    br["disengaged"] = br.below_healthy_engagement.fillna(True)
    br["churned"] = br.is_voluntary_churn | br.is_involuntary_churn
    g = br.groupby(["disengaged", "month_idx"]).agg(
        active=("status", lambda x: (x == "active").sum()),
        churned=("churned", "sum")).reset_index()
    g["start"] = g.groupby("disengaged")["active"].shift(1)
    g["gc"] = (g.churned / g.start).round(5)
    p = g[g.month_idx.between(26, 35)][["disengaged", "month_idx", "gc"]].reset_index(drop=True)

    r = parity.assert_parity("Q6 BR price engaged/disengaged", s, p, ["disengaged", "month_idx"])
    save("q6_br_price_engaged_split", r)
    piv = r.pivot(index="month_idx", columns="disengaged", values="gc")
    piv.columns = ["engaged" if c is False else "disengaged" for c in piv.columns]
    out = pd.DataFrame([{
        "segment": c,
        "pre_hike_m26_m29": round(piv.loc[26:29, c].mean(), 4),
        "post_hike_m31_m35": round(piv.loc[31:35, c].mean(), 4),
        "lift_pp": round(piv.loc[31:35, c].mean() - piv.loc[26:29, c].mean(), 4),
    } for c in piv.columns])
    save("q6_price_summary", out)
    return out


# =====================================================================
# Q7 — acquisition quality shift  (F3)
# =====================================================================
def q7():
    # low-quality-channel share of new subs by cohort month & market
    q = f"""
    WITH n AS (
      SELECT s.market, s.first_paid_month_idx AS coh,
             COUNT(*) AS new_subs,
             SUM(CASE WHEN c.is_low_quality THEN 1 ELSE 0 END) AS lowq
      FROM dim_subscriber s LEFT JOIN dim_channel c ON c.channel = s.acquisition_channel
      GROUP BY 1,2)
    SELECT market, coh, new_subs,
           ROUND(lowq::DOUBLE / new_subs, 4) AS lowq_share
    FROM n WHERE coh BETWEEN 12 AND 35 ORDER BY 1,2
    """
    s = _sql("q7_lowq_share_by_cohort", q)
    ds = load("dim_subscriber")
    dc = load("dim_channel")[["channel", "is_low_quality"]]
    m = ds.merge(dc, left_on="acquisition_channel", right_on="channel", how="left")
    g = m.groupby(["market", "first_paid_month_idx"]).agg(
        new_subs=("subscriber_key", "size"), lowq=("is_low_quality", "sum")).reset_index()
    g = g.rename(columns={"first_paid_month_idx": "coh"})
    g["lowq_share"] = (g.lowq / g.new_subs).round(4)
    p = g[g.coh.between(12, 35)][["market", "coh", "new_subs", "lowq_share"]].reset_index(drop=True)
    r = parity.assert_parity("Q7 low-q channel share", s, p, ["market", "coh"])
    save("q7_lowq_share_by_cohort", r)

    # early retention (still active at tenure 3) by channel quality & cohort period
    q2 = f"""
    WITH c0 AS (SELECT subscriber_key, MIN(month_idx) AS coh
                FROM fact_subscription_month WHERE status IN ('active','churned') GROUP BY 1),
    m3 AS (SELECT DISTINCT subscriber_key FROM fact_subscription_month
           WHERE tenure_months = 3 AND status='active'),
    j AS (
      SELECT s.market,
             CASE WHEN dc.is_low_quality THEN 'low_quality' ELSE 'other' END AS chan_q,
             CASE WHEN c0.coh BETWEEN {CHANNEL_SHIFT_IDX} AND 30 THEN 'post_shift_cohorts'
                  WHEN c0.coh BETWEEN 12 AND 23 THEN 'pre_shift_cohorts' END AS coh_era,
             (m3.subscriber_key IS NOT NULL) AS alive_m3
      FROM dim_subscriber s
      JOIN c0 USING (subscriber_key)
      LEFT JOIN dim_channel dc ON dc.channel = s.acquisition_channel
      LEFT JOIN m3 USING (subscriber_key))
    SELECT market, chan_q, coh_era,
           COUNT(*) AS cohort_n, ROUND(AVG(alive_m3::INT), 4) AS m3_retention
    FROM j WHERE coh_era IS NOT NULL GROUP BY 1,2,3 ORDER BY 1,2,3
    """
    s2 = _sql("q7_m3_retention_by_channel_quality", q2)
    fsm = load("fact_subscription_month")
    c0 = fsm[fsm.status.isin(["active", "churned"])].groupby("subscriber_key").month_idx.min().rename("coh")
    m3 = set(fsm[(fsm.tenure_months == 3) & (fsm.status == "active")].subscriber_key)
    j = ds.merge(dc, left_on="acquisition_channel", right_on="channel", how="left").join(c0, on="subscriber_key")
    j["chan_q"] = np.where(j.is_low_quality.fillna(False), "low_quality", "other")
    j["coh_era"] = np.select([j.coh.between(CHANNEL_SHIFT_IDX, 30), j.coh.between(12, 23)],
                             ["post_shift_cohorts", "pre_shift_cohorts"], None)
    j["alive_m3"] = j.subscriber_key.isin(m3)
    p2 = (j[j.coh_era.notna()].groupby(["market", "chan_q", "coh_era"])
          .agg(cohort_n=("subscriber_key", "size"), m3_retention=("alive_m3", "mean")).reset_index())
    p2["m3_retention"] = p2.m3_retention.round(4)
    parity.assert_parity("Q7 M3 retention by channel quality", s2, p2, ["market", "chan_q", "coh_era"])
    save("q7_m3_retention_by_channel_quality", s2)
    return r, s2


# =====================================================================
# Q8 — payments / involuntary
# =====================================================================
def q8():
    q = f"""
    WITH b AS (
      SELECT market, method, month_idx,
             COUNT(*) FILTER (WHERE NOT is_dunning) AS first_attempts,
             COUNT(*) FILTER (WHERE NOT is_dunning AND status='failed') AS first_fail,
             COUNT(*) FILTER (WHERE is_dunning) AS dunning_attempts,
             COUNT(*) FILTER (WHERE is_dunning AND status='approved') AS dunning_recovered
      FROM fact_billing_attempt WHERE market IS NOT NULL GROUP BY 1,2,3)
    SELECT market,
           CASE WHEN month_idx BETWEEN {PRE[0]} AND {PRE[1]} THEN 'pre_shift'
                WHEN month_idx BETWEEN {PEAK[0]} AND {PEAK[1]} THEN 'peak' END AS period,
           ROUND(SUM(first_fail)::DOUBLE / NULLIF(SUM(first_attempts),0), 4)          AS payment_failure_rate,
           ROUND(SUM(dunning_recovered)::DOUBLE / NULLIF(SUM(dunning_attempts),0), 4) AS dunning_recovery_rate
    FROM b WHERE month_idx BETWEEN {PRE[0]} AND {PEAK[1]}
    GROUP BY 1,2 HAVING period IS NOT NULL ORDER BY 1,2
    """
    s = _sql("q8_payments", q)
    b = load("fact_billing_attempt")
    b = b[b.month_idx.between(PRE[0], PEAK[1])].copy()
    b["period"] = np.select([b.month_idx.between(*PRE), b.month_idx.between(*PEAK)],
                            ["pre_shift", "peak"], None)
    b = b[b.period.notna()]
    g = b.groupby(["market", "period"]).apply(lambda x: pd.Series({
        "payment_failure_rate": round((~x.is_dunning & x.status.eq("failed")).sum()
                                      / max((~x.is_dunning).sum(), 1), 4),
        "dunning_recovery_rate": round((x.is_dunning & x.status.eq("approved")).sum()
                                       / max(x.is_dunning.sum(), 1), 4),
    }), include_groups=False).reset_index()
    r = parity.assert_parity("Q8 payments", s, g, ["market", "period"])
    save("q8_payments", r)

    q3 = f"""
    WITH m AS (
      SELECT sub_market AS market, month_idx,
             COUNT(*) FILTER (WHERE status='active') AS active,
             SUM(is_involuntary_churn::INT) AS invol
      FROM sm GROUP BY 1,2),
    r AS (SELECT market, month_idx,
                 invol::DOUBLE / NULLIF(LAG(active) OVER (PARTITION BY market ORDER BY month_idx),0) AS ic
          FROM m)
    SELECT market,
           ROUND(AVG(ic) FILTER (WHERE month_idx BETWEEN {PRE[0]} AND {PRE[1]}),5)  AS invol_pre,
           ROUND(AVG(ic) FILTER (WHERE month_idx BETWEEN {PEAK[0]} AND {PEAK[1]}),5) AS invol_peak
    FROM r GROUP BY 1 ORDER BY 1
    """
    s3 = _sql("q8_involuntary_by_market", q3)
    sm = sm_py()
    gg = sm.groupby(["sub_market", "month_idx"]).agg(
        active=("status", lambda x: (x == "active").sum()),
        invol=("is_involuntary_churn", "sum")).reset_index()
    gg["start"] = gg.groupby("sub_market")["active"].shift(1)
    gg["ic"] = gg.invol / gg.start
    p3 = (gg.groupby("sub_market").apply(lambda x: pd.Series({
        "invol_pre": round(x[x.month_idx.between(*PRE)].ic.mean(), 5),
        "invol_peak": round(x[x.month_idx.between(*PEAK)].ic.mean(), 5)}), include_groups=False)
        .reset_index().rename(columns={"sub_market": "market"}))
    parity.assert_parity("Q8 involuntary by market", s3, p3, ["market"])
    save("q8_involuntary_by_market", s3)
    return r, s3


# =====================================================================
# Q9 — financial / LTV impact
# =====================================================================
def q9():
    q = f"""
    WITH act AS (
      SELECT month_idx,
             COUNT(*) FILTER (WHERE status='active') AS active,
             SUM(CASE WHEN status='active' THEN mrr_usd ELSE 0 END) AS mrr_usd,
             SUM(CASE WHEN is_voluntary_churn OR is_involuntary_churn THEN 1 ELSE 0 END) AS churned
      FROM fact_subscription_month GROUP BY 1),
    r AS (SELECT month_idx, active, mrr_usd,
                 churned::DOUBLE / LAG(active) OVER (ORDER BY month_idx) AS gc
          FROM act)
    SELECT
      ROUND(AVG(gc) FILTER (WHERE month_idx BETWEEN {PRE[0]} AND {PRE[1]}),5)  AS churn_pre,
      ROUND(AVG(gc) FILTER (WHERE month_idx BETWEEN {PEAK[0]} AND {PEAK[1]}),5) AS churn_peak,
      ROUND(1.0/AVG(gc) FILTER (WHERE month_idx BETWEEN {PRE[0]} AND {PRE[1]}),1)  AS lifetime_pre_m,
      ROUND(1.0/AVG(gc) FILTER (WHERE month_idx BETWEEN {PEAK[0]} AND {PEAK[1]}),1) AS lifetime_peak_m,
      ROUND(AVG(mrr_usd/NULLIF(active,0)) FILTER (WHERE month_idx BETWEEN {PEAK[0]} AND {PEAK[1]}),2) AS arpu_peak,
      ROUND(AVG(mrr_usd) FILTER (WHERE month_idx BETWEEN {PEAK[0]} AND {PEAK[1]}),0) AS mrr_peak
    FROM r
    """
    s = _sql("q9_financial", q)
    f = load("fact_subscription_month")
    a = f.groupby("month_idx").agg(
        active=("status", lambda x: (x == "active").sum()),
        mrr=("mrr_usd", lambda x: x[f.loc[x.index, "status"] == "active"].sum())).reset_index()
    a["churned"] = f.groupby("month_idx")[["is_voluntary_churn", "is_involuntary_churn"]].sum().sum(axis=1).values
    a["start"] = a.active.shift(1)
    a["gc"] = a.churned / a.start
    cp = a[a.month_idx.between(*PRE)].gc.mean()
    ck = a[a.month_idx.between(*PEAK)].gc.mean()
    p = pd.DataFrame([{
        "churn_pre": round(cp, 5), "churn_peak": round(ck, 5),
        "lifetime_pre_m": round(1 / cp, 1), "lifetime_peak_m": round(1 / ck, 1),
        "arpu_peak": round((a[a.month_idx.between(*PEAK)].mrr / a[a.month_idx.between(*PEAK)].active).mean(), 2),
        "mrr_peak": round(a[a.month_idx.between(*PEAK)].mrr.mean(), 0),
    }])
    r = parity.assert_parity("Q9 financial", s, p, list(s.columns))
    r["ltv_erosion_pct"] = round(1 - r.lifetime_peak_m.iloc[0] / r.lifetime_pre_m.iloc[0], 3)
    save("q9_financial", r)

    # cumulative excess churned subscribers since the shift vs the pre-shift rate
    q2 = f"""
    WITH act AS (
      SELECT month_idx,
             COUNT(*) FILTER (WHERE status='active') AS active,
             SUM(CASE WHEN is_voluntary_churn OR is_involuntary_churn THEN 1 ELSE 0 END) AS churned
      FROM fact_subscription_month GROUP BY 1),
    r AS (SELECT month_idx, churned,
                 LAG(active) OVER (ORDER BY month_idx) AS start_active FROM act),
    base AS (SELECT AVG(churned::DOUBLE/start_active) AS b FROM r WHERE month_idx BETWEEN {PRE[0]} AND {PRE[1]})
    SELECT SUM(churned - start_active*(SELECT b FROM base))::INT AS excess_churned_since_shift
    FROM r WHERE month_idx BETWEEN {PEAK[0]} AND {PEAK[1]}
    """
    s2 = _sql("q9_excess_churn", q2)
    b = a[a.month_idx.between(*PRE)].gc.mean()
    excess = int(((a.churned - a.start * b)[a.month_idx.between(*PEAK)]).sum())
    p2 = pd.DataFrame([{"excess_churned_since_shift": excess}])
    parity.assert_parity("Q9 excess churn", s2, p2, ["excess_churned_since_shift"])
    save("q9_excess_churn", s2)
    return r, s2


# =====================================================================
# Q10 — synthesis: decompose the peak excess churn
# =====================================================================
def q10():
    # tag every peak-month voluntary churn row with the driver flags and attribute it
    q = f"""
    WITH v AS (
      SELECT sm.subscriber_key, sm.month_idx, sm.sub_market AS market, sm.sub_current_tier AS tier,
             sm.primary_device_family, sm.is_low_quality, sm.tenure_months,
             COALESCE(em.below_healthy_engagement, TRUE) AS disengaged
      FROM sm LEFT JOIN fact_engagement_month em
        ON em.subscriber_key = sm.subscriber_key AND em.month_idx = sm.month_idx
      WHERE sm.is_voluntary_churn AND sm.month_idx BETWEEN {PEAK[0]} AND {PEAK[1]}),
    tagged AS (
      SELECT *,
        (primary_device_family IN ('smart_tv','streaming_stick','console')) AS f1_ctv,
        (market='BR' AND tier IN ('Standard','Premium') AND disengaged)      AS f2_price_diseng,
        (is_low_quality AND tenure_months <= 5)                              AS f3_lowq_young
      FROM v)
    SELECT market,
           COUNT(*)                                        AS peak_voluntary_churn,
           ROUND(AVG(f1_ctv::INT),3)                        AS share_f1_ctv,
           ROUND(AVG(f2_price_diseng::INT),3)               AS share_f2_price,
           ROUND(AVG(f3_lowq_young::INT),3)                 AS share_f3_lowq,
           ROUND(AVG((NOT f1_ctv AND NOT f2_price_diseng AND NOT f3_lowq_young)::INT),3) AS share_none
    FROM tagged GROUP BY 1 ORDER BY 1
    """
    s = _sql("q10_driver_decomposition", q)

    sm = sm_py()
    em = load("fact_engagement_month")[["subscriber_key", "month_idx", "below_healthy_engagement"]]
    v = sm[(sm.is_voluntary_churn) & (sm.month_idx.between(*PEAK))].merge(
        em, on=["subscriber_key", "month_idx"], how="left")
    v["disengaged"] = v.below_healthy_engagement.fillna(True)
    v["f1_ctv"] = v.primary_device_family.isin(["smart_tv", "streaming_stick", "console"])
    v["f2_price_diseng"] = (v.sub_market.eq("BR") & v.current_tier.isin(["Standard", "Premium"]) & v.disengaged)
    v["f3_lowq_young"] = (v.is_low_quality.fillna(False) & (v.tenure_months <= 5))
    p = v.groupby("sub_market").apply(lambda x: pd.Series({
        "peak_voluntary_churn": len(x),
        "share_f1_ctv": round(x.f1_ctv.mean(), 3),
        "share_f2_price": round(x.f2_price_diseng.mean(), 3),
        "share_f3_lowq": round(x.f3_lowq_young.mean(), 3),
        "share_none": round((~x.f1_ctv & ~x.f2_price_diseng & ~x.f3_lowq_young).mean(), 3),
    }), include_groups=False).reset_index().rename(columns={"sub_market": "market"})
    r = parity.assert_parity("Q10 driver decomposition", s, p, ["market"])
    save("q10_driver_decomposition", r)
    return r


# =====================================================================
def main():
    print("Voxa+ churn diagnosis — dual-track (DuckDB SQL / pandas)\n")
    for fn in (q1, q2, q3, q4, q5, q6, q7, q8, q9, q10):
        print(f"[{fn.__name__}]")
        fn()
    ok = parity.report(HERE / "parity" / "parity_report.md")
    print(f"\nparity report -> parity/parity_report.md   ({'ALL PASS' if ok else 'FAILURES'})")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
