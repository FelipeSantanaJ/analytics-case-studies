"""
gen_semantic_model.py — generate the Power BI semantic model (TMDL) from the curated
Parquet schemas.

    python powerbi/gen_semantic_model.py          # reads data/curated (or $SB_DATA_DIR)

Produces powerbi/SwiftBiteDelivery.SemanticModel/** (TMDL, Parquet import partitions
via a pDataFolder parameter). Measures are injected from etl/pbi_measures.MEASURE_LIBRARY
if present (Phase 7); otherwise the _Measures table is created empty. The .pbip + .Report
shell come from Phase 8.
"""
from __future__ import annotations

import json
import os
import re
import sys
import uuid
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
CURATED = Path(os.environ.get("SB_DATA_DIR", str(ROOT / "data"))) / "curated"
PBI = ROOT / "powerbi"
NAME = "SwiftBiteDelivery"
SM = PBI / f"{NAME}.SemanticModel"
DEFN = SM / "definition"
TABLES = DEFN / "tables"
PDATAFOLDER_PLACEHOLDER = "C:/PATH/TO/REPO/SwiftBite-Delivery-Analytics/data/curated"

NS = uuid.UUID("5b17e0aa-9c42-4d31-8f60-1122aabbccdd")


def gid(*parts):
    return str(uuid.uuid5(NS, "::".join(str(p) for p in parts)))


