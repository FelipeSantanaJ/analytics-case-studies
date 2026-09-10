"""
Generate the Power BI semantic model (TMDL) for VoltEdge Electronics from the curated
Parquet schemas.

Emits  powerbi/VoltEdge Electronics.SemanticModel/  as a PBIP-format TMDL folder:
  .platform
  definition.pbism
  definition/database.tmdl
  definition/model.tmdl
  definition/expressions.tmdl          -- pDataFolder parameter
  definition/relationships.tmdl        -- hand-specified star relationships
  definition/tables/<table>.tmdl       -- one per curated table, Parquet import partition
  definition/tables/_Measures.tmdl     -- the full DAX measure library (from pbi_measures.py)

Run after the ETL pipeline. Re-runnable: lineage tags are deterministic (uuid5).
"""

from __future__ import annotations

import json
import shutil
import uuid
from pathlib import Path

import pyarrow.parquet as pq

import config as C
from pbi_measures import MEASURE_LIBRARY, MODEL_CULTURE

PBI_DIR = C.PROJECT_DIR / "powerbi"
SM_DIR = PBI_DIR / "VoltEdge Electronics.SemanticModel"
RPT_DIR = PBI_DIR / "VoltEdge Electronics.Report"
DEF = SM_DIR / "definition"
TABLES_DIR = DEF / "tables"

# a working PBIR report to borrow the Microsoft base-theme files from
_THEME_DONOR = Path.home() / "Documents" / "Portfolio" / "Orbit" / "orbit.Report" / "StaticResources"

PAGES = [
    ("executive-summary", "Executive Summary"),
    ("sales-performance", "Sales Performance"),
    ("marketing-acquisition", "Marketing & Acquisition"),
    ("website-digital", "Website & Digital"),
    ("logistics-fulfillment", "Logistics & Fulfillment"),
    ("crm-customer", "CRM & Customer"),
    ("product-inventory", "Product & Inventory"),
]
PAGE_W, PAGE_H = 1280, 1000
NS = uuid.UUID("5f1c0d2e-9a7b-4c33-8e11-voltedge0001".replace("voltedge0001", "0b1c2d3e4f50"))


def tag(*parts: str) -> str:
    return str(uuid.uuid5(NS, "|".join(parts)))


# ---- arrow -> TMDL dataType ---------------------------------------------------------

def tmdl_type(arrow_type: str) -> str:
    t = arrow_type.lower()
    if t.startswith(("int", "uint")):
        return "int64"
    if t.startswith(("float", "double", "decimal")):
        return "double"
    if t.startswith("bool"):
        return "boolean"
    if t.startswith(("timestamp", "date")):
        return "dateTime"
    return "string"


# ---- per-column summarizeBy / hidden ----------------------------------------------

_ADDITIVE_HINTS = ("amount", "qty", "quantity", "units", "value", "cost", "price",
                   "spend", "impressions", "clicks", "sessions", "users", "pageviews",
                   "bounces", "carts", "transactions", "revenue", "profit", "fee",
                   "financing", "target_value", "po_value")
_NONADDITIVE = ("_key", "_id", "id", "date", "year", "month", "day", "week", "quarter",
                "rate", "days", "hours", "pct", "_pct", "csat", "installment", "terms",
                "lag", "cover", "on_hand", "in_transit")


def col_props(name: str, dtype: str) -> tuple[str, bool]:
    n = name.lower()
    hidden = n.endswith("_key")
    if dtype in ("string", "boolean", "dateTime"):
        return "none", hidden
    if n.endswith("_key") or n in ("date_key",) or n.endswith("_id") or n == "id":
        return "none", hidden
    if any(h in n for h in _NONADDITIVE):
        return "none", hidden
    if any(h in n for h in _ADDITIVE_HINTS):
        return "sum", hidden
    return "none", hidden


# ---- relationships (from_table[from_col] *--1 to_table[to_col]) --------------------
# (dim, dim_key, fact, fact_col, is_active)

