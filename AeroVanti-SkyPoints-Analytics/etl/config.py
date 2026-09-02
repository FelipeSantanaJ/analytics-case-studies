"""
AeroVanti SkyPoints — ETL configuration.

Single source of truth for every tunable in the pipeline. One SEED drives every
random draw; every generator derives a named sub-seed from it (see utils.rng).

------------------------------------------------------------------------------
!!!  SPOILER  -------------------------------------------------------------------
Section `FLASH_EFFECT` below encodes the *true* underlying effect of the Flash
Redemption experiment. It is deliberately kept ONLY here. It must not be copied
into docs/00_scope.md, docs/01_business_context_kpis.md, or into any file under
data_analysis/. The Phase 10 read-out has to detect and quantify these numbers
from the data as if blind.
------------------------------------------------------------------------------
"""

from __future__ import annotations

import os
from datetime import date
from pathlib import Path

# Dev-only scale knob for the enrolled-member population (calibration iterations).
# SEED-default is 1.0 (the real build). The experiment sample size is NEVER scaled.
SCALE = float(os.environ.get("SKP_SCALE", "1.0"))

# --------------------------------------------------------------------------- #
# Paths
# --------------------------------------------------------------------------- #
ETL_DIR = Path(__file__).resolve().parent
PROJECT_DIR = ETL_DIR.parent
DATA_DIR = PROJECT_DIR / "data"
RAW_DIR = DATA_DIR / "raw"
STAGING_DIR = DATA_DIR / "staging"
CURATED_DIR = DATA_DIR / "curated"
QUALITY_DIR = DATA_DIR / "quality"
DQ_FRAGMENTS_DIR = QUALITY_DIR / "dq_fragments"
VOCAB_DIR = ETL_DIR / "vocab"

# --------------------------------------------------------------------------- #
# Determinism
# --------------------------------------------------------------------------- #
SEED = 20260902

# --------------------------------------------------------------------------- #
# Program-history window
# --------------------------------------------------------------------------- #
WINDOW_START = date(2024, 9, 1)      # program month 1
WINDOW_END = date(2026, 8, 31)      # program month 24 (data-generation date 2026-09-02)
N_MONTHS = 24

# Current Year / Prior Year (for YoY framing)
CY_START = date(2025, 9, 1)
PY_START = date(2024, 9, 1)

# Steady-state cohort: enrolled on or before this month (excludes the relaunch ramp)
STEADY_STATE_ENROLL_CUTOFF = date(2024, 12, 31)

# dim_date span — well beyond the fact window so late point-lot expiry / tier
# re-evaluation never produces a "(blank)" date member.
DIM_DATE_START = date(2024, 1, 1)
DIM_DATE_END = date(2027, 12, 31)

TIMEZONE = "America/Sao_Paulo"

# --------------------------------------------------------------------------- #
# Program scale
# --------------------------------------------------------------------------- #
N_MEMBERS_ENROLLED_TOTAL = int(120_000 * SCALE)   # cumulative enrolments across the window
# Monthly enrolment shape: relaunch surge in months 1-3, then a steadier ramp
# with a Black-Friday (Nov) bump. Values are relative weights, normalised to
# N_MEMBERS_ENROLLED_TOTAL by the generator.
ENROLLMENT_MONTH_WEIGHTS = [
    16, 12, 9,          # m1-3   relaunch surge (Sep-Nov 2024)  (Nov also BF)
    5.0, 4.2, 4.0,      # m4-6   Dec 2024 - Feb 2025
    3.6, 3.4, 3.3,      # m7-9   Mar-May 2025
    3.4, 3.6, 3.2,      # m10-12 Jun-Aug 2025
    3.1, 3.0, 4.6,      # m13-15 Sep-Nov 2025 (Nov BF bump)
    3.2, 2.9, 2.8,      # m16-18 Dec 2025 - Feb 2026
    2.8, 2.8, 2.7,      # m19-21 Mar-May 2026 (experiment window)
    2.7, 2.8, 2.7,      # m22-24 Jun-Aug 2026
]

ENROLLMENT_CHANNEL_MIX = {              # how members first join
    "flight": 0.46,
    "card": 0.31,                      # co-brand card acquisition funnel
    "web": 0.15,
    "partner": 0.08,
}

