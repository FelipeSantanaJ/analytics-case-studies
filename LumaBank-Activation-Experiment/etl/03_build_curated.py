"""
LumaBank — 03_build_curated.py

Reads data/staging/stg_*.parquet, writes the conformed Kimball star to
data/curated/ (Parquet + CSV mirror), plus curated DQ fragments.

Rules of the layer:
  - the effective experiment arm is derived from the assignment EVENT LOG,
    never the snapshot (the snapshot is measurement-only)
  - the contamination rule is auditable (doc 02 §7.3) and stamped here
  - in_analysis_flag = the clean re-run population the primary read-out filters on
  - all money is BRL; facts are never dropped for a missing dimension (user_key -1)
"""

from __future__ import annotations

from collections import Counter

import numpy as np
import pandas as pd
from scipy import stats

import config as C
from utils import banner, write_csv, write_dq_fragment, write_parquet

STG = C.STAGING_DIR
CUR = C.CURATED_DIR
DAY7 = pd.Timedelta(days=C.DAY7_WINDOW_DAYS)
BRT = pd.Timedelta(hours=-3)


def L(name):
    return pd.read_parquet(STG / f"{name}.parquet")


def dkey(s):
    d = pd.to_datetime(s)
    return (d.dt.year * 10000 + d.dt.month * 100 + d.dt.day).astype("Int64")


def to_brt_naive(s):
    d = pd.to_datetime(s, utc=True, errors="coerce")
    return d.dt.tz_convert("America/Sao_Paulo").dt.tz_localize(None)


def out(df, name, ctr=None):
    CUR.mkdir(parents=True, exist_ok=True)
    write_parquet(df, CUR / f"{name}.parquet")
    if C.WRITE_CSV_MIRROR:
        if len(df) > C.CSV_MIRROR_MAX_ROWS:
            print(f"    [skip csv] {name}: {len(df):,} rows")
        elif len(df) > 400_000:
            write_csv(df, CUR / f"{name}.csv.gz", compression="gzip")
        else:
            write_csv(df, CUR / f"{name}.csv")
    write_dq_fragment(f"curated__{name}", dict(ctr or {}, rows=len(df)))
    print(f"  {name:32s} {len(df):>10,} rows")


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
    df["is_weekend"] = df["day_of_week"] >= 5
    cal = pd.read_csv(C.VOCAB_DIR / "br_calendar.csv", parse_dates=["date"])
    df = df.merge(cal, on="date", how="left")
    df["is_holiday_br"] = df["is_holiday"].fillna(0).astype(int).astype(bool)
    df["is_school_break"] = df["is_school_break"].fillna(0).astype(int).astype(bool)
    df.drop(columns=["is_holiday", "holiday_name"], inplace=True, errors="ignore")
    m = df["month"]
    df["season_tag"] = np.select(
        [m.isin([12, 1, 2]), m.isin([3, 4, 5]), m.isin([6, 7, 8])],
        ["Summer", "Autumn", "Winter"], default="Spring")

    df["experiment_phase"] = "out_of_window"
    def stamp(lo, hi, label):
        df.loc[(df["date"] >= pd.Timestamp(lo)) & (df["date"] <= pd.Timestamp(hi)), "experiment_phase"] = label
    stamp(C.WINDOW_START, C.EXP1_START - pd.Timedelta(days=1).to_pytimedelta(), "pre")
    stamp(C.EXP1_START, C.EXP1_ABANDONED, "original")
    stamp(C.EXP1_ABANDONED + pd.Timedelta(days=1).to_pytimedelta(), C.EXP2_START - pd.Timedelta(days=1).to_pytimedelta(), "washout")
    stamp(C.EXP2_START, C.EXP2_END, "rerun")
    stamp(C.EXP2_END + pd.Timedelta(days=1).to_pytimedelta(), C.WINDOW_END, "post")
    df["is_post_deploy"] = (df["date"] >= pd.Timestamp(C.DEPLOY_DATE)) & (df["date"] <= pd.Timestamp(C.EXP1_ABANDONED))

    ed1 = ((df["date"] - pd.Timestamp(C.EXP1_START)).dt.days + 1)
    df["experiment_day"] = pd.NA
    df.loc[df["experiment_phase"] == "original", "experiment_day"] = ed1
    ed2 = ((df["date"] - pd.Timestamp(C.EXP2_START)).dt.days + 1)
    df.loc[df["experiment_phase"] == "rerun", "experiment_day"] = ed2
    df["experiment_day"] = df["experiment_day"].astype("Int64")
    out(df, "dim_date")
    return df


