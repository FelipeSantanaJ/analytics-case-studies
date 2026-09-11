"""Finding 02 - Is VoltEdge growing, or just opening markets?

Decompose headline Net Revenue growth CY vs PY into:
  * Comparable Base  (US only - live for the whole CY+PY span)   -> organic / like-for-like
  * Expansion        (UK + DE + BR)                              -> new-market contribution
and compare actuals to plan (fact_target, metric = 'Net Revenue').

CY = 2025-07-01..2026-06-30   PY = 2024-07-01..2025-06-30   (docs/01 section 1)
Net Revenue (USD) = SUM(net_amount_usd) - SUM(refund_amount_usd), order_status <> 'cancelled'.

Both tracks: pandas + DuckDB over data/curated/*.parquet. Parity asserted at the end.
"""
from __future__ import annotations

import sys
import pathlib

import numpy as np
import pandas as pd
from scipy import stats

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from utils import assert_close, duck, load_sql, t  # noqa: E402

CY_START, CY_END = 20250701, 20260630
PY_START, PY_END = 20240701, 20250630

# --------------------------------------------------------------------------- #
# Python track
# --------------------------------------------------------------------------- #
ol = t("fact_order_lines")
ol = ol[ol["order_status"] != "cancelled"].copy()
ol["nr"] = ol["net_amount_usd"] - ol["refund_amount_usd"]
mkt = t("dim_market")[["market_key", "market_id", "market_name", "is_comparable_base"]]
ol = ol.merge(mkt, on="market_key", how="left")

ol["period"] = pd.NA
ol.loc[ol["order_date_key"].between(PY_START, PY_END), "period"] = "PY"
ol.loc[ol["order_date_key"].between(CY_START, CY_END), "period"] = "CY"

piv = ol.pivot_table(index="market_name", columns="period", values="nr", aggfunc="sum").fillna(0.0)
piv = piv[["PY", "CY"]]
piv["yoy_abs"] = piv["CY"] - piv["PY"]
piv["yoy_pct"] = piv["yoy_abs"] / piv["PY"].where(piv["PY"] != 0)

total_cy, total_py = piv["CY"].sum(), piv["PY"].sum()
comp_cy = ol.loc[ol["is_comparable_base"] & (ol["period"] == "CY"), "nr"].sum()
comp_py = ol.loc[ol["is_comparable_base"] & (ol["period"] == "PY"), "nr"].sum()
exp_cy, exp_py = total_cy - comp_cy, total_py - comp_py

py_summary = {
    "total_cy": total_cy,
    "total_py": total_py,
    "total_yoy_pct": total_cy / total_py - 1,
    "comp_cy": comp_cy,
    "comp_py": comp_py,
    "comp_yoy_pct": comp_cy / comp_py - 1,
    "expansion_cy": exp_cy,
    "expansion_contribution_pct": exp_cy / total_cy,
}

# vs plan (CY only - every market has 12 CY months of plan)
tgt = t("fact_target")
tgt = tgt[tgt["metric"] == "Net Revenue"].merge(mkt, on="market_key", how="left")
tgt_cy = tgt[tgt["month_date_key"].between(CY_START, CY_END)]
plan_by_mkt = tgt_cy.groupby("market_name")["target_value"].sum()
actual_cy_by_mkt = piv["CY"]
vs_plan = pd.DataFrame({"actual_cy": actual_cy_by_mkt, "plan_cy": plan_by_mkt})
vs_plan["attain_pct"] = vs_plan["actual_cy"] / vs_plan["plan_cy"] - 1
py_summary["plan_cy_total"] = plan_by_mkt.sum()
py_summary["attain_total_pct"] = actual_cy_by_mkt.sum() / plan_by_mkt.sum() - 1

# US actual vs plan, by CY month -- is the -2.4% annual gap a consistent monthly
# shortfall, or a couple of bad months dragging an otherwise-on-plan year?
dd_m = t("dim_date")[["date_key", "month_year"]]
us_key = mkt.loc[mkt["market_id"] == "US", "market_key"].iloc[0]

us_ol = ol[(ol["market_key"] == us_key) & (ol["period"] == "CY")]
us_actual_m = us_ol.merge(dd_m, left_on="order_date_key", right_on="date_key") \
    .groupby("month_year")["nr"].sum().rename("actual")

tgt_us = tgt[(tgt["market_key"] == us_key) & (tgt["month_date_key"].between(CY_START, CY_END))]
us_plan_m = tgt_us.merge(dd_m, left_on="month_date_key", right_on="date_key") \
    .groupby("month_year")["target_value"].sum().rename("plan")

us_monthly = pd.concat([us_actual_m, us_plan_m], axis=1).sort_index()
us_monthly["attain_pct"] = us_monthly["actual"] / us_monthly["plan"] - 1

