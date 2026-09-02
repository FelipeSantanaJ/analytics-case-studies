"""
gen_semantic_model.py — generate the Power BI project (.pbip) + semantic model (TMDL)
from the curated Parquet schemas.

    python powerbi/gen_semantic_model.py

Produces powerbi/AeroVantiSkyPoints.SemanticModel/** (TMDL, Parquet import partitions
via a pDataFolder parameter). Measures come from etl/pbi_measures.MEASURE_LIBRARY
(Phase 7). The .pbip + .Report shell are created by powerbi/build_report.sh.
"""
from __future__ import annotations

import json
import re
import sys
import uuid
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
CURATED = ROOT / "data" / "curated"
PBI = ROOT / "powerbi"
NAME = "AeroVantiSkyPoints"
SM = PBI / f"{NAME}.SemanticModel"
DEFN = SM / "definition"
TABLES = DEFN / "tables"

NS = uuid.UUID("a3701c11-5f2b-4c88-9d10-aabbccddeeff")


def gid(*parts):
    return str(uuid.uuid5(NS, "::".join(str(p) for p in parts)))


def _write(path: Path, text: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(text.replace("\r\n", "\n").encode("utf-8"))


def _wjson(path: Path, obj):
    _write(path, json.dumps(obj, indent=2))


# every curated parquet is imported
HIDE_TABLES: set[str] = set()

SORT_BY = {
    "dim_date": {"month_name": "month_sort"},
    "dim_tier": {"tier_name": "tier_rank"},
    "dim_month": {"month_name": "month_sort"},
    "Funnel Stage": {"stage": "sort"},
}

NO_SUM_COLS = {
    "year", "quarter", "month", "month_key", "month_sort", "iso_week", "day_of_week",
    "date_key", "tier_rank", "tenure_months", "experiment_week", "week", "sort",
    "months_since_last_activity", "pre_tenure_months",
}


def dtype_of(s: pd.Series) -> str:
    from pandas.api import types as pt
    if pt.is_bool_dtype(s):
        return "boolean"
    if pt.is_datetime64_any_dtype(s):
        return "dateTime"
    if pt.is_integer_dtype(s):
        return "int64"
    if pt.is_float_dtype(s):
        return "double"
    return "string"


def summarize_by(col: str, dt: str) -> str:
    if dt in ("int64", "double") and not col.endswith(("_key", "_idx")) and col not in NO_SUM_COLS:
        return "sum"
    return "none"


def q(name: str) -> str:
    return name if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", name) else f"'{name}'"


def col_block(col, dt, sort_by=None, src=None):
    src = src or col
    L = [f"\tcolumn {q(col)}"]
    if col.endswith("_key") or col.endswith("_idx"):
        L.append("\t\tisHidden")
    L.append(f"\t\tdataType: {dt}")
    if dt == "dateTime":
        L.append("\t\tformatString: yyyy-mm-dd")
    if sort_by:
        L.append(f"\t\tsortByColumn: {sort_by}")
    L += [f"\t\tlineageTag: {gid('col', src, col)}",
          f"\t\tsummarizeBy: {summarize_by(col, dt)}",
          f"\t\tsourceColumn: {col}",
          "", "\t\tannotation SummarizationSetBy = Automatic", ""]
    return L


def m_partition(table, rel_path):
    return [f"\tpartition {q(table)} = m", "\t\tmode: import", "\t\tsource =",
            "\t\t\t\tlet",
            f'\t\t\t\t    Source = Parquet.Document(File.Contents(pDataFolder & "/{rel_path}"))',
            "\t\t\t\tin", "\t\t\t\t    Source"]


def table_tmdl(name, df, rel_path):
    L = [f"table {q(name)}", f"\tlineageTag: {gid('table', name)}"]
    if name in HIDE_TABLES:
        L.append("\tisHidden")
    L.append("")
    sb = SORT_BY.get(name, {})
    for c in df.columns:
        L += col_block(c, dtype_of(df[c]), sort_by=sb.get(c))
    L += m_partition(name, rel_path)
    L += ["", "\tannotation PBI_ResultType = Table", ""]
    return "\n".join(L)


def helper_table(name, columns, rows):
    types = ", ".join(f"{q(c)}={'text' if t=='string' else 'Int64.Type'}" for c, t in columns)

    def lit(v):
        return f'"{v}"' if isinstance(v, str) else str(v)

    rowlits = ", ".join("{" + ", ".join(lit(v) for v in r) + "}" for r in rows)
    L = [f"table {q(name)}", f"\tlineageTag: {gid('table', name)}", ""]
    sb = SORT_BY.get(name, {})
    for c, t in columns:
        L += col_block(c, "string" if t == "string" else "int64", sort_by=sb.get(c))
    L += [f"\tpartition {q(name)} = m", "\t\tmode: import", "\t\tsource =",
          "\t\t\t\tlet",
          f"\t\t\t\t    Source = #table(type table [{types}], {{{rowlits}}})",
          "\t\t\t\tin", "\t\t\t\t    Source",
          "", "\tannotation PBI_ResultType = Table", ""]
    return "\n".join(L)


def _load_measure_library():
    try:
        sys.path.insert(0, str(ROOT / "etl"))
        import pbi_measures
        return pbi_measures.MEASURE_LIBRARY
    except Exception as e:
        print(f"  (no measure library: {e})")
        return []


def _measure_block(m):
    dax_lines = m["dax"].splitlines() or ["BLANK()"]
    L = []
    if m.get("description"):
        L.append(f"\t/// {m['description']}")
    L.append(f"\tmeasure '{m['name']}' =")
    L += [f"\t\t\t{ln}" if ln.strip() else "" for ln in dax_lines]
    if m.get("format"):
        L.append(f"\t\tformatString: {m['format']}")
    if m.get("folder"):
        L.append(f"\t\tdisplayFolder: {m['folder']}")
    L.append(f"\t\tlineageTag: {gid('measure', m['name'])}")
    L.append("")
    return L


def measures_table():
    L = ["table _Measures", f"\tlineageTag: {gid('table', '_Measures')}", "",
         "\tcolumn Value", "\t\tisHidden", "\t\tformatString: 0",
         f"\t\tlineageTag: {gid('col', '_Measures', 'Value')}",
         "\t\tsummarizeBy: sum", "\t\tsourceColumn: [Value]", "",
         "\t\tannotation SummarizationSetBy = Automatic", ""]
    total = 0
    for _folder, group in _load_measure_library():
        for m in group:
            L += _measure_block(m)
            total += 1
    L += ["\tpartition _Measures = calculated", "\t\tmode: import",
          "\t\tsource = {BLANK()}", "", "\tannotation PBI_ResultType = Table", ""]
    print(f"  _Measures: {total} measures injected")
    return "\n".join(L)


def relationships_tmdl(schemas):
    rels = []

    def add(ft, fc, tt, tc, active=True):
        if ft not in schemas or fc not in schemas[ft].columns:
            return
        if tt not in schemas or tc not in schemas[tt].columns:
            return
        b = [f"relationship {gid('rel', ft, fc, tt, tc)}",
             f"\tfromColumn: {q(ft)}.{q(fc)}", f"\ttoColumn: {q(tt)}.{q(tc)}"]
        if not active:
            b.append("\tisActive: false")
        rels.append("\n".join(b))

    # day-grain facts -> dim_date
    add("fact_point_transaction", "txn_date_key", "dim_date", "date_key")
    add("fact_flight_segment", "flight_date_key", "dim_date", "date_key")
    add("fact_tier_change", "change_date_key", "dim_date", "date_key")
    # month-grain facts -> dim_month
    for f in ["fact_member_month", "fact_card_spend_month", "fact_liability_month",
              "fact_targets_month"]:
        add(f, "month_key", "dim_month", "month_key")
    # member hub
    for f in ["fact_point_transaction", "fact_flight_segment", "fact_tier_change",
              "fact_member_month", "fact_card_spend_month", "fact_experiment_assignment",
              "fact_experiment_member_week", "fact_experiment_outcome"]:
        add(f, "member_key", "dim_member", "member_key")
    # other dims
    add("fact_point_transaction", "earn_source_key", "dim_earn_source", "earn_source_key")
    add("fact_point_transaction", "reward_type_key", "dim_reward_type", "reward_type_key")
    add("fact_flight_segment", "route_key", "dim_route", "route_key")
    add("fact_member_month", "tier_key", "dim_tier", "tier_key")
    # experiment arm / stratum dims (real curated tables, related to all 3 experiment facts)
    for f in ["fact_experiment_assignment", "fact_experiment_member_week", "fact_experiment_outcome"]:
        add(f, "arm_key", "dim_experiment_arm", "arm_key")
        add(f, "stratum", "dim_experiment_stratum", "stratum")
    # NOTE: no dim_month <-> dim_date relationship — dim_date.month_key is not unique
    # (30+ rows per month), so it cannot sit on the "one" side of any relationship,
    # active or inactive. Month-grain facts join dim_month; day-grain facts join dim_date.
    return "\n\n".join(rels) + "\n"


def model_tmdl(table_names):
    order = json.dumps(table_names + ["pDataFolder"])
    return "\n".join([
        "model Model", "\tculture: en-US",
        "\tdefaultPowerBIDataSourceVersion: powerBI_V3",
        "\tdiscourageImplicitMeasures", "\tsourceQueryCulture: en-US", "",
        f"\tannotation PBI_QueryOrder = {order}", "",
        "\tannotation __PBI_TimeIntelligenceEnabled = 0", "",
        '\tannotation PBI_ProTooling = ["DevMode"]', "",
    ])


def expressions_tmdl():
    default = str(CURATED).replace("\\", "/")
    return "\n".join([
        f'expression pDataFolder = "{default}" meta [IsParameterQuery=true, Type="Text", IsParameterQueryRequired=true]',
        f"\tlineageTag: {gid('expr', 'pDataFolder')}", "",
        "\tannotation PBI_ResultType = Text", "",
        "\tannotation PBI_NavigationStepName = Navigation", "",
    ])


def main():
    TABLES.mkdir(parents=True, exist_ok=True)
    schemas: dict[str, pd.DataFrame] = {}
    for pq in sorted(CURATED.glob("*.parquet")):
        schemas[pq.stem] = pd.read_parquet(pq).head(50)

    # add sentinel members so non-member / orphan flight rows resolve
    dm = schemas["dim_member"]
    sent = pd.DataFrame([
        {c: (-1 if c == "member_key" else ("SENTINEL_NONMEMBER" if c == "member_id"
             else ("Non-member" if c == "current_tier_name" else
                   ("n/a" if dm[c].dtype == object else 0)))) for c in dm.columns},
        {c: (-2 if c == "member_key" else ("SENTINEL_ORPHAN" if c == "member_id"
             else ("Orphan" if c == "current_tier_name" else
                   ("n/a" if dm[c].dtype == object else 0)))) for c in dm.columns},
    ])
    schemas["dim_member"] = pd.concat([dm, sent], ignore_index=True)

    # dim_month helper — spans ONLY the fact window (2024-09 .. 2026-08) so that
    # MAX(dim_month[month_key]) in the "latest month" measures lands on a month that
    # actually has fact rows.
    dd = pd.read_parquet(CURATED / "dim_date.parquet")
    mo = (dd[(dd["date"] >= "2024-09-01") & (dd["date"] <= "2026-08-31")]
          .groupby("month_key", as_index=False)
          .agg(month_name=("month_name", "first"), month_sort=("month_sort", "first"),
               year=("year", "first"), quarter=("quarter", "first")))
    schemas["dim_month"] = mo

    table_names = list(schemas)
    for n, df in schemas.items():
        if n == "dim_month":
            _write(TABLES / "dim_month.tmdl", helper_table(
                "dim_month",
                [("month_key", "int"), ("month_name", "string"), ("month_sort", "int"),
                 ("year", "int"), ("quarter", "int")],
                mo[["month_key", "month_name", "month_sort", "year", "quarter"]].values.tolist()))
        else:
            _write(TABLES / f"{n}.tmdl", table_tmdl(n, df, f"{n}.parquet"))

    _write(TABLES / "Funnel Stage.tmdl", helper_table(
        "Funnel Stage",
        [("stage", "string"), ("sort", "int")],
        [["Active members", 1], ["Have points >= Flash threshold", 2],
         ["Ever redeemed", 3], ["Redeemed in last 12m", 4], ["Redeemed in last quarter", 5]]))
    _write(TABLES / "_Measures.tmdl", measures_table())

    helper_names = ["Funnel Stage", "_Measures"]
    DEFN.mkdir(parents=True, exist_ok=True)
    _write(DEFN / "database.tmdl", "database\n\tcompatibilityLevel: 1600\n")
    _write(DEFN / "model.tmdl", model_tmdl(table_names + helper_names))
    _write(DEFN / "expressions.tmdl", expressions_tmdl())
    _write(DEFN / "relationships.tmdl", relationships_tmdl(schemas))
    _wjson(SM / "definition.pbism", {
        "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/semanticModel/definitionProperties/1.0.0/schema.json",
        "version": "4.2", "settings": {}})
    _wjson(SM / ".platform", {
        "$schema": "https://developer.microsoft.com/json-schemas/fabric/gitIntegration/platformProperties/2.0.0/schema.json",
        "metadata": {"type": "SemanticModel", "displayName": NAME},
        "config": {"version": "2.0", "logicalId": gid("sm", NAME)}})
    print(f"semantic model: {len(table_names)} imported + {len(helper_names)} helper tables -> {SM}")


if __name__ == "__main__":
    main()