def _write(path: Path, text: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(text.replace("\r\n", "\n").encode("utf-8"))


def _wjson(path: Path, obj):
    _write(path, json.dumps(obj, indent=2))


SORT_BY = {
    "dim_date": {"month_name": "month"},
    "dim_time_block": {"daypart": "hour", "block_label": "hour"},
    "dim_zone": {"baseline_supply_stress_tier": "zone_key"},
}

# numeric columns that must NOT default to sum
NO_SUM_EXACT = {
    "hour", "year", "quarter", "month", "iso_week", "day_of_week", "date_key",
    "time_block_key", "experiment_week", "n_neighbours", "n_adjacent_zones_treated",
    "push_radius_m", "peak_block_start_hour", "peak_block_end_hour",
    "peak_start_hour", "peak_end_hour", "signup_date_key", "active_couriers",
    "area_km2", "centroid_lat", "centroid_lon", "avg_trip_km_baseline",
    "bonus_brl_per_delivery", "day_of_week",
}
NO_SUM_SUFFIX = ("_rate", "_ratio", "_p50_min", "_p90_min", "_p90_s",
                 "_per_active_hour_brl", "_per_delivered_order_brl", "eta_min", "_key", "_idx")
NO_SUM_PREFIX = ("pre_",)


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
    if dt not in ("int64", "double"):
        return "none"
    if col in NO_SUM_EXACT or col.endswith(NO_SUM_SUFFIX) or col.startswith(NO_SUM_PREFIX):
        return "none"
    return "sum"


def q(name: str) -> str:
    return name if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", name) else f"'{name}'"


def col_block(col, dt, sort_by=None, table=""):
    L = [f"\tcolumn {q(col)}"]
    if col.endswith(("_key", "_idx")):
        L.append("\t\tisHidden")
    L.append(f"\t\tdataType: {dt}")
    if dt == "dateTime":
        L.append("\t\tformatString: yyyy-mm-dd")
    if sort_by:
        L.append(f"\t\tsortByColumn: {sort_by}")
    L += [f"\t\tlineageTag: {gid('col', table, col)}",
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
    L = [f"table {q(name)}", f"\tlineageTag: {gid('table', name)}", ""]
    sb = SORT_BY.get(name, {})
    for c in df.columns:
        L += col_block(c, dtype_of(df[c]), sort_by=sb.get(c), table=name)
    L += m_partition(name, rel_path)
    L += ["", "\tannotation PBI_ResultType = Table", ""]
    return "\n".join(L)


def _load_measure_library():
    try:
        sys.path.insert(0, str(ROOT / "etl"))
        import pbi_measures
        return pbi_measures.MEASURE_LIBRARY
    except Exception as e:
        print(f"  (no measure library yet: {e})")
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
            print(f"  ! skip rel {ft}.{fc} (missing)")
            return
        if tt not in schemas or tc not in schemas[tt].columns:
            print(f"  ! skip rel -> {tt}.{tc} (missing)")
            return
        b = [f"relationship {gid('rel', ft, fc, tt, tc)}",
             f"\tfromColumn: {q(ft)}.{q(fc)}", f"\ttoColumn: {q(tt)}.{q(tc)}"]
        if not active:
            b.append("\tisActive: false")
        rels.append("\n".join(b))

    day_facts = ["fact_order", "fact_delivery", "fact_courier_shift_block", "fact_zone_hour",
                 "fact_incentive_assignment", "fact_experiment_zone_day",
                 "fact_experiment_zone_block_week"]
    date_fk = {"fact_order": "placed_date_key"}
    for f in day_facts:
        add(f, date_fk.get(f, "date_key"), "dim_date", "date_key")

    for f in ["fact_order", "fact_delivery", "fact_courier_shift_block", "fact_zone_hour",
              "fact_experiment_zone_block_week"]:
        add(f, "time_block_key", "dim_time_block", "time_block_key")

    # zone — role-playing on fact_order (dropoff current active; asbooked + pickup inactive)
    add("fact_order", "dropoff_zone_key_current", "dim_zone", "zone_key")
    add("fact_order", "dropoff_zone_key_asbooked", "dim_zone", "zone_key", active=False)
    add("fact_order", "pickup_zone_key", "dim_zone", "zone_key", active=False)
    for f in ["fact_delivery", "fact_courier_shift_block", "fact_zone_hour",
              "fact_incentive_assignment", "fact_experiment_zone_day",
              "fact_experiment_zone_block_week"]:
        add(f, "zone_key", "dim_zone", "zone_key")

    # zone adjacency bridge
    add("dim_zone_adjacency", "zone_key", "dim_zone", "zone_key")

    # courier / customer / restaurant
    add("fact_order", "courier_key", "dim_courier", "courier_key")
    add("fact_delivery", "courier_key", "dim_courier", "courier_key")
    add("fact_courier_shift_block", "courier_key", "dim_courier", "courier_key")
    add("fact_order", "customer_key", "dim_customer", "customer_key")
    add("fact_order", "restaurant_key", "dim_restaurant", "restaurant_key")

    # incentive campaign
    add("fact_incentive_assignment", "campaign_key", "dim_incentive_campaign", "campaign_key")

    # NOTE: fact_experiment_zone_day has no campaign_key; it joins dim_zone + dim_date
    # directly. arm / stratum are text columns read by measures with SELECTEDVALUE.
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
    return "\n".join([
        f'expression pDataFolder = "{PDATAFOLDER_PLACEHOLDER}" meta '
        f'[IsParameterQuery=true, Type="Text", IsParameterQueryRequired=true]',
        f"\tlineageTag: {gid('expr', 'pDataFolder')}", "",
        "\tannotation PBI_ResultType = Text", "",
        "\tannotation PBI_NavigationStepName = Navigation", "",
    ])


def add_sentinels(schemas):
    dc = schemas["dim_courier"]

    def row(k, cid):
        return {c: (k if c == "courier_key" else (cid if c == "courier_id"
                    else (0 if pd.api.types.is_numeric_dtype(dc[c]) else
                          (False if pd.api.types.is_bool_dtype(dc[c]) else "n/a"))))
                for c in dc.columns}
    schemas["dim_courier"] = pd.concat(
        [dc, pd.DataFrame([row(-1, "NO_COURIER"), row(-2, "ORPHAN")])], ignore_index=True)


def main():
    TABLES.mkdir(parents=True, exist_ok=True)
    pqs = sorted(CURATED.glob("*.parquet"))
    if not pqs:
        raise SystemExit(f"no curated parquet in {CURATED} — run etl/run_pipeline.py first")
    schemas = {pq.stem: pd.read_parquet(pq).head(50) for pq in pqs}
    add_sentinels(schemas)

    table_names = list(schemas)
    for n, df in schemas.items():
        _write(TABLES / f"{n}.tmdl", table_tmdl(n, df, f"{n}.parquet"))
    _write(TABLES / "_Measures.tmdl", measures_table())

    DEFN.mkdir(parents=True, exist_ok=True)
    _write(DEFN / "database.tmdl", "database\n\tcompatibilityLevel: 1600\n")
    _write(DEFN / "model.tmdl", model_tmdl(table_names + ["_Measures"]))
    _write(DEFN / "expressions.tmdl", expressions_tmdl())
    _write(DEFN / "relationships.tmdl", relationships_tmdl(schemas))
    _wjson(SM / "definition.pbism", {
        "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/semanticModel/definitionProperties/1.0.0/schema.json",
        "version": "4.2", "settings": {}})
    _wjson(SM / ".platform", {
        "$schema": "https://developer.microsoft.com/json-schemas/fabric/gitIntegration/platformProperties/2.0.0/schema.json",
        "metadata": {"type": "SemanticModel", "displayName": NAME},
        "config": {"version": "2.0", "logicalId": gid("sm", NAME)}})
    print(f"semantic model: {len(table_names)} tables + _Measures -> {SM}")


if __name__ == "__main__":
    main()