_DATE_ROLES = {
    "fact_order_lines": ["order_date_key", "ship_date_key", "delivery_date_key"],
    "fact_orders": ["order_date_key", "ship_date_key", "delivery_date_key"],
    "fact_payment_schedule": ["order_date_key", "due_date_key"],
    "fact_marketing_spend": ["date_key"],
    "fact_web_traffic_daily": ["date_key"],
    "fact_returns": ["return_date_key"],
    "fact_support_tickets": ["created_date_key", "resolved_date_key"],
    "fact_purchase_orders": ["order_date_key", "expected_receipt_date_key",
                             "actual_receipt_date_key", "payment_due_date_key",
                             "supplier_paid_date_key"],
    "fact_inventory_movement": ["movement_date_key"],
    "fact_inventory_snapshot": ["snapshot_date_key"],
    "fact_exchange_rate": ["date_key"],
    "fact_target": ["month_date_key"],
}
_MARKET_FACTS = ["fact_order_lines", "fact_orders", "fact_payment_schedule", "fact_returns",
                 "fact_marketing_spend", "fact_web_traffic_daily", "fact_support_tickets",
                 "fact_purchase_orders", "fact_inventory_movement", "fact_inventory_snapshot",
                 "fact_target"]
_CUSTOMER_FACTS = ["fact_order_lines", "fact_orders", "fact_returns", "fact_support_tickets"]
_PRODUCT_FACTS = ["fact_order_lines", "fact_returns", "fact_purchase_orders",
                  "fact_inventory_movement", "fact_inventory_snapshot"]
_CHANNEL_FACTS = ["fact_order_lines", "fact_orders", "fact_marketing_spend", "fact_web_traffic_daily"]
_CURRENCY_FACTS = ["fact_order_lines", "fact_orders", "fact_payment_schedule", "fact_returns",
                   "fact_exchange_rate"]
_WAREHOUSE_FACTS = ["fact_orders", "fact_purchase_orders", "fact_inventory_movement",
                    "fact_inventory_snapshot"]


def relationships() -> list[dict]:
    rels = []
    for fact, roles in _DATE_ROLES.items():
        for i, col in enumerate(roles):
            rels.append(dict(fromT=fact, fromC=col, toT="dim_date", toC="date_key",
                             active=(i == 0)))
    for fact in _MARKET_FACTS:
        rels.append(dict(fromT=fact, fromC="market_key", toT="dim_market", toC="market_key", active=True))
    for fact in _CUSTOMER_FACTS:
        rels.append(dict(fromT=fact, fromC="customer_key", toT="dim_customer", toC="customer_key", active=True))
    for fact in _PRODUCT_FACTS:
        rels.append(dict(fromT=fact, fromC="product_key", toT="dim_product", toC="product_key", active=True))
    for fact in _CHANNEL_FACTS:
        rels.append(dict(fromT=fact, fromC="channel_key", toT="dim_channel", toC="channel_key", active=True))
    for fact in _CURRENCY_FACTS:
        rels.append(dict(fromT=fact, fromC="currency_key", toT="dim_currency", toC="currency_key", active=True))
    for fact in _WAREHOUSE_FACTS:
        rels.append(dict(fromT=fact, fromC="warehouse_key", toT="dim_warehouse", toC="warehouse_key", active=True))
    rels += [
        dict(fromT="fact_orders", fromC="payment_method_key", toT="dim_payment_method", toC="payment_method_key", active=True),
        dict(fromT="fact_orders", fromC="carrier_key", toT="dim_carrier", toC="carrier_key", active=True),
        dict(fromT="fact_purchase_orders", fromC="supplier_key", toT="dim_supplier", toC="supplier_key", active=True),
        dict(fromT="fact_marketing_spend", fromC="campaign_key", toT="dim_campaign", toC="campaign_key", active=True),
        dict(fromT="dim_product", fromC="supplier_key", toT="dim_supplier", toC="supplier_key", active=False),
        # string-keyed small dims
        dict(fromT="fact_orders", fromC="device", toT="dim_device", toC="device", active=True),
        dict(fromT="fact_web_traffic_daily", fromC="device", toT="dim_device", toC="device", active=True),
        dict(fromT="fact_returns", fromC="reason", toT="dim_return_reason", toC="reason", active=True),
        dict(fromT="fact_support_tickets", fromC="category", toT="dim_ticket_category", toC="category", active=True),
        dict(fromT="fact_target", fromC="metric", toT="dim_metric", toC="metric", active=True),
    ]
    return rels


# ---- TMDL emitters ---------------------------------------------------------------

