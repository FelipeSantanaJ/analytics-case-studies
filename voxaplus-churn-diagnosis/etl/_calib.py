"""Fast calibration probe: build the world only, print churn / retention / KPI bands.
Run:  VOXA_POP_SCALE=0.08 python etl/_calib.py
"""
import sys, numpy as np, pandas as pd
sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent))
import config as C
from gen.world import build_world

w = build_world()
sm = w["subscription_month"]
sub = w["subscribers"].set_index("subscriber_id")
sm = sm.join(sub[["market", "channel", "is_incentivised"]], on="subscriber_id")

act = sm[sm.status == "active"].groupby("month_idx").size()
vol = sm.groupby("month_idx")["is_voluntary_churn"].sum()
inv = sm.groupby("month_idx")["is_involuntary_churn"].sum()
start = act.shift(1)
gross = (vol + inv) / start

print(f"\nPOP_SCALE={C.POP_SCALE}  subs={len(sub):,}  active@end={int(act.iloc[-1]):,}  "
      f"cum_signups={len(sub):,}")
print("\nidx  active   gross%  vol%  inv%")
for i in range(22, 36):
    print(f"{i:3d} {int(act.get(i,0)):7d}  {gross.get(i,np.nan)*100:5.2f} "
          f"{vol.get(i,0)/start.get(i,1)*100:5.2f} {inv.get(i,0)/start.get(i,1)*100:5.2f}")

pre = gross.loc[24:32].mean()
peak = gross.loc[33:35].mean()
print(f"\npre-shift mean gross (24-32): {pre*100:.2f}%   target {C.SPIKE_TARGET_PRESHIFT[0]*100:.1f}-{C.SPIKE_TARGET_PRESHIFT[1]*100:.1f}")
print(f"peak mean gross (33-35):      {peak*100:.2f}%   target {C.SPIKE_TARGET_PEAK[0]*100:.1f}-{C.SPIKE_TARGET_PEAK[1]*100:.1f}")
print(f"ratio peak/pre:               {peak/pre:.2f}x   target ~1.7-2.0x")

print("\nby market  gross% (idx 26..35):")
for mk in ["BR", "MX", "US"]:
    s = sm[sm.market == mk]
    a = s[s.status == "active"].groupby("month_idx").size()
    c = (s.groupby("month_idx")["is_voluntary_churn"].sum()
         + s.groupby("month_idx")["is_involuntary_churn"].sum()) / a.shift(1)
    print(f"  {mk}: " + " ".join(f"{c.get(i,np.nan)*100:4.1f}" for i in range(26, 36)))

# counterfactual attribution at peak (idx 33-35): share of churn rows by driver flag
print("\nchurn mix at peak (idx 33-35), voluntary rows:")
peakrows = sm[(sm.month_idx.between(33, 35)) & (sm.is_voluntary_churn)]
print(f"  total voluntary churn rows: {len(peakrows)}")
print(f"  in BR: {(peakrows.market=='BR').mean()*100:.0f}%   MX: {(peakrows.market=='MX').mean()*100:.0f}%   US: {(peakrows.market=='US').mean()*100:.0f}%")
print(f"  below-healthy-engagement: {peakrows.is_below_healthy_engagement.mean()*100:.0f}%")
print(f"  CTV-heavy (ctv_share>=.35): {(peakrows.ctv_share>=0.35).mean()*100:.0f}%")
print(f"  low-quality channel: {peakrows.channel.isin(C.LOWQ_CHANNELS).mean()*100:.0f}%")

# retention curve (cohort survival) for pre-shift cohorts
coh = sm.copy()
first = coh[coh.status.isin(["active", "paused"])].groupby("subscriber_id")["month_idx"].min()
coh = coh.join(first.rename("coh0"), on="subscriber_id")
coh["age"] = coh.month_idx - coh.coh0
base_coh = coh[coh.coh0.between(6, 20)]
size0 = base_coh[base_coh.age == 0].groupby("subscriber_id").size().shape[0]
for age in [1, 3, 6, 12]:
    alive = base_coh[(base_coh.age == age) & (base_coh.status == "active")]["subscriber_id"].nunique()
    print(f"  M{age:<2d} retention (cohorts m6-20): {alive/size0*100:.0f}%")
