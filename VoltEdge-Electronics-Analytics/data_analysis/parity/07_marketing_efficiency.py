"""Finding 07 - Marketing efficiency: what moved contribution margin, and is it durable?

docs/06 section 08:
  Marketing Spend (USD) = SUM(fact_marketing_spend.cost_usd)
  New Customers         = customers whose FIRST-EVER non-cancelled order falls in the period
  Blended CAC (USD)     = Marketing Spend / New Customers
  MER / ROAS            = Net Revenue / Marketing Spend
  New Customer Revenue  = Net Revenue from customers whose first order is in the period
Cuts: full/CY/PY, by channel group (Paid/Owned/Earned), CAC vs fact_target, monthly trend.
Both tracks; parity asserted.
"""
from __future__ import annotations

import sys
import pathlib

import numpy as np
import pandas as pd
import statsmodels.formula.api as smf
from scipy import stats

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from utils import assert_close, duck, load_sql, t  # noqa: E402

CY = (20250701, 20260630)
PY = (20240701, 20250630)

# ---------------- Python ----------------
fo = t("fact_orders")
fo_nc = fo[~fo["is_cancelled"]].copy()
first_order = fo_nc.groupby("customer_key")["order_date_key"].min().rename("first_key")

ol = t("fact_order_lines")
ol_nc = ol[ol["order_status"] != "cancelled"].copy()
ol_nc["nr"] = ol_nc["net_amount_usd"] - ol_nc["refund_amount_usd"]
ol_nc = ol_nc.merge(first_order, on="customer_key", how="left")

ms = t("fact_marketing_spend")
ch = t("dim_channel")[["channel_key", "channel_name", "channel_group", "is_paid"]]
ms = ms.merge(ch, on="channel_key", how="left")


def block(lo, hi, label):
    spend = ms.loc[ms["date_key"].between(lo, hi), "cost_usd"].sum()
    new_cust_keys = first_order[(first_order >= lo) & (first_order <= hi)].index
    orders_in = fo_nc[fo_nc["order_date_key"].between(lo, hi)]
    new_customers = orders_in.loc[orders_in["customer_key"].isin(new_cust_keys), "customer_key"].nunique()
    nr_period = ol_nc.loc[ol_nc["order_date_key"].between(lo, hi), "nr"].sum()
    nr_new = ol_nc.loc[ol_nc["order_date_key"].between(lo, hi)
                       & ol_nc["first_key"].between(lo, hi), "nr"].sum()
    imp = ms.loc[ms["date_key"].between(lo, hi), "impressions"].sum()
    clk = ms.loc[ms["date_key"].between(lo, hi), "clicks"].sum()
    return dict(
        label=label, spend=spend, new_customers=new_customers,
        blended_cac=spend / new_customers, net_revenue=nr_period, mer=nr_period / spend,
        new_rev=nr_new, new_rev_pct=nr_new / nr_period,
        cpc=spend / clk, ctr=clk / imp,
    )


full = block(1, 99999999, "full")
cy = block(*CY, "CY")
py = block(*PY, "PY")

# spend by channel group, CY vs PY  (share shift = the F03 driver)
def spend_grp(lo, hi):
    return ms.loc[ms["date_key"].between(lo, hi)].groupby("channel_group")["cost_usd"].sum()


grp = pd.DataFrame({"PY": spend_grp(*PY), "CY": spend_grp(*CY)}).fillna(0.0)
grp["PY_share"] = grp["PY"] / grp["PY"].sum()
grp["CY_share"] = grp["CY"] / grp["CY"].sum()

# new customers by paid/non-paid acquisition channel and by market (CY)
dc = t("dim_customer")[["customer_key", "acquisition_channel", "market_id"]]
paid_ch = {"Paid Search", "Paid Social", "Display", "Affiliate"}
new_cy_keys = first_order[(first_order >= CY[0]) & (first_order <= CY[1])].index
new_cy = dc[dc["customer_key"].isin(new_cy_keys)].copy()
new_cy["is_paid_acq"] = new_cy["acquisition_channel"].isin(paid_ch)
acq_split = new_cy["is_paid_acq"].value_counts()
pct_new_paid = acq_split.get(True, 0) / acq_split.sum()
new_by_market = new_cy.groupby("market_id").size()
paid_spend_cy = ms.loc[ms["date_key"].between(*CY) & ms["is_paid"], "cost_usd"].sum()
cac_paid_cy = paid_spend_cy / acq_split.get(True, 1)