# ordered-text columns that must sort by a numeric sibling, not alphabetically
_SORT_BY = {
    "dim_date": {"month_year": "month_sort", "month_name": "month",
                 "quarter_name": "quarter_sort", "day_name": "day_of_week"},
}


def emit_table(name: str, schema) -> str:
    lines = [f"table {name}", f"\tlineageTag: {tag('table', name)}", ""]
    sort_by = _SORT_BY.get(name, {})
    for field in schema:
        dtype = tmdl_type(str(field.type))
        summ, hidden = col_props(field.name, dtype)
        lines.append(f"\tcolumn {field.name}")
        lines.append(f"\t\tdataType: {dtype}")
        if hidden:
            lines.append("\t\tisHidden")
        lines.append(f"\t\tlineageTag: {tag('col', name, field.name)}")
        lines.append(f"\t\tsummarizeBy: {summ}")
        lines.append(f"\t\tsourceColumn: {field.name}")
        if field.name in sort_by:
            lines.append(f"\t\tsortByColumn: {sort_by[field.name]}")
        if dtype == "dateTime":
            lines.append("\t\tformatString: yyyy-mm-dd")
        lines.append("")
        lines.append("\t\tannotation SummarizationSetBy = Automatic")
        lines.append("")
    if name == "dim_date":
        # a string label for the extract window (safe to use as a categorical filter)
        lines += [
            '\tcolumn period_label = IF ( dim_date[in_extract_window], "Analysis window", "Buffer" )',
            "\t\tdataType: string",
            f"\t\tlineageTag: {tag('col', name, 'period_label')}",
            "\t\tsummarizeBy: none", "",
            "\t\tannotation SummarizationSetBy = Automatic", "",
        ]
        for cn, expr in (("month_sort", "dim_date[year] * 100 + dim_date[month]"),  # year-aware sort keys
                         ("quarter_sort", "dim_date[year] * 10 + dim_date[quarter]")):
            lines += [
                f"\tcolumn {cn} = {expr}",
                "\t\tdataType: int64",
                "\t\tisHidden",
                f"\t\tlineageTag: {tag('col', name, cn)}",
                "\t\tsummarizeBy: none",
                "",
                "\t\tannotation SummarizationSetBy = Automatic",
                "",
            ]
    grp = "dimensions" if name.startswith("dim") else ("parameters" if name.startswith("_") else "facts")
    lines += [
        f"\tpartition {name} = m",
        "\t\tmode: import",
        f"\t\tqueryGroup: {grp}",
        "\t\tsource =",
        "\t\t\t\tlet",
        f'\t\t\t\t    Source = Parquet.Document(File.Contents(pDataFolder & "\\{name}.parquet"))',
        "\t\t\t\tin",
        "\t\t\t\t    Source",
        "",
        "\tannotation PBI_ResultType = Table",
        "",
    ]
    return "\n".join(lines) + "\n"


def emit_measures_table() -> str:
    lines = ["table _Measures",
             f"\tlineageTag: {tag('table', '_Measures')}", ""]
    for folder, measures in MEASURE_LIBRARY:
        for m in measures:
            nm, dax = m["name"], m["dax"].strip()
            fmt = m.get("format")
            if "\n" in dax:
                body = "\n".join("\t\t\t" + ln for ln in dax.splitlines())
                lines.append(f"\tmeasure '{nm}' =")
                lines.append(body)
            else:
                lines.append(f"\tmeasure '{nm}' = {dax}")
            if fmt:
                lines.append(f"\t\tformatString: {fmt}")
            lines.append(f"\t\tdisplayFolder: {folder}")
            lines.append(f"\t\tlineageTag: {tag('measure', nm)}")
            if m.get("hint"):
                lines.append(f'\t\tannotation PBI_FormatHint = {m["hint"]}')
            lines.append("")
    # a hidden placeholder column so Desktop shows it as a measure table
    lines += [
        "\tcolumn _placeholder",
        "\t\tdataType: int64",
        "\t\tisHidden",
        f"\t\tlineageTag: {tag('col', '_Measures', '_placeholder')}",
        "\t\tsummarizeBy: none",
        "\t\tsourceColumn: _placeholder",
        "",
        "\t\tannotation SummarizationSetBy = Automatic",
        "",
        "\tpartition _Measures = m",
        "\t\tmode: import",
        "\t\tqueryGroup: parameters",
        "\t\tsource =",
        "\t\t\t\tlet",
        '\t\t\t\t    Source = #table(type table [_placeholder = Int64.Type], {{1}})',
        "\t\t\t\tin",
        "\t\t\t\t    Source",
        "",
        "\tannotation PBI_ResultType = Table",
        "",
    ]
    return "\n".join(lines) + "\n"


