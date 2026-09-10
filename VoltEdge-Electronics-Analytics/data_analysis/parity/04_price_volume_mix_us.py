"""Finding 04 - Price / Volume / Mix decomposition of the US like-for-like growth.

Follows docs/06 section 07 exactly:
  Units Sold        = SUM(quantity)  where order_status<>'cancelled' AND line_type='product'
  Gross Revenue     = SUM(gross_amount_usd) where order_status<>'cancelled'
  Avg Selling Price = Gross Revenue / Units Sold
  PVM Price  Effect = SUMX(category, (ASP_CY - ASP_PY) * UnitsPY_category)
  PVM Volume Effect = GrossRevPY_total * (Units_CY_total - Units_PY_total) / Units_PY_total
  PVM Mix    Effect = (GrossRev_CY - GrossRev_PY) - Price - Volume
Scope: dim_market.is_comparable_base = TRUE  (United States).
CY = 2025-07..2026-06, PY = 2024-07..2025-06 by order_date_key.
Both tracks (pandas + DuckDB); parity asserted.
"""
from __future__ import annotations

import sys
import pathlib

import pandas as pd

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from utils import assert_close, duck, load_sql, t  # noqa: E402

CY = (20250701, 20260630)
PY = (20240701, 20250630)

# --------------------------------------------------------------------------- #
# Python track
# --------------------------------------------------------------------------- #
ol = t("fact_order_lines")
mk = t("dim_market")[["market_key", "is_comparable_base"]]
pr = t("dim_product")[["product_key", "category"]]
ol = ol.merge(mk, on="market_key").merge(pr, on="product_key")
ol = ol[(ol["order_status"] != "cancelled") & ol["is_comparable_base"]]


def period(df, lo, hi):
    return df[df["order_date_key"].between(lo, hi)]


cy_l, py_l = period(ol, *CY), period(ol, *PY)


def by_cat(df):
    g = df.groupby("category").apply(
        lambda x: pd.Series({
            "gross": x["gross_amount_usd"].sum(),
            "units": x.loc[x["line_type"] == "product", "quantity"].sum(),
        }), include_groups=False,
    )
    g["asp"] = g["gross"] / g["units"]
    return g


cy_c, py_c = by_cat(cy_l), by_cat(py_l)
cats = sorted(set(cy_c.index) | set(py_c.index))
cy_c = cy_c.reindex(cats).fillna(0.0)
py_c = py_c.reindex(cats).fillna(0.0)

gross_cy, gross_py = cy_c["gross"].sum(), py_c["gross"].sum()
units_cy, units_py = cy_c["units"].sum(), py_c["units"].sum()

price_effect = ((cy_c["asp"].replace([float("inf")], 0) - py_c["asp"].replace([float("inf")], 0)) * py_c["units"]).sum()
volume_effect = gross_py * (units_cy - units_py) / units_py
mix_effect = (gross_cy - gross_py) - price_effect - volume_effect

py_res = {
    "gross_cy": gross_cy, "gross_py": gross_py, "delta": gross_cy - gross_py,
    "units_cy": units_cy, "units_py": units_py,
    "price_effect": price_effect, "volume_effect": volume_effect, "mix_effect": mix_effect,
}

# --------------------------------------------------------------------------- #
# SQL track
# --------------------------------------------------------------------------- #
con = duck()
Q = load_sql("04_price_volume_mix_us")
con.execute(Q["base_view"])


def cat_sql(lo, hi):
    return con.execute(Q["by_cat"], {"lo": lo, "hi": hi}).df().set_index("category")


s_cy, s_py = cat_sql(*CY), cat_sql(*PY)
s_cy = s_cy.reindex(cats).fillna(0.0)
s_py = s_py.reindex(cats).fillna(0.0)
s_cy["asp"] = (s_cy["gross"] / s_cy["units"]).replace([float("inf")], 0).fillna(0)
s_py["asp"] = (s_py["gross"] / s_py["units"]).replace([float("inf")], 0).fillna(0)
s_gross_cy, s_gross_py = s_cy["gross"].sum(), s_py["gross"].sum()
s_units_cy, s_units_py = s_cy["units"].sum(), s_py["units"].sum()
s_price = ((s_cy["asp"] - s_py["asp"]) * s_py["units"]).sum()
s_volume = s_gross_py * (s_units_cy - s_units_py) / s_units_py
s_mix = (s_gross_cy - s_gross_py) - s_price - s_volume

# --------------------------------------------------------------------------- #
# Parity + report
# --------------------------------------------------------------------------- #
print("=== Finding 04 - PVM (US like-for-like): parity ===")
assert_close(gross_cy, s_gross_cy, label="Gross Revenue CY (US)")
assert_close(gross_py, s_gross_py, label="Gross Revenue PY (US)")
assert_close(units_cy, s_units_cy, abs_=0, label="Units CY (US)")
assert_close(units_py, s_units_py, abs_=0, label="Units PY (US)")
assert_close(price_effect, s_price, label="PVM Price Effect")
assert_close(volume_effect, s_volume, label="PVM Volume Effect")
assert_close(mix_effect, s_mix, label="PVM Mix Effect")

print(f"\nUS Gross Revenue: PY ${gross_py:,.0f}  ->  CY ${gross_cy:,.0f}   (Δ +${gross_cy-gross_py:,.0f}, {gross_cy/gross_py-1:+.1%})")
print(f"US Units (product): PY {units_py:,.0f}  ->  CY {units_cy:,.0f}   ({units_cy/units_py-1:+.1%})")
print("\nDecomposition of the +${:,.0f} gross-revenue gain:".format(gross_cy - gross_py))
print(f"  Price effect  (higher ASP within category) : {price_effect:>+14,.0f}   ({price_effect/(gross_cy-gross_py):+.0%})")
print(f"  Volume effect (more units, PY mix)          : {volume_effect:>+14,.0f}   ({volume_effect/(gross_cy-gross_py):+.0%})")
print(f"  Mix effect    (shift between categories)    : {mix_effect:>+14,.0f}   ({mix_effect/(gross_cy-gross_py):+.0%})")

detail = pd.DataFrame({
    "gross_py": py_c["gross"], "gross_cy": cy_c["gross"],
    "units_py": py_c["units"], "units_cy": cy_c["units"],
    "asp_py": py_c["asp"], "asp_cy": cy_c["asp"],
})
detail["price_eff"] = (cy_c["asp"].replace([float("inf")], 0) - py_c["asp"].replace([float("inf")], 0)) * py_c["units"]
detail["gross_share_py"] = py_c["gross"] / gross_py
detail["gross_share_cy"] = cy_c["gross"] / gross_cy
detail["share_delta_pp"] = (detail["gross_share_cy"] - detail["gross_share_py"]) * 100
pd.set_option("display.float_format", lambda x: f"{x:,.1f}")
print("\nBy category:")
print(detail.sort_values("gross_cy", ascending=False)[
    ["gross_py", "gross_cy", "asp_py", "asp_cy", "price_eff", "share_delta_pp"]])

out = pathlib.Path(__file__).resolve().parents[1] / "outputs" / "tables"
detail.to_csv(out / "04_pvm_us_by_category.csv")
pd.Series(py_res).to_csv(out / "04_pvm_us_summary.csv")
print(f"\nBacking tables -> {out}\nALL PARITY CHECKS PASSED")
