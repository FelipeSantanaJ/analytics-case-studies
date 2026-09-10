"""
Generate docs/03_data_dictionary.md from the actual files on disk.

Run after the pipeline. Documents every raw export, every staging table and every
curated table: columns, dtype, null %, row count, plus a one-line hand-written purpose
for each table and a sample value per column.
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

import config as C

DOC = C.PROJECT_DIR / "docs" / "03_data_dictionary.md"

RAW_PURPOSE = {
    "fx_rates.csv": "Finance — daily USD-per-unit FX rates (EU date format, USD row omitted).",
    "suppliers.csv": "Procurement — supplier master: country, payment terms, lead time, reliability.",
    "erp_products.xlsx": "ERP — product master + monthly cost_history + price_history (3 sheets); category spellings intentionally inconsistent.",
    "crm_customers.csv": "CRM — customer master (utf-8 region files).",
    "crm_customers_br.csv": "CRM — Brazil customer master, exported in Latin-1.",
    "oms_orders.csv": "Storefront/OMS — order headers; mixed date & money formats.",
    "oms_order_lines.csv": "Storefront/OMS — order lines; a few duplicates & negative quantities.",
    "psp_transactions.csv": "Payment processor — one auth per order (+ unmatched noise); fee column mislabelled.",
    "procurement_purchase_orders.csv": "Procurement — PO lines with receipt, due and paid dates.",
    "wms_inventory_movements.csv": "WMS — stock movement ledger (adjustment / receipt / sale).",
    "wms_inventory_snapshots.csv": "WMS — month-end snapshots; ~3% perturbed vs the ledger.",
    "returns.csv": "Storefront — return lines with reason and restock flag.",
    "web_analytics_daily.csv": "Web analytics — daily sessions & funnel by market·channel·device.",
    "google_ads_report.csv": "Google Ads — daily paid search + display.",
    "meta_ads_export.csv": "Meta Ads — daily paid social (different column names & date format).",
    "other_marketing_spend.csv": "Finance — monthly affiliate commission + email tooling.",
    "support_tickets.csv": "Support desk — tickets with timestamps, FCR flag and CSAT.",
    "carrier_tracking.json": "Carrier — nested shipment + tracking events (sample); inconsistent status vocab.",
    "finance_targets.csv": "Finance — monthly plan per market for 5 metrics.",
}

CURATED_PURPOSE = {
    "dim_date": "Calendar dimension; fiscal year starts 1 July; promo / Black-Friday / YoY flags.",
    "dim_market": "The four markets, their currency, go-live date and comparable-base flag.",
    "dim_currency": "USD / EUR / GBP / BRL with the reporting-currency flag.",
    "dim_customer": "Customer dimension enriched with lifetime orders / revenue / status / loyalty tier.",
    "dim_product": "Product dimension: category hierarchy, price tier, lifecycle dates (+ Unknown stub).",
    "dim_supplier": "Supplier dimension: payment terms band, lead time, reliability band.",
    "dim_channel": "Marketing / acquisition channels grouped Paid / Owned / Earned.",
    "dim_campaign": "Distinct marketing campaigns with parsed theme.",
    "dim_payment_method": "Payment method rate card: MDR, fixed fee, settlement lag, instalment rules.",
    "dim_carrier": "Carriers per market with baseline transit days and on-time rate.",
    "dim_warehouse": "Fulfilment centres per market.",
    "dim_device": "Mobile / Desktop / Tablet.",
    "dim_return_reason": "Return reason codes.",
    "dim_ticket_category": "Support ticket categories.",
    "dim_order_status": "Order status values.",
    "dim_metric": "Target metric names.",
    "fact_order_lines": "One row per order line (product or warranty). Centre of the model.",
    "fact_orders": "One row per order header with delivery / perfect-order flags.",
    "fact_payment_schedule": "One row per settlement tranche (order × instalment).",
    "fact_returns": "One row per return line.",
    "fact_purchase_orders": "One row per PO line with receipt / due / paid dates.",
    "fact_inventory_movement": "Stock movement ledger with moving-average valuation.",
    "fact_inventory_snapshot": "Month-end stock per SKU×warehouse, derived from the ledger.",
    "fact_marketing_spend": "Daily spend / impressions / clicks by market·channel·campaign.",
    "fact_web_traffic_daily": "Daily sessions & funnel by market·channel·device.",
    "fact_support_tickets": "One row per support ticket.",
    "fact_exchange_rate": "Daily rate_to_usd / rate_from_usd per currency.",
    "fact_target": "Monthly plan value per market and metric.",
}


def sample_val(s: pd.Series) -> str:
    v = s.dropna()
    if v.empty:
        return ""
    x = str(v.iloc[0])
    return (x[:40] + "…") if len(x) > 41 else x


def frame_table(df: pd.DataFrame) -> list[str]:
    out = ["| column | dtype | null % | sample |", "|---|---|---:|---|"]
    n = max(1, len(df))
    for c in df.columns:
        out.append(f"| `{c}` | {df[c].dtype} | {df[c].isna().mean()*100:.1f} | {sample_val(df[c])} |")
    return out


def main() -> None:
    L = ["# 03 — Data Dictionary", "",
         "_Generated by `etl/gen_data_dictionary.py` from the files on disk._", "",
         "Three layers: **raw** (source-faithful, messy) → **staging** (cleaned & typed) → "
         "**curated** (star schema, BI-ready). Row counts and null rates are from the "
         "current seeded run.", ""]

    # ---- raw ----
    L += ["---", "", "## Raw layer — `data/raw/`", ""]
    for fname, purpose in RAW_PURPOSE.items():
        p = C.RAW_DIR / fname
        if not p.exists():
            continue
        L += [f"### `{fname}`", "", purpose, ""]
        try:
            if fname.endswith(".xlsx"):
                xl = pd.ExcelFile(p)
                for sh in xl.sheet_names:
                    d = xl.parse(sh, nrows=5000)
                    L += [f"**sheet `{sh}`** — {len(pd.read_excel(p, sheet_name=sh)):,} rows", ""]
                    L += frame_table(d) + [""]
            elif fname.endswith(".json"):
                obj = json.loads(p.read_text(encoding="utf-8"))
                key = [k for k in obj if isinstance(obj[k], list)][0]
                d = pd.json_normalize(obj[key])
                L += [f"{len(obj[key]):,} records (nested `events` array flattened on load)", ""]
                L += frame_table(d) + [""]
            else:
                enc = "latin-1" if fname.endswith("_br.csv") else "utf-8"
                d = pd.read_csv(p, nrows=5000, dtype=str, encoding=enc)
                full = sum(1 for _ in open(p, encoding=enc, errors="ignore")) - 1
                L += [f"{full:,} rows", ""]
                L += frame_table(d) + [""]
        except Exception as e:  # pragma: no cover
            L += [f"_(could not introspect: {e})_", ""]

    # ---- staging ----
    L += ["---", "", "## Staging layer — `data/staging/`", "",
          "Typed Parquet, one table per entity. Cleaning rules in "
          "[`04_etl_pipeline.md`](04_etl_pipeline.md).", ""]
    for p in sorted(C.STAGING_DIR.glob("*.parquet")):
        d = pd.read_parquet(p)
        L += [f"### `{p.stem}` — {len(d):,} rows", ""]
        L += frame_table(d) + [""]

    # ---- curated ----
    L += ["---", "", "## Curated layer — `data/curated/`", "",
          "Star schema (Parquet + CSV). Grain and relationships in "
          "[`05_data_model.md`](05_data_model.md).", ""]
    order = [k for k in CURATED_PURPOSE]
    files = {p.stem: p for p in C.CURATED_DIR.glob("*.parquet")}
    for name in order + [n for n in files if n not in order]:
        if name not in files:
            continue
        d = pd.read_parquet(files[name])
        L += [f"### `{name}` — {len(d):,} rows", "",
              CURATED_PURPOSE.get(name, ""), ""]
        L += frame_table(d) + [""]

    DOC.write_text("\n".join(L), encoding="utf-8")
    print(f"wrote {DOC}  ({len(L)} lines)")


if __name__ == "__main__":
    main()