def emit_reporting_currency_table() -> str:
    """Disconnected what-if table driving the reporting-currency selector."""
    rows = ",\n".join(
        f'\t\t\t\t\t\t{{"{c}", {i}}}' for i, c in enumerate(C.CURRENCIES))
    return (
        "table 'Reporting Currency'\n"
        f"\tlineageTag: {tag('table', 'Reporting Currency')}\n\n"
        "\tcolumn Currency\n\t\tdataType: string\n"
        f"\t\tlineageTag: {tag('col', 'rc', 'Currency')}\n"
        "\t\tsummarizeBy: none\n\t\tsourceColumn: Currency\n\t\tsortByColumn: Sort\n\n"
        "\t\tannotation SummarizationSetBy = Automatic\n\n"
        "\tcolumn Sort\n\t\tdataType: int64\n\t\tisHidden\n"
        f"\t\tlineageTag: {tag('col', 'rc', 'Sort')}\n"
        "\t\tsummarizeBy: none\n\t\tsourceColumn: Sort\n\n"
        "\t\tannotation SummarizationSetBy = Automatic\n\n"
        "\tpartition 'Reporting Currency' = m\n\t\tmode: import\n\t\tqueryGroup: parameters\n"
        "\t\tsource =\n\t\t\t\tlet\n"
        '\t\t\t\t    Source = #table(type table [Currency = Text.Type, Sort = Int64.Type], {\n'
        f"{rows}\n\t\t\t\t    }})\n\t\t\t\tin\n\t\t\t\t    Source\n\n"
        "\tannotation PBI_ResultType = Table\n"
    )


def emit_funnel_stage_table() -> str:
    # on-site funnel (media metrics — impressions/clicks — live on cards, not here)
    stages = [("Sessions", 1), ("Add-to-Cart", 2), ("Cart", 3), ("Orders", 4)]
    rows = ",\n".join(f'\t\t\t\t\t\t{{"{s}", {i}}}' for s, i in stages)
    return (
        "table 'Funnel Stage'\n"
        f"\tlineageTag: {tag('table', 'Funnel Stage')}\n\n"
        "\tcolumn Stage\n\t\tdataType: string\n"
        f"\t\tlineageTag: {tag('col', 'fs', 'Stage')}\n"
        "\t\tsummarizeBy: none\n\t\tsourceColumn: Stage\n\t\tsortByColumn: Sort\n\n"
        "\t\tannotation SummarizationSetBy = Automatic\n\n"
        "\tcolumn Sort\n\t\tdataType: int64\n\t\tisHidden\n"
        f"\t\tlineageTag: {tag('col', 'fs', 'Sort')}\n"
        "\t\tsummarizeBy: none\n\t\tsourceColumn: Sort\n\n"
        "\t\tannotation SummarizationSetBy = Automatic\n\n"
        "\tpartition 'Funnel Stage' = m\n\t\tmode: import\n\t\tqueryGroup: parameters\n"
        "\t\tsource =\n\t\t\t\tlet\n"
        '\t\t\t\t    Source = #table(type table [Stage = Text.Type, Sort = Int64.Type], {\n'
        f"{rows}\n\t\t\t\t    }})\n\t\t\t\tin\n\t\t\t\t    Source\n\n"
        "\tannotation PBI_ResultType = Table\n"
    )


def _q(name: str) -> str:
    """Quote a TMDL object name if it contains characters that need it."""
    return f"'{name}'" if (" " in name or "-" in name) else name


