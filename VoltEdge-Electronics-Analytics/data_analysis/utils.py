"""Shared loaders / helpers for the VoltEdge data_analysis tracks.

Both tracks (pandas + DuckDB) read the same curated parquet files.
"""
from __future__ import annotations

import pathlib
import re
import sys

import pandas as pd

# Windows consoles default to cp1252; force UTF-8 so non-ASCII in prints is safe.
try:  # pragma: no cover
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

# --- paths -------------------------------------------------------------------
ROOT = pathlib.Path(__file__).resolve().parents[1]
CUR = ROOT / "data" / "curated"
SQL_DIR = pathlib.Path(__file__).resolve().parent / "sql"
OUT_TABLES = pathlib.Path(__file__).resolve().parent / "outputs" / "tables"
OUT_FIGS = pathlib.Path(__file__).resolve().parent / "outputs" / "figures"

# --- extract window (docs/01 §1) ------------------------------------------------
WINDOW_START = pd.Timestamp("2024-07-01")
WINDOW_END = pd.Timestamp("2026-06-30")
CY_START = pd.Timestamp("2025-07-01")
PY_START = pd.Timestamp("2024-07-01")


def setup_mpl():
    """Consistent chart style; disable mathtext so literal '$' is safe in labels."""
    import matplotlib as mpl

    mpl.rcParams["text.parse_math"] = False
    mpl.rcParams["font.family"] = "DejaVu Sans"
    mpl.rcParams["axes.titlesize"] = 12
    mpl.rcParams["figure.facecolor"] = "white"
    mpl.rcParams["savefig.facecolor"] = "white"


# palette matching the Power BI report (navy / blue / amber)
NAVY, BLUE, AMBER, RED, GREEN, GREY = (
    "#12305B", "#2E6FB2", "#E8A33D", "#C0392B", "#2E8B57", "#9AA5B1",
)


def t(name: str) -> pd.DataFrame:
    """Load a curated table by name (no extension) as a pandas DataFrame."""
    return pd.read_parquet(CUR / f"{name}.parquet")


def curated_path(name: str) -> str:
    """POSIX path to a curated parquet file, for DuckDB FROM '...' clauses."""
    return (CUR / f"{name}.parquet").as_posix()


_SQL_SECTION = re.compile(r"^\s*--\s*name:\s*(\S+)\s*$")


def load_sql(name: str) -> dict[str, str]:
    """Parse ``sql/<name>.sql`` into an ordered ``{section: query}`` dict.

    Sections are delimited by a ``-- name: <section>`` line; everything up to the
    next such line (or EOF) is that section's SQL. Any text before the first
    marker is a file header and is ignored. Queries carry bare curated-table
    names (``duck()`` registers a view per parquet) and use DuckDB ``$param``
    placeholders for values that vary between calls.
    """
    text = (SQL_DIR / f"{name}.sql").read_text(encoding="utf-8")
    out: dict[str, list[str]] = {}
    cur: str | None = None
    for line in text.splitlines():
        m = _SQL_SECTION.match(line)
        if m:
            cur = m.group(1)
            out[cur] = []
        elif cur is not None:
            out[cur].append(line)
    return {k: "\n".join(v).strip() for k, v in out.items()}


def duck():
    """A fresh in-memory DuckDB connection with a p(name) helper macro."""
    import duckdb

    con = duckdb.connect()
    for f in CUR.glob("*.parquet"):
        con.execute(
            f"CREATE OR REPLACE VIEW {f.stem} AS SELECT * FROM read_parquet('{f.as_posix()}')"
        )
    return con


def assert_close(a: float, b: float, *, rel: float = 1e-6, abs_: float = 0.01, label: str = ""):
    """Parity assertion: exact-ish for money/ratios. Raises on mismatch."""
    diff = abs(a - b)
    tol = max(abs_, rel * max(abs(a), abs(b)))
    status = "OK  " if diff <= tol else "FAIL"
    print(f"[{status}] {label}: python={a:,.4f}  sql={b:,.4f}  diff={diff:,.6f}  tol={tol:,.6f}")
    if diff > tol:
        raise AssertionError(f"parity mismatch on {label}: {a} vs {b} (diff {diff} > tol {tol})")
