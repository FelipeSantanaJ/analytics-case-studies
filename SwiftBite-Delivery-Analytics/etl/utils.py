"""SwiftBite Delivery — shared ETL utilities."""

from __future__ import annotations

import hashlib
import json
import time
from datetime import date, datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

from config import (
    DQ_FRAGMENTS_DIR,
    DQ_WRITE_BACKOFF_SEC,
    DQ_WRITE_RETRIES,
    PARQUET_COMPRESSION,
    SEED,
)

# --------------------------------------------------------------------------- #
# Deterministic RNG — one named stream per generator
# --------------------------------------------------------------------------- #
def rng(name: str) -> np.random.Generator:
    h = hashlib.sha256(f"{SEED}:{name}".encode()).digest()
    return np.random.default_rng(int.from_bytes(h[:8], "big"))


# --------------------------------------------------------------------------- #
# Date / time helpers
# --------------------------------------------------------------------------- #
EXCEL_EPOCH = date(1899, 12, 30)


def to_excel_serial(d: date) -> int:
    return (d - EXCEL_EPOCH).days


def from_excel_serial(n: float) -> date:
    return EXCEL_EPOCH + timedelta(days=int(round(float(n))))


def date_key(d: date) -> int:
    return d.year * 10000 + d.month * 100 + d.day


def month_key(d: date) -> int:
    return d.year * 100 + d.month


def month_floor(d: date) -> date:
    return date(d.year, d.month, 1)


def add_months(d: date, n: int) -> date:
    m = d.month - 1 + n
    return date(d.year + m // 12, m % 12 + 1, 1)


def daterange(start: date, end: date):
    cur = start
    while cur <= end:
        yield cur
        cur += timedelta(days=1)


def month_range(start: date, end: date) -> list[date]:
    out, cur = [], month_floor(start)
    end = month_floor(end)
    while cur <= end:
        out.append(cur)
        cur = add_months(cur, 1)
    return out


def window_month_index(d: date, window_start: date) -> int:
    return (d.year - window_start.year) * 12 + (d.month - window_start.month) + 1


# --------------------------------------------------------------------------- #
# Messy-export helpers (used by 01_generate_raw)
# --------------------------------------------------------------------------- #
def fmt_money_brl(x, style: str = "plain") -> str:
    """Format a number the way a Brazilian source system would export text money."""
    if x is None or (isinstance(x, float) and np.isnan(x)):
        return ""
    neg = x < 0
    x = abs(round(float(x), 2))
    inteiro, frac = divmod(int(round(x * 100)), 100)
    s = f"{inteiro:,}".replace(",", ".") + f",{frac:02d}"
    if style == "symbol":
        s = "R$ " + s
    if neg:
        s = f"({s})" if style == "parens" else "-" + s
    return s


def fmt_dt(dt: datetime, fmt: str) -> str:
    if fmt == "iso":
        return dt.replace(microsecond=0).isoformat()
    if fmt == "iso_z":                       # UTC feeds
        return dt.replace(microsecond=0).isoformat() + "Z"
    if fmt == "br_datetime":
        return dt.strftime("%d/%m/%Y %H:%M")
    if fmt == "epoch_ms":
        return str(int(dt.timestamp() * 1000))
    return dt.replace(microsecond=0).isoformat()


_MOJIBAKE_MAP = str.maketrans({
    "á": "Ã¡", "â": "Ã¢", "ã": "Ã£", "à": "Ã ", "é": "Ã©", "ê": "Ãª", "í": "Ã­",
    "ó": "Ã³", "ô": "Ã´", "õ": "Ãµ", "ú": "Ãº", "ç": "Ã§", "Á": "Ã", "É": "Ã‰",
    "Ç": "Ã‡",
})


def mojibake(s):
    if not isinstance(s, str):
        return s
    return s.translate(_MOJIBAKE_MAP)


# --------------------------------------------------------------------------- #
# Geometry — synthetic grid zones, point-in-cell lookup
# --------------------------------------------------------------------------- #
def haversine_km(lat1, lon1, lat2, lon2):
    r = 6371.0
    p1, p2 = np.radians(lat1), np.radians(lat2)
    dphi = np.radians(lat2 - lat1)
    dlmb = np.radians(lon2 - lon1)
    a = np.sin(dphi / 2) ** 2 + np.cos(p1) * np.cos(p2) * np.sin(dlmb / 2) ** 2
    return 2 * r * np.arcsin(np.sqrt(a))


# --------------------------------------------------------------------------- #
# IO with OneDrive / Windows lock retries
# --------------------------------------------------------------------------- #
def _atomic_write(path: Path, write_fn) -> None:
    import os
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    last_err = None
    for attempt in range(DQ_WRITE_RETRIES):
        try:
            write_fn(tmp)
            os.replace(tmp, path)
            return
        except (PermissionError, OSError) as e:
            last_err = e
            time.sleep(DQ_WRITE_BACKOFF_SEC * (attempt + 1))
    # last resort: write in place (non-atomic) — tolerates transient sync locks
    try:
        write_fn(path)
        return
    except (PermissionError, OSError):
        pass
    raise RuntimeError(f"could not write {path} after {DQ_WRITE_RETRIES} attempts: {last_err}")


def write_parquet(df: pd.DataFrame, path: Path) -> None:
    _atomic_write(path, lambda p: df.to_parquet(p, engine="pyarrow",
                                                compression=PARQUET_COMPRESSION, index=False))


def write_csv(df: pd.DataFrame, path: Path, **kw) -> None:
    _atomic_write(path, lambda p: df.to_csv(p, index=False, **kw))


def read_parquet(path: Path) -> pd.DataFrame:
    return pd.read_parquet(path, engine="pyarrow")


# --------------------------------------------------------------------------- #
# DQ fragments
# --------------------------------------------------------------------------- #
def write_dq_fragment(name: str, counters: dict) -> None:
    DQ_FRAGMENTS_DIR.mkdir(parents=True, exist_ok=True)
    payload = {"entity": name, "generated_at": datetime.utcnow().isoformat() + "Z",
               "counters": counters}
    _atomic_write(DQ_FRAGMENTS_DIR / f"{name}.json",
                  lambda p: p.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8"))


def read_dq_fragments() -> list[dict]:
    if not DQ_FRAGMENTS_DIR.exists():
        return []
    return [json.loads(p.read_text(encoding="utf-8"))
            for p in sorted(DQ_FRAGMENTS_DIR.glob("*.json"))]


# --------------------------------------------------------------------------- #
# Misc
# --------------------------------------------------------------------------- #
def logistic(x):
    return 1.0 / (1.0 + np.exp(-x))


def interp_map(x: float, table: dict) -> float:
    """Piecewise-linear interpolation over a {x: y} dict (keys sorted)."""
    xs = sorted(table)
    if x <= xs[0]:
        return table[xs[0]]
    if x >= xs[-1]:
        return table[xs[-1]]
    for lo, hi in zip(xs, xs[1:]):
        if lo <= x <= hi:
            t = (x - lo) / (hi - lo)
            return table[lo] * (1 - t) + table[hi] * t
    return table[xs[-1]]


def banner(msg: str) -> None:
    print(f"\n{'=' * 78}\n{msg}\n{'=' * 78}", flush=True)
