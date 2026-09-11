"""
LumaBank — 02_clean_stage.py

Reads data/raw/**, writes one typed stg_<source>_<entity>.parquet per raw entity
to data/staging/, plus a DQ fragment per entity.

Staging = parse, repair, de-duplicate, normalise categories, coerce types.
No cross-source joins. No business logic. No metric definitions.
NOTE: multi-row variant_assignments are KEPT (they are the contamination signal).
"""

from __future__ import annotations

import re
from collections import Counter

import numpy as np
import pandas as pd

import config as C
from utils import EXCEL_EPOCH, banner, write_dq_fragment, write_parquet

RAW = C.RAW_DIR
STG = C.STAGING_DIR


# --------------------------------------------------------------------------- #
# parsers
# --------------------------------------------------------------------------- #
def parse_dt_flex(s: pd.Series, ctr: Counter, hint: str = "br") -> pd.Series:
    """Parse ISO / DD-MM-YYYY / MM-DD-YYYY / Excel serial / epoch-ms / epoch-s."""
    raw = s.astype("string").str.strip()
    out = pd.Series(pd.NaT, index=s.index, dtype="datetime64[ns]")

    num = raw.str.fullmatch(r"\d{5,16}")
    if num.any():
        v = pd.to_numeric(raw[num], errors="coerce")
        as_ms = pd.to_datetime(v.where(v > 10**11), unit="ms", errors="coerce")
        as_s = pd.to_datetime(v.where((v > 10**8) & (v <= 10**11)), unit="s", errors="coerce")
        as_serial = pd.to_datetime(EXCEL_EPOCH) + pd.to_timedelta(v.where(v <= 10**8), unit="D")
        out.loc[num] = as_ms.combine_first(as_s).combine_first(as_serial)
        ctr["epochs_or_serials_converted"] += int(num.sum())

    iso = raw.str.match(r"^\d{4}-\d{2}-\d{2}") & out.isna()
    if iso.any():
        # naive local (America/Sao_Paulo wall time); mixed with/without fractional seconds
        out.loc[iso] = pd.to_datetime(raw[iso], errors="coerce", format="ISO8601")

    slash = raw.str.contains("/", na=False) & out.isna()
    if slash.any():
        fmt = "%m/%d/%Y" if hint == "us" else "%d/%m/%Y"
        out.loc[slash] = pd.to_datetime(raw[slash], format=fmt, errors="coerce")

    ctr["dates_parsed"] += int(out.notna().sum())
    ctr["dates_unparseable"] += int(out.isna().sum() - s.isna().sum())
    return out


_MONEY_RE = re.compile(r"[^\d,.\-]")


def parse_money_brl(s: pd.Series, ctr: Counter) -> pd.Series:
    raw = s.astype("string").str.strip()
    empty = raw.isna() | (raw == "") | (raw.str.lower() == "nan")
    was_text = int((~empty & raw.str.contains(r"[R$ ]", na=False)).sum())

    def one(x):
        if x is None or x is pd.NA:
            return np.nan
        x = _MONEY_RE.sub("", str(x))
        if "," in x:
            x = x.replace(".", "").replace(",", ".")
        try:
            return float(x)
        except ValueError:
            return np.nan

    out = pd.Series([np.nan if e else one(v) for e, v in zip(empty.to_numpy(), raw.to_numpy())],
                    index=s.index, dtype=float)
    ctr["money_strings_parsed"] += was_text
    return out


def load_vocab(name: str, key="raw_value", val="canonical") -> dict:
    df = pd.read_csv(C.VOCAB_DIR / name)
    return dict(zip(df[key].astype(str).str.strip().str.lower(), df[val]))


def map_vocab(s: pd.Series, vocab: dict, ctr: Counter, key: str) -> pd.Series:
    k = s.astype("string").str.strip().str.lower()
    out = k.map(vocab)
    unknown = out.isna() & k.notna()
    ctr[f"{key}_normalised"] += int((~unknown & k.notna()).sum())
    ctr[f"{key}_unknowns"] += int(unknown.sum())
    return out.where(~unknown, "unknown")


def fix_encoding(s: pd.Series, ctr: Counter) -> pd.Series:
    import ftfy
    raw = s.astype("string")
    bad = raw.str.contains(r"Ã|Â", na=False)
    ctr["mojibake_repaired"] += int(bad.sum())
    return raw.map(lambda x: ftfy.fix_text(x) if isinstance(x, str) else x)


