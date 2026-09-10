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
        "# Voxa+ — DAX Measure Library", "",
        f"_Auto-generated from `etl/pbi_measures.py` on {_dt.date.today()} by "
        "`etl/gen_dax_doc.py`. Do not edit by hand._", "",
        f"**{n} measures** in the `_Measures` table, injected into the semantic model by "
        "`powerbi/gen_semantic_model.py`.", "",
        "**Conventions**", "",
        "- Monetary measures are computed in USD from the curated `*_usd` columns, then "
        "multiplied by `[FX Rate to Reporting]` so the **Reporting Currency** slicer "
        "re-expresses them. `[Currency Symbol]` is available for labels and the narrative.",
        "- Time intelligence uses `dim_date[abs_month]` (a linear `year*12 + month` index), "
        "so it needs **no marked date table** and never calls `SAMEPERIODLASTYEAR`. "
        "Prior year = `abs_month - 12`.",
        "- **Comparable Base** = Brazil (`dim_subscriber[is_comparable_base]`); "
        "**Expansion** = Mexico + US.",
        "- Churn, CAC and payback are **lower-is-better**: their `vs Target` measures are "
        "good when negative, and the KPI cards invert the delta colour.", "",
        "---", "",
    ]
    for folder, group in MEASURE_LIBRARY:
        L.append(f"## {folder}")
        L.append("")
        for m in group:
            tags = []
            if m["format"]:
                tags.append(f"format `{m['format']}`")
            if m["hidden"]:
                tags.append("hidden")
            suffix = f"  \n<sub>{' · '.join(tags)}</sub>" if tags else ""
            L.append(f"### {m['name']}{suffix}")
            if m["description"]:
                L.append("")
                L.append(m["description"])
            L.append("")
            L.append("```dax")
            L.append(m["dax"])
            L.append("```")
            L.append("")
    (C.DOCS / "06_dax_measures.md").write_text("\n".join(L), encoding="utf-8")
    print(f"wrote {C.DOCS / '06_dax_measures.md'}  ({n} measures)")


if __name__ == "__main__":
    main()
