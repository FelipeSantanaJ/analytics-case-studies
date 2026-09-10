"""
Voxa+ ETL — single source of truth for every tunable.

One SEED drives every random draw. Change SEED or any value here and rerun
`python etl/run_pipeline.py` to get a new, internally-consistent synthetic world.

NOTE ON THE ROOT CAUSE
----------------------
Section 9 ("ROOT-CAUSE EFFECT SIZES") encodes the churn-spike mechanism. It is
deliberately *not* described in docs/01_business_context_kpis.md. It is a
combination of three contributing factors that only becomes visible by slicing
the curated data (Phase 10). Do not summarise it into the business-context doc.
"""

from __future__ import annotations
import datetime as _dt
import os as _os

# ---------------------------------------------------------------------------
# 1. Determinism
# ---------------------------------------------------------------------------
SEED = int(_os.environ.get("VOXA_SEED", 20260902))

# Population scale. 1.0 -> ~120k cumulative sign-ups / ~70k active at window end.
# Use a smaller value for fast calibration runs (env: VOXA_POP_SCALE).
POP_SCALE = float(_os.environ.get("VOXA_POP_SCALE", 1.0))

# ---------------------------------------------------------------------------
# 2. Time window
# ---------------------------------------------------------------------------
WINDOW_START = _dt.date(2023, 9, 1)     # window-month 1  (index 0)
N_MONTHS = 36                           # window-month 36 (index 35) = 2026-08
# dim_date is built wider than the fact window (guardrail: stray "(blank)" member)
DIM_DATE_START = _dt.date(2023, 1, 1)
DIM_DATE_END = _dt.date(2027, 12, 31)

# Current Year / Prior Year (12-month blocks ending at the window end)
CY_START_IDX, CY_END_IDX = 24, 35       # Sep 2025 .. Aug 2026
PY_START_IDX, PY_END_IDX = 12, 23       # Sep 2024 .. Aug 2025

# ---------------------------------------------------------------------------
# 3. Markets & FX
# ---------------------------------------------------------------------------
# market_id -> (currency, window-month index it becomes active, tz)
MARKETS = {
    "BR": {"currency": "BRL", "active_from_idx": 0,  "tz": "America/Sao_Paulo"},
    "MX": {"currency": "MXN", "active_from_idx": 9,  "tz": "America/Mexico_City"},   # month 10
    "US": {"currency": "USD", "active_from_idx": 15, "tz": "America/New_York"},      # month 16
}
REPORTING_CURRENCY_DEFAULT = "USD"

# Seeded FX random walk (monthly avg), clamped to these bands. No single-month shock.
FX = {
    "BRL": {"start": 4.95, "drift_per_month": 0.006, "vol": 0.02, "lo": 4.85, "hi": 5.55},
    "MXN": {"start": 17.2, "drift_per_month": 0.045, "vol": 0.12, "lo": 16.8, "hi": 20.2},
    "USD": {"start": 1.0,  "drift_per_month": 0.0,   "vol": 0.0,  "lo": 1.0,  "hi": 1.0},
}

# ---------------------------------------------------------------------------
# 4. Plans & pricing  (list price as of window end, local currency)
# ---------------------------------------------------------------------------
TIERS = ["Basico", "Standard", "Premium"]
BILLING_PERIODS = ["monthly", "annual"]        # annual billed at 10x monthly
ANNUAL_MONTHS_CHARGED = 10

PRICE_LOCAL_END = {                            # tier -> {market -> monthly list price}
    "Basico":   {"BR": 18.90, "MX": 89.0,  "US": 6.99},
    "Standard": {"BR": 29.90, "MX": 139.0, "US": 12.99},
    "Premium":  {"BR": 44.90, "MX": 219.0, "US": 17.99},
}

