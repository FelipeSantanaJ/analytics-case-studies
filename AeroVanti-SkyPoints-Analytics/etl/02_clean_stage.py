"""
AeroVanti SkyPoints — 02_clean_stage.py

Reads data/raw/**, writes one typed stg_<source>_<entity>.parquet per raw entity
to data/staging/, plus a DQ fragment per entity to data/quality/dq_fragments/.

Staging = parse, repair, de-duplicate, normalise categories, coerce types.
No cross-source joins. No business logic. No metric definitions.
"""

from __future__ import annotations

import re
from collections import Counter

import numpy as np
import pandas as pd

import config as C
from utils import EXCEL_EPOCH, banner, rng, write_dq_fragment, write_parquet

RAW = C.RAW_DIR
STG = C.STAGING_DIR


# --------------------------------------------------------------------------- #
# parsers (vectorized)
# --------------------------------------------------------------------------- #
def parse_dates(s: pd.Series, hint: str, ctr: Counter) -> pd.Series:
    raw = s.astype("string").str.strip()
    out = pd.Series(pd.NaT, index=s.index, dtype="datetime64[ns]")

    is_serial = raw.str.fullmatch(r"\d{4,6}")
    if is_serial.any():
        vals = pd.to_numeric(raw[is_serial], errors="coerce")
        out.loc[is_serial] = pd.to_datetime(EXCEL_EPOCH) + pd.to_timedelta(vals, unit="D")
        ctr["excel_serials_converted"] += int(is_serial.sum())

    iso = raw.str.match(r"^\d{4}-\d{2}-\d{2}") & out.isna()
    if iso.any():
        out.loc[iso] = pd.to_datetime(raw[iso].str.slice(0, 10), format="%Y-%m-%d", errors="coerce")

    slash = raw.str.contains(r"/", na=False) & out.isna()
    if slash.any():
        fmt = "%m/%d/%Y" if hint == "us" else "%d/%m/%Y"
        out.loc[slash] = pd.to_datetime(raw[slash], format=fmt, errors="coerce")

    ctr["dates_parsed"] += int(out.notna().sum())
    ctr["dates_unparseable"] += int(out.isna().sum() - s.isna().sum())
    return out


_MONEY_RE = re.compile(r"[^\d,.\-()]")


def parse_money_brl(s: pd.Series, ctr: Counter) -> pd.Series:
    raw = s.astype("string").str.strip()
    empty = raw.isna() | (raw == "") | (raw.str.lower() == "nan")
    was_text = int((~empty & raw.str.contains(r"[R$.,() ]", na=False)).sum())

    def one(x):
        if x is None or x is pd.NA or (isinstance(x, float) and np.isnan(x)):
            return np.nan
        x = str(x)
        neg = x.startswith("(") or x.startswith("-")
        x = _MONEY_RE.sub("", x).replace("(", "").replace(")", "").replace("-", "")
        if "," in x:                       # BR format: '.' thousands, ',' decimal
            x = x.replace(".", "").replace(",", ".")
        try:
            v = float(x)
        except ValueError:
            return np.nan
        return -v if neg else v

    out = pd.Series([np.nan if e else one(v) for e, v in zip(empty.to_numpy(), raw.to_numpy())],
                    index=s.index, dtype=float)
    ctr["money_strings_parsed"] += was_text
    ctr["money_negatives_from_parens"] += int((out < 0).sum())
    ctr["money_null_from_blank"] += int(empty.sum())
    return out


def parse_points(s: pd.Series, ctr: Counter) -> pd.Series:
    raw = s.astype("string").str.strip()
    txt = raw.str.contains(r"[.,]", na=False)
    cleaned = raw.str.replace(".", "", regex=False).str.replace(",", "", regex=False)
    out = pd.to_numeric(cleaned, errors="coerce")
    ctr["points_strings_parsed"] += int(txt.sum())
    ctr["points_unparseable"] += int(out.isna().sum() - s.isna().sum())
    return out


