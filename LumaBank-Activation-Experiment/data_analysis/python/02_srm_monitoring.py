"""
02 — Daily SRM monitoring: catching the break.

Decision it informs: can the original run be trusted at all, and on what day did the
standing monitor (doc 01 section 9) first have grounds to say no? Audience: the
experimentation platform on-call + whoever has to explain the incident afterwards.

Grain: fact_variant_assignment (one row per assignment EVENT), re-aggregated to
experiment-day. This is an INDEPENDENT re-derivation of fact_srm_daily -- built here from
the raw assignment log, then checked against the curated table, exactly as the runbook
intends: the daily job and this analysis should never rely on each other being right.

Method (both tracks): first-assignment counts by day and arm; cumulative and
trailing-7-day Pearson chi-square goodness-of-fit vs 50/50; the alert_state per the
runbook thresholds (WARN p<0.01, ALERT p<0.001).
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

banner("02 — Daily SRM monitoring (original run)")

fva = t("fact_variant_assignment")
first = fva[fva["is_first_assignment"]].copy()
first["d"] = pd.to_datetime(first["assigned_ts_brt"]).dt.date

ORIG_START, ORIG_END = pd.Timestamp("2026-07-06").date(), pd.Timestamp("2026-07-21").date()
orig = first[(first["d"] >= ORIG_START) & (first["d"] <= ORIG_END)].sort_values("d")

days = pd.date_range(ORIG_START, ORIG_END, freq="D").date
rows = []
for day in days:
    upto = orig[orig["d"] <= day]
    window = orig[(orig["d"] > day - pd.Timedelta(days=7)) & (orig["d"] <= day)]

    def chi(frame):
        c = int((frame["arm_key"] == "control").sum())
        tr = int((frame["arm_key"] == "treatment").sum())
        n = c + tr
        if n < 20:
            return np.nan, np.nan
        chi2 = (c - n / 2) ** 2 / (n / 2) + (tr - n / 2) ** 2 / (n / 2)
        return chi2, float(stats.chi2.sf(chi2, 1))

    chi_c, p_c = chi(upto)
    chi_w, p_w = chi(window)
    dd = orig[orig["d"] == day]
    state = "ok"
    if (not np.isnan(p_c) and p_c < 0.001) or (not np.isnan(p_w) and p_w < 0.001):
        state = "alert"
    elif (not np.isnan(p_c) and p_c < 0.01) or (not np.isnan(p_w) and p_w < 0.01):
        state = "warn"
    rows.append(dict(day=str(day), n_control=int((dd["arm_key"] == "control").sum()),
                     n_treatment=int((dd["arm_key"] == "treatment").sum()),
                     n_fallback=int((dd["assignment_source"] == "fallback").sum()),
                     srm_p_cumulative=p_c, srm_p_trailing7=p_w, alert_state=state))
srm = pd.DataFrame(rows)
print(srm.to_string(index=False))
save_table(srm, "02_srm_daily")

first_alert = srm.loc[srm["alert_state"] == "alert", "day"].min()
alert_days = srm.loc[srm["alert_state"].isin(["warn", "alert"]), "day"].tolist()
print(f"\nFirst ALERT day: {first_alert}")
print(f"WARN/ALERT days: {alert_days}")
print(f"Deploy date (doc 02): 2026-07-16  ->  detection lag: "
      f"{(pd.Timestamp(first_alert) - pd.Timestamp('2026-07-16')).days} day(s)")

# ---- chart: daily allocation + trailing-7d p-value ----------------------
fig, ax1 = plt.subplots(figsize=(9, 4))
total = srm["n_control"] + srm["n_treatment"]
treat_share = srm["n_treatment"] / total.replace(0, np.nan)
ax1.plot(srm["day"], treat_share, "o-", color="#E2624B", label="Treatment share")
ax1.axhline(0.5, color="#93A29C", lw=1, ls="--")
ax1.axvline("2026-07-16", color="#0E4A52", lw=1.5, label="Deploy (2026-07-16)")
ax1.set_ylabel("Daily treatment share")
ax1.set_xticks(range(0, len(srm), 2))
ax1.set_xticklabels(srm["day"].iloc[::2], rotation=45, ha="right")
ax2 = ax1.twinx()
ax2.plot(srm["day"], srm["srm_p_trailing7"], "s--", color="#0E4A52", alpha=0.6, label="Trailing-7d p-value")
ax2.axhline(0.001, color="#C0453B", lw=1, ls=":")
ax2.set_yscale("log")
ax2.set_ylabel("Trailing-7d SRM p-value (log)")
ax1.set_title("Daily allocation and SRM p-value — the break, original run")
fig.legend(loc="upper left", bbox_to_anchor=(0.08, 0.88), frameon=False, fontsize=8)
fig.tight_layout()
fig.savefig(OUT_FIG / "02_srm_break.png", dpi=150)
print(f"figure -> {OUT_FIG / '02_srm_break.png'}")

# ---- cross-check against the curated fact_srm_daily (built independently in ETL) --
fsrm = t("fact_srm_daily")
fsrm_orig = fsrm[fsrm["experiment_phase"] == "original"].sort_values("assign_date")
merged = srm.merge(fsrm_orig[["assign_date", "alert_state"]], left_on="day", right_on="assign_date",
                   suffixes=("_rederived", "_curated"))
agree = (merged["alert_state_rederived"] == merged["alert_state_curated"]).mean()
print(f"\nCross-check vs curated fact_srm_daily: alert_state agreement = {agree:.0%}")

# ---- SQL parity (re-derivation done in SQL directly from the assignment log) -----
c = con()
sql_first_day_counts = c.execute("""
    SELECT assigned_date_key, arm_key, COUNT(*) n
    FROM fva WHERE is_first_assignment
    GROUP BY 1, 2 ORDER BY 1, 2
""").df()
py_total_orig = len(orig)
sql_total_orig = c.execute("""
    SELECT COUNT(*) n FROM fva
    WHERE is_first_assignment AND assigned_date_key BETWEEN 20260706 AND 20260721
""").df()["n"].iloc[0]
parity("original-run first-assignment count", py_total_orig, sql_total_orig, tol=0, rel=False)

print("\n02 SRM monitoring: OK")
