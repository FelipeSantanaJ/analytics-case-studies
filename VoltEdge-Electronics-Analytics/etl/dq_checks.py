"""
Stage 04 — data-quality gate on the curated star schema.

Runs structural and business assertions over data/curated/*, assembles the full
data-quality report (this file's checks + the cleaning fragments from stage 02) into
data/quality/dq_report.md, and exits non-zero if any HARD check fails.

HARD  = breaks the model or the numbers (nulls in keys, broken relationships,
        accounting identities that don't hold).
SOFT  = worth knowing, expected in messy data (unmatched PSP rows, snapshot variance).
"""

from __future__ import annotations

import datetime as dt
import sys

import numpy as np
import pandas as pd

import config as C
import utils as U

CUR = C.CURATED_DIR
results: list[dict] = []


def check(name: str, ok: bool, detail: str, hard: bool = True) -> None:
    results.append({"name": name, "ok": bool(ok), "detail": detail,
                    "level": "HARD" if hard else "SOFT"})
    tag = "PASS" if ok else ("FAIL" if hard else "WARN")
    U.log(f"  [{tag}] {name} — {detail}")


def L(name: str) -> pd.DataFrame:
    return pd.read_parquet(CUR / f"{name}.parquet")


def fk_ok(fact: pd.DataFrame, col: str, dim: pd.DataFrame, key: str) -> tuple[bool, int]:
    valid = set(dim[key].dropna().tolist())
    bad = fact.loc[~fact[col].isin(valid) & fact[col].notna(), col]
    return bad.empty, int(bad.nunique())