def load_vocab(name: str) -> dict:
    df = pd.read_csv(C.VOCAB_DIR / name)
    return dict(zip(df["raw_value"].astype(str).str.strip().str.lower(), df["canonical"]))


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
    out = raw.map(lambda x: ftfy.fix_text(x) if isinstance(x, str) else x)
    ctr["mojibake_repaired"] += int(bad.sum())
    return out


def dq(name: str, ctr: Counter, rows_in: int, rows_out: int):
    ctr["rows_in"] = rows_in
    ctr["rows_out"] = rows_out
    write_dq_fragment(name, dict(ctr))
    print(f"  {name:38s} in={rows_in:>9,} out={rows_out:>9,}  "
          + " ".join(f"{k}={v}" for k, v in ctr.items() if k not in ('rows_in', 'rows_out')))


# --------------------------------------------------------------------------- #
# SkyCore
# --------------------------------------------------------------------------- #
def stage_skycore():
    banner("stage: SkyCore")

    # ---- members_snapshot: collapse to one row per member per month --------
    ctr = Counter()
    frames = []
    for f in sorted(RAW.glob("skycore/skycore__members_snapshot__*.csv")):
        ym = f.stem.split("__")[-1][:7]
        d = pd.read_csv(f, dtype=str)
        d["snapshot_month"] = ym
        frames.append(d)
    snap = pd.concat(frames, ignore_index=True)
    rows_in = len(snap)
    # keep the last occurrence per (member, month) -> collapses the intra-month dumps
    snap = snap.drop_duplicates(["member_id", "snapshot_month"], keep="last").copy()
    ctr["snapshot_rows_collapsed"] = rows_in - len(snap)
    snap["member_since"] = parse_dates(snap["member_since"], "br", ctr)
    snap["balance_points"] = parse_points(snap["balance_points"], ctr).astype("Int64")
    snap["home_city"] = snap["home_city"].str.title()
    snap["current_tier"] = snap["current_tier"].str.strip().str.capitalize()
    write_parquet(snap, STG / "stg_skycore_members.parquet")
    dq("stg_skycore_members", ctr, rows_in, len(snap))

    # ---- point_transactions: dedupe across the month-file overlap ---------
    ctr = Counter()
    tv = load_vocab("txn_type_map.csv")
    frames = []
    for f in sorted(RAW.glob("skycore/skycore__point_transactions__*.csv*")):
        frames.append(pd.read_csv(f, dtype=str))
    tx = pd.concat(frames, ignore_index=True)
    rows_in = len(tx)
    tx = tx.drop_duplicates("txn_id", keep="first").copy()
    ctr["dupe_txn_dropped"] = rows_in - len(tx)
    tx["txn_type"] = map_vocab(tx["txn_type"], tv, ctr, "categories")
    tx["txn_date"] = parse_dates(tx["txn_date"], "br", ctr)
    tx["points"] = parse_points(tx["points"], ctr).astype("Int64")
    tx["value_brl"] = parse_money_brl(tx["value_brl"], ctr)
    tx["earn_source"] = tx["earn_source"].fillna("").str.strip()
    tx["reward_name"] = tx["reward_name"].fillna("").str.strip()
    # sign hygiene: earn positive, redeem/expire negative
    sign_ok = np.where(tx["txn_type"].eq("earn"), tx["points"] > 0, tx["points"] < 0)
    ctr["points_sign_fixed"] = int((~sign_ok & tx["points"].notna()).sum())
    tx.loc[tx["txn_type"].eq("earn"), "points"] = tx["points"].abs()
    tx.loc[tx["txn_type"].isin(["redeem", "expire"]), "points"] = -tx["points"].abs()
    write_parquet(tx, STG / "stg_skycore_point_transactions.parquet")
    dq("stg_skycore_point_transactions", ctr, rows_in, len(tx))

    # ---- tier snapshots monthly -----------------------------------------
    ctr = Counter()
    ts = pd.read_csv(next(RAW.glob("skycore/skycore__tier_snapshots_monthly.csv*")), dtype=str)
    rows_in = len(ts)
    ts = ts.drop_duplicates(["member_id", "ym"], keep="last")
    ts["tier"] = ts["tier"].str.strip().str.capitalize()
    write_parquet(ts, STG / "stg_skycore_tier_snapshots.parquet")
    dq("stg_skycore_tier_snapshots", ctr, rows_in, len(ts))

    # ---- tier change events -------------------------------------------
    ctr = Counter()
    ev = pd.read_csv(RAW / "skycore/skycore__tier_change_events.csv", dtype=str)
    rows_in = len(ev)
    ev = ev.drop_duplicates("event_id", keep="first")
    ctr["dupe_events_dropped"] = rows_in - len(ev)
    ev["change_date"] = parse_dates(ev["change_date"], "br", ctr)
    for c in ("from_tier", "to_tier"):
        ev[c] = ev[c].str.strip().str.capitalize()
    write_parquet(ev, STG / "stg_skycore_tier_change_events.parquet")
    dq("stg_skycore_tier_change_events", ctr, rows_in, len(ev))

    # ---- reward catalog ---------------------------------------------
    ctr = Counter()
    rc = pd.read_excel(RAW / "skycore/skycore__reward_catalog.xlsx", dtype=str)
    rows_in = len(rc)
    rc["available_from"] = parse_dates(rc["available_from"], "excel", ctr)
    rc["points_price"] = parse_points(rc["points_price"], ctr).astype("Int64")
    rc["value_per_point_brl"] = pd.to_numeric(rc["value_per_point_brl"], errors="coerce")
    write_parquet(rc, STG / "stg_skycore_reward_catalog.parquet")
    dq("stg_skycore_reward_catalog", ctr, rows_in, len(rc))


