"""
gen_semantic_model.py — generate the Power BI project (.pbip) + semantic model (TMDL)
from the curated Parquet schemas.

    python powerbi/gen_semantic_model.py

Produces:
  powerbi/VoxaChurnDiagnosis.pbip
  powerbi/VoxaChurnDiagnosis.SemanticModel/.platform
  powerbi/VoxaChurnDiagnosis.SemanticModel/definition.pbism
  powerbi/VoxaChurnDiagnosis.SemanticModel/definition/{database,model,expressions,relationships}.tmdl
  powerbi/VoxaChurnDiagnosis.SemanticModel/definition/tables/*.tmdl
  powerbi/VoxaChurnDiagnosis.Report/{.platform,definition.pbir}     (shell; Phase 8 fills it)

Import tables read `data/curated/*.parquet` through the `pDataFolder` parameter.
Measures are added in Phase 7 by re-running this with `etl/pbi_measures.py` present.
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
NAME = "VoxaChurnDiagnosis"
SM = PBI / f"{NAME}.SemanticModel"
RPT = PBI / f"{NAME}.Report"
DEFN = SM / "definition"
TABLES = DEFN / "tables"

NS = uuid.UUID("5f0b7e02-9c3a-4d21-9a55-b0b0b0b0c0c0")
def gid(*parts):
    return str(uuid.uuid5(NS, "::".join(str(p) for p in parts)))


def _write(path: Path, text: str):
    """Write with LF line endings (TMDL / PBIP convention), UTF-8, no BOM."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(text.replace("\r\n", "\n").encode("utf-8"))


def _wjson(path: Path, obj):
    _write(path, json.dumps(obj, indent=2))

# curated tables to import into the model (fact_viewing_daily stays analyst-only)
EXCLUDE = {"fact_viewing_daily"}

# tables to hide from the field list (technical / helper)
HIDE_TABLES = {"fact_fx_rate", "fact_finance_month"}

