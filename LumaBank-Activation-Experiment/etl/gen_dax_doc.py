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
        "# LumaBank — DAX Measure Library", "",
        f"_Auto-generated from `etl/pbi_measures.py` on {_dt.date.today()} by "
        "`etl/gen_dax_doc.py`. Do not edit by hand._", "",
        f"**{n} measures** in the `_Measures` table, injected into the semantic model by "
        "`powerbi/gen_semantic_model.py`.", "",
        "**Conventions**", "",
        "- `fact_activation` is **one row per signup, platform-wide** — most measures "
        "here carry no arm filter (platform-health questions); the Experiment Readout "
        "group filters `in_analysis_flag = TRUE()` (the clean re-run population only).",
        "- \"Latest day\" = `MAX(dim_date[date])` in the current filter context. No marked "
        "date table, no time-intelligence functions — trailing windows use explicit "
        "`dim_date[date]` arithmetic.",
        "- SRM measures read `fact_srm_daily` (one row per experiment x calendar day) and "
        "are never sliced by arm.",
        "- **KYC rejection rate, fraud flag rate, and onboarding tickets are "
        "lower-is-better** — guardrail delta measures are framed so positive = "
        "treatment worse, matching the non-inferiority bounds in doc 01 section 8.3 "
        "(+1.5 pp KYC, +0.5 pp fraud).", "",
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