# --------------------------------------------------------------------------- #
# BancoAV
# --------------------------------------------------------------------------- #
def stage_bancoav():
    banner("stage: BancoAV")

    ctr = Counter()
    ca = pd.read_csv(RAW / "bancoav/bancoav__card_accounts.csv", dtype=str, encoding="latin-1")
    rows_in = len(ca)
    ca["holder_name"] = fix_encoding(ca["holder_name"], ctr)
    ca["cidade"] = fix_encoding(ca["cidade"], ctr).str.title()
    ca["abertura"] = parse_dates(ca["abertura"], "br", ctr)
    ca["member_id"] = ca["member_id"].replace({"": pd.NA})
    ctr["null_member_id"] = int(ca["member_id"].isna().sum())
    write_parquet(ca, STG / "stg_bancoav_card_accounts.parquet")
    dq("stg_bancoav_card_accounts", ctr, rows_in, len(ca))

    ctr = Counter()
    cs = pd.read_csv(next(RAW.glob("bancoav/bancoav__card_spend_monthly.csv*")),
                     dtype=str, encoding="latin-1")
    rows_in = len(cs)
    cs["competencia"] = parse_dates(cs["competencia"], "excel", ctr)
    cs["competencia_month"] = cs["competencia"].dt.to_period("M").astype(str)
    before = len(cs)
    cs = cs.drop_duplicates(["card_id", "competencia_month"], keep="first")
    ctr["dupe_month_rows_dropped"] = before - len(cs)   # the re-delivered 2025-06 file
    cs["valor_fatura"] = parse_money_brl(cs["valor_fatura"], ctr)
    cs["pontos_gerados"] = pd.to_numeric(cs["pontos_gerados"], errors="coerce").astype("Int64")
    write_parquet(cs, STG / "stg_bancoav_card_spend.parquet")
    dq("stg_bancoav_card_spend", ctr, rows_in, len(cs))