# monthly panel: spend + new customers, one row per month in the 24-month extract window
# (PY = Jul24-Jun25, CY = Jul25-Jun26 -- NOT dim_date.yoy_period, which is flagged for a
# calendar that runs past the extract window and would double-count calendar months below).
dd_m = t("dim_date")[["date_key", "month", "month_year"]]
in_window = dd_m["date_key"].between(PY[0], CY[1])
dd_m = dd_m[in_window].copy()
dd_m["yoy_period"] = np.where(dd_m["date_key"] <= PY[1], "PY", "CY")

ms_m = ms.merge(dd_m, on="date_key", how="left")
spend_month = ms_m[ms_m["yoy_period"].notna()].groupby("month_year")["cost_usd"].sum()

fo_first = first_order.reset_index().merge(
    dd_m, left_on="first_key", right_on="date_key", how="left")
newc_month = fo_first[fo_first["yoy_period"].notna()].groupby("month_year").size()

months = dd_m[["month_year", "month", "yoy_period"]].drop_duplicates()
panel = months.merge(spend_month.rename("spend"), on="month_year", how="left") \
              .merge(newc_month.rename("new_customers"), on="month_year", how="left") \
              .fillna({"spend": 0.0, "new_customers": 0}).sort_values("month_year").reset_index(drop=True)
panel["cac"] = panel["spend"] / panel["new_customers"]

# CAC vs target
tgt = t("fact_target")
cac_tgt = tgt[tgt["metric"] == "Blended CAC"]
cac_tgt_cy = cac_tgt.loc[cac_tgt["month_date_key"].between(*CY), "target_value"].mean()

# marketing as % of net revenue
mktg_pct_cy = cy["spend"] / cy["net_revenue"]
mktg_pct_py = py["spend"] / py["net_revenue"]

# CY contribution-margin sensitivity to blended CAC (CM base from Finding 03 = +$325,498)
CM_CY_ACTUAL = 325_498
cm_if_py_cac = CM_CY_ACTUAL - (py["blended_cac"] * cy["new_customers"] - cy["spend"])
cm_if_tgt_cac = CM_CY_ACTUAL - (cac_tgt_cy * cy["new_customers"] - cy["spend"])

# ---------------- SQL ----------------
con = duck()
Q = load_sql("07_marketing_efficiency")
con.execute(Q["first_order_view"])


def sql_block(lo, hi):
    p = {"lo": lo, "hi": hi}
    spend = con.execute(Q["spend"], p).fetchone()[0]
    newc = con.execute(Q["new_customers"], p).fetchone()[0]
    nr = con.execute(Q["net_revenue"], p).fetchone()[0]
    nr_new = con.execute(Q["new_revenue"], p).fetchone()[0]
    return spend, newc, nr, nr_new


for lbl, b in [("CY", cy), ("PY", py), ("full", full)]:
    lo, hi = {"CY": CY, "PY": PY, "full": (1, 99999999)}[lbl]
    s_spend, s_newc, s_nr, s_nrnew = sql_block(lo, hi)
    assert_close(b["spend"], s_spend, label=f"{lbl} Marketing Spend")
    assert_close(b["new_customers"], s_newc, abs_=0, label=f"{lbl} New Customers")
    assert_close(b["net_revenue"], s_nr, label=f"{lbl} Net Revenue")
    assert_close(b["new_rev"], s_nrnew, label=f"{lbl} New Customer Revenue")

s_panel = con.execute(Q["monthly_panel"], {"py_lo": PY[0], "py_hi": PY[1], "cy_hi": CY[1]}) \
    .df().sort_values("month_year").reset_index(drop=True)
for col in ("spend", "new_customers"):
    assert_close(panel[col].sum(), s_panel[col].sum(), abs_=0.01, label=f"monthly panel {col} total")
for (_, p_row), (_, s_row) in zip(panel.iterrows(), s_panel.iterrows()):
    assert p_row["month_year"] == s_row["month_year"], "monthly panel month mismatch"
    assert_close(p_row["spend"], s_row["spend"], label=f"{p_row['month_year']} spend")
    assert_close(p_row["new_customers"], s_row["new_customers"], abs_=0, label=f"{p_row['month_year']} new customers")

# ---------------- report ----------------
print("=== Finding 07 - marketing efficiency ===")
for b in (py, cy, full):
    print(f"\n[{b['label']}]  spend ${b['spend']:,.0f} | new customers {b['new_customers']:,} | "
          f"blended CAC ${b['blended_cac']:,.2f} | MER {b['mer']:.1f}x")
    print(f"          new-customer revenue ${b['new_rev']:,.0f} ({b['new_rev_pct']:.0%} of NR) | "
          f"CPC ${b['cpc']:.2f} | CTR {b['ctr']:.2%}")
print(f"\nBlended CAC:  PY ${py['blended_cac']:,.2f}  ->  CY ${cy['blended_cac']:,.2f}   "
      f"(target CY ${cac_tgt_cy:,.2f}, {cy['blended_cac']/cac_tgt_cy-1:+.0%})")