# BR macro-regions for home_city assignment (rough population-of-air-travel weights)
REGION_MIX = {
    "Sudeste": 0.48,
    "Sul": 0.17,
    "Nordeste": 0.20,
    "Centro-Oeste": 0.09,
    "Norte": 0.06,
}

# --------------------------------------------------------------------------- #
# Tiers
# --------------------------------------------------------------------------- #
TIERS = ["Blue", "Silver", "Gold", "Platinum"]
TIER_RANK = {"Blue": 1, "Silver": 2, "Gold": 3, "Platinum": 4}
TIER_EARN_MULTIPLIER = {"Blue": 1.0, "Silver": 1.25, "Gold": 1.5, "Platinum": 2.0}
TIER_TP_THRESHOLD = {"Blue": 0, "Silver": 8_000, "Gold": 25_000, "Platinum": 60_000}
TIER_SEGMENT_THRESHOLD = {"Blue": 0, "Silver": 4, "Gold": 12, "Platinum": 30}

# Target steady-state active-member tier mix (used to calibrate flight/earn rates)
TIER_MIX_TARGET = {"Blue": 0.68, "Silver": 0.20, "Gold": 0.09, "Platinum": 0.03}

# Snapshot-vs-ledger drift: share of member-months where the SkyCore tier snapshot
# disagrees with the event-ledger-derived status (DQ issue Q06).
TIER_SNAPSHOT_DRIFT_RATE = 0.045

# --------------------------------------------------------------------------- #
# Points economics
# --------------------------------------------------------------------------- #
POINT_LOT_LIFETIME_MONTHS = 24          # SkyPoints expire 24 months after the month earned
POINT_UNIT_COST_BRL = 0.021            # weighted award value per point (liability basis)
EXPECTED_BREAKAGE = 0.40               # program-to-date; used for breakage-adjusted liability

# Earn: SkyPoints per BRL of base fare, before tier multiplier
SKYPOINTS_PER_BRL_BASE_FARE = 1.0
FLEX_FARE_EARN_BONUS = 0.50            # +50% on flexible fare families
TIER_POINTS_PER_BRL_BASE_FARE = 1.0
TIER_POINTS_PER_SEGMENT = 100

# Co-brand card
COBRAND_SPEND_PER_SKYPOINT_BRL = 2.50  # 1 SkyPoint per R$2.50 card spend
COBRAND_WELCOME_BONUS_PTS = 15_000
COBRAND_PENETRATION_TARGET = 0.20      # of active members, at window end
COBRAND_ISSUANCE_SHARE_TARGET = 0.42   # of all SkyPoints issued, at window end

# Issuance source mix target (share of SkyPoints issued, window cumulative)
EARN_SOURCE_SHARE_TARGET = {
    "flight": 0.45,
    "cobrand_card": 0.42,
    "partner_hotel": 0.04,
    "partner_car": 0.02,
    "partner_retail": 0.02,
    "promo": 0.03,
    "service_recovery": 0.02,
}

# Redemption catalog. points_price is typical; value_per_point_brl is member value delivered.
REWARD_CATALOG = [
    # name,                 category,       points_price, value_per_point_brl, low_cost, available_from
    ("Award flight - short",   "award_flight", 8_000,  0.024, False, WINDOW_START),
    ("Award flight - medium",  "award_flight", 14_000, 0.025, False, WINDOW_START),
    ("Points+cash flight",     "award_flight", 6_000,  0.022, False, WINDOW_START),
    ("Seat selection",         "seat",         1_500,  0.013, True,  date(2026, 3, 2)),
    ("Extra checked bag",      "bag",          2_500,  0.014, True,  date(2026, 3, 2)),
    ("Lounge day pass",        "lounge",       5_000,  0.016, True,  date(2026, 3, 2)),
    ("Gift card R$25",         "gift_card",    3_500,  0.0080, True, date(2026, 3, 2)),
    ("Gift card R$50",         "gift_card",    6_500,  0.0090, True, date(2026, 3, 2)),
    ("Onboard Wi-Fi voucher",  "voucher",      1_800,  0.012, True,  date(2026, 3, 2)),
]