PLAN_FEATURES = {
    "Basico":   {"has_ads": True,  "max_streams": 1, "max_resolution": "1080p", "has_downloads": False},
    "Standard": {"has_ads": False, "max_streams": 2, "max_resolution": "1080p", "has_downloads": True},
    "Premium":  {"has_ads": False, "max_streams": 4, "max_resolution": "4K",    "has_downloads": True},
}

# New-subscriber plan mix
TIER_MIX = {"Basico": 0.34, "Standard": 0.44, "Premium": 0.22}
ANNUAL_SHARE = {"Basico": 0.08, "Standard": 0.19, "Premium": 0.30}

TRIAL_DAYS = 7
TRIAL_ELIGIBLE_TIERS = ("Standard", "Premium")   # direct sign-up only
TRIAL_TO_PAID_BASE = 0.57

# ---------------------------------------------------------------------------
# 5. Acquisition
# ---------------------------------------------------------------------------
# Base new paid subs per month at POP_SCALE=1.0, before seasonality/ramp.
ACQ_BASE = {"BR": 1450, "MX": 950, "US": 800}
# Linear-ish organic growth across the window (multiplier at last month).
ACQ_GROWTH_TO_END = {"BR": 1.25, "MX": 1.7, "US": 1.4}
# First-N-months launch ramp for MX/US (fraction of steady volume).
LAUNCH_RAMP = [0.35, 0.55, 0.72, 0.85, 0.93, 1.0]

CHANNELS = ["direct", "organic", "paid_search", "paid_social", "affiliate", "partner_bundle"]
CHANNEL_GROUP = {
    "direct": "owned", "organic": "owned",
    "paid_search": "performance", "paid_social": "performance",
    "affiliate": "performance", "partner_bundle": "partner",
}
# Channel mix before / after the H2-2025 shift (see section 9, Factor 3).
CHANNEL_MIX_PRE = {
    "direct": 0.18, "organic": 0.16, "paid_search": 0.17,
    "paid_social": 0.21, "affiliate": 0.12, "partner_bundle": 0.16,
}
CHANNEL_MIX_POST = {
    "direct": 0.11, "organic": 0.08, "paid_search": 0.13,
    "paid_social": 0.26, "affiliate": 0.20, "partner_bundle": 0.22,
}
# Blended CAC (USD) by channel — used to derive marketing spend from volume.
CAC_USD = {
    "direct": 4, "organic": 1, "paid_search": 19,
    "paid_social": 17, "affiliate": 13, "partner_bundle": 6,
}
INCENTIVISED_SIGNUP_RATE = {   # share of sign-ups carrying a promo code, by channel
    "direct": 0.15, "organic": 0.05, "paid_search": 0.28,
    "paid_social": 0.40, "affiliate": 0.62, "partner_bundle": 0.20,
}

# ---------------------------------------------------------------------------
# 6. Payments & dunning
# ---------------------------------------------------------------------------
PAYMENT_METHOD_MIX = {
    "BR": {"pix": 0.34, "card": 0.40, "boleto": 0.16, "carrier_billing": 0.10},
    "MX": {"card": 0.44, "oxxo": 0.34, "carrier_billing": 0.22},
    "US": {"card": 1.00},
}
AUTH_RATE = {"card": 0.92, "pix": 0.975, "boleto": 0.80, "oxxo": 0.75, "carrier_billing": 0.93}
# Processing cost: pct of amount + fixed fee (local currency, order-of-magnitude).
PROC_COST = {
    "card":            {"pct": 0.029, "fixed": 0.40},
    "pix":             {"pct": 0.009, "fixed": 0.05},
    "boleto":          {"pct": 0.018, "fixed": 1.80},
    "oxxo":            {"pct": 0.035, "fixed": 6.0},
    "carrier_billing": {"pct": 0.090, "fixed": 0.0},
}
DUNNING_RETRIES = 3
DUNNING_RETRY_DAYS = [2, 4, 7]
DUNNING_RECOVERY_RATE = {"card": 0.58, "pix": 0.66, "boleto": 0.40, "oxxo": 0.38, "carrier_billing": 0.52}
INVOLUNTARY_CHURN_ON_EXHAUST = 0.82   # share that actually churn once dunning is exhausted
SETTLEMENT_LAG_DAYS = {"card": 2, "pix": 0, "boleto": 3, "oxxo": 3, "carrier_billing": 32}