print(f"Marketing as % of Net Revenue:  PY {mktg_pct_py:.1%}  ->  CY {mktg_pct_cy:.1%}")
print(f"\nCY new customers: {len(new_cy):,} | via paid acq channel {pct_new_paid:.0%} | "
      f"CAC (paid only) ${cac_paid_cy:,.2f}")
print("CY new customers by market:")
print(new_by_market.to_string())
print(f"\nCY contribution margin sensitivity to blended CAC (base +${CM_CY_ACTUAL:,}):")
print(f"  at actual CAC ${cy['blended_cac']:.2f}  -> +${CM_CY_ACTUAL:,.0f}")
print(f"  at PY CAC     ${py['blended_cac']:.2f}  -> ${cm_if_py_cac:+,.0f}")
print(f"  at target CAC ${cac_tgt_cy:.2f}  -> ${cm_if_tgt_cac:+,.0f}")
pd.set_option("display.float_format", lambda x: f"{x:,.3f}")
print("\nSpend by channel group (PY -> CY):")
print(grp)

# ---------- is the CAC drop real, or 12 noisy months? ----------
# Paired by calendar month (Jul PY vs Jul CY, ... Jun PY vs Jun CY) so any month-of-year
# seasonality in acquisition cost cancels out in the pairing itself.
wide = panel.pivot(index="month", columns="yoy_period", values="cac").dropna()
assert len(wide) == 12, f"expected 12 paired months, got {len(wide)}"
paired_diff = wide["CY"] - wide["PY"]  # negative = CAC improved

t_stat, p_value = stats.ttest_rel(wide["CY"], wide["PY"])
rng = np.random.default_rng(42)
N_BOOT = 10_000
boot_mean = np.array([rng.choice(paired_diff, size=12, replace=True).mean() for _ in range(N_BOOT)])
diff_ci_lo, diff_ci_hi = np.percentile(boot_mean, [2.5, 97.5])

print("\n--- is the blended-CAC drop real, or 12 noisy months? ---")
print(f"Paired months (n=12): mean CAC change ${paired_diff.mean():+,.2f}   "
      f"paired t = {t_stat:.2f}  p = {p_value:.3f}")
print(f"95% CI (bootstrap, {N_BOOT:,} resamples, seed=42): "
      f"[${diff_ci_lo:+,.2f}, ${diff_ci_hi:+,.2f}]")
print("  -> paired on calendar month, so seasonal swings in acquisition cost (e.g. cheaper "
      "CAC around Black Friday every year) net out of the comparison.")

# Spend -> new-customers elasticity (log-log OLS, all 24 months). Observational, not
# causal: spend and organic pull both move with the same demand calendar (Finding 05),
# so this is "how tightly do they move together," not "what happens if we spend +1%."
panel_pos = panel[(panel["spend"] > 0) & (panel["new_customers"] > 0)].copy()
panel_pos["log_spend"] = np.log(panel_pos["spend"])
panel_pos["log_newc"] = np.log(panel_pos["new_customers"])
elm = smf.ols("log_newc ~ log_spend", data=panel_pos).fit(cov_type="HC3")
elas = elm.params["log_spend"]
elas_lo, elas_hi = elm.conf_int().loc["log_spend"]
elas_p = elm.pvalues["log_spend"]
print(f"\nSpend -> new-customers elasticity (log-log, n={len(panel_pos)} months): "
      f"{elas:.2f}  [95% CI: {elas_lo:.2f}, {elas_hi:.2f}]  p={elas_p:.3f}")
print(f"  -> a 1% change in monthly spend associates with a {elas:.2f}% change in new "
      "customers that same month (observational; spend and organic demand share a "
      "seasonal calendar, so this is not a causal 'raise spend by X' estimate).")

sig_out = pd.DataFrame([{
    "paired_mean_cac_change": paired_diff.mean(), "paired_t": t_stat, "paired_p": p_value,
    "bootstrap_ci_lo": diff_ci_lo, "bootstrap_ci_hi": diff_ci_hi,
    "elasticity_log_spend": elas, "elasticity_ci_lo": elas_lo, "elasticity_ci_hi": elas_hi,
    "elasticity_p": elas_p,
}])

out = pathlib.Path(__file__).resolve().parents[1] / "outputs" / "tables"
grp.to_csv(out / "07_spend_by_channel_group.csv")
pd.DataFrame([py, cy, full]).to_csv(out / "07_marketing_blocks.csv", index=False)
panel.to_csv(out / "07_monthly_panel.csv", index=False)
sig_out.to_csv(out / "07_cac_significance.csv", index=False)
print(f"\nBacking tables -> {out}\nALL PARITY CHECKS PASSED")
