"""Shared helpers: deterministic RNG, resilient IO, and messy-format emitters."""
from __future__ import annotations

import hashlib
import io
import json
import os
import time
import datetime as _dt
from pathlib import Path

import numpy as np
import pandas as pd

import config as C


# ---------------------------------------------------------------------------
# Deterministic RNG
# ---------------------------------------------------------------------------
def rng(*name_parts) -> np.random.Generator:
    """A NumPy Generator seeded from SEED + a stable hash of the name parts.

    Lets each generation step draw from an independent, reproducible stream:
        r = rng("world", "acquisition", "BR")
    """
    key = "::".join(str(p) for p in name_parts)
    h = hashlib.sha256(f"{C.SEED}::{key}".encode()).digest()
    seed = int.from_bytes(h[:8], "big")
    return np.random.default_rng(seed)


# ---------------------------------------------------------------------------
# Calendar helpers
# ---------------------------------------------------------------------------
def month_start(idx: int) -> _dt.date:
    """First day of window-month index `idx` (0-based)."""
    y = C.WINDOW_START.year + (C.WINDOW_START.month - 1 + idx) // 12
    m = (C.WINDOW_START.month - 1 + idx) % 12 + 1
    return _dt.date(y, m, 1)


def month_end(idx: int) -> _dt.date:
    nxt = month_start(idx + 1)
    return nxt - _dt.timedelta(days=1)


def month_label(idx: int) -> str:
    d = month_start(idx)
    return f"{d.year}-{d.month:02d}"


def all_month_indices() -> range:
    return range(C.N_MONTHS)


def date_key(d) -> int:
    if d is None or (isinstance(d, float) and np.isnan(d)):
        return -1
    d = pd.Timestamp(d)
    return d.year * 10000 + d.month * 100 + d.day


def days_in_month(idx: int) -> int:
    return (month_end(idx) - month_start(idx)).days + 1


# ---------------------------------------------------------------------------
# Resilient parquet/csv IO (OneDrive/Windows file-lock retry, atomic replace)
# ---------------------------------------------------------------------------
def _atomic_write(path: Path, write_fn, attempts: int = 5, backoff: float = 0.8):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + f".tmp{os.getpid()}")
    last_err = None
    for i in range(attempts):
        try:
            write_fn(tmp)
            os.replace(tmp, path)
            return path
        except (PermissionError, OSError) as e:      # WinError 5 / 32
            last_err = e
            time.sleep(backoff * (i + 1))
            try:
                if tmp.exists():
                    tmp.unlink()
            except OSError:
                pass
    raise RuntimeError(f"could not write {path} after {attempts} attempts: {last_err}")


def write_parquet(df: pd.DataFrame, path, **kw):
    return _atomic_write(Path(path), lambda p: df.to_parquet(p, index=False, **kw))


def write_csv(df: pd.DataFrame, path, **kw):
    kw.setdefault("index", False)
    return _atomic_write(Path(path), lambda p: df.to_csv(p, **kw))


def write_text(text: str, path, encoding: str = "utf-8"):
    return _atomic_write(Path(path), lambda p: Path(p).write_text(text, encoding=encoding))


def write_bytes(data: bytes, path):
    return _atomic_write(Path(path), lambda p: Path(p).write_bytes(data))


def write_jsonl(records, path):
    buf = io.StringIO()
    for r in records:
        buf.write(json.dumps(r, default=str, ensure_ascii=False))
        buf.write("\n")
    return write_text(buf.getvalue(), path)


def read_parquet(path) -> pd.DataFrame:
    return pd.read_parquet(path)


# ---------------------------------------------------------------------------
# DQ fragments
# ---------------------------------------------------------------------------
def dq_fragment(name: str, counters: dict):
    """Write one DQ fragment (a dict of named counts/metrics)."""
    payload = {"fragment": name, "generated_at": _dt.datetime.now().isoformat(timespec="seconds"),
               "counters": {k: (int(v) if isinstance(v, (np.integer,)) else v) for k, v in counters.items()}}
    write_text(json.dumps(payload, indent=2, default=str), C.DQ_FRAGMENTS / f"{name}.json")


