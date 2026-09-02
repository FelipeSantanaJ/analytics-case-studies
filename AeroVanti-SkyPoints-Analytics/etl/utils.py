"""AeroVanti SkyPoints — shared ETL utilities."""

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
# Deterministic RNG
# --------------------------------------------------------------------------- #
def rng(name: str) -> np.random.Generator:
    """A named, reproducible numpy Generator derived from the global SEED.

    Every generator in the pipeline gets its own stream so that adding a draw in
    one place does not shift draws everywhere else.
    """
    h = hashlib.sha256(f"{SEED}:{name}".encode()).digest()
    sub_seed = int.from_bytes(h[:8], "big")
    return np.random.default_rng(sub_seed)


# --------------------------------------------------------------------------- #
# Date helpers
# --------------------------------------------------------------------------- #
EXCEL_EPOCH = date(1899, 12, 30)


def to_excel_serial(d: date) -> int:
    return (d - EXCEL_EPOCH).days


def from_excel_serial(n: float) -> date:
    return EXCEL_EPOCH + timedelta(days=int(round(float(n))))


def month_floor(d: date) -> date:
    return date(d.year, d.month, 1)


def add_months(d: date, n: int) -> date:
    m = d.month - 1 + n
    y = d.year + m // 12
    m = m % 12 + 1
    return date(y, m, 1)


def month_key(d: date) -> int:
    return d.year * 100 + d.month


def date_key(d: date) -> int:
    return d.year * 10000 + d.month * 100 + d.day


def month_range(start: date, end: date) -> list[date]:
    out, cur = [], month_floor(start)
    end = month_floor(end)
    while cur <= end:
        out.append(cur)
        cur = add_months(cur, 1)
    return out


# --------------------------------------------------------------------------- #
# Messy-export helpers (used by 01_generate_raw)
# --------------------------------------------------------------------------- #
def fmt_money_brl(x: float, style: str = "br") -> str:
    """Format a number the way a Brazilian source system would export text money."""
    if x is None or (isinstance(x, float) and np.isnan(x)):
        return ""
    neg = x < 0
    x = abs(round(float(x), 2))
    inteiro, frac = divmod(int(round(x * 100)), 100)
    s = f"{inteiro:,}".replace(",", ".") + f",{frac:02d}"
    if style == "br_symbol":
        s = "R$ " + s
    if neg:
        s = f"({s})" if style == "ledger" else "-" + s
    return s


def jitter_date_string(d: date, fmt: str, gen: np.random.Generator | None = None) -> str:
    """Render a date in one of several source-specific string formats."""
    if fmt == "iso":
        return d.isoformat()
    if fmt == "br":
        return d.strftime("%d/%m/%Y")
    if fmt == "us":
        return d.strftime("%m/%d/%Y")
    if fmt == "excel":
        return str(to_excel_serial(d))
    if fmt == "mixed" and gen is not None:
        return jitter_date_string(d, gen.choice(["iso", "br"]), gen)
    return d.isoformat()


_MOJIBAKE_MAP = str.maketrans(
    {
        "á": "Ã¡", "â": "Ã¢", "ã": "Ã£", "à": "Ã ", "é": "Ã©", "ê": "Ãª",
        "í": "Ã­", "ó": "Ã³", "ô": "Ã´", "õ": "Ãµ", "ú": "Ãº", "ç": "Ã§",
        "Á": "Ã", "Â": "Ã", "Ã": "Ã", "É": "Ã‰", "Ê": "ÃŠ", "Í": "Ã",
        "Ó": "Ã“", "Ô": "Ã”", "Õ": "Ã•", "Ú": "Ãš", "Ç": "Ã‡",
    }
)


def mojibake(s: str) -> str:
    """Simulate Latin-1 bytes mis-decoded as UTF-8."""
    if not isinstance(s, str):
        return s
    return s.translate(_MOJIBAKE_MAP)


# --------------------------------------------------------------------------- #
# IO with OneDrive/Windows lock retries
# --------------------------------------------------------------------------- #
def _atomic_write(path: Path, write_fn) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    last_err = None
    for attempt in range(DQ_WRITE_RETRIES):
        try:
            write_fn(tmp)
            import os

            os.replace(tmp, path)
            return
        except (PermissionError, OSError) as e:  # WinError 5 / 32
            last_err = e
            time.sleep(DQ_WRITE_BACKOFF_SEC * (attempt + 1))
    raise RuntimeError(f"could not write {path} after {DQ_WRITE_RETRIES} attempts: {last_err}")


def write_parquet(df: pd.DataFrame, path: Path) -> None:
    _atomic_write(path, lambda p: df.to_parquet(p, engine="pyarrow", compression=PARQUET_COMPRESSION, index=False))


def write_csv(df: pd.DataFrame, path: Path, **kw) -> None:
    _atomic_write(path, lambda p: df.to_csv(p, index=False, **kw))


def write_raw_csv(df: pd.DataFrame, path: Path, encoding: str = "utf-8", **kw) -> None:
    _atomic_write(path, lambda p: df.to_csv(p, index=False, encoding=encoding, **kw))


# --------------------------------------------------------------------------- #
# DQ fragments
# --------------------------------------------------------------------------- #
def write_dq_fragment(name: str, counters: dict) -> None:
    """One JSON file per staging/curated entity; assembled into dq_report.md later."""
    DQ_FRAGMENTS_DIR.mkdir(parents=True, exist_ok=True)
    payload = {"entity": name, "generated_at": datetime.utcnow().isoformat() + "Z", "counters": counters}
    path = DQ_FRAGMENTS_DIR / f"{name}.json"
    _atomic_write(path, lambda p: p.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8"))


def read_dq_fragments() -> list[dict]:
    if not DQ_FRAGMENTS_DIR.exists():
        return []
    out = []
    for p in sorted(DQ_FRAGMENTS_DIR.glob("*.json")):
        out.append(json.loads(p.read_text(encoding="utf-8")))
    return out


# --------------------------------------------------------------------------- #
# Misc
# --------------------------------------------------------------------------- #
def logistic(x: np.ndarray | float) -> np.ndarray | float:
    return 1.0 / (1.0 + np.exp(-x))


def clip_series(s: pd.Series, lo=None, hi=None) -> pd.Series:
    return s.clip(lower=lo, upper=hi)


def banner(msg: str) -> None:
    print(f"\n{'=' * 78}\n{msg}\n{'=' * 78}", flush=True)
