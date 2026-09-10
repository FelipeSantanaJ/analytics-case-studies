"""Shared helpers for the VoltEdge ETL pipeline."""

from __future__ import annotations

import datetime as dt
import json
import random
import time
from pathlib import Path

import numpy as np
import pandas as pd

import config

# --------------------------------------------------------------------------------------
# RNG
# --------------------------------------------------------------------------------------

def rng(offset: int = 0) -> np.random.Generator:
    """A fresh NumPy Generator seeded deterministically from config.SEED."""
    return np.random.default_rng(config.SEED + offset)


def py_random(offset: int = 0) -> random.Random:
    """A seeded stdlib Random (used for Faker and simple choices)."""
    return random.Random(config.SEED + offset)


# --------------------------------------------------------------------------------------
# Console
# --------------------------------------------------------------------------------------

_T0 = time.time()

def log(msg: str) -> None:
    print(f"[{time.time() - _T0:7.1f}s] {msg}", flush=True)


def section(title: str) -> None:
    print(f"\n{'=' * 78}\n  {title}\n{'=' * 78}", flush=True)


# --------------------------------------------------------------------------------------
# Dates
# --------------------------------------------------------------------------------------

def date_range(start: dt.date, end: dt.date) -> list[dt.date]:
    n = (end - start).days + 1
    return [start + dt.timedelta(days=i) for i in range(n)]


def month_starts(start: dt.date, end: dt.date) -> list[dt.date]:
    out, cur = [], dt.date(start.year, start.month, 1)
    while cur <= end:
        out.append(cur)
        cur = dt.date(cur.year + (cur.month == 12), (cur.month % 12) + 1, 1)
    return out


def month_end(d: dt.date) -> dt.date:
    nxt = dt.date(d.year + (d.month == 12), (d.month % 12) + 1, 1)
    return nxt - dt.timedelta(days=1)


def add_months(d: dt.date, n: int) -> dt.date:
    m = d.month - 1 + n
    return dt.date(d.year + m // 12, m % 12 + 1, min(d.day, 28))


def date_key(d: dt.date) -> int:
    return d.year * 10000 + d.month * 100 + d.day


def black_friday(year: int) -> dt.date:
    """US Black Friday = day after the 4th Thursday of November."""
    d = dt.date(year, 11, 1)
    thursdays = [d + dt.timedelta(days=i) for i in range(30)
                 if (d + dt.timedelta(days=i)).month == 11
                 and (d + dt.timedelta(days=i)).weekday() == 3]
    return thursdays[3] + dt.timedelta(days=1)


# --------------------------------------------------------------------------------------
# Sampling
# --------------------------------------------------------------------------------------

def weighted_choice(gen: np.random.Generator, mapping: dict, size: int | None = None):
    keys = list(mapping.keys())
    probs = np.array(list(mapping.values()), dtype=float)
    probs = probs / probs.sum()
    idx = gen.choice(len(keys), size=size, p=probs)
    if size is None:
        return keys[idx]
    return [keys[i] for i in idx]


def psychological_price(x: float) -> float:
    """Round a raw price to a retail-looking value (…9.99 / …9.90 / …0)."""
    if x < 30:
        return round(x) - 0.01 if x >= 2 else round(x, 2)
    if x < 300:
        return float(int(x)) - 0.01
    return float(round(x / 10) * 10) - 1.0


def clamp(x, lo, hi):
    return max(lo, min(hi, x))


# --------------------------------------------------------------------------------------
# FX
# --------------------------------------------------------------------------------------

def build_fx_series() -> pd.DataFrame:
    """Daily USD-per-unit rate for every currency across the dim_date span."""
    gen = rng(1)
    days = date_range(config.DIM_DATE_START, config.DIM_DATE_END)
    rows = []
    for cur in config.CURRENCIES:
        anchor = config.FX_ANCHORS[cur]
        vol = config.FX_DAILY_VOL[cur]
        rate = anchor
        for d in days:
            if vol > 0:
                shock = gen.normal(0, vol)
                rate = rate * (1 + shock) + config.FX_MEAN_REVERSION * (anchor - rate)
                rate = clamp(rate, anchor * 0.86, anchor * 1.14)
            rows.append({"date": d, "currency_code": cur, "rate_to_usd": round(rate, 6)})
    return pd.DataFrame(rows)


def fx_lookup(fx: pd.DataFrame) -> dict:
    """{(iso_date_str, currency): rate_to_usd} for fast per-row conversion."""
    return {
        (d.isoformat() if isinstance(d, dt.date) else str(d), c): r
        for d, c, r in zip(fx["date"], fx["currency_code"], fx["rate_to_usd"])
    }


# --------------------------------------------------------------------------------------
# IO
# --------------------------------------------------------------------------------------

def write_csv(df: pd.DataFrame, path: Path, **kw) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False, **kw)
    log(f"  wrote {path.relative_to(config.PROJECT_DIR)}  ({len(df):,} rows, {len(df.columns)} cols)")


def write_parquet(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(path, index=False)


def write_curated(df: pd.DataFrame, name: str) -> None:
    """Every curated table is published as both Parquet and CSV."""
    write_parquet(df, config.CURATED_DIR / f"{name}.parquet")
    df.to_csv(config.CURATED_DIR / f"{name}.csv", index=False)
    log(f"  curated {name}  ({len(df):,} rows, {len(df.columns)} cols)")


def write_json(obj, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(obj, fh, ensure_ascii=False, indent=2, default=str)
    log(f"  wrote {path.relative_to(config.PROJECT_DIR)}")


# --------------------------------------------------------------------------------------
# Data-quality report fragments (written by stage 02, assembled by dq_checks)
# --------------------------------------------------------------------------------------

def dq_fragment(name: str, lines: list[str]) -> None:
    frag_dir = config.QUALITY_DIR / "_fragments"
    frag_dir.mkdir(parents=True, exist_ok=True)
    with open(frag_dir / f"{name}.md", "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