# --------------------------------------------------------------------------- #
# Reserva
# --------------------------------------------------------------------------- #
def stage_reserva():
    banner("stage: Reserva")
    ch = load_vocab("booking_channel_map.csv")

    ctr = Counter()
    bk = pd.read_csv(next(RAW.glob("reserva/reserva__bookings.csv*")), dtype=str)
    rows_in = len(bk)
    bk = bk.drop_duplicates("booking_id", keep="first")
    ctr["dupe_bookings_dropped"] = rows_in - len(bk)
    bk["booking_date"] = parse_dates(bk["booking_date"], "us", ctr)
    bk["flight_date"] = parse_dates(bk["flight_date"], "us", ctr)
    bk["channel"] = map_vocab(bk["channel"], ch, ctr, "categories")
    bk["loyalty_member_id"] = bk["loyalty_member_id"].replace({"": pd.NA})
    ctr["nonmember_bookings"] = int(bk["loyalty_member_id"].isna().sum())
    write_parquet(bk, STG / "stg_reserva_bookings.parquet")
    dq("stg_reserva_bookings", ctr, rows_in, len(bk))

    ctr = Counter()
    sg = pd.read_csv(next(RAW.glob("reserva/reserva__segments.csv*")), dtype=str)
    rows_in = len(sg)
    sg = sg.drop_duplicates("segment_id", keep="first")
    ctr["dupe_segments_dropped"] = rows_in - len(sg)
    sg["flight_date"] = parse_dates(sg["flight_date"], "us", ctr)
    sg["base_fare"] = pd.to_numeric(sg["base_fare"], errors="coerce")
    sg["taxes"] = pd.to_numeric(sg["taxes"], errors="coerce")
    tax_missing = sg["taxes"].isna() & sg["base_fare"].notna()
    sg.loc[tax_missing, "taxes"] = (sg.loc[tax_missing, "base_fare"] * C.TAXES_SHARE_OF_FARE).round(2)
    ctr["taxes_imputed"] = int(tax_missing.sum())
    sg["is_award"] = sg["is_award"].isin(["Y", "y", "1", "true", "True"])
    sg["points_redeemed"] = pd.to_numeric(sg["points_redeemed"], errors="coerce").astype("Int64")
    sg["loyalty_member_id"] = sg["loyalty_member_id"].replace({"": pd.NA})
    write_parquet(sg, STG / "stg_reserva_segments.parquet")
    dq("stg_reserva_segments", ctr, rows_in, len(sg))


# --------------------------------------------------------------------------- #
# Aurora CRM
# --------------------------------------------------------------------------- #
def stage_aurora():
    banner("stage: Aurora CRM")
    lc = load_vocab("lifecycle_stage_map.csv")

    ctr = Counter()
    cm = pd.read_csv(RAW / "aurora/aurora__crm_contacts.csv", dtype=str)
    rows_in = len(cm)
    cm["cidade"] = fix_encoding(cm["cidade"], ctr).str.title()
    cm["lifecycle_stage"] = map_vocab(cm["lifecycle_stage"], lc, ctr, "categories")
    bd = parse_dates(cm["birth_date"], "br", ctr)
    bad = bd.isna() | (bd.dt.year < 1915) | (bd.dt.year > 2012)
    cm["birth_date"] = bd.where(~bad)
    cm["birth_year_valid"] = ~bad
    ctr["birthyear_invalidated"] = int(bad.sum())
    cm["consent_email"] = cm["consent_email"].isin(["True", "true", "1"])
    write_parquet(cm, STG / "stg_aurora_crm_contacts.parquet")
    dq("stg_aurora_crm_contacts", ctr, rows_in, len(cm))

    ctr = Counter()
    cp = pd.read_csv(RAW / "aurora/aurora__campaign_membership.csv", dtype=str)
    rows_in = len(cp)
    cp["campaign_name"] = cp["campaign_name"].str.strip().str.title()
    cp["joined_date"] = parse_dates(cp["joined_date"], "br", ctr)
    cp = cp.drop_duplicates(["member_id", "campaign_id"], keep="last")
    ctr["dupe_membership_dropped"] = rows_in - len(cp)
    write_parquet(cp, STG / "stg_aurora_campaign_membership.parquet")
    dq("stg_aurora_campaign_membership", ctr, rows_in, len(cp))