def dq(name: str, ctr: Counter, rows_in: int, rows_out: int):
    ctr["rows_in"], ctr["rows_out"] = rows_in, rows_out
    write_dq_fragment(name, dict(ctr))
    print(f"  {name:36s} in={rows_in:>9,} out={rows_out:>9,}  "
          + " ".join(f"{k}={v}" for k, v in ctr.items() if k not in ("rows_in", "rows_out")))


# --------------------------------------------------------------------------- #
def stage_lumencore():
    banner("stage: Lumen Core")

    ctr = Counter()
    frames = []
    for f in sorted(RAW.glob("lumencore/lumencore__users_snapshot__*.csv")):
        d = pd.read_csv(f, dtype=str)
        d["snapshot_month"] = f.stem.split("__")[-1][:7]
        frames.append(d)
    snap = pd.concat(frames, ignore_index=True)
    rows_in = len(snap)
    snap = snap.sort_values("snapshot_month").drop_duplicates("user_id", keep="last")
    ctr["snapshot_rows_collapsed"] = rows_in - len(snap)
    snap["full_name"] = fix_encoding(snap["full_name"], ctr)
    snap["opened_at"] = parse_dt_flex(snap["opened_at"], ctr, "br")
    write_parquet(snap, STG / "stg_lumencore_users.parquet")
    dq("stg_lumencore_users", ctr, rows_in, len(snap))

    ctr = Counter()
    ac = pd.read_csv(RAW / "lumencore/lumencore__accounts.csv", dtype=str)
    rows_in = len(ac)
    ac = ac.drop_duplicates("account_id", keep="first")
    ac["opened_at"] = parse_dt_flex(ac["opened_at"], ctr, "br")
    write_parquet(ac, STG / "stg_lumencore_accounts.parquet")
    dq("stg_lumencore_accounts", ctr, rows_in, len(ac))

    ctr = Counter()
    tvocab = load_vocab("txn_type_map.csv")
    frames = [pd.read_csv(f, dtype=str) for f in sorted(RAW.glob("lumencore/lumencore__transactions__*.csv*"))]
    tx = pd.concat(frames, ignore_index=True)
    rows_in = len(tx)
    tx = tx.drop_duplicates("txn_id", keep="first")
    ctr["dupe_txn_dropped"] = rows_in - len(tx)
    tx["ts"] = parse_dt_flex(tx["epoch_ms"], ctr)
    tx["type"] = map_vocab(tx["type"], tvocab, ctr, "txn_type")
    tx["amount_brl"] = parse_money_brl(tx["amount"], ctr)
    tx = tx.drop(columns=["epoch_ms", "amount"])
    write_parquet(tx, STG / "stg_lumencore_transactions.parquet")
    dq("stg_lumencore_transactions", ctr, rows_in, len(tx))

    ctr = Counter()
    se = pd.read_csv(RAW / "lumencore/lumencore__account_status_events.csv", dtype=str)
    rows_in = len(se)
    se = se.drop_duplicates("event_id", keep="first")
    ctr["dupe_events_dropped"] = rows_in - len(se)
    se["changed_at"] = parse_dt_flex(se["changed_at"], ctr)
    write_parquet(se, STG / "stg_lumencore_account_status_events.parquet")
    dq("stg_lumencore_account_status_events", ctr, rows_in, len(se))