# display column -> the column it should sort by (chronological / logical order)
SORT_BY = {
    "dim_date": {"year_month": "month_sort", "month_name": "month_num"},
    "dim_subscriber": {"cohort_month": "first_paid_month_idx"},
    "P&L Line": {"Display": "Sort"},
    "Reporting Currency": {"Currency": "Sort"},
    "Subscriber Bridge": {"Step": "Sort"},
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
    if dt in ("int64", "double") and not col.endswith(("_key", "_idx", "_year")) \
            and col not in ("year", "quarter", "month_num", "iso_week", "day_of_month",
                            "month_sort", "date_key", "major", "runtime_min"):
        return "sum"
    return "none"


# ---------------------------------------------------------------------------
def col_block(col: str, dt: str, src: str | None = None, sort_by: str | None = None) -> list[str]:
    src = src or col
    L = [f"\tcolumn {q(col)}"]
    if col.endswith("_key") or col.endswith("_idx") or col in ("account_ref", "subject"):
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


def q(name: str) -> str:
    return name if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", name) else f"'{name}'"


def m_partition(table: str, rel_path: str, is_folder: bool = False) -> list[str]:
    if is_folder:
        src = [
            "\t\tsource =",
            "\t\t\t\tlet",
            f'\t\t\t\t    Source = Folder.Files(pDataFolder & "/{rel_path}"),',
            '\t\t\t\t    OnlyParquet = Table.SelectRows(Source, each [Extension] = ".parquet"),',
            "\t\t\t\t    Combined = Table.Combine(List.Transform(OnlyParquet[Content], each Parquet.Document(_)))",
            "\t\t\t\tin",
            "\t\t\t\t    Combined",
        ]
    else:
        src = [
            "\t\tsource =",
            "\t\t\t\tlet",
            f'\t\t\t\t    Source = Parquet.Document(File.Contents(pDataFolder & "/{rel_path}"))',
            "\t\t\t\tin",
            "\t\t\t\t    Source",
        ]
    return [f"\tpartition {q(table)} = m", "\t\tmode: import", *src]


def table_tmdl(name: str, df: pd.DataFrame, rel_path: str) -> str:
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


# ---------------------------------------------------------------------------
def helper_table(name: str, columns: list[tuple[str, str]], rows: list[list]) -> str:
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
    """Import etl/pbi_measures.MEASURE_LIBRARY if present."""
    try:
        sys.path.insert(0, str(ROOT / "etl"))
        import pbi_measures  # noqa
        return pbi_measures.MEASURE_LIBRARY
    except Exception as e:  # pragma: no cover
        print(f"  (no measure library: {e})")
        return []


def _measure_block(m: dict) -> list[str]:
    dax_lines = m["dax"].splitlines() or ["BLANK()"]
    L = []
    if m.get("description"):
        L.append(f"\t/// {m['description']}")
    L.append(f"\tmeasure '{m['name']}' =")
    L += [f"\t\t\t{ln}" if ln.strip() else "" for ln in dax_lines]
    if m.get("format"):
        L.append(f"\t\tformatString: {m['format']}")
    if m.get("hidden"):
        L.append("\t\tisHidden")
    if m.get("folder"):
        L.append(f"\t\tdisplayFolder: {m['folder']}")
    L.append(f"\t\tlineageTag: {gid('measure', m['name'])}")
    L.append("")
    return L


def measures_table() -> str:
    L = [
        "table _Measures",
        f"\tlineageTag: {gid('table', '_Measures')}",
        "",
        "\tcolumn Value",
        "\t\tisHidden",
        "\t\tformatString: 0",
        f"\t\tlineageTag: {gid('col', '_Measures', 'Value')}",
        "\t\tsummarizeBy: sum",
        "\t\tsourceColumn: [Value]",
        "",
        "\t\tannotation SummarizationSetBy = Automatic",
        "",
    ]
    lib = _load_measure_library()
    total = 0
    for _folder, group in lib:
        for m in group:
            L += _measure_block(m)
            total += 1
    L += [
        "\tpartition _Measures = calculated",
        "\t\tmode: import",
        "\t\tsource = {BLANK()}",
        "",
        "\tannotation PBI_ResultType = Table",
        "",
    ]
    print(f"  _Measures: {total} measures injected")
    return "\n".join(L)


# ---------------------------------------------------------------------------
def relationships_tmdl(schemas: dict) -> str:
    rels = []

    def add(frm_t, frm_c, to_t, to_c, active=True, both=False):
        if frm_t not in schemas or frm_c not in schemas[frm_t].columns:
            return
        if to_t not in schemas or to_c not in schemas[to_t].columns:
            return
        b = [f"relationship {gid('rel', frm_t, frm_c, to_t, to_c)}",
             f"\tfromColumn: {q(frm_t)}.{q(frm_c)}",
             f"\ttoColumn: {q(to_t)}.{q(to_c)}"]
        if not active:
            b.append("\tisActive: false")
        if both:
            b.append("\tcrossFilteringBehavior: bothDirections")
        rels.append("\n".join(b))

    # per-fact date column -> dim_date[date_key]
    date_col = {"fact_subscription_event": "event_date_key",
                "fact_marketing_spend": "week_date_key",
                "fact_support_ticket": "created_date_key"}
    for f in ["fact_subscription_month", "fact_subscription_event", "fact_billing_attempt",
              "fact_engagement_month", "fact_engagement_device_month",
              "fact_app_performance_daily", "fact_support_ticket", "fact_marketing_spend",
              "fact_ad_revenue", "fact_content_cost", "fact_finance_month",
              "fact_targets_month", "fact_fx_rate"]:
        add(f, date_col.get(f, "date_key"), "dim_date", "date_key")

    # subscriber hub — market/channel/tier/device slice through dim_subscriber
    for f in ["fact_subscription_month", "fact_subscription_event", "fact_billing_attempt",
              "fact_engagement_month", "fact_support_ticket"]:
        add(f, "subscriber_key", "dim_subscriber", "subscriber_key")
    add("dim_subscriber", "market_key", "dim_market", "market_key")

    # market only for facts WITHOUT a subscriber path (avoids ambiguous filter routes)
    add("fact_app_performance_daily", "market", "dim_market", "market_id")
    for f in ["fact_engagement_device_month", "fact_ad_revenue", "fact_marketing_spend",
              "fact_finance_month", "fact_targets_month"]:
        add(f, "market_key", "dim_market", "market_key")
    add("fact_engagement_device_month", "device_key", "dim_device", "device_key")
    add("fact_app_performance_daily", "device_key", "dim_device", "device_key")
    add("fact_app_performance_daily", "app_version", "dim_app_version", "app_version")
    add("fact_billing_attempt", "method_key", "dim_payment_method", "method_key")
    add("fact_marketing_spend", "channel_key", "dim_channel", "channel_key")
    add("fact_support_ticket", "support_reason_key", "dim_support_reason", "support_reason_key")
    add("fact_content_cost", "content_key", "dim_content", "content_key")
    # role-playing (inactive)
    add("dim_content", "release_date_key", "dim_date", "date_key", active=False)
    # helper dimension: P&L line ordering for the finance page
    if "fact_finance_month" in schemas and "pnl_line" in schemas["fact_finance_month"].columns:
        rels.append("\n".join([
            f"relationship {gid('rel', 'fact_finance_month', 'pnl_line', 'P&L Line', 'pnl_line')}",
            "\tfromColumn: fact_finance_month.pnl_line",
            "\ttoColumn: 'P&L Line'.pnl_line"]))
    return "\n\n".join(rels) + "\n"


# ---------------------------------------------------------------------------
def model_tmdl(table_names: list[str]) -> str:
    order = json.dumps(table_names + ["pDataFolder"])
    return "\n".join([
        "model Model",
        "\tculture: en-US",
        "\tdefaultPowerBIDataSourceVersion: powerBI_V3",
        "\tdiscourageImplicitMeasures",
        "\tsourceQueryCulture: en-US",
        "",
        f"\tannotation PBI_QueryOrder = {order}",
        "",
        "\tannotation __PBI_TimeIntelligenceEnabled = 0",
        "",
        "\tannotation PBI_ProTooling = [\"DevMode\"]",
        "",
    ])


def expressions_tmdl() -> str:
    default = str(CURATED).replace("\\", "/")
    return "\n".join([
        f'expression pDataFolder = "{default}" meta [IsParameterQuery=true, Type="Text", IsParameterQueryRequired=true]',
        f"\tlineageTag: {gid('expr', 'pDataFolder')}",
        "",
        "\tannotation PBI_ResultType = Text",
        "",
        "\tannotation PBI_NavigationStepName = Navigation",
        "",
    ])


# ---------------------------------------------------------------------------
def main():
    TABLES.mkdir(parents=True, exist_ok=True)

    schemas: dict[str, pd.DataFrame] = {}
    for pq in sorted(CURATED.glob("*.parquet")):
        n = pq.stem
        if n in EXCLUDE:
            continue
        schemas[n] = pd.read_parquet(pq).head(50)

    table_names = list(schemas)

    # per-table TMDL
    for n, df in schemas.items():
        _write(TABLES / f"{n}.tmdl", table_tmdl(n, df, f"{n}.parquet"))

    # helper / disconnected tables
    _write(TABLES / "Reporting Currency.tmdl", helper_table(
        "Reporting Currency",
        [("Currency", "string"), ("Symbol", "string"), ("Sort", "int")],
        [["USD", "$", 1], ["BRL", "R$", 2], ["MXN", "MX$", 3]]))
    _write(TABLES / "P&L Line.tmdl", helper_table(
        "P&L Line",
        [("pnl_line", "string"), ("Display", "string"), ("Sign", "int"), ("Sort", "int")],
        [["subscription_revenue", "Subscription revenue", 1, 1],
         ["advertising_revenue", "Advertising revenue", 1, 2],
         ["partner_revenue", "Partner revenue", 1, 3],
         ["content_amortization", "Content amortisation", -1, 4],
         ["streaming_delivery", "Streaming delivery (CDN)", -1, 5],
         ["payment_processing", "Payment processing", -1, 6],
         ["customer_support", "Customer support", -1, 7],
         ["marketing", "Marketing", -1, 8],
         ["g_a_allocation", "G&A allocation", -1, 9]]))
    _write(TABLES / "Subscriber Bridge.tmdl", helper_table(
        "Subscriber Bridge",
        [("Step", "string"), ("Sort", "int")],
        [["Start of period", 1], ["New", 2], ["Reactivation", 3],
         ["Voluntary churn", 4], ["Involuntary churn", 5], ["End of period", 6]]))
    _write(TABLES / "Funnel Stage.tmdl", helper_table(
        "Funnel Stage",
        [("Stage", "string"), ("Sort", "int")],
        [["Sign-ups", 1], ["Trial starts", 2], ["Trial to paid", 3],
         ["Active at M1", 4], ["Active at M3", 5], ["Active at M6", 6]]))
    _write(TABLES / "_Measures.tmdl", measures_table())

    helper_names = ["Reporting Currency", "P&L Line", "Subscriber Bridge", "Funnel Stage", "_Measures"]

    # model-level files
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
        "config": {"version": "2.0", "logicalId": gid("sm", NAME)},
    })

    # The .pbip and the .Report are created by powerbi/build_report.sh
    # (via `pbir new report --thick` + `pbir report rebind --local`).
    print(f"semantic model: {len(table_names)} imported tables + {len(helper_names)} helper tables")
    print(f"  {SM}")


if __name__ == "__main__":
    main()
