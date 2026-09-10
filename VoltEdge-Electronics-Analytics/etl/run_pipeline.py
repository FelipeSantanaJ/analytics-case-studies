"""
Orchestrate the full VoltEdge ETL: 01_generate_raw -> 02_clean_stage ->
03_build_curated -> dq_checks. Stops on the first non-zero exit.

Usage:  python run_pipeline.py [--from N]     # N in {1,2,3,4}, default 1
"""

from __future__ import annotations

import subprocess
import sys
import time

STAGES = [
    ("01  generate raw", "01_generate_raw.py"),
    ("02  clean & stage", "02_clean_stage.py"),
    ("03  build curated", "03_build_curated.py"),
    ("04  data-quality gate", "dq_checks.py"),
]


def main() -> int:
    start_at = 1
    if len(sys.argv) == 3 and sys.argv[1] == "--from":
        start_at = int(sys.argv[2])

    t0 = time.time()
    for i, (label, script) in enumerate(STAGES, start=1):
        if i < start_at:
            print(f"  (skip)  {label}")
            continue
        print(f"\n{'#' * 78}\n#  {label}\n{'#' * 78}", flush=True)
        rc = subprocess.run([sys.executable, script], cwd=str(__import__("pathlib").Path(__file__).parent)).returncode
        if rc != 0:
            print(f"\n!! stage '{label}' exited {rc} — pipeline halted after {time.time()-t0:,.0f}s")
            return rc
    print(f"\n== pipeline complete in {time.time()-t0:,.0f}s ==")
    return 0


if __name__ == "__main__":
    sys.exit(main())
