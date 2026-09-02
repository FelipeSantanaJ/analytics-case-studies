"""
AeroVanti SkyPoints — run_pipeline.py

Runs the ETL end to end:  01 generate raw -> 02 stage -> 03 curate -> dq_checks.

  python etl/run_pipeline.py            # full build
  python etl/run_pipeline.py --from 02  # skip raw generation
  python etl/run_pipeline.py --from 03  # rebuild curated + dq only
"""

from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path

ETL = Path(__file__).resolve().parent
STEPS = [
    ("01", "01_generate_raw.py"),
    ("02", "02_clean_stage.py"),
    ("03", "03_build_curated.py"),
    ("dq", "dq_checks.py"),
]


def main():
    start_from = "01"
    if "--from" in sys.argv:
        start_from = sys.argv[sys.argv.index("--from") + 1]

    started = False
    for tag, script in STEPS:
        if tag == start_from:
            started = True
        if not started:
            print(f"--- skip {script}")
            continue
        print(f"\n### running {script}")
        t0 = time.time()
        r = subprocess.run([sys.executable, "-u", str(ETL / script)], cwd=ETL)
        dt = time.time() - t0
        if r.returncode != 0:
            print(f"\n### {script} FAILED (exit {r.returncode}) after {dt:.0f}s")
            sys.exit(r.returncode)
        print(f"### {script} ok ({dt:.0f}s)")
    print("\n### pipeline complete")


if __name__ == "__main__":
    main()