# Minimum redemption threshold (balance below which the redemption UI will not transact)
MIN_REDEMPTION_THRESHOLD_DEFAULT = 10_000
MIN_REDEMPTION_THRESHOLD_FLASH = 3_500

# Baseline (control-equivalent) behaviour --------------------------------------
# Quarterly redemption rate among active members, pre-experiment steady state.
BASELINE_QUARTERLY_REDEMPTION_RATE = 0.105
# Share of active members who have ever redeemed (window end, control-equivalent).
BASELINE_EVER_REDEEMED_SHARE = 0.27
# Program-to-date burn/earn ratio (points redeemed / points issued, trailing 12m).
BASELINE_BURN_EARN_RATIO = 0.55

# --------------------------------------------------------------------------- #
# Retention / lapse
# --------------------------------------------------------------------------- #
LAPSE_INACTIVITY_MONTHS = 12           # no earn AND no redemption for 12 consecutive months
# 12-month lapse rate, control-equivalent steady state, split by whether the
# member has ever redeemed. The gap is partly driven by a latent engagement
# factor (confounding) — see LATENT_ENGAGEMENT_* below.
LAPSE_RATE_NEVER_REDEEMED = 0.285
LAPSE_RATE_REDEEMED = 0.140
REACTIVATION_RATE = 0.12

# A per-member latent "engagement" factor ~ Normal(0, 1) drives BOTH redemption
# propensity and retention, so the observed redeemer/non-redeemer lapse gap
# overstates the causal effect of redeeming. Phase 10 has to disentangle this;
# the experiment is the clean causal test.
LATENT_ENGAGEMENT_ON_REDEEM_PROPENSITY = 0.55   # logit coef
LATENT_ENGAGEMENT_ON_RETENTION = 0.42           # logit coef (higher engagement -> lower lapse)

# --------------------------------------------------------------------------- #
# Flight activity / revenue
# --------------------------------------------------------------------------- #
BASE_FARE_BRL_MEAN = 430.0
BASE_FARE_BRL_CV = 0.55
TAXES_SHARE_OF_FARE = 0.28
FLEX_FARE_SHARE = 0.22
AWARD_SEAT_SHARE_TARGET = 0.075        # award-flight seats / total seats

# Travel seasonality multiplier by calendar month (Jan..Dec), applied to flight volume
TRAVEL_SEASONALITY = {
    1: 1.28, 2: 0.92, 3: 0.90, 4: 0.96, 5: 0.88, 6: 1.02,
    7: 1.22, 8: 0.95, 9: 0.90, 10: 1.00, 11: 1.05, 12: 1.20,
}
# Award-redemption bookings lead travel by ~1-2 months (book Oct-Nov for Dec-Jan)
REDEMPTION_SEASONALITY_LEAD_MONTHS = 1

# --------------------------------------------------------------------------- #
# The Flash Redemption experiment
# --------------------------------------------------------------------------- #
EXPERIMENT_START = date(2026, 3, 2)     # Monday
EXPERIMENT_WEEKS = 12
EXPERIMENT_END = date(2026, 5, 24)      # inclusive; EXPERIMENT_START + 12*7 - 1
EXPERIMENT_FREEZE_DATE = date(2026, 3, 1)   # eligibility + pre-period covariates frozen here
POST_WINDOW_OBS_DAYS = 99              # 2026-05-25 .. 2026-08-31

# Eligible = active (earn or flight in trailing 12m) AND not lapsed at freeze date.
# Sample: stratified by tier with Gold/Platinum oversampled; 50/50 within stratum.
EXPERIMENT_STRATA_N = {"Blue": 7_000, "Silver": 3_800, "Gold": 2_600, "Platinum": 1_600}
EXPERIMENT_TOTAL_N = sum(EXPERIMENT_STRATA_N.values())   # 15,000
EXPERIMENT_INELIGIBLE_LATE_CORRECTIONS = 30   # rows Flesk exports that must be reconciled out

# Planning values recorded in doc 01 (for reference; not used to generate data)
PLANNING_CONTROL_RATE = 0.11
PLANNING_MDE_ABS = 0.022