def build_static_dims():
    uf = pd.read_csv(C.VOCAB_DIR / "br_uf_region_tz.csv")
    uf.insert(0, "region_key", range(1, len(uf) + 1))
    uf = pd.concat([pd.DataFrame([{"region_key": -1, "uf": "??", "uf_name": "unknown",
                                   "macro_region": "unknown", "timezone": C.DEFAULT_TZ,
                                   "utc_offset_hours": -3, "is_amazon_tz": 0, "pop_weight": 0}]), uf],
                   ignore_index=True)
    uf["is_amazon_tz"] = uf["is_amazon_tz"].astype(bool)
    out(uf, "dim_region")

    ch = ["paid_social", "organic", "app_store_search", "referral", "influencer", "unknown"]
    grp = {"paid_social": "paid", "organic": "owned", "app_store_search": "owned",
           "referral": "earned", "influencer": "paid", "unknown": "unknown"}
    dch = pd.DataFrame({"channel_key": range(1, len(ch) + 1), "channel_name": ch,
                        "channel_group": [grp[c] for c in ch],
                        "is_paid": [grp[c] == "paid" for c in ch]})
    out(dch, "dim_acquisition_channel")

    steps = ["signup_started", "personal_data", "kyc_upload", "account_created",
             "first_transaction", "limits_lifted"]
    fstage = {"signup_started": "signup", "personal_data": "signup", "kyc_upload": "kyc",
              "account_created": "account", "first_transaction": "activation", "limits_lifted": "post"}
    dstep = pd.DataFrame({"step_key": range(1, len(steps) + 1), "step_name": steps,
                          "step_order": range(1, len(steps) + 1),
                          "funnel_stage": [fstage[s] for s in steps]})
    out(dstep, "dim_onboarding_step")

    out(pd.DataFrame({"arm_key": ["control", "treatment", "ambiguous"]}), "dim_experiment_arm")

    rl = L("stg_beacon_app_releases").copy()
    rl = rl.dropna(subset=["released_at"]).sort_values("released_at").reset_index(drop=True)
    rl.insert(0, "app_release_key", range(1, len(rl) + 1))
    rl["released_date_key"] = dkey(rl["released_at"])
    # Match on the exact deploy date, not the version string: the "4.61.0" label the
    # generator hardcodes for the cache-reset release can coincidentally collide with an
    # earlier, unrelated release that organically counted up to the same number.
    rl["is_cache_reset_release"] = (pd.to_datetime(rl["released_at"]).dt.date == C.DEPLOY_DATE)
    rl = pd.concat([pd.DataFrame([{"app_release_key": -1, "version": "unknown", "platform": "unknown",
                                   "released_at": pd.NaT, "released_date_key": pd.NA, "rollout_pct": np.nan,
                                   "release_type": "unknown", "notes": "", "is_cache_reset_release": False}]),
                    rl], ignore_index=True)
    out(rl, "dim_app_release")
    return dch, dstep