def emit_pl_line_table() -> str:
    lines_ = [("Gross Profit", 1), ("Marketing", 2), ("Shipping", 3),
              ("Payment Fees", 4), ("Financing", 5)]
    rows = ",\n".join(f'\t\t\t\t\t\t{{"{s}", {i}}}' for s, i in lines_)
    return (
        "table 'PL Line'\n"
        f"\tlineageTag: {tag('table', 'PL Line')}\n\n"
        "\tcolumn Line\n\t\tdataType: string\n"
        f"\t\tlineageTag: {tag('col', 'pl', 'Line')}\n"
        "\t\tsummarizeBy: none\n\t\tsourceColumn: Line\n\t\tsortByColumn: Sort\n\n"
        "\t\tannotation SummarizationSetBy = Automatic\n\n"
        "\tcolumn Sort\n\t\tdataType: int64\n\t\tisHidden\n"
        f"\t\tlineageTag: {tag('col', 'pl', 'Sort')}\n"
        "\t\tsummarizeBy: none\n\t\tsourceColumn: Sort\n\n"
        "\t\tannotation SummarizationSetBy = Automatic\n\n"
        "\tpartition 'PL Line' = m\n\t\tmode: import\n\t\tqueryGroup: parameters\n"
        "\t\tsource =\n\t\t\t\tlet\n"
        '\t\t\t\t    Source = #table(type table [Line = Text.Type, Sort = Int64.Type], {\n'
        f"{rows}\n\t\t\t\t    }})\n\t\t\t\tin\n\t\t\t\t    Source\n\n"
        "\tannotation PBI_ResultType = Table\n"
    )


def emit_revenue_bridge_table() -> str:
    # Plan -> variance by product category -> (waterfall adds the Total)
    _cats = list(C.CATEGORIES.keys())
    lines_ = [("Plan", 1)] + [(c, i + 2) for i, c in enumerate(_cats)]
    rows = ",\n".join(f'\t\t\t\t\t\t{{"{s}", {i}}}' for s, i in lines_)
    return (
        "table 'Revenue Bridge'\n"
        f"\tlineageTag: {tag('table', 'Revenue Bridge')}\n\n"
        "\tcolumn Line\n\t\tdataType: string\n"
        f"\t\tlineageTag: {tag('col', 'rb', 'Line')}\n"
        "\t\tsummarizeBy: none\n\t\tsourceColumn: Line\n\t\tsortByColumn: Sort\n\n"
        "\t\tannotation SummarizationSetBy = Automatic\n\n"
        "\tcolumn Sort\n\t\tdataType: int64\n\t\tisHidden\n"
        f"\t\tlineageTag: {tag('col', 'rb', 'Sort')}\n"
        "\t\tsummarizeBy: none\n\t\tsourceColumn: Sort\n\n"
        "\t\tannotation SummarizationSetBy = Automatic\n\n"
        "\tpartition 'Revenue Bridge' = m\n\t\tmode: import\n\t\tqueryGroup: parameters\n"
        "\t\tsource =\n\t\t\t\tlet\n"
        '\t\t\t\t    Source = #table(type table [Line = Text.Type, Sort = Int64.Type], {\n'
        f"{rows}\n\t\t\t\t    }})\n\t\t\t\tin\n\t\t\t\t    Source\n\n"
        "\tannotation PBI_ResultType = Table\n"
    )


def emit_model(table_names: list[str]) -> str:
    order = ", ".join(f'"{t}"' for t in table_names)
    refs = "\n".join(f"ref table {_q(t)}" for t in table_names)
    return (
        "model Model\n"
        f"\tculture: {MODEL_CULTURE}\n"
        "\tdefaultPowerBIDataSourceVersion: powerBI_V3\n"
        "\tdiscourageImplicitMeasures\n"
        f"\tsourceQueryCulture: {MODEL_CULTURE}\n"
        "\tdataAccessOptions\n"
        "\t\tlegacyRedirects\n"
        "\t\treturnErrorValuesAsNull\n\n"
        "queryGroup dimensions\n\n\tannotation PBI_QueryGroupOrder = 0\n\n"
        "queryGroup facts\n\n\tannotation PBI_QueryGroupOrder = 1\n\n"
        "queryGroup parameters\n\n\tannotation PBI_QueryGroupOrder = 2\n\n"
        "annotation __PBI_TimeIntelligenceEnabled = 0\n\n"
        f"annotation PBI_QueryOrder = [{order}]\n\n"
        f"{refs}\n"
    )


