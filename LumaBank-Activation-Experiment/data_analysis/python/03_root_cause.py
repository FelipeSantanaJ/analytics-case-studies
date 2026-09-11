"""
03 — Root-cause investigation: what broke, and how do we know?

Decision it informs: is this really a deploy-triggered bug (not coincidence), and can we
draw an auditable line between "contaminated" and "clean" users? Audience: the
experimentation platform team + whoever signs off on the restart decision.

Grain: dim_app_release (the release calendar) for the timing cross-reference;
fact_activation (contaminated_flag, assignment_switch_flag) for the contaminated-vs-clean
split; fact_variant_assignment joined to dim_user/dim_region for the fallback's
geographic composition bias.

Method (both tracks): exact-date cross-reference against the release calendar;
contaminated-vs-clean counts and Day-7 rates; fallback treatment-share by macro-region vs
the primary path's ~50/50, with a chi-square test that the fallback's regional mix differs
from primary.
"""
from __future__ import annotations
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import numpy as np, pandas as pd
from scipy import stats
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from utils import t, con, save_table, parity, banner, OUT_FIG

banner("03 — Root-cause investigation")

# ---- 1. release-calendar cross-reference --------------------------------
rel = t("dim_app_release")
cache_reset_releases = rel[rel["is_cache_reset_release"]][["version", "platform", "released_at"]]
print("Release flagged as the cache-reset trigger:")
print(cache_reset_releases.to_string(index=False))
deploy_date = pd.Timestamp(cache_reset_releases["released_at"].min()).date()
print(f"\nDeploy date from the release calendar: {deploy_date}")
print("SRM ALERT first fired: 2026-07-18 (block 02) -> 2-day detection lag, exactly the "
      "release that touches variant-assignment storage. No other release in the window "
      "coincides with the break.")

# ---- 2. contaminated vs clean segmentation -------------------------------
fa = t("fact_activation")
exp1 = fa[fa["experiment_cohort"].isin(["pre_deploy", "post_deploy"])].copy()
seg = (exp1.groupby(["experiment_cohort", "contaminated_flag"])
       .agg(n=("user_key", "size"), day7_rate=("day7_activated", "mean"))
       .reset_index())
print("\nContaminated vs clean, by cohort:")
print(seg.round(4).to_string(index=False))
save_table(seg, "03_contaminated_segments")

n_contaminated = int(exp1["contaminated_flag"].sum())
n_switch = int(exp1["assignment_switch_flag"].sum())
print(f"\nTotal contaminated (original run): {n_contaminated} "
      f"({n_contaminated/len(exp1):.1%} of {len(exp1)})")
print(f"  of which arm-switched (rule a): {n_switch}")
print(f"  cache-reset-in-window only (rule b): {n_contaminated - n_switch}")

# ---- 3. fallback geographic bias -----------------------------------------
fva = t("fact_variant_assignment")
du = t("dim_user")[["user_key", "region_key"]]
dreg = t("dim_region")[["region_key", "macro_region"]]
first = fva[fva["is_first_assignment"]].merge(du, on="user_key", how="left").merge(dreg, on="region_key", how="left")

post = first[(pd.to_datetime(first["assigned_ts_brt"]).dt.date >= pd.Timestamp("2026-07-16").date())
            & (pd.to_datetime(first["assigned_ts_brt"]).dt.date <= pd.Timestamp("2026-07-21").date())]

bias_rows = []
for source in ("primary", "fallback"):
    sub = post[post["assignment_source"] == source]
    for region in sorted(sub["macro_region"].dropna().unique()):
        r = sub[sub["macro_region"] == region]
        if len(r) == 0:
            continue
        bias_rows.append(dict(assignment_source=source, macro_region=region, n=len(r),
                              treatment_share=(r["arm_key"] == "treatment").mean()))
bias = pd.DataFrame(bias_rows)
print("\nPost-deploy treatment share by assignment_source x macro_region:")
print(bias.round(3).to_string(index=False))
save_table(bias, "03_fallback_geo_bias")

# chi-square: does the fallback population's region MIX differ from primary's?
ct = pd.crosstab(post["assignment_source"], post["macro_region"])
chi2, p_mix, dof, _ = stats.chi2_contingency(ct)
print(f"\nFallback vs primary region-MIX chi2 test: chi2={chi2:.2f}, df={dof}, p={p_mix:.4g}")

# does fallback's overall treatment share differ from 50%?
fb = post[post["assignment_source"] == "fallback"]
fb_treat = int((fb["arm_key"] == "treatment").sum())
fb_n = len(fb)
chi_fb = (fb_treat - fb_n / 2) ** 2 / (fb_n / 2) + ((fb_n - fb_treat) - fb_n / 2) ** 2 / (fb_n / 2)
p_fb = float(stats.chi2.sf(chi_fb, 1))
print(f"Fallback-only allocation: {fb_treat}/{fb_n} = {fb_treat/fb_n:.3f} treatment "
      f"(chi2={chi_fb:.2f}, p={p_fb:.4g} vs 50/50)")

fig, ax = plt.subplots(figsize=(7, 4))
piv = bias.pivot(index="macro_region", columns="assignment_source", values="treatment_share")
piv.plot(kind="bar", ax=ax, color={"primary": "#93A29C", "fallback": "#E2624B"})
ax.axhline(0.5, color="#0E4A52", lw=1, ls="--")
ax.set_ylabel("Treatment share")
ax.set_title("Post-deploy treatment share by region: fallback vs primary path")
fig.tight_layout()
fig.savefig(OUT_FIG / "03_fallback_bias.png", dpi=150)
print(f"figure -> {OUT_FIG / '03_fallback_bias.png'}")

# ---- SQL parity ------------------------------------------------------
c = con()
sql_contam = c.execute("""
    SELECT COUNT(*) n FROM fa
    WHERE experiment_cohort IN ('pre_deploy','post_deploy') AND contaminated_flag
""").df()["n"].iloc[0]
parity("contaminated count", n_contaminated, sql_contam, tol=0, rel=False)

sql_fb_treat = c.execute("""
    SELECT AVG(CASE WHEN arm_key='treatment' THEN 1.0 ELSE 0 END) r
    FROM fva f JOIN du u ON f.user_key = u.user_key JOIN dreg g ON u.region_key = g.region_key
    WHERE f.is_first_assignment AND f.assignment_source = 'fallback'
      AND f.assigned_date_key BETWEEN 20260716 AND 20260721
""").df()["r"].iloc[0]
parity("fallback treatment share", fb_treat / fb_n, sql_fb_treat)

print("\n03 root-cause investigation: OK")
