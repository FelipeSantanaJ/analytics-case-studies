"""
run_all.py — run every analysis end to end and confirm the SQL/Python parity.

Each data_analysis/python/NN_*.py computes its numbers on BOTH tracks (pandas and
DuckDB over the same curated parquet) and calls utils.parity(...) which raises on
any mismatch beyond tolerance. This script just runs them all and reports.

    python data_analysis/parity/run_all.py
"""
from __future__ import annotations
import runpy
import sys
import time
from pathlib import Path

PYDIR = Path(__file__).resolve().parents[1] / "python"
SCRIPTS = sorted(p for p in PYDIR.glob("[0-9][0-9]_*.py"))

fails = []
for s in SCRIPTS:
    print(f"\n{'#' * 78}\n# {s.name}\n{'#' * 78}")
    t0 = time.time()
    try:
        runpy.run_path(str(s), run_name="__main__")
        print(f"# {s.name}: OK ({time.time() - t0:.1f}s)")
    except Exception as e:
        print(f"# {s.name}: FAILED — {type(e).__name__}: {e}")
        fails.append(s.name)

print(f"\n{'=' * 78}")
if fails:
    print(f"{len(fails)} script(s) FAILED: {fails}")
    sys.exit(1)
print(f"All {len(SCRIPTS)} analyses ran and every SQL/Python parity check passed.")