# ---------------------------------------------------------------------------
# 7. Engagement & content
# ---------------------------------------------------------------------------
# Monthly streamed hours per active sub ~ LogNormal-ish around these means by tier.
ENGAGEMENT_HOURS_MEAN = {"Basico": 34, "Standard": 52, "Premium": 63}
ENGAGEMENT_HOURS_CV = 0.55
TENURE_ENGAGEMENT_DECAY = 0.985       # per month multiplicative
HEALTHY_ENGAGEMENT_HOURS = 5.0        # below this = "below healthy engagement"
ACTIVE_RATE_BASE = 0.86               # share of paid subs who stream in a month

# Device-family viewing propensity (a sub draws a persistent profile from this).
DEVICE_FAMILIES = ["mobile_ios", "mobile_android", "web", "smart_tv", "streaming_stick", "console"]
DEVICE_CLASS = {
    "mobile_ios": "mobile", "mobile_android": "mobile", "web": "web",
    "smart_tv": "ctv", "streaming_stick": "ctv", "console": "ctv",
}
DEVICE_MIX_POP = {   # population-level share of "primary device"
    "mobile_ios": 0.17, "mobile_android": 0.28, "web": 0.12,
    "smart_tv": 0.24, "streaming_stick": 0.15, "console": 0.04,
}

# Content catalogue
N_TITLES = 3500
ORIGINAL_SHARE = 0.14
TENTPOLES_PER_QUARTER = {"BR": 3, "MX": 2, "US": 2}
CONTENT_GAP_ENGAGEMENT_HIT = 0.90     # streamed hours multiplier during a content gap
# Two Brazil licence expiries (doc 01 §8, ~month 22) trim catalogue engagement slightly.
BR_LICENCE_EXPIRY_MONTH = 21
BR_LICENCE_EXPIRY_ENGAGEMENT_HIT = 0.97

# Baseline app quality (pre-v3)
CRASH_FREE_RATE_BASE = 0.9965
PLAYBACK_ERROR_RATE_BASE = 0.006
VIDEO_START_FAILURE_RATE_BASE = 0.011
REBUFFER_RATIO_BASE = 0.012

# ---------------------------------------------------------------------------
# 8. Churn hazard (monthly probability, voluntary)
# ---------------------------------------------------------------------------
CHURN_BASE_BY_TENURE = {   # months since first paid billing -> base monthly hazard
    0: 0.060, 1: 0.047, 2: 0.038, 3: 0.033,
    4: 0.033, 5: 0.031, 6: 0.030,
    7: 0.028, 8: 0.027, 9: 0.026, 10: 0.025, 11: 0.024, 12: 0.026,   # 12 = annual renewal bump
    13: 0.023, 18: 0.021, 24: 0.022, 30: 0.019,   # sparse; interpolated in code
}
CHURN_MULT_TIER = {"Basico": 1.28, "Standard": 1.00, "Premium": 0.82}
CHURN_MULT_MARKET = {"BR": 1.00, "MX": 1.02, "US": 0.98}
CHURN_MULT_ANNUAL = 0.42                      # annual plans locked in
CHURN_MULT_LOW_ENGAGEMENT = 1.50             # < HEALTHY_ENGAGEMENT_HOURS this month
CHURN_MULT_ENGAGEMENT_SLOPE = -0.006         # per streamed hour above healthy (capped)
CHURN_MULT_INCENTIVISED_EARLY = 1.35         # promo-code sign-ups, first 3 months
REACTIVATION_RATE = 0.11                     # of churned base, per following 12 months
PLAN_CHANGE_RATE = {"upgrade": 0.014, "downgrade": 0.017}   # per active sub-month
PAUSE_RATE = 0.010
RESUME_RATE = 0.45                            # of paused, per month