# ========================================================================== #
#  FLASH_EFFECT — the true underlying effect (SPOILER; keep out of docs/analysis)
# ========================================================================== #
FLASH_EFFECT = {
    # Realized control-arm redemption rate over the 12-week window (share with >=1
    # redemption of any kind). Slightly above the 11.0% planning value.
    "control_window_redemption_rate": 0.115,

    # True absolute lift in P(redeem in window), treatment vs control, BY TIER.
    # Concentrated in the threshold-constrained lower tiers; ~zero at the top.
    "ate_abs_pp_by_tier": {
        "Blue": 0.033,
        "Silver": 0.028,
        "Gold": 0.015,
        "Platinum": 0.000,   # no effect built in; any observed diff is sampling noise
    },
    # Design-weighted pooled ATE  ~= +2.65 pp   (8/4/2.2/0.8k weights)
    # Population-weighted (post-stratified 68/20/9/3) ATE ~= +2.96 pp
    #   -> the pooled estimate UNDERSTATES the population effect because Blue
    #      (largest true effect) is undersampled by the oversampling design.

    # Novelty: treatment's first-redemption hazard is elevated in the first weeks
    # and decays. Extra multiplicative lift on the weekly hazard in week 1,
    # decaying as exp(-(week-1)/tau). Durable ("settled", weeks 9-12) effect works
    # out to roughly +1.9 pp window-equivalent.
    "novelty_hazard_mult_week1": 1.9,      # week 1 hazard x this, above the settled treatment hazard
    "novelty_decay_tau_weeks": 2.5,

    # Guardrails — true effects, treatment vs control.
    "revenue_per_member_rel": -0.004,       # -0.4%  (not significant; NI vs -3% holds)
    "revenue_per_member_extra_noise_cv": 0.9,
    "liability_drawdown_per_member_brl": 3.20,   # treatment draws liability down MORE
    "reward_cash_cost_per_member_brl": 1.10,     # ... but partner reward cash cost is higher
    #   -> net liability cost per member ~ -R$2.10 (favorable, marginally significant)
    "avg_redemption_value_delta_brl": -16.0,     # treatment redemptions are shallower (low-cost catalog)
    "low_cost_only_share_treatment_redeemers": 0.46,
    "disengage_90d_post_abs_pp": -0.016,         # favorable; ~p = 0.03

    # Contamination / spillover assumed negligible; no cross-arm effect modelled.
}
# ========================================================================== #

# --------------------------------------------------------------------------- #
# Data-quality injection knobs
# --------------------------------------------------------------------------- #
DQ = {
    "snapshot_daily_dump": True,               # SkyCore re-dumps every member every day
    "snapshot_dump_every_n_days": 1,
    "point_txn_monthly_overlap_days": 3,       # overlapping date ranges across monthly files
    "point_txn_text_value_rate": 0.06,         # share of rows with points/value exported as text
    "bancoav_latin1": True,
    "bancoav_duplicate_month": "2025-06",
    "reserva_us_date_format": True,
    "reserva_orphan_member_rate": 0.02,        # member bookings pointing to a member absent from SkyCore
    "reserva_nonmember_booking_rate": 0.34,    # bookings with no loyalty_member_id at all
    "reserva_dupe_segment_rate": 0.015,
    "aurora_crm_golive_month": 4,              # months 1-3 have no CRM row
    "aurora_bad_birthyear_rate": 0.03,
    "flesk_exposure_at_least_once_rate": 0.08,
    "ledger_restated_months": ["2025-11", "2026-02"],
    "excel_serial_date_sources": ["bancoav", "ledger", "reward_catalog"],
    "event_dupe_rate": 0.01,                   # generic at-least-once duplication
}

# --------------------------------------------------------------------------- #
# Output
# --------------------------------------------------------------------------- #
WRITE_CSV_MIRROR = os.environ.get("SKP_NO_CSV") != "1"   # curated tables also written as .csv
CSV_MIRROR_MAX_ROWS = 3_000_000        # guardrail; fail loudly if a curated table exceeds this
PARQUET_COMPRESSION = "zstd"
FLOAT_ROUND_BRL = 2
DQ_WRITE_RETRIES = 5
DQ_WRITE_BACKOFF_SEC = 0.6