def stage_flagfox():
    banner("stage: Flagfox")

    ctr = Counter()
    va = pd.read_csv(RAW / "flagfox/flagfox__variant_assignments.csv", dtype=str)
    rows_in = len(va)
    va["assigned_ts"] = pd.to_datetime(va["assigned_at"], utc=True, errors="coerce", format="ISO8601")
    ctr["timestamps_localized"] += int(va["assigned_ts"].notna().sum())
    va["cache_reset"] = va["cache_reset"].isin(["true", "True", "1"])
    va["assignment_seq"] = pd.to_numeric(va["assignment_seq"], errors="coerce").astype("Int64")
    va = va.drop(columns=["assigned_at"]).drop_duplicates(["user_id", "assignment_seq"], keep="first")
    ctr["multi_assignment_users"] = int((va.groupby("user_id").size() > 1).sum())
    write_parquet(va, STG / "stg_flagfox_variant_assignments.parquet")
    dq("stg_flagfox_variant_assignments", ctr, rows_in, len(va))

    ctr = Counter()
    ex = pd.read_csv(RAW / "flagfox/flagfox__exposure_log.csv", dtype=str)
    rows_in = len(ex)
    ex = ex.drop_duplicates(["user_id", "exposed_at", "surface", "cache_reset"], keep="first")
    ctr["dupe_exposure_dropped"] = rows_in - len(ex)
    ex["exposed_ts"] = pd.to_datetime(ex["exposed_at"], utc=True, errors="coerce", format="ISO8601")
    ex["cache_reset"] = ex["cache_reset"].isin(["true", "True", "1"])
    ex = ex.drop(columns=["exposed_at"])
    write_parquet(ex, STG / "stg_flagfox_exposure_log.parquet")
    dq("stg_flagfox_exposure_log", ctr, rows_in, len(ex))

    ctr = Counter()
    sn = pd.read_csv(next(RAW.glob("flagfox/flagfox__variant_snapshot.csv*")), dtype=str)
    rows_in = len(sn)
    sn = sn.drop_duplicates(["snapshot_date", "user_id"], keep="last")
    ctr["snapshot_rows_collapsed"] = rows_in - len(sn)
    write_parquet(sn, STG / "stg_flagfox_variant_snapshot.parquet")
    dq("stg_flagfox_variant_snapshot", ctr, rows_in, len(sn))


def stage_trilha():
    banner("stage: Trilha")
    svocab = load_vocab("step_map.csv")

    ctr = Counter()
    st = pd.read_csv(next(RAW.glob("trilha/trilha__onboarding_step_events.csv*")), dtype=str)
    rows_in = len(st)
    st["step_name"] = map_vocab(st["step_name"], svocab, ctr, "step")
    st["occurred_ts"] = parse_dt_flex(st["occurred_at"], ctr)
    st = st.drop(columns=["occurred_at"]).drop_duplicates(["user_id", "step_name"], keep="first")
    ctr["dupe_steps_dropped"] = rows_in - len(st)
    write_parquet(st, STG / "stg_trilha_onboarding_steps.parquet")
    dq("stg_trilha_onboarding_steps", ctr, rows_in, len(st))

    ctr = Counter()
    ks = pd.read_csv(RAW / "trilha/trilha__kyc_submissions.csv", dtype=str)
    rows_in = len(ks)
    ks = ks.drop_duplicates("submission_id", keep="first")
    ks["submitted_ts"] = parse_dt_flex(ks["submitted_at"], ctr)
    ks["doc_type"] = ks["doc_type"].str.strip().str.lower()
    ks["submitted_after_account"] = ks["submitted_after_account"].isin(["True", "true", "1"])
    ks = ks.drop(columns=["submitted_at"])
    write_parquet(ks, STG / "stg_trilha_kyc_submissions.parquet")
    dq("stg_trilha_kyc_submissions", ctr, rows_in, len(ks))


def stage_riskguard():
    banner("stage: RiskGuard")
    rvocab = load_vocab("kyc_reason_map.csv")
    rgrp = load_vocab("kyc_reason_map.csv", val="reason_group")

    ctr = Counter()
    kd = pd.read_csv(RAW / "riskguard/riskguard__kyc_decisions.csv", dtype=str)
    rows_in = len(kd)
    kd = kd.drop_duplicates(["user_id", "decided_at", "outcome"], keep="first")
    kd["decided_ts"] = pd.to_datetime(kd["decided_at"], utc=True, errors="coerce", format="ISO8601")
    kd["time_imputed"] = kd["decided_at"].str.fullmatch(r"\d{4}-\d{2}-\d{2}").fillna(False)
    ctr["decisions_date_only"] = int(kd["time_imputed"].sum())
    kd["outcome"] = kd["outcome"].str.strip().str.lower()
    k = kd["reason_code"].astype("string").str.strip().str.lower()
    kd["reason_code_clean"] = k.map(rvocab).fillna("unknown")
    kd["reason_group"] = k.map(rgrp).fillna("n/a")
    kd = kd.drop(columns=["decided_at"])
    write_parquet(kd, STG / "stg_riskguard_kyc_decisions.parquet")
    dq("stg_riskguard_kyc_decisions", ctr, rows_in, len(kd))

    rc = pd.read_csv(RAW / "riskguard/riskguard__kyc_reason_codes.csv", dtype=str)
    write_parquet(rc, STG / "stg_riskguard_kyc_reason_codes.parquet")
    dq("stg_riskguard_kyc_reason_codes", Counter(), len(rc), len(rc))

    ctr = Counter()
    fr = pd.read_csv(RAW / "riskguard/riskguard__fraud_signals.csv", dtype=str)
    rows_in = len(fr)
    fr = fr.drop_duplicates("signal_id", keep="first")
    fr["signal_ts"] = parse_dt_flex(fr["signal_ts"], ctr)
    fr["score"] = pd.to_numeric(fr["score"], errors="coerce")
    fr["confirmed"] = fr["confirmed"].isin(["true", "True", "1"])
    write_parquet(fr, STG / "stg_riskguard_fraud_signals.parquet")
    dq("stg_riskguard_fraud_signals", ctr, rows_in, len(fr))


