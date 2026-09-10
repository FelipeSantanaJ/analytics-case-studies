"""
02_clean_stage.py — raw/**  ->  data/staging/stg_*.parquet

One typed staging table per raw entity. Parsing, encoding repair, de-duplication,
unit normalisation, category harmonisation. NO cross-source business logic, NO
metric definitions. Every fix is counted into data/quality/dq_fragments/stg_*.json.
"""
from __future__ import annotations

import io
import json
import re
import sys
import datetime as _dt
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

import config as C
from utils import (month_start, month_label, progress, write_parquet, dq_fragment)

try:
    import ftfy
except ImportError:
    ftfy = None

EXCEL_EPOCH = _dt.date(1899, 12, 30)
CNT = {}


def _c(k, n=1):
    CNT[k] = CNT.get(k, 0) + int(n)


# ---------------------------------------------------------------------------
# generic parsers
# ---------------------------------------------------------------------------
_MONTHS = {m: i for i, m in enumerate(
    ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"], 1)}


def parse_date_any(v, prefer="dmy"):
    """Parse a value that may be ISO / DD-MM-YYYY / MM/DD/YYYY / DD-Mon-YY / Excel serial."""
    if v is None or (isinstance(v, float) and np.isnan(v)) or v == "":
        return pd.NaT
    if isinstance(v, (int, float, np.integer, np.floating)) and not isinstance(v, bool):
        f = float(v)
        if 10000 < f < 80000:                       # Excel serial range
            _c("excel_serials_converted")
            return pd.Timestamp(EXCEL_EPOCH + _dt.timedelta(days=int(round(f))))
        return pd.NaT
    s = str(v).strip()
    if re.fullmatch(r"\d{4,5}(\.0)?", s):
        _c("excel_serials_converted")
        return pd.Timestamp(EXCEL_EPOCH + _dt.timedelta(days=int(float(s))))
    m = re.fullmatch(r"(\d{1,2})[-/](\d{1,2})[-/](\d{2,4})", s)
    if m:
        a, b, c = int(m.group(1)), int(m.group(2)), int(m.group(3))
        if c < 100:
            c += 2000
        if prefer == "mdy" or (a > 12 >= b) is False and prefer == "mdy":
            mm, dd = a, b
        else:
            dd, mm = (a, b) if a <= 12 or b > 12 else (a, b)
            if prefer == "mdy":
                dd, mm = b, a
        try:
            _c("dates_parsed")
            return pd.Timestamp(c, mm, dd)
        except ValueError:
            try:
                return pd.Timestamp(c, dd, mm)
            except ValueError:
                _c("dates_unparseable")
                return pd.NaT
    m = re.fullmatch(r"(\d{1,2})-([A-Za-z]{3})-(\d{2,4})", s)
    if m:
        dd = int(m.group(1)); mm = _MONTHS.get(m.group(2).lower()); c = int(m.group(3))
        if c < 100:
            c += 2000
        if mm:
            _c("dates_parsed")
            return pd.Timestamp(c, mm, dd)
    try:
        out = pd.to_datetime(s, utc=False, errors="coerce")
        if pd.isna(out):
            _c("dates_unparseable")
        else:
            _c("dates_parsed")
        return pd.Timestamp(out).tz_localize(None) if out is not pd.NaT and pd.notna(out) else pd.NaT
    except Exception:
        _c("dates_unparseable")
        return pd.NaT


def parse_money(v):
    """'R$ 1.234,56' / '(120.000,00)' / '$12.99' / '-$5' / '' -> float or NaN."""
    if v is None or (isinstance(v, float) and np.isnan(v)):
        return np.nan
    if isinstance(v, (int, float, np.integer, np.floating)) and not isinstance(v, bool):
        return float(v)
    s = str(v).strip()
    if s == "" or s.lower() in ("nan", "none", "n/a"):
        return np.nan
    neg = s.startswith("(") and s.endswith(")")
    if neg:
        s = s[1:-1]
        _c("money_negatives_from_parens")
    neg = neg or s.startswith("-")
    s = re.sub(r"[^\d.,]", "", s)
    if "," in s and "." in s:
        if s.rfind(",") > s.rfind("."):            # 1.234,56  (BR)
            s = s.replace(".", "").replace(",", ".")
        else:                                       # 1,234.56  (US)
            s = s.replace(",", "")
    elif "," in s:
        # comma only: decimal if 2 trailing digits, else thousands
        s = s.replace(",", ".") if re.search(r",\d{2}$", s) else s.replace(",", "")
    if s in ("", ".", "-"):
        return np.nan
    _c("money_strings_parsed")
    val = float(s)
    return -val if neg else val


def fix_text(s):
    if not isinstance(s, str):
        return s
    out = ftfy.fix_text(s) if ftfy else s
    if out != s:
        _c("mojibake_repaired")
    return out


def load_vocab(name):
    df = pd.read_csv(C.VOCAB / f"{name}.csv", dtype=str, keep_default_na=False)
    return dict(zip(df["variant"], df["canonical"]))


CH_V = load_vocab("channels"); PL_V = load_vocab("plan_names")
MK_V = load_vocab("markets"); DV_V = load_vocab("device_families")


def norm(mapping, v, unknown="unknown"):
    if v is None or (isinstance(v, float) and np.isnan(v)):
        return unknown
    key = str(v).strip()
    if key in mapping:
        if mapping[key] != key:
            _c("categories_normalised")
        return mapping[key]
    _c("category_unknowns")
    return unknown


def read_csv(path, **kw):
    return pd.read_csv(path, dtype=str, keep_default_na=False, **kw)


# ---------------------------------------------------------------------------
# vectorised variants (used on the multi-million-row tables)
# ---------------------------------------------------------------------------
def norm_series(s, mapping, unknown="unknown"):
    key = s.astype(str).str.strip()
    out = key.map(mapping)
    _c("category_unknowns", int(out.isna().sum()))
    out = out.fillna(unknown)
    _c("categories_normalised", int((out != key).sum()))
    return out


def parse_date_series(s, style="auto"):
    """style: iso | dmy | mdy | iso8601tz | auto (excel serial + dmy fallback)."""
    ss = s.astype(str).str.strip()
    if style == "iso":
        return pd.to_datetime(ss, format="%Y-%m-%d", errors="coerce")
    if style == "dmy":
        return pd.to_datetime(ss, dayfirst=True, errors="coerce")
    if style == "mdy":
        return pd.to_datetime(ss, format="%m/%d/%Y", errors="coerce")
    if style == "mon":
        return pd.to_datetime(ss, format="%d-%b-%y", errors="coerce")
    if style == "iso8601tz":
        return pd.to_datetime(ss, utc=True, errors="coerce").dt.tz_localize(None)
    is_serial = ss.str.fullmatch(r"\d{4,5}(\.0)?").fillna(False)
    out = pd.Series(pd.NaT, index=ss.index, dtype="datetime64[ns]")
    if is_serial.any():
        ser = pd.to_numeric(ss[is_serial], errors="coerce")
        out.loc[is_serial] = pd.Timestamp(EXCEL_EPOCH) + pd.to_timedelta(ser, unit="D")
        _c("excel_serials_converted", int(is_serial.sum()))
    rest = ~is_serial
    if rest.any():
        out.loc[rest] = pd.to_datetime(ss[rest], dayfirst=True, errors="coerce")
    _c("dates_parsed", int(out.notna().sum()))
    return out


def parse_money_series(s, locale="auto"):
    """locale: br (1.234,56) | us (1,234.56) | auto (decide per row by last separator)."""
    x = s.astype(str).str.strip()
    empty = x.eq("") | x.str.lower().isin(["nan", "none", "n/a"])
    parens = x.str.startswith("(") & x.str.endswith(")")
    neg = parens | x.str.startswith("-")
    _c("money_negatives_from_parens", int(parens.sum()))
    x = x.str.replace(r"[^0-9.,]", "", regex=True)
    if locale == "br":
        x = x.str.replace(".", "", regex=False).str.replace(",", ".", regex=False)
    elif locale == "us":
        x = x.str.replace(",", "", regex=False)
    else:
        br_like = x.str.rfind(",") > x.str.rfind(".")
        xb = x.str.replace(".", "", regex=False).str.replace(",", ".", regex=False)
        xu = x.str.replace(",", "", regex=False)
        x = xb.where(br_like, xu)
    val = pd.to_numeric(x, errors="coerce")
    val = val.where(~neg, -val)
    val[empty] = np.nan
    _c("money_strings_parsed", int(val.notna().sum()))
    return val


def month_idx_from_dt(dt_series):
    y0, m0 = month_start(0).year, month_start(0).month
    d = pd.to_datetime(dt_series, errors="coerce")
    return ((d.dt.year - y0) * 12 + d.dt.month - m0)


# ---------------------------------------------------------------------------
# per-source staging
# ---------------------------------------------------------------------------
def stg_ketch():
    R = C.RAW / "ketch"
    # plan catalog (tiny)
    pc = pd.read_excel(R / "ketch__plan_catalog.xlsx", sheet_name="plans")
    pc["effective_from"] = parse_date_series(pc["effective_from"], "auto")
    pc["list_price"] = parse_money_series(pc["list_price"], "auto")
    pc["plan_name"] = norm_series(pc["plan_name"], PL_V)
    pc["market"] = norm_series(pc["market"], MK_V)
    write_parquet(pc, C.STAGING / "stg_ketch_plan_catalog.parquet")

    # invoices: dedupe on invoice_id across overlapping monthly files
    inv = pd.concat([read_csv(f) for f in sorted(R.glob("ketch__invoices__*.csv"))],
                    ignore_index=True)
    before = len(inv)
    inv = inv.drop_duplicates(subset="invoice_id")
    _c("dupe_invoice_lines_dropped", before - len(inv))
    inv["amount_local"] = np.nan
    for cur, loc, dstyle in [("BRL", "br", "dmy"), ("USD", "us", "mdy"), ("MXN", "us", "iso")]:
        m = inv["currency"].eq(cur)
        if m.any():
            inv.loc[m, "amount_local"] = parse_money_series(inv.loc[m, "amount"], loc).values
            inv.loc[m, "issued_date"] = parse_date_series(inv.loc[m, "issued"], dstyle).values
    inv["issued_date"] = pd.to_datetime(inv.get("issued_date"), errors="coerce")
    inv["status"] = inv["status"].str.lower()
    write_parquet(inv[["invoice_id", "account", "issued_date", "amount_local", "currency", "status"]],
                  C.STAGING / "stg_ketch_invoices.parquet")

    # snapshot: collapse the daily full-dump to one row per account per month, per file
    parts = []
    dropped = 0
    for f in sorted(R.glob("ketch__subscriptions_snapshot__*.csv")):
        d = read_csv(f)
        d["month_label"] = f.stem.split("__")[-1]
        d["snapshot_date"] = parse_date_series(d["snapshot_date"], "iso")
        n0 = len(d)
        d = d.sort_values("snapshot_date").drop_duplicates(subset="account", keep="last")
        dropped += n0 - len(d)
        parts.append(d)
    snap = pd.concat(parts, ignore_index=True)
    _c("snapshot_rows_collapsed", dropped)
    snap["plan_name"] = norm_series(snap["plan_name"], PL_V)
    snap["market"] = norm_series(snap["country"], MK_V)
    write_parquet(snap[["account", "month_label", "snapshot_date", "status", "plan_name",
                        "billing_period", "market"]],
                  C.STAGING / "stg_ketch_subscriptions_snapshot.parquet")
    progress("stg: ketch")


def stg_pagstream():
    R = C.RAW / "pagstream"
    txn = []
    for f in sorted(R.glob("pagstream__transactions__*.csv")):
        txn.append(read_csv(f))
    txn = pd.concat(txn, ignore_index=True)
    # extract the semi-structured meta blob with vectorised regex (no per-row json.loads)
    mt = txn["meta"].astype(str)
    txn["method"] = mt.str.extract(r'"method":\s*"([^"]+)"')[0]
    txn["attempt_number"] = pd.to_numeric(mt.str.extract(r'"attempt":\s*(\d+)')[0],
                                          errors="coerce").fillna(1).astype(int)
    txn["is_dunning"] = mt.str.contains(r'"dunning":\s*true')
    txn["failure_reason"] = mt.str.extract(r'"reason":\s*"([^"]+)"')[0].fillna("")
    txn["amount"] = pd.to_numeric(txn["amount"], errors="coerce")
    txn["fee"] = pd.to_numeric(txn["fee"], errors="coerce")
    # Q06: the gateway 'amount' column is gross for some approved rows and net-of-fee for
    # others (mislabel) and is not reliably separable here. Curated therefore takes the
    # billed amount from the plan-price schedule and uses this table only for
    # status / method / attempt / dunning. We keep the raw amount as `amount_reported`
    # and flag the column as untrusted.
    txn = txn.rename(columns={"amount": "amount_reported"})
    txn["amount_is_trusted"] = False
    txn["ts"] = pd.to_datetime(txn["ts"], utc=True, errors="coerce")
    _c("timestamps_localized", int(txn["ts"].notna().sum()))
    _c("null_keys_flagged", int(txn["account_id"].isna().sum() + txn["account_id"].eq("").sum()))
    txn["account_id"] = txn["account_id"].replace("", np.nan)
    txn["month_idx"] = month_idx_from_dt(txn["ts"].dt.tz_localize(None))
    write_parquet(txn[["txn_id", "account_id", "ts", "month_idx", "amount_reported",
                       "amount_is_trusted", "fee", "currency", "type", "result", "method",
                       "attempt_number", "is_dunning", "failure_reason"]],
                  C.STAGING / "stg_pagstream_transactions.parquet")

    sett = []
    for f in sorted(R.glob("pagstream__settlement__*.csv")):
        sett.append(read_csv(f))
    sett = pd.concat(sett, ignore_index=True)
    for col in ("gross", "fees", "n"):
        sett[col] = pd.to_numeric(sett[col], errors="coerce")
    sett["settle_date"] = sett["settle_date"].map(lambda x: parse_date_any(x))
    write_parquet(sett, C.STAGING / "stg_pagstream_settlement.parquet")
    progress("stg: pagstream")


def stg_identity_crm():
    # accounts (strip BOM)
    raw = (C.RAW / "voxaid" / "voxaid__accounts.csv").read_text(encoding="utf-8-sig")
    _c("bom_stripped", 1)
    acc = pd.read_csv(io.StringIO(raw), dtype=str, keep_default_na=False)
    acc["market"] = norm_series(acc["market"], MK_V)
    acc["primary_device"] = norm_series(acc["primary_device"], DV_V)
    acc["created_date"] = parse_date_series(acc["created_at"], "mon")
    write_parquet(acc[["account_id", "email", "market", "primary_device", "created_date"]],
                  C.STAGING / "stg_voxaid_accounts.parquet")

    reg = read_csv(C.RAW / "voxaid" / "voxaid__device_registrations.csv")
    before = len(reg)
    reg = reg.drop_duplicates()
    _c("dupe_events_dropped", before - len(reg))
    reg["device_family"] = norm_series(reg["device_family"], DV_V)
    reg["registered_date"] = parse_date_series(reg["registered_at"], "iso")
    write_parquet(reg[["account_id", "device_family", "registered_date"]],
                  C.STAGING / "stg_voxaid_device_registrations.parquet")

    # CRM (latin-1 file -> fix)
    crm = pd.read_csv(C.RAW / "bonsai" / "bonsai__crm_contacts.csv", dtype=str,
                      keep_default_na=False, encoding="latin-1")
    crm["full_name"] = crm["full_name"].map(fix_text)
    crm["birth_year"] = pd.to_numeric(crm["birth_year"], errors="coerce")
    bad = crm["birth_year"].isin([0, 1900]) | (crm["birth_year"] < 1920)
    _c("implausible_birth_year_nulled", int(bad.sum()))
    crm.loc[bad, "birth_year"] = np.nan
    crm["lifecycle_stage"] = crm["lifecycle_stage"].str.lower().replace(
        {"novo": "new", "engajado": "engaged"})
    write_parquet(crm[["account_id", "full_name", "lifecycle_stage", "birth_year", "consent_marketing"]],
                  C.STAGING / "stg_bonsai_crm_contacts.parquet")

    wb = read_csv(C.RAW / "bonsai" / "bonsai__winback_membership.csv")
    wb["campaign_norm"] = wb["campaign"].str.lower().str.replace(r"[ _-]", "", regex=True)
    wb["joined_date"] = parse_date_series(wb["joined_at"], "iso")
    write_parquet(wb[["account_id", "campaign_norm", "joined_date"]],
                  C.STAGING / "stg_bonsai_winback_membership.parquet")
    progress("stg: identity + crm")


def stg_entitlement():
    recs = []
    with open(C.RAW / "entitlement" / "entitlement__events.jsonl", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                recs.append(json.loads(line))
    df = pd.DataFrame(recs)
    before = len(df)
    df = df.drop_duplicates(subset="event_id")
    _c("dupe_events_dropped", before - len(df))
    df["occurred_at"] = pd.to_datetime(df["occurred_at"], utc=True, errors="coerce")
    df = df.sort_values(["subject", "occurred_at"]).reset_index(drop=True)
    df["month_idx"] = ((df["occurred_at"].dt.year - month_start(0).year) * 12
                       + df["occurred_at"].dt.month - month_start(0).month)
    for c in ("from_tier", "to_tier", "reason_code"):
        if c not in df.columns:
            df[c] = np.nan
    write_parquet(df[["event_id", "subject", "kind", "occurred_at", "month_idx",
                      "from_tier", "to_tier", "reason_code"]],
                  C.STAGING / "stg_entitlement_events.parquet")
    progress("stg: entitlement")


def stg_content():
    R = C.RAW / "reelbase"
    t = pd.read_excel(R / "reelbase__titles.xlsx", sheet_name="titles")
    t["title"] = t["title"].map(fix_text)
    t["release_date"] = t["release_date"].map(lambda x: parse_date_any(x, prefer="dmy"))
    t["primary_genre"] = t["primary_genre"].replace("", np.nan)
    _c("missing_genre_rows", int(t["primary_genre"].isna().sum()))
    t["is_original"] = t["is_original"].astype(str).str.lower().isin(["y", "1", "true"])
    write_parquet(t[["content_id", "title", "content_type", "primary_genre", "language",
                     "is_original", "release_date", "runtime_min"]],
                  C.STAGING / "stg_reelbase_titles.parquet")

    lw = read_csv(R / "reelbase__licence_windows.csv")
    lw["window_start"] = lw["window_start"].map(lambda x: parse_date_any(x))
    lw["window_end"] = lw["window_end"].map(lambda x: parse_date_any(x))
    lw["market"] = lw["market"].map(lambda x: norm(MK_V, x))
    write_parquet(lw, C.STAGING / "stg_reelbase_licence_windows.parquet")

    # content finance: unpivot amort schedule, parse serial columns + parens money
    am = pd.read_excel(C.RAW / "contentfin" / "contentfin__amort_schedule.xlsx", sheet_name="amort")
    idcol = am.columns[0]
    long = am.melt(id_vars=[idcol], var_name="serial", value_name="raw_amt")
    long["month_date"] = long["serial"].map(lambda x: parse_date_any(x))
    long["amort_usd"] = long["raw_amt"].map(parse_money).abs()
    long = long.dropna(subset=["month_date"])
    long["month_idx"] = ((long["month_date"].dt.year - month_start(0).year) * 12
                         + long["month_date"].dt.month - month_start(0).month)
    long = long[(long["month_idx"] >= 0) & (long["month_idx"] < C.N_MONTHS)]
    write_parquet(long[[idcol, "month_idx", "amort_usd"]].rename(columns={idcol: "content_id"}),
                  C.STAGING / "stg_contentfin_amort_schedule.parquet")

    cm = pd.read_excel(C.RAW / "contentfin" / "contentfin__cash_milestones.xlsx",
                       sheet_name="cash_milestones")
    cm["milestone_date"] = cm["milestone_date"].map(lambda x: parse_date_any(x, prefer="mdy"))
    cm["amount_usd"] = cm["amount"].map(parse_money)
    write_parquet(cm[["content_id", "milestone_date", "amount_usd"]],
                  C.STAGING / "stg_contentfin_cash_milestones.parquet")
    progress("stg: content")


def stg_marketing():
    sw = read_csv(C.RAW / "adbridge" / "adbridge__spend_weekly.csv")
    sw["channel"] = sw["channel"].map(lambda x: norm(CH_V, x))
    for col in ("spend_usd", "impressions", "clicks", "signups_attributed"):
        sw[col] = pd.to_numeric(sw[col], errors="coerce")
    sw["is_test_campaign"] = sw["is_test_campaign"].astype(str).str.lower().isin(["true", "1"])
    sw["week_start"] = sw["week_start"].map(lambda x: parse_date_any(x))
    # Q06 MXN-in-USD column for MX rows -> restore local + recompute usd (rate ~17.8)
    mx = sw["market"].map(lambda x: norm(MK_V, x)) == "MX"
    sw["spend_local"] = np.where(mx, sw["spend_usd"], sw["spend_usd"])
    sw.loc[mx, "spend_usd"] = (sw.loc[mx, "spend_local"] / 17.8).round(2)
    _c("mislabeled_columns_corrected", int(mx.sum()))
    # Q06 partner_bundle rows: clicks actually holds impressions -> clicks unknown
    pb = sw["channel"] == "partner_bundle"
    sw.loc[pb, "clicks"] = np.nan
    _c("mislabeled_columns_corrected", int(pb.sum()))
    sw["market"] = sw["market"].map(lambda x: norm(MK_V, x))
    write_parquet(sw[["week_start", "market", "channel", "campaign_id", "spend_usd", "spend_local",
                      "impressions", "clicks", "signups_attributed", "is_test_campaign"]],
                  C.STAGING / "stg_adbridge_spend_weekly.parquet")

    at = read_csv(C.RAW / "adbridge" / "adbridge__attribution.csv")
    at["channel"] = at["channel"].map(lambda x: norm(CH_V, x))
    at["market"] = at["market"].map(lambda x: norm(MK_V, x))
    at["touch_date"] = at["touch_ts"].map(lambda x: parse_date_any(x))
    write_parquet(at[["market", "channel", "campaign_id", "touch_date"]],
                  C.STAGING / "stg_adbridge_attribution.parquet")

    ssp = read_csv(C.RAW / "voxaads" / "voxaads__ssp_daily_revenue.csv")
    ssp["date"] = ssp["date"].map(lambda x: parse_date_any(x, prefer="mdy"))
    for col in ("impressions_served", "fill_rate", "ecpm_usd", "ad_revenue_usd"):
        ssp[col] = pd.to_numeric(ssp[col], errors="coerce")
    ssp["market"] = ssp["market"].map(lambda x: norm(MK_V, x))
    before = len(ssp)
    ssp = ssp.drop_duplicates(subset=["date", "market"])
    _c("dupe_events_dropped", before - len(ssp))
    write_parquet(ssp, C.STAGING / "stg_voxaads_ssp_daily_revenue.parquet")
    progress("stg: marketing")


def stg_support():
    xw = pd.read_csv(C.VOCAB / "support_reason_crosswalk.csv", dtype=str)
    xwd = {(r.source_version, r.source_reason): (r.reason_category, r.reason_group)
           for r in xw.itertuples()}
    v1 = read_csv(C.RAW / "helpline" / "helpline__v1_tickets.csv")
    v2 = read_csv(C.RAW / "helpdesk" / "helpdesk__v2_tickets.csv")
    _c("support_rows_v1", len(v1)); _c("support_rows_v2", len(v2))
    r1 = pd.DataFrame({
        "ticket_id": v1["TicketID"], "account_id": v1["Account"],
        "created_ts": v1["Created"].map(lambda x: parse_date_any(x)),
        "contact_channel": v1["Channel"].str.lower(),
        "csat_score": pd.to_numeric(v1["CSAT"], errors="coerce") / 5.0,
        "resolution_hours": pd.to_numeric(v1["ResolutionHrs"], errors="coerce"),
        "source_version": "v1", "src_reason": v1["Reason"],
    })
    r2 = pd.DataFrame({
        "ticket_id": v2["ticket_ref"], "account_id": v2["user_id"],
        "created_ts": pd.to_datetime(v2["opened_at"], utc=True, errors="coerce").dt.tz_localize(None),
        "contact_channel": v2["contact_channel"].str.lower(),
        "csat_score": pd.to_numeric(v2["satisfaction_0_10"], errors="coerce") / 10.0,
        "resolution_hours": pd.to_numeric(v2["handle_time_min"], errors="coerce") / 60.0,
        "source_version": "v2", "src_reason": v2["reason_code"],
    })
    _c("csat_rescaled", len(r1) + len(r2))
    both = pd.concat([r1, r2], ignore_index=True)
    before = len(both)
    both = both.drop_duplicates(subset="ticket_id")
    _c("cutover_dupes_dropped", before - len(both))
    cats = both.apply(lambda r: xwd.get((r["source_version"], r["src_reason"]), ("other", "other")),
                      axis=1)
    both["reason_category"] = [c[0] for c in cats]
    both["reason_group"] = [c[1] for c in cats]
    both["month_idx"] = ((pd.to_datetime(both["created_ts"]).dt.year - month_start(0).year) * 12
                         + pd.to_datetime(both["created_ts"]).dt.month - month_start(0).month)
    write_parquet(both[["ticket_id", "account_id", "created_ts", "month_idx", "contact_channel",
                        "reason_category", "reason_group", "csat_score", "resolution_hours",
                        "source_version"]],
                  C.STAGING / "stg_support_tickets.parquet")
    progress("stg: support")


def stg_ledger():
    gl = []
    for f in sorted((C.RAW / "ledger").glob("ledger__gl_trial_balance__*.csv")):
        gl.append(read_csv(f))
    gl = pd.concat(gl, ignore_index=True)
    gl["amount_usd"] = pd.to_numeric(gl["amount_usd"], errors="coerce")
    gl["pnl_line"] = gl["account"].str.extract(r"^\d+\s+(.*)$")[0].str.strip().str.lower().str.replace(
        r"[ &]+", "_", regex=True)
    gl["market"] = gl["market"].map(lambda x: norm(MK_V, x))
    gl["month_idx"] = gl["period"].map(lambda s: (int(s[:4]) - month_start(0).year) * 12
                                       + int(s[5:7]) - month_start(0).month)
    write_parquet(gl[["month_idx", "market", "pnl_line", "amount_usd"]],
                  C.STAGING / "stg_ledger_gl.parquet")

    fx = read_csv(C.RAW / "ledger" / "ledger__fx_rates.csv")
    fx["avg_rate"] = pd.to_numeric(fx["avg_rate"], errors="coerce")
    fx["eop_rate"] = pd.to_numeric(fx["eop_rate"], errors="coerce")
    fx["month_idx"] = fx["month"].map(lambda s: (int(s[:4]) - month_start(0).year) * 12
                                      + int(s[5:7]) - month_start(0).month)
    # Q12 forward-fill missing months per currency
    full = []
    for cur, g in fx.groupby("currency"):
        g = g.set_index("month_idx").reindex(range(C.N_MONTHS))
        miss = int(g["avg_rate"].isna().sum())
        g[["avg_rate", "eop_rate"]] = g[["avg_rate", "eop_rate"]].ffill().bfill()
        g["currency"] = cur
        _c("fx_months_forward_filled", miss)
        full.append(g.reset_index().rename(columns={"index": "month_idx"}))
    fx_full = pd.concat(full, ignore_index=True)
    usd = pd.DataFrame({"month_idx": range(C.N_MONTHS), "currency": "USD",
                        "avg_rate": 1.0, "eop_rate": 1.0})
    fx_full = pd.concat([fx_full[["month_idx", "currency", "avg_rate", "eop_rate"]], usd],
                        ignore_index=True)
    write_parquet(fx_full, C.STAGING / "stg_ledger_fx.parquet")
    progress("stg: ledger")


def stg_playlog_and_app():
    outp = C.STAGING / "stg_playlog"
    outa = C.STAGING / "stg_trackpad_app_events"
    outp.mkdir(parents=True, exist_ok=True)
    outa.mkdir(parents=True, exist_ok=True)
    for f in sorted((C.RAW / "playlog").glob("playlog__*.parquet")):
        ml = f.stem.split("__")[-1]
        idx = (int(ml[:4]) - month_start(0).year) * 12 + int(ml[5:7]) - month_start(0).month
        df = pd.read_parquet(f)
        before = len(df)
        df = df.drop_duplicates(subset="beacon_id")
        _c("dupe_events_dropped", before - len(df))
        df["device_family"] = df["device"].astype(str).str.strip().map(DV_V).fillna("unknown")
        # Q09 unit normalisation: watch_time seconds vs milliseconds (by era + magnitude)
        wt = df["watch_time"].to_numpy(float)
        ms_era = idx >= C.PLAYLOG_MS_ERA_START_IDX
        wt_sec = np.where((np.abs(wt) > 200000) | ms_era, wt / 1000.0, wt)
        _c("watchtime_unit_fixed", int(((np.abs(wt) > 200000) | ms_era).sum()))
        # Q08 negative watch (clock skew) -> abs + flag
        neg = wt_sec < 0
        _c("sign_errors_fixed", int(neg.sum()))
        df["watch_seconds"] = np.abs(wt_sec)
        df["watch_minutes"] = (df["watch_seconds"] / 60.0).clip(upper=1440)
        # Q09 CDN bytes MB (edge-b) -> GB
        gb = np.where(df["edge_provider"].to_numpy() == "edge-b",
                      df["cdn_bytes"].to_numpy(float) / 1024.0, df["cdn_bytes"].to_numpy(float))
        _c("bytes_unit_fixed", int((df["edge_provider"] == "edge-b").sum()))
        df["cdn_gb"] = np.abs(gb)
        df["event_ts_utc"] = pd.to_datetime(df["event_utc"], utc=True, errors="coerce",
                                            format="%Y-%m-%dT%H:%M:%SZ")
        df["local_date"] = df["event_ts_utc"].dt.tz_convert(None).dt.normalize()
        df["month_idx"] = idx
        keep = ["beacon_id", "account_ref", "asset_id", "device_family", "event_ts_utc",
                "local_date", "month_idx", "watch_minutes", "play_starts", "distinct_assets",
                "video_start_failures", "playback_errors", "rebuffer_ratio", "cdn_gb"]
        write_parquet(df[keep], outp / f"{ml}.parquet")

        af = C.RAW / "trackpad" / f"app_events__{ml}.parquet"
        a = pd.read_parquet(af)
        bA = len(a)
        a = a.drop_duplicates(subset="event_id")
        _c("dupe_events_dropped", bA - len(a))
        a["device_family"] = a["device_family"].astype(str).str.strip().map(DV_V).fillna("unknown")
        a["ingest_ts_utc"] = pd.to_datetime(a["ingest_utc"], utc=True, errors="coerce")
        a["local_date"] = pd.to_datetime(a["day"], errors="coerce")
        a["month_idx"] = idx
        write_parquet(a[["event_id", "user_ref", "local_date", "month_idx", "device_family",
                         "app_version", "session_count", "crash_count", "screen_views"]],
                      outa / f"{ml}.parquet")
        progress(f"stg: playlog+app {ml}")


def main():
    t0 = _dt.datetime.now()
    for p in C.STAGING.glob("stg_*"):
        if p.is_file():
            p.unlink()
    progress("STAGING build")
    stg_ketch()
    stg_pagstream()
    stg_identity_crm()
    stg_entitlement()
    stg_content()
    stg_marketing()
    stg_support()
    stg_ledger()
    stg_playlog_and_app()
    dq_fragment("stg_fixes", CNT)
    progress(f"STAGING done in {(_dt.datetime.now()-t0).total_seconds():.0f}s")
    print(json.dumps(CNT, indent=2))


if __name__ == "__main__":
    main()