def emit_expressions() -> str:
    p = str(C.CURATED_DIR).replace("\\", "\\\\")
    return (
        f'expression pDataFolder = "{p}" meta [IsParameterQuery=true, Type="Text", '
        "IsParameterQueryRequired=true]\n"
        f"\tlineageTag: {tag('expr', 'pDataFolder')}\n"
        "\tqueryGroup: parameters\n\n"
        "\tannotation PBI_NavigationStepName = Navigation\n"
        "\tannotation PBI_ResultType = Text\n"
    )


def emit_relationships(rels: list[dict]) -> str:
    out = []
    for r in rels:
        rid = tag("rel", r["fromT"], r["fromC"], r["toT"], r["toC"])
        block = [f"relationship {rid}"]
        if not r["active"]:
            block.append("\tisActive: false")
        block.append(f"\tfromColumn: {r['fromT']}.{r['fromC']}")
        block.append(f"\ttoColumn: {r['toT']}.{r['toC']}")
        out.append("\n".join(block))
    return "\n\n".join(out) + "\n"


# ---- main ------------------------------------------------------------------------

def main() -> None:
    TABLES_DIR.mkdir(parents=True, exist_ok=True)
    (SM_DIR / ".pbi").mkdir(exist_ok=True)

    parquets = sorted(C.CURATED_DIR.glob("*.parquet"))
    dims = [p.stem for p in parquets if p.stem.startswith("dim")]
    facts = [p.stem for p in parquets if p.stem.startswith("fact")]
    data_tables = dims + facts

    for p in parquets:
        schema = pq.read_schema(p)
        (TABLES_DIR / f"{p.stem}.tmdl").write_text(emit_table(p.stem, schema), encoding="utf-8")
    (TABLES_DIR / "_Measures.tmdl").write_text(emit_measures_table(), encoding="utf-8")
    (TABLES_DIR / "Reporting Currency.tmdl").write_text(emit_reporting_currency_table(), encoding="utf-8")
    (TABLES_DIR / "Funnel Stage.tmdl").write_text(emit_funnel_stage_table(), encoding="utf-8")
    (TABLES_DIR / "PL Line.tmdl").write_text(emit_pl_line_table(), encoding="utf-8")
    (TABLES_DIR / "Revenue Bridge.tmdl").write_text(emit_revenue_bridge_table(), encoding="utf-8")

    all_tables = data_tables + ["_Measures", "Reporting Currency", "Funnel Stage",
                                "PL Line", "Revenue Bridge"]
    (DEF / "model.tmdl").write_text(emit_model(all_tables), encoding="utf-8")
    (DEF / "database.tmdl").write_text("database\n\tcompatibilityLevel: 1600\n", encoding="utf-8")
    (DEF / "expressions.tmdl").write_text(emit_expressions(), encoding="utf-8")
    (DEF / "relationships.tmdl").write_text(emit_relationships(relationships()), encoding="utf-8")

    (SM_DIR / "definition.pbism").write_text(
        '{\n  "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/'
        'semanticModel/definitionProperties/1.0.0/schema.json",\n  "version": "4.2",\n'
        '  "settings": {}\n}\n', encoding="utf-8")
    (SM_DIR / ".platform").write_text(
        '{\n  "$schema": "https://developer.microsoft.com/json-schemas/fabric/'
        'gitIntegration/platformProperties/2.0.0/schema.json",\n  "metadata": {\n'
        '    "type": "SemanticModel",\n    "displayName": "VoltEdge Electronics"\n  },\n'
        f'  "config": {{\n    "version": "2.0",\n    "logicalId": "{tag("logical", "SemanticModel")}"\n  }}\n}}\n',
        encoding="utf-8")

    n_meas = sum(len(ms) for _, ms in MEASURE_LIBRARY)
    print(f"semantic model written to {SM_DIR}")
    print(f"  {len(data_tables)} data tables + _Measures ({n_meas} measures) + Reporting Currency")
    print(f"  {len(relationships())} relationships")

    if RPT_DIR.exists():
        print(f"report scaffold already exists at {RPT_DIR} — left untouched "
              "(delete it to regenerate the empty scaffold)")
    else:
        emit_report_scaffold()
        print(f"report scaffold written to {RPT_DIR}  ({len(PAGES)} pages)")


# ---- report (PBIR) scaffold -----------------------------------------------------

