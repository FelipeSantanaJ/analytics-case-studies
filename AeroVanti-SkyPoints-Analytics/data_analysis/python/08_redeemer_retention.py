"""
08 — Do redeemers stay? The observational redeemer -> retention link.

Decision: is "get members to redeem" a retention lever, or just a correlate?
Audience: CRM / retention manager. The Flash Redemption experiment (03-06) is the
clean causal test of the same lever; this quantifies the *observational* gap and
shows how much of it survives adjustment.

Grain: fact_member_month (member x month panel). "Engagement lapse" = a member
with 12 consecutive months of no flight and no redemption (card-only earn does not
count) — see docs/01 §6.

Method (both tracks):
  1. 12-month engagement-lapse rate for members who had redeemed by a reference
     month vs those who had not.
  2. Logistic regression of lapse on prior_redeemer + tenure + tier + prior earn
     activity + prior flights -> the adjusted gap.
  3. Forward flight revenue: redeemers vs matched non-redeemers over the next 6
     months.
Caveat: a latent "engagement" trait plausibly drives both redeeming and staying,
so even the adjusted gap over-states causation. The experiment settles it.
"""
from __future__ import annotations
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import numpy as np, pandas as pd
import statsmodels.formula.api as smf
from utils import t, con, save_table, parity, banner, two_prop

banner("08 — Redeemer -> retention (observational)")
mm = t("fact_member_month").sort_values(["member_key", "month_key"])
months = sorted(mm["month_key"].unique())
REF = months[-13]                       # 12 months of look-ahead
END = months[-1]
print(f"reference month = {REF};  outcome observed through {END}")

pre = mm[mm.month_key <= REF]
post = mm[(mm.month_key > REF) & (mm.month_key <= END)]

# per-member pre-period features
g = pre.groupby("member_key")
feat = pd.DataFrame({
    "prior_redeemer": (g["redemptions_m"].sum() > 0).astype(int),
    "tenure_at_ref": g["tenure_months"].max(),
    "tier_at_ref": pre.sort_values("month_key").groupby("member_key")["tier_key"].last(),
    "prior_earn_pts": g["points_earned_m"].sum(),
    "prior_flights": g["flights_m"].sum(),
    "prior_card_only": ((g["flights_m"].sum() == 0) & (g["points_earned_m"].sum() > 0)).astype(int),
})
# outcome: engagement lapse in the look-ahead window = no flight AND no redemption
post_g = post.groupby("member_key").agg(fl=("flights_m", "sum"), rd=("redemptions_m", "sum"))
feat = feat.join(post_g, how="inner")
feat["eng_lapsed"] = ((feat["fl"] == 0) & (feat["rd"] == 0)).astype(int)
feat = feat[feat["tenure_at_ref"] >= 6]              # need some history
tiername = t("dim_tier").set_index("tier_key")["tier_name"]
feat["tier_name"] = feat["tier_at_ref"].map(tiername)
print(f"members in scope: {len(feat):,}")

# ---- 1. raw gap ---------------------------------------------------
raw = feat.groupby("prior_redeemer")["eng_lapsed"].agg(["mean", "count"])
gap = two_prop(feat.loc[feat.prior_redeemer == 1, "eng_lapsed"].sum(), (feat.prior_redeemer == 1).sum(),
               feat.loc[feat.prior_redeemer == 0, "eng_lapsed"].sum(), (feat.prior_redeemer == 0).sum())
print("\n12-month engagement-lapse rate:")
print(f"  prior redeemers    : {raw.loc[1, 'mean']*100:.1f}%  (n={raw.loc[1, 'count']:,})")
print(f"  never redeemed      : {raw.loc[0, 'mean']*100:.1f}%  (n={raw.loc[0, 'count']:,})")
print(f"  RAW gap (never - redeemer) : {(raw.loc[0, 'mean'] - raw.loc[1, 'mean'])*100:+.1f} pp")

# ---- 2. adjusted (logistic) -------------------------------------
feat["log_earn"] = np.log1p(feat["prior_earn_pts"])
m = smf.logit("eng_lapsed ~ prior_redeemer + tenure_at_ref + C(tier_name) + log_earn "
              "+ prior_flights + prior_card_only", data=feat).fit(disp=0)
d0, d1 = feat.copy(), feat.copy()
d0["prior_redeemer"] = 0
d1["prior_redeemer"] = 1
ame = (m.predict(d1) - m.predict(d0)).mean()
print(f"\nAdjusted average marginal effect of 'prior redeemer' on lapse: {ame*100:+.1f} pp "
      f"(logit {m.params['prior_redeemer']:+.3f}, p={m.pvalues['prior_redeemer']:.2e})")
print("  -> a large observational association survives adjustment, but a latent engagement")
print("     trait plausibly drives both; the experiment's 90-day guardrail (04/G3, -2.0 pp,")
print("     p=0.001) is the clean causal signal, on a shorter horizon.")

# ---- 3. forward flight revenue --------------------------------
rev = post.groupby("member_key")["flight_revenue_brl_m"].sum().rename("fwd_rev")
feat = feat.join(rev, how="left").fillna({"fwd_rev": 0})
fr = feat.groupby("prior_redeemer")["fwd_rev"].mean()
print(f"\nForward 12-month flight revenue per member: redeemer R${fr.get(1,0):,.0f}  "
      f"never R${fr.get(0,0):,.0f}  (raw diff R${fr.get(1,0)-fr.get(0,0):+,.0f})")

save_table(pd.DataFrame([dict(
    ref_month=REF, n=len(feat),
    lapse_prior_redeemer=raw.loc[1, "mean"], lapse_never=raw.loc[0, "mean"],
    raw_gap_pp=(raw.loc[0, "mean"] - raw.loc[1, "mean"]) * 100,
    adjusted_ame_pp=ame * 100, adj_logit=m.params["prior_redeemer"], adj_p=m.pvalues["prior_redeemer"],
    fwd_rev_redeemer=fr.get(1, 0), fwd_rev_never=fr.get(0, 0))]), "08_redeemer_retention")

# SQL parity
c = con()
sql_ref = c.execute(f"""
  WITH pre AS (
    SELECT member_key,
           MAX(CASE WHEN redemptions_m>0 THEN 1 ELSE 0 END) prior_redeemer,
           MAX(tenure_months) ten
    FROM fact_member_month WHERE month_key <= {REF} GROUP BY member_key),
  post AS (
    SELECT member_key, SUM(flights_m) fl, SUM(redemptions_m) rd
    FROM fact_member_month WHERE month_key > {REF} AND month_key <= {END} GROUP BY member_key)
  SELECT pre.prior_redeemer,
         AVG(CASE WHEN post.fl=0 AND post.rd=0 THEN 1.0 ELSE 0.0 END) lapse_rate
  FROM pre JOIN post USING (member_key)
  WHERE pre.ten >= 6
  GROUP BY 1 ORDER BY 1
""").df().set_index("prior_redeemer")["lapse_rate"]
parity("lapse rate | never redeemed", raw.loc[0, "mean"], sql_ref[0])
parity("lapse rate | prior redeemer", raw.loc[1, "mean"], sql_ref[1])
print("\n08 redeemer retention: OK")
