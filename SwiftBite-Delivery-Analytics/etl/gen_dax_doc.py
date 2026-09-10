"""
gen_dax_doc.py — render docs/06_dax_measures.md from etl/pbi_measures.MEASURE_LIBRARY.

    python etl/gen_dax_doc.py
"""
from __future__ import annotations

import datetime as _dt
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config as C
from pbi_measures import MEASURE_LIBRARY, all_measures


def main():
    n = sum(1 for _ in all_measures())
    L = [
        "# SwiftBite Delivery — DAX Measure Library", "",
        f"_Auto-generated from `etl/pbi_measures.py` on {_dt.date.today()} by "
        "`etl/gen_dax_doc.py`. Do not edit by hand._", "",
        f"**{n} measures** in the `_Measures` table, injected into the semantic model by "
        "`powerbi/gen_semantic_model.py`.", "",
        "## Conventions", "",
        "- All money is **BRL** — no currency slicer.",
        "- The report's date grain is the day; `dim_date[date_key]` is the calendar key on "
        "every fact. Time-of-day comes from `dim_time_block` (`is_peak_block` = 18:00–21:59).",
        "- **ETA p50 / p90** are stored per zone-hour; the measures aggregate them as an "
        "order-weighted mean of the per-zone-hour percentile — a close approximation. The "
        "exact distribution-level percentile is a Phase-10 artifact, not a live measure.",
        "- Experiment measures read `fact_experiment_zone_day` (one row per randomised "
        "zone-day) and `fact_incentive_assignment` (design + frozen pre-period covariates); "
        "`arm` / `stratum` are text columns filtered directly.",
        "- The live experiment CI is a **two-sample normal interval on the zone-day means**. "
        "The cluster-robust (by zone) SE, the randomization-inference p-value and the formal "
        "arm×tier interaction test are **Phase-10 deliverables**, not measures.",
        "- **ETA, cancellation rate, no-courier rate, idle-courier ratio and incentive cost "
        "per incremental order are lower-is-better** — their `vs Target` measures are good "
        "when negative.", "",
        "---", "",
    ]
    for folder, group in MEASURE_LIBRARY:
        L += [f"## {folder}", ""]
        for m in group:
            tag = f"  \n<sub>format `{m['format']}`</sub>" if m["format"] else ""
            L += [f"### {m['name']}{tag}", ""]
            if m["description"]:
                L += [m["description"], ""]
            L += ["```dax", m["dax"], "```", ""]
    (C.PROJECT_DIR / "docs" / "06_dax_measures.md").write_text("\n".join(L), encoding="utf-8")
    print(f"wrote docs/06_dax_measures.md  ({n} measures)")


if __name__ == "__main__":
    main()