# ---------------------------------------------------------------------------
# 9. ROOT-CAUSE EFFECT SIZES   (NOT in docs/01 — surfaces only through the data)
# ---------------------------------------------------------------------------
# The month-34 (idx 33) gross-churn spike is the product of THREE factors that
# overlap in time. No single report page shows all three.
#
#   F1  App "v3" connected-TV playback regression  (acute trigger, ~idx 32-33)
#   F2  Brazil price increase absorbed by engaged users, biting the disengaged
#       (amplifier, migration spread over idx 30-35)
#   F3  Acquisition-quality decline concentrated in Mexico  (pre-existing drag,
#       building from idx ~27)
#
# Diagnosis requires: Content&Engagement (F1 by device), Pricing&Plans (F2 by
# engagement x tier x timing), Acquisition Quality (F3 by channel x market),
# Market Context (BR step vs MX ramp vs US flat).

# -- F1: App v3 connected-TV playback regression -----------------------------
# v3 shipped device-family by device-family; connected-TV last.
APP_V3_ROLLOUT_IDX = {
    "mobile_ios": 29, "mobile_android": 29, "web": 30,
    "smart_tv": 32, "streaming_stick": 32, "console": 33,
}
CTV_FAMILIES = ("smart_tv", "streaming_stick", "console")
# QoE regression multipliers applied to CTV families once on v3.
APP_V3_CTV_VSF_MULT = 3.1               # video-start-failure rate
APP_V3_CTV_REBUFFER_MULT = 2.2
APP_V3_CTV_PLAYBACK_ERR_MULT = 2.6
APP_V3_CTV_CRASHFREE_DROP = 0.0060      # 0.9965 -> ~0.9905 on CTV
APP_V3_MOBILE_WEB_CRASHFREE_DROP = 0.0008   # tiny, non-diagnostic bump elsewhere
CTV_HEAVY_SHARE_THRESHOLD = 0.35        # >= this fraction of viewing on CTV -> "CTV-heavy"
CTV_QOE_ENGAGEMENT_MULT = 0.70         # CTV-heavy subs lose ~30% streamed hours while QoE bad
CTV_QOE_CHURN_ADD = 0.035            # additive monthly voluntary hazard, LAGGED 1 month
APP_V3_CTV_RECOVERY_IDX = 99           # not fixed inside the window (still live at idx 35)
# US connected-TV footprint was far less affected by the v3 regression (better CDN /
# newer device base) -> F1 barely moves US. This is what keeps US "the control market".
APP_V3_CTV_US_SENSITIVITY = 0.42

# -- F2: Brazil price increase (Standard/Premium) ---------------------------
BR_PRICE_HIKE_IDX = 30                 # list price changes (Mar 2026)
BR_PRICE_HIKE_PCT = {"Basico": 0.00, "Standard": 0.13, "Premium": 0.15}
# Existing subs migrate to the new price on their next renewal -> effect spreads.
PRICE_MIGRATION_SPREAD_MONTHS = 5      # idx 30..34
PRICE_CHURN_ADD_ENGAGED = 0.030       # engaged BR Std/Prem subs mostly absorb it
PRICE_CHURN_ADD_DISENGAGED = 0.135    # disengaged BR Std/Prem subs leave on migration
PRICE_CHURN_ADD_BR_BASICO = 0.016    # BR Basico reacts to the m32 plan-lineup change
PRICE_ANNUAL_SHIELD_MULT = 0.20       # annual subs barely react until their renewal
PRICE_MIGRATION_TAIL_MONTHS = 2       # elevated hazard for this many months after migration