# ======================================================================== #
def build_users_and_experiment(dch):
    banner("curated: dim_user + experiment derivation")
    su = L("stg_lumencore_users").copy()
    su = su.dropna(subset=["user_id"]).drop_duplicates("user_id")
    su.insert(0, "user_key", range(1, len(su) + 1))
    uk = dict(zip(su["user_id"], su["user_key"]))

    steps = L("stg_trilha_onboarding_steps")
    signup = (steps[steps["step_name"] == "signup_started"]
              .sort_values("occurred_ts").drop_duplicates("user_id")
              .set_index("user_id")["occurred_ts"])
    su["signup_ts"] = pd.to_datetime(su["user_id"].map(signup))
    su = su.dropna(subset=["signup_ts"]).copy()
    su["signup_date_key"] = dkey(su["signup_ts"])
    su["signup_cohort_week"] = su["signup_ts"].dt.to_period("W-SUN").astype(str).str.slice(0, 10)

    acq = L("stg_orbita_acquisition")
    su = su.merge(acq[["user_id", "channel"]], on="user_id", how="left")
    su["channel"] = su["channel"].fillna("unknown")
    su = su.merge(dch[["channel_key", "channel_name"]].rename(columns={"channel_name": "channel"}),
                  on="channel", how="left")

    reg = pd.read_parquet(CUR / "dim_region.parquet")[["region_key", "uf"]]
    su = su.merge(reg, on="uf", how="left")
    su["region_key"] = su["region_key"].fillna(-1).astype(int)

    rl = pd.read_parquet(CUR / "dim_app_release.parquet")
    rl = rl[rl["app_release_key"] > 0].sort_values("released_at")
    su["app_version_at_signup"] = rl["version"].to_numpy()[
        np.clip(np.searchsorted(rl["released_at"].to_numpy(), su["signup_ts"].to_numpy(), side="right") - 1,
                0, len(rl) - 1)]

    # ---- assignment event log -> effective arm + contamination (vectorised) ----
    va = L("stg_flagfox_variant_assignments").copy()
    va["assigned_brt"] = to_brt_naive(va["assigned_ts"])
    va = va.merge(su[["user_id", "signup_ts"]], on="user_id", how="left")
    va = va.sort_values(["user_id", "assignment_seq"])

    per = pd.DataFrame({"user_id": va["user_id"].drop_duplicates().to_numpy()})
    per = per.merge(va[va["assignment_seq"] == 1][["user_id", "arm", "assignment_source", "signup_ts"]]
                    .rename(columns={"arm": "first_arm", "assignment_source": "first_src"}),
                    on="user_id", how="left")
    s2 = va[va["assignment_seq"] == 2][["user_id", "arm", "assigned_brt"]].rename(
        columns={"arm": "seq2_arm", "assigned_brt": "seq2_brt"})
    per = per.merge(s2, on="user_id", how="left")
    per["any_fallback"] = per["user_id"].isin(set(va.loc[va["assignment_source"] == "fallback", "user_id"]))
    resets = (L("stg_flagfox_exposure_log").query("cache_reset")
              .assign(brt=lambda d: to_brt_naive(d["exposed_ts"]))
              .groupby("user_id")["brt"].min().rename("reset_brt"))
    per = per.merge(resets, on="user_id", how="left")

    per["assignment_switch_flag"] = per["seq2_arm"].notna() & (per["seq2_arm"] != per["first_arm"])
    before_half = per["seq2_brt"].notna() & (per["seq2_brt"] <= per["signup_ts"] + DAY7 / 2)
    per["effective_arm"] = np.where(per["assignment_switch_flag"] & before_half,
                                    per["seq2_arm"], per["first_arm"])
    per["contaminated_flag"] = (per["assignment_switch_flag"]
                                | (per["reset_brt"].notna()
                                   & (per["reset_brt"] <= per["signup_ts"] + DAY7)))
    d = per["signup_ts"].dt.date
    per["experiment_cohort"] = np.select(
        [(d >= C.EXP2_START) & (d <= C.EXP2_END),
         (d >= C.DEPLOY_DATE) & (d < C.EXP1_ENROLL_PAUSED),
         (d >= C.EXP1_START) & (d < C.DEPLOY_DATE)],
        ["rerun", "post_deploy", "pre_deploy"], default="not_in_experiment")
    per["in_analysis_flag"] = ((per["experiment_cohort"] == "rerun")
                               & ~per["contaminated_flag"] & ~per["any_fallback"])
    exp = per[["user_id", "effective_arm", "experiment_cohort", "contaminated_flag",
               "assignment_switch_flag", "in_analysis_flag"]].copy()
    su = su.merge(exp, on="user_id", how="left")
    su["experiment_arm"] = su["effective_arm"].fillna("not_in_experiment")
    su["experiment_cohort"] = su["experiment_cohort"].fillna("not_in_experiment")
    for c in ("contaminated_flag", "assignment_switch_flag", "in_analysis_flag"):
        su[c] = su[c].fillna(False)
    su["is_experiment_subject"] = su["experiment_arm"].isin(["control", "treatment"])
    su["is_test_account"] = False

    by = pd.to_datetime(su["signup_ts"]).dt.year  # placeholder; no birth date modelled
    su["age_band"] = "unknown"
    su["birth_year_valid"] = False

    dim_user = su[[
        "user_key", "user_id", "signup_date_key", "signup_cohort_week", "channel_key",
        "channel", "region_key", "device_os", "app_version_at_signup", "age_band",
        "birth_year_valid", "is_test_account", "experiment_arm", "experiment_cohort",
        "is_experiment_subject", "contaminated_flag", "assignment_switch_flag", "in_analysis_flag",
    ]].rename(columns={"channel": "acquisition_channel"}).copy()
    # sentinel row so orphan events (KYC/fraud user_key = -1, queue-lag) resolve in the
    # semantic model instead of landing on an unmatched blank row. Column dtypes are
    # object at this point (post-merge/fillna), so key off each column's own non-null
    # value type rather than pandas dtype inference.
    bool_cols = {"birth_year_valid", "is_test_account", "is_experiment_subject",
                 "contaminated_flag", "assignment_switch_flag", "in_analysis_flag"}
    int_cols = {"user_key", "channel_key", "region_key", "signup_date_key"}
    sentinel = {c: (-1 if c in ("user_key",) else "SENTINEL_ORPHAN" if c == "user_id" else
                    False if c in bool_cols else
                    -1 if c in int_cols else "unknown")
                for c in dim_user.columns}
    dim_user = pd.concat([dim_user, pd.DataFrame([sentinel])], ignore_index=True)
    for c in bool_cols:
        dim_user[c] = dim_user[c].astype(bool)
    out(dim_user, "dim_user")

    # ---- fact_variant_assignment ----------------------------------------
    fva = va.merge(su[["user_id", "user_key"]], on="user_id", how="left")
    fva["user_key"] = fva["user_key"].fillna(-1).astype(int)
    fva["assigned_ts_brt"] = fva["assigned_brt"]
    fva["assigned_date_key"] = dkey(fva["assigned_brt"])
    fva["arm_key"] = fva["arm"]
    fva["is_first_assignment"] = fva["assignment_seq"] == 1
    # exactly one effective row per user: the lowest-seq row whose arm == effective_arm
    fva["_eff_arm"] = fva["user_id"].map(dict(zip(exp["user_id"], exp["effective_arm"])))
    fva = fva.sort_values(["user_id", "assignment_seq"]).reset_index(drop=True)
    fva["is_effective_assignment"] = False
    match_idx = fva.index[fva["arm"] == fva["_eff_arm"]]
    fva.loc[fva.loc[match_idx].groupby("user_id", sort=False).head(1).index, "is_effective_assignment"] = True
    no_match = set(fva["user_id"]) - set(fva.loc[fva["is_effective_assignment"], "user_id"])
    if no_match:
        first_rows = fva.groupby("user_id", sort=False).head(1)
        fva.loc[first_rows.index[first_rows["user_id"].isin(no_match)], "is_effective_assignment"] = True
    _rk = (pd.read_parquet(CUR / "dim_app_release.parquet")[["app_release_key", "version"]]
           .drop_duplicates("version").rename(columns={"version": "app_version"}))
    fva = fva.merge(_rk, on="app_version", how="left")
    fva["app_release_key"] = fva["app_release_key"].fillna(-1).astype(int)
    fva_out = fva[["user_key", "user_id", "arm_key", "assigned_ts_brt", "assigned_date_key",
                   "assignment_seq", "assignment_source", "cache_reset", "app_release_key",
                   "is_first_assignment", "is_effective_assignment"]].rename(
        columns={"cache_reset": "cache_reset_flag"})
    out(fva_out, "fact_variant_assignment")
    return su, dim_user, fva


