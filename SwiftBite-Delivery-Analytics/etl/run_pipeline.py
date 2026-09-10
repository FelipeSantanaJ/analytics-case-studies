"""
SwiftBite Delivery — run_pipeline.py

    python etl/run_pipeline.py            # full: raw -> staging -> curated -> dq_checks
    python etl/run_pipeline.py --from 02  # skip regeneration, rebuild staging + curated + dq

Point the regenerated data layers outside a synced folder with SB_DATA_DIR to
avoid OneDrive file-locks on Windows (see etl/config.py).
"""
from __future__ import annotations

import argparse
import importlib
import sys
import time

STEPS = [("01", "01_generate_raw"), ("02", "02_clean_stage"),
         ("03", "03_build_curated"), ("dq", "dq_checks")]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--from", dest="start", default="01", choices=[s[0] for s in STEPS])
    args = ap.parse_args()
    started = False
    t0 = time.time()
    for tag, mod_name in STEPS:
        if tag == args.start:
            started = True
        if not started:
            continue
        t = time.time()
        mod = importlib.import_module(mod_name)
        mod.main()
        print(f">>> {mod_name} finished in {time.time() - t:.1f}s\n")
    print(f"pipeline done in {time.time() - t0:.1f}s")


if __name__ == "__main__":
    sys.exit(main())