def emit_report_scaffold() -> None:
    rdef = RPT_DIR / "definition"
    (rdef / "pages").mkdir(parents=True, exist_ok=True)
    (RPT_DIR / ".pbi").mkdir(exist_ok=True)

    # borrow the Microsoft base-theme files from a working local report
    sr = RPT_DIR / "StaticResources"
    if _THEME_DONOR.exists():
        src, dst = _THEME_DONOR / "SharedResources/BaseThemes", sr / "SharedResources/BaseThemes"
        dst.mkdir(parents=True, exist_ok=True)
        for f in (src.glob("*.json") if src.exists() else []):
            shutil.copy2(f, dst / f.name)
    # register the custom VoltEdge theme
    rr = sr / "RegisteredResources"
    rr.mkdir(parents=True, exist_ok=True)
    theme_src = PBI_DIR / "theme" / "VoltEdge.json"
    if theme_src.exists():
        shutil.copy2(theme_src, rr / "VoltEdge.json")

    (RPT_DIR / ".platform").write_text(json.dumps({
        "$schema": "https://developer.microsoft.com/json-schemas/fabric/gitIntegration/platformProperties/2.0.0/schema.json",
        "metadata": {"type": "Report", "displayName": "VoltEdge Electronics"},
        "config": {"version": "2.0", "logicalId": tag("logical", "Report")},
    }, indent=2), encoding="utf-8")

    (RPT_DIR / "definition.pbir").write_text(json.dumps({
        "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definitionProperties/2.0.0/schema.json",
        "version": "4.0",
        "datasetReference": {"byPath": {"path": "../VoltEdge Electronics.SemanticModel"}},
    }, indent=2), encoding="utf-8")

    (rdef / "version.json").write_text(json.dumps({
        "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/versionMetadata/1.0.0/schema.json",
        "version": "2.0.0",
    }, indent=2), encoding="utf-8")

    report_json = {
        "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/report/3.3.0/schema.json",
        "themeCollection": {
            "baseTheme": {"name": "CY26SU05",
                          "reportVersionAtImport": {"visual": "2.9.0", "report": "3.3.0", "page": "2.3.1"},
                          "type": "SharedResources"},
            "customTheme": {"name": "VoltEdge.json", "type": "RegisteredResources",
                            "reportVersionAtImport": {"visual": "2.9.0", "report": "3.3.0", "page": "2.3.1"}},
        },
        "objects": {"section": [{"properties": {"verticalAlignment": {"expr": {"Literal": {"Value": "'Top'"}}}}}]},
        "resourcePackages": [
            {"name": "SharedResources", "type": "SharedResources",
             "items": [{"name": "CY26SU05", "path": "BaseThemes/CY26SU05.json", "type": "BaseTheme"}]},
            {"name": "RegisteredResources", "type": "RegisteredResources",
             "items": [{"name": "VoltEdge.json", "path": "VoltEdge.json", "type": "CustomTheme"}]},
        ],
        "settings": {
            "useStylableVisualContainerHeader": True,
            "exportDataMode": "AllowSummarized",
            "defaultDrillFilterOtherVisuals": True,
            "allowChangeFilterTypes": True,
            "useEnhancedTooltips": True,
        },
    }
    (rdef / "report.json").write_text(json.dumps(report_json, indent=2), encoding="utf-8")

    for slug, title in PAGES:
        pdir = rdef / "pages" / slug
        (pdir / "visuals").mkdir(parents=True, exist_ok=True)
        (pdir / "page.json").write_text(json.dumps({
            "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/page/2.1.0/schema.json",
            "name": slug,
            "displayName": title,
            "displayOption": "FitToPage",
            "height": PAGE_H,
            "width": PAGE_W,
            "objects": {"background": [{"properties": {}}]},
        }, indent=2), encoding="utf-8")

    (rdef / "pages" / "pages.json").write_text(json.dumps({
        "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/pagesMetadata/1.1.0/schema.json",
        "pageOrder": [s for s, _ in PAGES],
        "activePageName": PAGES[0][0],
    }, indent=2), encoding="utf-8")

    (PBI_DIR / "VoltEdge Electronics.pbip").write_text(json.dumps({
        "$schema": "https://developer.microsoft.com/json-schemas/fabric/pbip/pbipProperties/1.0.0/schema.json",
        "version": "1.0",
        "artifacts": [{"report": {"path": "VoltEdge Electronics.Report"}}],
        "settings": {"enableAutoRecovery": True},
    }, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
