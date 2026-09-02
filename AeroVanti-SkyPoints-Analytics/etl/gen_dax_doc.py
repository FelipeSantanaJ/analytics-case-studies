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
        "# AeroVanti SkyPoints — DAX Measure Library", "",
        f"_Auto-generated from `etl/pbi_measures.py` on {_dt.date.today()} by "
        "`etl/gen_dax_doc.py`. Do not edit by hand._", "",
        f"**{n} measures** in the `_Measures` table, injected into the semantic model by "
        "`powerbi/gen_semantic_model.py`.", "",
        "**Conventions**", "",
        "- All money is **BRL** — no currency slicer.",
        "- \"Latest month\" = `MAX(dim_month[month_key])` in the current filter context.",
        "- Time intelligence uses `dim_month[month_sort]` (a linear `year*12 + month` "
        "index): PY = `month_sort - 12`. No marked date table, no `SAMEPERIODLASTYEAR`.",
        "- Experiment measures read `fact_experiment_outcome` / "
        "`fact_experiment_member_week` and respect the Experiment Arm / Stratum slicers; "
        "arm-specific measures pin the arm with `CALCULATE(..., arm_key = \"...\")`.",
        "- **Breakage rate, lapse rate and liability per member are lower-is-better** — "
        "their `vs Target` measures are good when negative.", "",
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
