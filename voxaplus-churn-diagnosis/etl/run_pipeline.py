"""
run_pipeline.py — full ETL build: raw -> staging -> curated -> dq_checks.

    python etl/run_pipeline.py                # everything
    python etl/run_pipeline.py --from 02      # staging + curated + checks
    python etl/run_pipeline.py --from 03      # curated + checks
    python etl/run_pipeline.py --only dq      # checks only

Honours env VOXA_POP_SCALE / VOXA_SEED (see config.py).
"""
from __future__ import annotations

import argparse
import subprocess
import sys
import time
from pathlib import Path

ETL = Path(__file__).resolve().parent
STEPS = [("01", "01_generate_raw.py"), ("02", "02_clean_stage.py"),
         ("03", "03_build_curated.py"), ("dq", "dq_checks.py")]


def run(script):
    print(f"\n{'='*70}\n>>> {script}\n{'='*70}", flush=True)
    t0 = time.time()
    r = subprocess.run([sys.executable, str(ETL / script)], cwd=str(ETL))
    print(f"<<< {script} finished in {time.time()-t0:.0f}s (exit {r.returncode})", flush=True)
    if r.returncode != 0:
        sys.exit(r.returncode)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--from", dest="start", default="01", choices=[s[0] for s in STEPS])
    ap.add_argument("--only", default=None, choices=[s[0] for s in STEPS])
    a = ap.parse_args()
    t0 = time.time()
    for code, script in STEPS:
        if a.only:
            if code == a.only:
                run(script)
            continue
        if _ge(code, a.start):
            run(script)
    print(f"\nPIPELINE COMPLETE in {time.time()-t0:.0f}s", flush=True)


def _ge(code, start):
    order = [s[0] for s in STEPS]
    return order.index(code) >= order.index(start)


if __name__ == "__main__":
    main()