# -- F3: Acquisition-quality decline, concentrated in Mexico ---------------
CHANNEL_SHIFT_IDX = 24                 # Sep 2025 — mix moves PRE -> POST from here
LOWQ_CHANNELS = ("affiliate", "partner_bundle")
# Extra ABSOLUTE monthly voluntary hazard for low-quality-channel cohorts, by age.
LOWQ_CHURN_ADD_BY_AGE = {0: 0.048, 1: 0.042, 2: 0.030, 3: 0.019, 4: 0.011, 5: 0.005}
# Mexico gets an extra bundle tilt and worse involuntary churn post-shift.
MX_BUNDLE_SHARE_AFTER = 0.50          # partner_bundle share of MX acquisition post-shift
MX_DRIFT_START_IDX = 27              # MX gross churn visibly drifts up from here
MX_INVOL_CHURN_MULT_AFTER = 1.6      # OXXO / bundle dunning deteriorates
MX_LOWQ_ENGAGEMENT_MULT = 0.88      # low-q MX cohorts also stream less

# -- Calibration guardrail for the spike ----------------------------------
# Pre-shift blended gross monthly churn should sit ~3.8-4.3%.
# Months idx 33-35 should reach ~7-8% blended ("nearly doubled").
SPIKE_TARGET_PRESHIFT = (0.036, 0.046)
SPIKE_TARGET_PEAK = (0.064, 0.086)

# ---------------------------------------------------------------------------
# 10. Support & tickets
# ---------------------------------------------------------------------------
SUPPORT_CONTACTS_PER_1000_BASE = 62
SUPPORT_REASON_MIX = {
    "billing_payment": 0.30, "app_playback": 0.24, "app_crash": 0.10,
    "content_request": 0.12, "account_access": 0.14, "other": 0.10,
}
SUPPORT_MIGRATION_IDX = 12            # Helpline v1 -> Helpdesk v2 (doc 01 §8)
CSAT_MEAN_V1, CSAT_MEAN_V2 = 4.15, 4.05   # on their native scales (1-5 / 0-10 handled in messify)

# ---------------------------------------------------------------------------
# 11. Data-quality injection switches (all True for the shipped build)
# ---------------------------------------------------------------------------
DQ_INJECT = {
    "date_formats": True, "excel_serials": True, "money_strings": True,
    "encoding_mojibake": True, "bom": True, "duplicate_events": True,
    "overlapping_invoice_files": True, "daily_full_dump_snapshot": True,
    "orphan_foreign_keys": True, "mislabeled_columns": True,
    "snapshot_ledger_drift": True, "sign_errors": True, "unit_breaks": True,
    "category_noise": True, "schema_break_support": True, "late_partial_files": True,
    "null_keys": True, "outliers": True, "timezone_bleed": True,
}
# Rough magnitude of a few injections (fractions of affected rows).
DQ_RATES = {
    "duplicate_event_frac": 0.018,
    "snapshot_drift_frac": 0.012,
    "orphan_subscriber_frac": 0.004,
    "orphan_content_frac": 0.006,
    "negative_watch_batch_frac": 0.002,
    "null_billing_key_frac": 0.003,
}
PLAYLOG_MS_ERA_START_IDX = 19          # watch time switches seconds -> milliseconds

# ---------------------------------------------------------------------------
# 12. Paths
# ---------------------------------------------------------------------------
import pathlib as _pl
ETL_DIR = _pl.Path(__file__).resolve().parent
ROOT = ETL_DIR.parent
RAW = ROOT / "data" / "raw"
STAGING = ROOT / "data" / "staging"
CURATED = ROOT / "data" / "curated"
QUALITY = ROOT / "data" / "quality"
DQ_FRAGMENTS = QUALITY / "dq_fragments"
VOCAB = ETL_DIR / "vocab"
DOCS = ROOT / "docs"

for _p in (RAW, STAGING, CURATED, QUALITY, DQ_FRAGMENTS):
    _p.mkdir(parents=True, exist_ok=True)

# Tolerance for accounting-identity DQ checks.
IDENTITY_TOL = 0.005