# --------------------------------------------------------------------------- #
# Flesk
# --------------------------------------------------------------------------- #
def stage_flesk():
    banner("stage: Flesk")

    ctr = Counter()
    asg = pd.read_csv(RAW / "flesk/flesk__ab_assignments.csv", dtype=str)
    rows_in = len(asg)
    asg["assigned_ts"] = pd.to_datetime(asg["assigned_ts"], utc=True, errors="coerce")
    ctr["timestamps_localized"] += int(asg["assigned_ts"].notna().sum())
    asg["eligible"] = asg["eligible"].isin(["True", "true", "1"])
    for c in ("pre_earn_12m_pts", "pre_flights_12m", "pre_redemptions_12m",
              "pre_balance_pts", "pre_tenure_months"):
        asg[c] = pd.to_numeric(asg[c], errors="coerce").astype("Int64")
    asg["prior_redeemer_flag"] = asg["prior_redeemer_flag"].isin(["True", "true", "1"])
    write_parquet(asg, STG / "stg_flesk_ab_assignments.parquet")
    dq("stg_flesk_ab_assignments", ctr, rows_in, len(asg))

    ctr = Counter()
    ex = pd.read_csv(RAW / "flesk/flesk__exposure_log.csv", dtype=str)
    rows_in = len(ex)
    ex = ex.drop_duplicates(["member_id", "exposure_at", "surface"], keep="first")
    ctr["dupe_exposure_dropped"] = rows_in - len(ex)
    ex["exposure_at"] = pd.to_datetime(ex["exposure_at"], utc=True, errors="coerce")
    write_parquet(ex, STG / "stg_flesk_exposure_log.parquet")
    dq("stg_flesk_exposure_log", ctr, rows_in, len(ex))

    # analyst feeds — typed passthrough (the weekly/outcome truth)
    for feed, tgt in [("redemption_week_feed", "stg_flesk_redemption_week"),
                      ("outcome_feed", "stg_flesk_outcome")]:
        ctr = Counter()
        d = pd.read_csv(RAW / f"flesk/flesk__{feed}.csv")
        write_parquet(d, STG / f"{tgt}.parquet")
        dq(tgt, ctr, len(d), len(d))


# --------------------------------------------------------------------------- #
# Ledger
# --------------------------------------------------------------------------- #
def stage_ledger():
    banner("stage: Ledger")

    ctr = Counter()
    rf = pd.read_excel(RAW / "ledger/ledger__liability_rollforward_monthly.xlsx", dtype=str)
    rows_in = len(rf)
    rf["mes"] = parse_dates(rf["mes"], "excel", ctr)
    rf = rf.sort_index().drop_duplicates("mes", keep="last")   # restated months: last wins
    ctr["restated_months_resolved"] = rows_in - len(rf)
    for c in ("pontos_emitidos", "pontos_resgatados", "pontos_expirados", "saldo_pontos_fim"):
        rf[c] = pd.to_numeric(rf[c], errors="coerce").astype("Int64")
    for c in ("passivo_brl", "provisao_breakage_brl"):
        rf[c] = parse_money_brl(rf[c], ctr)
    write_parquet(rf, STG / "stg_ledger_liability_rollforward.parquet")
    dq("stg_ledger_liability_rollforward", ctr, rows_in, len(rf))

    ctr = Counter()
    rc = pd.read_excel(RAW / "ledger/ledger__reward_cost_monthly.xlsx", dtype=str)
    rows_in = len(rc)
    rc["mes"] = parse_dates(rc["mes"], "excel", ctr)
    rc["custo_caixa_brl"] = parse_money_brl(rc["custo_caixa_brl"], ctr)
    write_parquet(rc, STG / "stg_ledger_reward_cost.parquet")
    dq("stg_ledger_reward_cost", ctr, rows_in, len(rc))


def main():
    banner("AeroVanti SkyPoints — 02_clean_stage")
    STG.mkdir(parents=True, exist_ok=True)
    stage_skycore()
    stage_bancoav()
    stage_reserva()
    stage_aurora()
    stage_flesk()
    stage_ledger()
    banner("02_clean_stage complete")


if __name__ == "__main__":
    main()