def stage_beacon():
    banner("stage: Beacon")
    pvocab = load_vocab("platform_map.csv")

    ctr = Counter()
    rl = pd.read_excel(RAW / "beacon/beacon__app_releases.xlsx", dtype=str)
    rows_in = len(rl)
    rl["released_at"] = parse_dt_flex(rl["released_at"], ctr)
    rl["platform"] = map_vocab(rl["platform"], pvocab, ctr, "platform")
    rl["rollout_pct"] = pd.to_numeric(rl["rollout_pct"].str.replace("%", "", regex=False), errors="coerce")
    write_parquet(rl, STG / "stg_beacon_app_releases.parquet")
    dq("stg_beacon_app_releases", ctr, rows_in, len(rl))

    ctr = Counter()
    cl = pd.read_csv(RAW / "beacon/beacon__deploy_changelog.csv", dtype=str)
    rows_in = len(cl)
    cl["changed_ts"] = parse_dt_flex(cl["changed_at"], ctr)
    cl = cl.drop(columns=["changed_at"])
    write_parquet(cl, STG / "stg_beacon_deploy_changelog.parquet")
    dq("stg_beacon_deploy_changelog", ctr, rows_in, len(cl))


def stage_orbita():
    banner("stage: Orbita")
    cvocab = load_vocab("channel_map.csv")
    tvocab = load_vocab("ticket_category_map.csv")

    ctr = Counter()
    aq = pd.read_csv(RAW / "orbita/orbita__acquisition.csv", dtype=str)
    rows_in = len(aq)
    aq = aq.drop_duplicates("user_id", keep="first")
    aq["channel"] = map_vocab(aq["channel"], cvocab, ctr, "channel")
    aq["first_touch_ts"] = parse_dt_flex(aq["first_touch_at"], ctr)
    aq = aq.drop(columns=["first_touch_at"])
    write_parquet(aq, STG / "stg_orbita_acquisition.parquet")
    dq("stg_orbita_acquisition", ctr, rows_in, len(aq))

    ctr = Counter()
    tk = pd.read_csv(RAW / "orbita/orbita__support_tickets.csv", dtype=str, encoding="latin-1")
    rows_in = len(tk)
    tk = tk.drop_duplicates("ticket_id", keep="first")
    ctr["dupe_tickets_dropped"] = rows_in - len(tk)
    tk["cidade"] = fix_encoding(tk["cidade"], ctr).str.title()
    tk["category"] = map_vocab(tk["category"], tvocab, ctr, "category")
    tk["opened_ts"] = parse_dt_flex(tk["opened_at"], ctr)
    tk = tk.drop(columns=["opened_at"])
    write_parquet(tk, STG / "stg_orbita_support_tickets.parquet")
    dq("stg_orbita_support_tickets", ctr, rows_in, len(tk))


def main():
    banner("LumaBank — 02_clean_stage")
    STG.mkdir(parents=True, exist_ok=True)
    stage_lumencore()
    stage_flagfox()
    stage_trilha()
    stage_riskguard()
    stage_beacon()
    stage_orbita()
    banner("02_clean_stage complete")


if __name__ == "__main__":
    main()
