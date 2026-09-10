"""
gen_data_dictionary.py — introspect data/curated/ and (re)write docs/03_data_dictionary.md.

Auto-generated: table grain guess, row count, and every column with dtype + sample values.
"""
from __future__ import annotations

import sys
import datetime as _dt
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config as C

GRAIN = {
    "dim_date": "one row per calendar day",
    "dim_market": "one row per market",
    "dim_subscriber": "one row per subscriber (account with >=1 paid start)",
    "dim_plan": "one row per tier x billing period x market",
    "dim_price_history": "one row per tier x market x price-effective period",
    "dim_channel": "one row per acquisition channel",
    "dim_device": "one row per device family",
    "dim_payment_method": "one row per payment method",
    "dim_content": "one row per catalogue title",
    "dim_support_reason": "one row per unified support reason category",
    "dim_app_version": "one row per observed app version string",
    "fact_subscription_event": "one row per subscription lifecycle event (movement ledger)",
    "fact_subscription_month": "one row per subscriber x month while subscribed (folded from the ledger)",
    "fact_billing_attempt": "one row per billing attempt",
    "fact_viewing_daily": "one row per subscriber x local date x device family (partitioned by month)",
    "fact_engagement_month": "one row per subscriber x month with streaming activity",
    "fact_app_performance_daily": "one row per market x date x device family x app version",
    "fact_marketing_spend": "one row per week x market x channel x campaign",
    "fact_ad_revenue": "one row per market x day",
    "fact_content_cost": "one row per title x month",
    "fact_support_ticket": "one row per support ticket",
    "fact_fx_rate": "one row per month x currency",
    "fact_finance_month": "one row per month x market x P&L line",
    "fact_targets_month": "one row per market x month x KPI",
}


def sample_vals(s: pd.Series, k=3):
    vals = s.dropna().unique()[:k]
    out = []
    for v in vals:
        v = str(v)
        out.append(v if len(v) <= 32 else v[:29] + "...")
    return ", ".join(out) if out else "—"


def describe(path: Path):
    if path.is_dir():
        parts = sorted(path.glob("*.parquet"))
        if not parts:
            return None
        df = pd.read_parquet(parts[0])
        nrows = sum(pd.read_parquet(p, columns=[df.columns[0]]).shape[0] for p in parts)
        note = f" (across {len(parts)} monthly parts)"
    else:
        df = pd.read_parquet(path)
        nrows = len(df)
        note = ""
    name = path.stem if path.is_file() else path.name
    lines = [f"### `{name}`", "",
             f"*{GRAIN.get(name, 'one row per record')}* · **{nrows:,} rows**{note}", "",
             "| column | dtype | sample values |", "|---|---|---|"]
    for c in df.columns:
        lines.append(f"| `{c}` | {df[c].dtype} | {sample_vals(df[c])} |")
    lines.append("")
    return "\n".join(lines)


def main():
    cur = C.CURATED
    entries = sorted([p for p in cur.iterdir()
                      if (p.suffix == ".parquet") or (p.is_dir() and any(p.glob("*.parquet")))],
                     key=lambda p: (0 if p.name.startswith("dim") else 1, p.name))
    seen = set()
    blocks = []
    for p in entries:
        key = p.stem if p.is_file() else p.name
        if key in seen:
            continue
        seen.add(key)
        b = describe(p)
        if b:
            blocks.append(b)
    header = [
        "# Voxa+ — Data Dictionary (curated layer)", "",
        f"_Auto-generated from `data/curated/` on {_dt.date.today()} by "
        "`etl/gen_data_dictionary.py`. Do not edit by hand._", "",
        "All monetary columns are stored `*_local` (transaction currency) and `*_usd` "
        "(month-average FX). Surrogate keys are `*_key` (integer); business keys keep their "
        "source form as `*_id`. Sentinel keys: `-1` unknown, `0` unresolved.", "",
        "---", "",
    ]
    (C.DOCS).mkdir(parents=True, exist_ok=True)
    (C.DOCS / "03_data_dictionary.md").write_text("\n".join(header) + "\n\n".join(blocks),
                                                  encoding="utf-8")
    print(f"wrote {C.DOCS / '03_data_dictionary.md'}  ({len(blocks)} tables)")


if __name__ == "__main__":
    main()