# ======================================================================== #
def build_funnel_kyc_activation(su, dch, dstep):
    banner("curated: funnel / kyc / activation / transactions")
    uk = dict(zip(su["user_id"], su["user_key"]))
    sig = dict(zip(su["user_id"], su["signup_ts"]))

    # ---- fact_onboarding_step ----------------------------------------
    st = L("stg_trilha_onboarding_steps").copy()
    st["user_key"] = st["user_id"].map(uk).fillna(-1).astype(int)
    st = st.merge(dstep[["step_key", "step_name"]], on="step_name", how="left")
    st["step_key"] = st["step_key"].fillna(-1).astype(int)
    st["occurred_date_key"] = dkey(st["occurred_ts"])
    st["sig"] = st["user_id"].map(sig)
    st["seconds_since_signup"] = (pd.to_datetime(st["occurred_ts"]) - pd.to_datetime(st["sig"])).dt.total_seconds()
    st["is_reached"] = True
    out(st[["user_key", "user_id", "step_key", "step_name", "occurred_ts", "occurred_date_key",
            "seconds_since_signup", "is_reached"]], "fact_onboarding_step")

    # ---- dim_kyc_outcome + fact_kyc_decision -----------------------
    kd = L("stg_riskguard_kyc_decisions").copy()
    kd = kd.sort_values("decided_ts").drop_duplicates("user_id", keep="last")
    combos = kd[["outcome", "reason_code_clean", "reason_group"]].drop_duplicates().reset_index(drop=True)
    combos.insert(0, "kyc_outcome_key", range(1, len(combos) + 1))
    combos["is_rejection"] = combos["outcome"] == "rejected"
    combos = pd.concat([pd.DataFrame([{"kyc_outcome_key": -1, "outcome": "none",
                                       "reason_code_clean": "none", "reason_group": "n/a",
                                       "is_rejection": False}]), combos], ignore_index=True)
    out(combos.rename(columns={"reason_code_clean": "reason_code"}), "dim_kyc_outcome")

    ks = L("stg_trilha_kyc_submissions")[["user_id", "submitted_ts", "doc_type", "submitted_after_account"]]
    fkd = kd.merge(ks, on="user_id", how="left").merge(combos, on=["outcome", "reason_code_clean", "reason_group"], how="left")
    fkd["user_key"] = fkd["user_id"].map(uk).fillna(-1).astype(int)
    fkd["kyc_outcome_key"] = fkd["kyc_outcome_key"].fillna(-1).astype(int)
    fkd["decision_latency_hours"] = (pd.to_datetime(fkd["decided_ts"]).dt.tz_convert(None)
                                     - pd.to_datetime(fkd["submitted_ts"])).dt.total_seconds() / 3600
    fkd["is_rejection"] = fkd["outcome"] == "rejected"
    fkd["is_manual_review"] = fkd["outcome"] == "manual_review"
    out(fkd[["user_key", "user_id", "kyc_outcome_key", "submitted_ts", "decided_ts",
             "decision_latency_hours", "is_rejection", "is_manual_review", "doc_type",
             "submitted_after_account"]], "fact_kyc_decision")

    # ---- transactions -> fact_transaction_day + first txn -----------
    tx = L("stg_lumencore_transactions").copy()
    tx["user_key"] = tx["user_id"].map(uk).fillna(-1).astype(int)
    tx["ts"] = pd.to_datetime(tx["ts"])
    tx = tx[tx["ts"] <= pd.Timestamp(C.WINDOW_END) + pd.Timedelta(days=1)]   # window guard
    tx["date_key"] = dkey(tx["ts"])
    first_txn = tx.groupby("user_id")["ts"].min()
    for t in ("pix", "card", "boleto", "transfer"):
        tx[f"{t}_count"] = (tx["type"] == t).astype("int32")
    ftd = (tx.groupby(["user_key", "user_id", "date_key"], sort=False)
           .agg(txn_count=("txn_id", "size"), txn_amount_brl=("amount_brl", "sum"),
                pix_count=("pix_count", "sum"), card_count=("card_count", "sum"),
                boleto_count=("boleto_count", "sum"), transfer_count=("transfer_count", "sum"))
           .reset_index())
    ftd["txn_amount_brl"] = ftd["txn_amount_brl"].round(2)
    first_dk = tx.groupby("user_id")["date_key"].min()
    ftd["is_first_txn_day"] = ftd["date_key"] == ftd["user_id"].map(first_dk)
    out(ftd, "fact_transaction_day")

    # ---- fact_activation (one row per SIGNUP -- platform-wide; is_experiment_subject
    #      flags the randomized ones, which the experiment read-out filters on) -------
    subj = su.copy()
    subj["first_txn_ts"] = subj["user_id"].map(first_txn)
    acc = L("stg_lumencore_accounts").copy()
    acc_open = acc.sort_values("opened_at").drop_duplicates("user_id", keep="first").set_index("user_id")["opened_at"]
    subj["account_opened_ts"] = subj["user_id"].map(acc_open)
    subj["account_opened_flag"] = subj["account_opened_ts"].notna()
    subj["hours_to_first_txn"] = ((pd.to_datetime(subj["first_txn_ts"]) - pd.to_datetime(subj["signup_ts"]))
                                  .dt.total_seconds() / 3600)
    within = pd.to_datetime(subj["first_txn_ts"]) <= pd.to_datetime(subj["signup_ts"]) + DAY7
    subj["day7_activated"] = (subj["account_opened_flag"] & within & subj["first_txn_ts"].notna()).astype(int)
    subj["day1_activated"] = (subj["day7_activated"].astype(bool) & (subj["hours_to_first_txn"] <= 24)).astype(int)
    subj["day30_activated"] = (subj["account_opened_flag"] & subj["first_txn_ts"].notna()
                               & (pd.to_datetime(subj["first_txn_ts"])
                                  <= pd.to_datetime(subj["signup_ts"]) + pd.Timedelta(days=30))).astype(int)

    ks_flag = set(L("stg_trilha_kyc_submissions")["user_id"])
    subj["kyc_submitted_flag"] = subj["user_id"].isin(ks_flag)
    rej = set(kd[kd["outcome"] == "rejected"]["user_id"])
    subj["kyc_rejected_flag"] = subj["user_id"].isin(rej)

    fr = L("stg_riskguard_fraud_signals").copy()
    fr["brt"] = to_brt_naive(fr["signal_ts"])
    fr30 = fr.merge(subj[["user_id", "first_txn_ts"]], on="user_id", how="inner")
    fr30 = fr30[pd.to_datetime(fr30["brt"]) <= pd.to_datetime(fr30["first_txn_ts"]) + pd.Timedelta(days=30)]
    subj["fraud_flag_30d"] = subj["user_id"].isin(set(fr30["user_id"]))

    tk = L("stg_orbita_support_tickets")
    onb = tk[tk["category"] == "onboarding"].groupby("user_id").size()
    subj["onboarding_tickets_n"] = subj["user_id"].map(onb).fillna(0).astype(int)

    subj["assigned_date_key"] = dkey(subj["signup_ts"])
    fact_act = subj[[
        "user_key", "user_id", "experiment_arm", "assigned_date_key", "signup_ts",
        "experiment_cohort", "channel_key", "region_key", "app_version_at_signup",
        "account_opened_flag", "account_opened_ts", "first_txn_ts", "hours_to_first_txn",
        "day7_activated", "day1_activated", "day30_activated", "kyc_submitted_flag",
        "kyc_rejected_flag", "fraud_flag_30d", "onboarding_tickets_n",
        "is_experiment_subject", "contaminated_flag", "assignment_switch_flag", "in_analysis_flag",
    ]].rename(columns={"experiment_arm": "arm_key", "signup_ts": "assigned_ts"})
    out(fact_act, "fact_activation")

    # ---- fact_fraud_event / fact_support_ticket -------------------
    fr["user_key"] = fr["user_id"].map(uk).fillna(-1).astype(int)
    fr["flagged_date_key"] = dkey(fr["brt"])
    fr = fr.merge(subj[["user_id", "first_txn_ts"]], on="user_id", how="left")
    fr["days_since_activation"] = ((pd.to_datetime(fr["brt"]) - pd.to_datetime(fr["first_txn_ts"]))
                                   .dt.total_seconds() / 86400).round(1)
    out(fr[["user_key", "user_id", "brt", "flagged_date_key", "signal_type", "score",
            "confirmed", "days_since_activation"]].rename(columns={"brt": "flagged_ts",
                                                                  "confirmed": "is_confirmed"}),
        "fact_fraud_event")

    tk = tk.copy()
    tk["user_key"] = tk["user_id"].map(uk).fillna(-1).astype(int)
    tk["opened_date_key"] = dkey(tk["opened_ts"])
    tk["is_onboarding"] = tk["category"] == "onboarding"
    out(tk[["user_key", "user_id", "opened_ts", "opened_date_key", "category", "channel",
            "cidade", "is_onboarding"]], "fact_support_ticket")