def load_dq_fragments() -> list[dict]:
    out = []
    for f in sorted(C.DQ_FRAGMENTS.glob("*.json")):
        out.append(json.loads(f.read_text(encoding="utf-8")))
    return out


# ---------------------------------------------------------------------------
# Messy-format emitters (used by 01_generate_raw.py)
# ---------------------------------------------------------------------------
EXCEL_EPOCH = _dt.date(1899, 12, 30)


def to_excel_serial(d) -> float:
    d = pd.Timestamp(d).date()
    return float((d - EXCEL_EPOCH).days)


def fmt_date(d, style: str) -> str:
    """style in {iso, br, us, dmy_dash, mon, ts_utc}"""
    d = pd.Timestamp(d)
    if style == "iso":
        return d.strftime("%Y-%m-%d")
    if style == "br":
        return d.strftime("%d/%m/%Y")
    if style == "us":
        return d.strftime("%m/%d/%Y")
    if style == "dmy_dash":
        return d.strftime("%d-%m-%Y")
    if style == "mon":
        return d.strftime("%d-%b-%y")
    if style == "ts_utc":
        return d.strftime("%Y-%m-%dT%H:%M:%SZ")
    raise ValueError(style)


def money_str(value: float, locale: str) -> str:
    """Render a number as a locale-flavoured money string.

    locale in {br, mx, us, parens_br}
    """
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return ""
    neg = value < 0
    v = abs(float(value))
    if locale in ("br", "parens_br"):
        s = f"{v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        s = f"R$ {s}"
        if neg:
            return f"({s})" if locale == "parens_br" else f"-{s}"
        return s
    if locale == "mx":
        s = f"$ {v:,.2f}"           # US-style separators, MXN implied
        return f"-{s}" if neg else s
    if locale == "us":
        s = f"${v:,.2f}"
        return f"-{s}" if neg else s
    raise ValueError(locale)


def maybe_mojibake(s: str, do_it: bool) -> str:
    """Simulate a Latin-1 string decoded as UTF-8 (reversible with ftfy)."""
    if not do_it or not isinstance(s, str):
        return s
    try:
        return s.encode("utf-8").decode("latin-1")
    except (UnicodeEncodeError, UnicodeDecodeError):
        return s


def add_bom(text: str) -> str:
    return "﻿" + text


def jitter_category(value: str, r: np.random.Generator, variants: dict[str, list[str]]) -> str:
    """Randomly replace a canonical category value with a noisy variant."""
    opts = variants.get(value)
    if not opts:
        return value
    return str(r.choice(opts + [value]))


CATEGORY_VARIANTS = {
    "paid_social": ["Paid Social", "paid_social", "FB/IG", "Meta", "social-paid"],
    "paid_search": ["Paid Search", "paid_search", "SEM", "Google Ads", "search"],
    "partner_bundle": ["Partner Bundle", "partner_bundle", "Telco Bundle", "bundle", "PARTNER"],
    "affiliate": ["Affiliate", "affiliate", "AFF", "affiliates"],
    "direct": ["Direct", "direct", "DIRECT", "web-direct"],
    "organic": ["Organic", "organic", "ORG", "unpaid"],
    "Basico": ["Basico", "Básico", "BASICO", "basic", "Voxa Basico"],
    "Standard": ["Standard", "STANDARD", "std", "Voxa Standard"],
    "Premium": ["Premium", "PREMIUM", "prem", "Voxa Premium"],
    "BR": ["BR", "Brasil", "Brazil", "bra"],
    "MX": ["MX", "Mexico", "México", "mex"],
    "US": ["US", "USA", "United States", "us"],
    "smart_tv": ["smart_tv", "Smart TV", "SmartTV", "CTV", "TV"],
    "streaming_stick": ["streaming_stick", "Streaming Stick", "stick", "FireTV/Chromecast"],
    "mobile_ios": ["mobile_ios", "iOS", "iPhone", "ios"],
    "mobile_android": ["mobile_android", "Android", "android"],
    "web": ["web", "Web", "Browser", "desktop"],
    "console": ["console", "Console", "Game Console", "PS/Xbox"],
}


def progress(msg: str):
    print(f"  [{_dt.datetime.now():%H:%M:%S}] {msg}", flush=True)