def main() -> int:
    U.section("VoltEdge Electronics — Stage 04: data-quality gate")

    dims = {n: L(n) for n in [
        "dim_date", "dim_market", "dim_currency", "dim_channel", "dim_product",
        "dim_customer", "dim_payment_method", "dim_carrier", "dim_warehouse", "dim_supplier"]}
    fol = L("fact_order_lines"); fo = L("fact_orders")
    fps = L("fact_payment_schedule"); fmk = L("fact_marketing_spend")
    fret = L("fact_returns"); fsnap = L("fact_inventory_snapshot")
    fpo = L("fact_purchase_orders"); fweb = L("fact_web_traffic_daily")

    # ---- 1. non-null surrogate keys -----------------------------------------
    for fact, name, keys in [
        (fol, "fact_order_lines", ["order_date_key", "product_key", "market_key", "currency_key"]),
        (fo, "fact_orders", ["order_date_key", "customer_key", "market_key", "payment_method_key"]),
        (fps, "fact_payment_schedule", ["order_date_key", "due_date_key", "market_key"]),
        (fmk, "fact_marketing_spend", ["date_key", "market_key", "channel_key"]),
    ]:
        nulls = int(fact[keys].isna().any(axis=1).sum())
        check(f"{name}: no null keys", nulls == 0, f"{nulls} rows with a null key")

    # ---- 2. referential integrity ----------------------------------------------
    ri = [
        ("fact_order_lines", fol, "product_key", "dim_product", "product_key"),
        ("fact_order_lines", fol, "market_key", "dim_market", "market_key"),
        ("fact_order_lines", fol, "currency_key", "dim_currency", "currency_key"),
        ("fact_order_lines", fol, "channel_key", "dim_channel", "channel_key"),
        ("fact_orders", fo, "customer_key", "dim_customer", "customer_key"),
        ("fact_orders", fo, "payment_method_key", "dim_payment_method", "payment_method_key"),
        ("fact_orders", fo, "carrier_key", "dim_carrier", "carrier_key"),
        ("fact_purchase_orders", fpo, "supplier_key", "dim_supplier", "supplier_key"),
        ("fact_purchase_orders", fpo, "product_key", "dim_product", "product_key"),
        ("fact_returns", fret, "product_key", "dim_product", "product_key"),
        ("fact_inventory_snapshot", fsnap, "product_key", "dim_product", "product_key"),
    ]
    for fname, fact, col, dname, dkey in ri:
        ok, nbad = fk_ok(fact, col, dims_all(dims, dname), dkey)
        check(f"RI {fname}.{col} -> {dname}", ok, f"{nbad} unresolved key values")

    # ---- 3. date coverage ----------------------------------------------------
    dd = dims["dim_date"]
    covered = set(dd["date_key"].tolist())
    for fact, name, col in [(fol, "fact_order_lines", "order_date_key"),
                            (fmk, "fact_marketing_spend", "date_key"),
                            (fweb, "fact_web_traffic_daily", "date_key")]:
        miss = int((~fact[col].isin(covered)).sum())
        check(f"{name}: dates within dim_date", miss == 0, f"{miss} rows outside dim_date")

    # ---- 4. accounting identities -----------------------------------------------
    d = (fol["gross_amount_local"] - fol["discount_amount_local"] - fol["net_amount_local"]).abs()
    check("fact_order_lines: net = gross - discount", (d > 0.05).sum() == 0,
          f"{int((d > 0.05).sum())} lines break the identity")

    # rows moved to rejects (injected negative-qty lines) legitimately drop out of the
    # curated fact, so their orders will not tie to the header — exclude them.
    rej_path = C.STAGING_DIR / "stg_order_line_rejects.parquet"
    rej_orders = set(pd.read_parquet(rej_path)["order_id"]) if rej_path.exists() else set()
    g = fol.groupby("order_id")["net_amount_local"].sum()
    o = fo.set_index("order_id")["net_amount_local"]
    j = g.to_frame("lines").join(o.rename("header"), how="inner")
    j = j[~j.index.isin(rej_orders)]
    diff = (j["lines"] - j["header"]).abs()
    check("order lines roll up to order header (net local)", (diff > 0.5).mean() < 0.001,
          f"{int((diff > 0.5).sum())} of {len(j):,} clean orders differ > 0.5 "
          f"({len(rej_orders):,} reject-touched orders excluded)")

    gp_neg = (fol.loc[fol["line_type"] == "product", "gross_profit_usd"] < 0).mean()
    check("product lines sold below moving-avg cost (loss leaders + cost drift)",
          gp_neg < 0.08,
          f"{gp_neg*100:.1f}% of product lines have negative gross profit (expected < 8%)",
          hard=False)

    # ---- 5. comparable base -------------------------------------------------
    cb = dims["dim_market"].loc[dims["dim_market"]["is_comparable_base"], "market_id"].tolist()
    check("comparable base = US only", cb == ["US"], f"comparable-base markets: {cb}")

    # ---- 6. FX -----------------------------------------------------------------
    fx = L("fact_exchange_rate")
    usd_bad = (fx.loc[fx["currency_code"] == "USD", "rate_to_usd"] != 1.0).sum()
    check("FX: USD rate is exactly 1.0", usd_bad == 0, f"{int(usd_bad)} USD rows != 1.0")
    check("FX: no non-positive rates", (fx["rate_to_usd"] <= 0).sum() == 0,
          f"{int((fx['rate_to_usd'] <= 0).sum())} rows")

    # ---- 7. volumes are in a sane band ---------------------------------------
    n_orders = fo.loc[fo["order_status"] != "cancelled", "order_id"].nunique()
    check("order count in 110k–200k", 110_000 <= n_orders <= 200_000, f"{n_orders:,} orders", hard=False)
    aov = (fol.loc[fol["order_status"] != "cancelled", "net_amount_usd"].sum() / n_orders)
    check("AOV in $120–$320", 120 <= aov <= 320, f"AOV = ${aov:,.0f}", hard=False)
    gm = fol["gross_profit_usd"].sum() / fol["net_amount_usd"].sum()
    check("blended gross margin 12–24%", 0.12 <= gm <= 0.24, f"GM = {gm*100:.1f}%", hard=False)

    # ---- 8. payment schedule integrity ------------------------------------------
    ps_sum = fps.groupby("order_id")["gross_amount_usd"].sum()
    on = fo.assign(tot=lambda x: x["net_amount_usd"] + x["tax_amount_usd"] + x["shipping_fee_usd"])
    on = on.loc[on["order_status"] != "cancelled"].set_index("order_id")["tot"]
    jj = ps_sum.to_frame("sched").join(on.rename("order"), how="inner")
    rel = ((jj["sched"] - jj["order"]).abs() / jj["order"].clip(lower=1))
    check("payment schedule sums to order total", (rel > 0.02).mean() < 0.005,
          f"{int((rel > 0.02).sum())} orders differ > 2%")

    # ---- assemble report -------------------------------------------------------
    res = pd.DataFrame(results)
    hard_fail = res[(~res["ok"]) & (res["level"] == "HARD")]
    frag_dir = C.QUALITY_DIR / "_fragments"
    frags = "\n\n".join(sorted(
        (p.read_text(encoding="utf-8") for p in frag_dir.glob("*.md")), reverse=True)
    ) if frag_dir.exists() else "_none_"

    lines = [
        "# VoltEdge Electronics — Data-Quality Report", "",
        f"_generated {dt.datetime.now():%Y-%m-%d %H:%M}_  ·  seed `{C.SEED}`", "",
        "## Curated-layer gate", "",
        f"- checks run: **{len(res)}**  ·  passed: **{int(res['ok'].sum())}**  "
        f"·  hard failures: **{len(hard_fail)}**  ·  soft warnings: "
        f"**{int(((~res['ok']) & (res['level'] == 'SOFT')).sum())}**", "",
        "| level | check | result | detail |",
        "|---|---|---|---|",
        *[f"| {r.level} | {r.name} | {'✅' if r.ok else ('❌' if r.level=='HARD' else '⚠️')} | {r.detail} |"
          for r in res.itertuples(index=False)],
        "", frags, "",
    ]
    out = C.QUALITY_DIR / "dq_report.md"
    out.write_text("\n".join(lines), encoding="utf-8")
    U.log(f"wrote {out.relative_to(C.PROJECT_DIR)}")

    if len(hard_fail):
        U.log(f"HARD FAILURES: {len(hard_fail)}")
        return 1
    U.section("Stage 04 complete — no hard failures")
    return 0


def dims_all(dims: dict, name: str) -> pd.DataFrame:
    return dims[name]


if __name__ == "__main__":
    sys.exit(main())