# --------------------------------------------------------------------------- #
# SQL track (DuckDB)
# --------------------------------------------------------------------------- #
con = duck()
Q = load_sql("02_growth_decomposition")
sql_piv = con.execute(Q["piv"]).df().set_index("market_name").fillna(0.0)
sql_comp = con.execute(Q["comp"]).df().iloc[0]
sql_plan_total = con.execute(Q["plan_total"]).fetchone()[0]
sql_us_monthly = con.execute(Q["us_monthly"]).df().set_index("month_year").sort_index()

# --------------------------------------------------------------------------- #
# Parity
# --------------------------------------------------------------------------- #
print("=== Finding 02 - growth decomposition: parity ===")
for name in piv.index:
    assert_close(piv.loc[name, "PY"], float(sql_piv.loc[name, "py"]), label=f"PY NR - {name}")
    assert_close(piv.loc[name, "CY"], float(sql_piv.loc[name, "cy"]), label=f"CY NR - {name}")
assert_close(comp_cy, float(sql_comp["comp_cy"]), label="Comparable-base CY")
assert_close(comp_py, float(sql_comp["comp_py"]), label="Comparable-base PY")
assert_close(total_cy, float(sql_comp["total_cy"]), label="Total CY")
assert_close(total_py, float(sql_comp["total_py"]), label="Total PY")
assert_close(py_summary["plan_cy_total"], float(sql_plan_total), label="Plan CY total")
assert len(us_monthly) == 12 and len(sql_us_monthly) == 12, "expected 12 US CY months"
for m in us_monthly.index:
    assert_close(us_monthly.loc[m, "actual"], float(sql_us_monthly.loc[m, "actual"]), label=f"US actual {m}")
    assert_close(us_monthly.loc[m, "plan"], float(sql_us_monthly.loc[m, "plan"]), label=f"US plan {m}")

# --------------------------------------------------------------------------- #
# Report
# --------------------------------------------------------------------------- #
pd.set_option("display.float_format", lambda x: f"{x:,.2f}")
print("\n--- Net Revenue by market: PY vs CY ---")
print(piv)
print("\n--- Decomposition of the headline YoY ---")
print(f"Total     PY {total_py:,.0f}  ->  CY {total_cy:,.0f}   ({py_summary['total_yoy_pct']:+.1%})")
print(f"Comparable PY {comp_py:,.0f}  ->  CY {comp_cy:,.0f}   ({py_summary['comp_yoy_pct']:+.1%})  = US like-for-like")
print(f"Expansion  PY {exp_py:,.0f}  ->  CY {exp_cy:,.0f}   (UK+DE+BR)")
print(f"Expansion contribution to CY Net Revenue: {py_summary['expansion_contribution_pct']:.1%}")
growth_from_expansion = (exp_cy - exp_py) / (total_cy - total_py)
print(f"Share of the +${total_cy - total_py:,.0f} YoY gain that is expansion: {growth_from_expansion:.1%}")
print("\n--- Actual CY vs plan ---")
print(vs_plan)
print(f"\nTotal CY actual {actual_cy_by_mkt.sum():,.0f}  vs plan {plan_by_mkt.sum():,.0f}"
      f"  ({py_summary['attain_total_pct']:+.1%})")

# ---------- is the US -2.4% vs plan a consistent shortfall, or a couple of bad months? ----------
print("\n--- US vs plan, by month ---")
print(us_monthly)
t_stat, p_value = stats.ttest_1samp(us_monthly["attain_pct"], popmean=0.0)
rng = np.random.default_rng(42)
N_BOOT = 10_000
boot_mean = np.array([rng.choice(us_monthly["attain_pct"], size=12, replace=True).mean()
                       for _ in range(N_BOOT)])
attain_ci_lo, attain_ci_hi = np.percentile(boot_mean, [2.5, 97.5])
months_under = int((us_monthly["attain_pct"] < 0).sum())
print(f"\nMean monthly attainment: {us_monthly['attain_pct'].mean():+.1%}   "
      f"one-sample t = {t_stat:.2f}  p = {p_value:.3f}")
print(f"95% CI (bootstrap, {N_BOOT:,} resamples, seed=42): "
      f"[{attain_ci_lo:+.1%}, {attain_ci_hi:+.1%}]")
print(f"Months under plan: {months_under}/12")
print("  -> the annual -2.4% gap is a real, computed number either way; this asks whether "
      "the monthly pattern behind it reads as a consistent miss or noisy scatter around zero.")

# save backing tables
out = pathlib.Path(__file__).resolve().parents[1] / "outputs" / "tables"
piv.to_csv(out / "02_net_revenue_market_py_cy.csv")
vs_plan.to_csv(out / "02_net_revenue_vs_plan_cy.csv")
us_monthly.to_csv(out / "02_us_vs_plan_monthly.csv")
print(f"\nBacking tables -> {out}")
print("\nALL PARITY CHECKS PASSED")
