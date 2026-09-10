"""SQL-vs-Python parity check."""
from __future__ import annotations
import numpy as np
import pandas as pd

_LOG: list[dict] = []


def assert_parity(name: str, sql_df: pd.DataFrame, py_df: pd.DataFrame,
                  keys: list[str], value_cols: list[str] | None = None,
                  tol: float = 1e-6) -> pd.DataFrame:
    """Align two result frames on `keys`, compare `value_cols` within `tol`.
    Records the outcome; returns the SQL frame (the canonical result)."""
    a = sql_df.copy()
    b = py_df.copy()
    for df in (a, b):
        for k in keys:
            if k in df.columns and df[k].dtype == object:
                df[k] = df[k].astype(str)
    a = a.sort_values(keys).reset_index(drop=True)
    b = b.sort_values(keys).reset_index(drop=True)
    vcols = value_cols or [c for c in a.columns if c not in keys]

    ok = True
    detail = []
    if len(a) != len(b):
        ok = False
        detail.append(f"row count {len(a)} vs {len(b)}")
    else:
        for kc in keys:
            if not a[kc].astype(str).equals(b[kc].astype(str)):
                ok = False
                detail.append(f"key mismatch on {kc}")
        for vc in vcols:
            if vc not in b.columns:
                ok = False
                detail.append(f"missing column {vc} in python")
                continue
            av = pd.to_numeric(a[vc], errors="coerce").to_numpy(float)
            bv = pd.to_numeric(b[vc], errors="coerce").to_numpy(float)
            both_nan = np.isnan(av) & np.isnan(bv)
            close = np.isclose(av, bv, rtol=tol, atol=tol, equal_nan=True) | both_nan
            if not close.all():
                ok = False
                i = np.where(~close)[0][:3]
                detail.append(f"{vc}: {len(i)}+ rows differ e.g. "
                              + ", ".join(f"{av[j]:.6g}!={bv[j]:.6g}" for j in i))
    _LOG.append({"question": name, "pass": ok, "rows": len(a),
                 "cols": ", ".join(vcols), "detail": "; ".join(detail) or "exact"})
    print(f"  parity [{'PASS' if ok else 'FAIL'}] {name}  {'; '.join(detail) or ''}")
    return a


def report(path) -> bool:
    lines = ["# Voxa+ — SQL vs Python parity report", "",
             "Every analytical result is computed independently in DuckDB SQL and in "
             "pandas; the two must agree within tolerance before the number becomes a "
             "finding.", "",
             "| Question | Result | Rows | Value columns | Detail |",
             "|---|---|--:|---|---|"]
    all_ok = True
    for r in _LOG:
        all_ok &= r["pass"]
        lines.append(f"| {r['question']} | {'✅ pass' if r['pass'] else '❌ FAIL'} "
                     f"| {r['rows']} | {r['cols']} | {r['detail']} |")
    lines += ["", f"**{sum(r['pass'] for r in _LOG)}/{len(_LOG)} checks pass.**"]
    from pathlib import Path
    Path(path).write_text("\n".join(lines), encoding="utf-8")
    return all_ok