# ======================================================================== #
def build_srm_daily(fva, su):
    banner("curated: fact_srm_daily")
    a = fva[fva["is_first_assignment"]].copy()
    a = a.merge(su[["user_id", "signup_ts", "assignment_switch_flag"]], on="user_id", how="left")
    a["d"] = pd.to_datetime(a["assigned_ts_brt"]).dt.date
    multi_users = set(fva.groupby("user_id").size()[lambda s: s > 1].index)

    runs = [("original", C.EXP1_START, C.EXP1_ENROLL_PAUSED - pd.Timedelta(days=1).to_pytimedelta()),
            ("rerun", C.EXP2_START, C.EXP2_END)]
    rows = []
    for phase, lo, hi in runs:
        sub = a[(a["d"] >= lo) & (a["d"] <= hi)]
        days = pd.date_range(lo, hi, freq="D").date
        for day in days:
            upto = sub[sub["d"] <= day]
            win = sub[(sub["d"] > day - pd.Timedelta(days=C.SRM_TRAILING_DAYS).to_pytimedelta()) & (sub["d"] <= day)]
            dd = sub[sub["d"] == day]
            nc = int((dd["arm_key"] == "control").sum())
            nt = int((dd["arm_key"] == "treatment").sum())
            def chi_p(frame):
                c = (frame["arm_key"] == "control").sum()
                t = (frame["arm_key"] == "treatment").sum()
                n = c + t
                if n < 20:
                    return np.nan, 1.0
                chi = (c - n / 2) ** 2 / (n / 2) + (t - n / 2) ** 2 / (n / 2)
                return chi, float(stats.chi2.sf(chi, 1))
            chi_c, p_c = chi_p(upto)
            chi_w, p_w = chi_p(win)
            mism = int(upto["assignment_switch_flag"].fillna(False).sum())
            multi = int(upto["user_id"].isin(multi_users).sum())
            state = "ok"
            if (not np.isnan(p_c) and p_c < C.SRM_ALERT_P) or (not np.isnan(p_w) and p_w < C.SRM_ALERT_P):
                state = "alert"
            elif (not np.isnan(p_c) and p_c < C.SRM_WARN_P) or (not np.isnan(p_w) and p_w < C.SRM_WARN_P):
                state = "warn"
            rows.append(dict(experiment_phase=phase, assign_date=str(day),
                             assign_date_key=day.year * 10000 + day.month * 100 + day.day,
                             n_control=nc, n_treatment=nt,
                             n_fallback=int((dd["assignment_source"] == "fallback").sum()),
                             n_primary=int((dd["assignment_source"] == "primary").sum()),
                             srm_chisq_cumulative=None if np.isnan(chi_c) else round(chi_c, 3),
                             srm_p_cumulative=round(p_c, 6),
                             srm_chisq_trailing7=None if np.isnan(chi_w) else round(chi_w, 3),
                             srm_p_trailing7=round(p_w, 6),
                             snapshot_log_mismatch_n=mism, multi_assignment_n=multi,
                             alert_state=state))
    out(pd.DataFrame(rows), "fact_srm_daily")


def build_targets():
    win = pd.period_range(C.WINDOW_START, C.WINDOW_END, freq="M")
    n = len(win)
    ramp = np.linspace(0, 1, n)
    rows = []
    for i, p in enumerate(win):
        mk = p.year * 100 + p.month
        rows += [
            (mk, "day7_activation_rate", round(0.44 + 0.08 * ramp[i], 4)),
            (mk, "active_users", int(round(8000 + 52000 * ramp[i]))),
            (mk, "kyc_rejection_rate", 0.10),
            (mk, "flagged_fraud_rate", 0.015),
            (mk, "onboarding_tickets_per_1k", 85),
        ]
    out(pd.DataFrame(rows, columns=["month_key", "kpi", "target_value"]), "fact_targets_month")


def main():
    banner("LumaBank — 03_build_curated")
    CUR.mkdir(parents=True, exist_ok=True)
    build_dim_date()
    dch, dstep = build_static_dims()
    su, dim_user, fva = build_users_and_experiment(dch)
    build_funnel_kyc_activation(su, dch, dstep)
    build_srm_daily(fva, su)
    build_targets()
    banner("03_build_curated complete")


if __name__ == "__main__":
    main()
