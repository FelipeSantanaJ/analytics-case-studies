# F05 — The connected-TV app-quality regression  *(Factor 1)*

**Question.** Did streaming quality degrade on any device family in the months before the
spike, and did the subscribers who rely on that device churn more?

**Hypothesis.** The Voxa+ "v3" app rollout — which reached connected-TV devices last, around
window-month 32–33 — introduced a playback regression on smart-TV / streaming-stick /
console. Subscribers who watch mostly on those devices lost quality, then value, then
churned a month later.

**Method (both tracks).**
1. `fact_engagement_device_month` joined to `dim_device`: video-start-failure rate and
   playback-error rate (failures ÷ play starts) by **device class** by `month_idx`.
2. `sm` view: gross monthly churn for **CTV-heavy** subscribers (primary device in
   smart_tv / streaming_stick / console) vs the rest, pre-shift vs peak.
`q5_qoe_by_device`, `q5_ctv_heavy_churn`; SQL and pandas agree exactly.

**Evidence.**

Connected-TV quality (`results/q5_qoe_by_device.csv`):

| window-month | 31 | **32** | 33 | 34 | 35 | 36 |
|---|---|---|---|---|---|---|
| CTV video-start-failure rate | 1.09 % | **3.05 %** | 3.41 % | 3.42 % | — | 3.44 % |
| CTV playback-error rate | 0.59 % | **1.43 %** | 1.58 % | 1.55 % | — | 1.57 % |

Mobile and web rates are flat at ~1.1 % / ~0.6 % throughout. The CTV rates **triple at
window-month 32** — exactly one month before the churn step at window-month 34.

CTV-heavy vs rest — gross monthly churn (`results/q5_ctv_heavy_churn.csv`):

| Segment | Pre-shift | Peak |
|---|---|---|
| Not CTV-heavy | 4.09 % | 5.65 % |
| **CTV-heavy** | 4.14 % | **8.42 %** |

**Conclusion.** Before the shift, CTV-heavy and non-CTV subscribers churned at the **same**
rate (~4.1 %). After the v3 CTV rollout, CTV-heavy churn **doubled to 8.4 %** while the rest
rose only modestly. The one-month lag between the quality drop (window-month 32) and the
churn step (window-month 34, i.e. `month_idx` 33) is consistent with a value → decision
delay of roughly one billing cycle. This is **Factor 1**: an app regression on the
big-screen experience, hitting the heaviest-viewing part of the base. It is present in
every market but weakest in the US (`F02`), which had a smoother CTV rollout.

**Limitations.** "CTV-heavy" is proxied by the subscriber's primary device family (a
`dim_subscriber` attribute), not a live per-month device mix. Playback telemetry is
synthetic and aggregated at `fact_engagement_device_month`.

**Recommendation.** Treat the v3 connected-TV player as a Sev-1: roll back or hotfix the
start-up / playback path on smart-TV and streaming-stick, and confirm the video-start-
failure rate returns to ~1 %. Run a save campaign for CTV-heavy subscribers whose viewing
dropped after window-month 32.
