"""
07 — The hoarding problem: the redemption funnel + the point-liability / breakage.

Decision: how big is the prize Flash Redemption is chasing, and what does the
unredeemed-points liability cost the company? Audience: CFO / loyalty finance.

Grain:
  fact_member_month  — member x month panel (~1.9M rows)
  fact_point_transaction — one ledger entry (earn / redeem / expire / adjust)
  fact_liability_month — one row per calendar month

Method (both tracks):
  1. Redemption funnel at the latest month: active -> balance clears the Flash
     threshold -> ever redeemed -> redeemed in last 12m -> redeemed last quarter,
     overall and by tier.
  2. Points roll-forward and realised breakage (expired / issued), window-to-date
     and by issuance source.
  3. Liability trajectory (gross vs breakage-adjusted) and a sensitivity table of
     the recognised cost to the breakage assumption.
"""
from __future__ import annotations
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import numpy as np, pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from utils import t, con, save_table, parity, banner, OUT_FIG, STRATA

banner("07 — Hoarding funnel + point liability")
mm = t("fact_member_month")
LAST = int(mm["month_key"].max())
last = mm[mm.month_key == LAST].copy()
tiers = t("dim_tier").set_index("tier_key")["tier_name"]
last["tier_name"] = last["tier_key"].map(tiers)
active = last[last.is_active_eom]
print(f"latest month = {LAST};  active members = {len(active):,}")

# trailing-12m & trailing-quarter redeemers
def redeemers_since(k_from):
    d = mm[(mm.month_key <= LAST)]
    ms = sorted(mm["month_key"].unique())
    cut = ms[max(0, len(ms) - k_from)]
    r = d[(d.month_key >= cut) & (d.redemptions_m > 0)]["member_key"].unique()
    return set(r)

r12 = redeemers_since(12)
rq = redeemers_since(3)

fun = []
for grp, sub in [("ALL", active)] + [(s, active[active.tier_name == s]) for s in STRATA]:
    n = len(sub)
    fun.append(dict(
        segment=grp, active=n,
        balance_ge_flash=int((sub.balance_pts_eom >= 3500).sum()),
        ever_redeemed=int(sub.has_redeemed_ever_eom.sum()),
        redeemed_12m=int(sub.member_key.isin(r12).sum()),
        redeemed_quarter=int(sub.member_key.isin(rq).sum()),
    ))
fun = pd.DataFrame(fun)
for c in ["balance_ge_flash", "ever_redeemed", "redeemed_12m", "redeemed_quarter"]:
    fun[c + "_pct"] = (fun[c] / fun["active"] * 100).round(1)
print("\nRedemption funnel (latest month):")
print(fun[["segment", "active", "balance_ge_flash_pct", "ever_redeemed_pct",
           "redeemed_12m_pct", "redeemed_quarter_pct"]].to_string(index=False))
save_table(fun, "07_redemption_funnel")

# ---- points roll-forward / breakage ------------------------------
fpt = t("fact_point_transaction")
roll = fpt.groupby("txn_type")["points"].sum()
issued = roll.get("earn", 0)
redeemed = -roll.get("redeem", 0)
expired = -roll.get("expire", 0)
print(f"\nPoints window-to-date:  issued {issued/1e6:,.0f}M  redeemed {redeemed/1e6:,.0f}M "
      f"({redeemed/issued:.1%})  expired {expired/1e6:,.0f}M ({expired/issued:.1%} of issued)")
by_src = (fpt[fpt.txn_type == "earn"].merge(
    t("dim_earn_source"), on="earn_source_key", how="left")
    .groupby("source_name")["points"].sum().sort_values(ascending=False))
print("\nSkyPoints issued by source:")
print((by_src / 1e6).round(1).to_string())
save_table(by_src.reset_index().rename(columns={"points": "points_issued"}), "07_issued_by_source")

# ---- liability trajectory + sensitivity --------------------------
li = t("fact_liability_month").sort_values("month_key")
lg = li["liability_brl_gross"].iloc[-1]
print(f"\nPoint liability at {LAST}:  gross R${lg/1e6:,.1f}M   "
      f"breakage-adj (40%) R${li['liability_brl_breakage_adj'].iloc[-1]/1e6:,.1f}M")
out_pts = li["points_outstanding_eop"].iloc[-1]
sens = pd.DataFrame({"assumed_breakage": [0.20, 0.30, 0.40, 0.50]})
sens["recognised_liability_brl_m"] = (out_pts * 0.021 * (1 - sens["assumed_breakage"]) / 1e6).round(2)
sens["vs_40pct_base_brl_m"] = (sens["recognised_liability_brl_m"]
                               - sens.loc[sens.assumed_breakage == 0.40, "recognised_liability_brl_m"].iloc[0]).round(2)
print("\nRecognised-liability sensitivity to the breakage assumption:")
print(sens.to_string(index=False))
save_table(sens, "07_breakage_sensitivity")

fig, ax = plt.subplots(1, 2, figsize=(9.6, 3.4))
ax[0].bar([s.replace("ALL", "All") for s in fun.segment],
          fun["ever_redeemed_pct"], color="#5C8CB8", label="ever redeemed")
ax[0].bar([s.replace("ALL", "All") for s in fun.segment],
          fun["redeemed_quarter_pct"], color="#0B5FA5", label="redeemed last quarter")
ax[0].set_ylabel("% of active members"); ax[0].set_title("Redemption reach by tier")
ax[0].legend(frameon=False)
ax[1].plot(li["month_key"].astype(str), li["liability_brl_gross"] / 1e6, "-o", color="#0B5FA5",
           ms=3, label="gross")
ax[1].plot(li["month_key"].astype(str), li["liability_brl_breakage_adj"] / 1e6, "-o", color="#E08A1E",
           ms=3, label="breakage-adjusted")
ax[1].set_title("Point-liability trajectory (R$M)")
ax[1].tick_params(axis="x", rotation=90, labelsize=6); ax[1].legend(frameon=False)
fig.tight_layout(); fig.savefig(OUT_FIG / "07_hoarding.png", dpi=150)
print(f"figure -> {OUT_FIG / '07_hoarding.png'}")

# SQL parity
c = con()
s = c.execute("""
  SELECT SUM(CASE WHEN txn_type='earn' THEN points END) issued,
        -SUM(CASE WHEN txn_type='redeem' THEN points END) redeemed,
        -SUM(CASE WHEN txn_type='expire' THEN points END) expired
  FROM fact_point_transaction
""").df().iloc[0]
parity("points issued", issued, s["issued"])
parity("points redeemed", redeemed, s["redeemed"])
parity("points expired", expired, s["expired"])
sql_ever = c.execute(f"""
  SELECT AVG(CAST(has_redeemed_ever_eom AS INT)) FROM fact_member_month
  WHERE month_key={LAST} AND is_active_eom
""").df().iloc[0, 0]
parity("ever-redeemed share (active, latest)",
       fun.loc[fun.segment == "ALL", "ever_redeemed"].iloc[0] / fun.loc[fun.segment == "ALL", "active"].iloc[0],
       sql_ever)
print("\n07 hoarding + liability: OK")
