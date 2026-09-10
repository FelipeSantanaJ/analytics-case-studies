"""
SwiftBite Delivery — ETL configuration.

Single source of truth for every tunable in the pipeline. One SEED drives every
random draw; every generator derives a named sub-seed from it (see utils.rng).

------------------------------------------------------------------------------
!!!  SPOILER  ----------------------------------------------------------------
Section `INCENTIVE_EFFECT` below encodes the *true* underlying effect of the
zone-hour incentive experiment, including the neighbour-zone cannibalisation
term. It is deliberately kept ONLY here. It must not be copied into
docs/00_scope.md, docs/01_business_context_kpis.md, docs/02_data_architecture.md,
or into any file under data_analysis/. The Phase 10 read-out has to detect and
quantify these numbers from the data as if blind.
------------------------------------------------------------------------------
"""

from __future__ import annotations

import os
from datetime import date
from pathlib import Path

# Dev scale knob. SCALE=1.0 is a fast calibration build (~500 orders/day metro).
# Set SB_SCALE higher for a denser build; the experiment's zone-day structure and
# per-zone-day order counts scale with it. Rates (fulfillment, ETA, cancel, idle)
# are calibrated to be SCALE-invariant.
SCALE = float(os.environ.get("SB_SCALE", "1.0"))

# --------------------------------------------------------------------------- #
# Paths
# --------------------------------------------------------------------------- #
ETL_DIR = Path(__file__).resolve().parent
PROJECT_DIR = ETL_DIR.parent
# The regenerated data layers (raw/staging/curated) can be pointed OUTSIDE the
# OneDrive-synced project tree via SB_DATA_DIR, to avoid sync file-locks on
# Windows. They are git-ignored and fully reproducible either way. The
# human-readable DQ report stays in the project (it is the one committed artifact).
_DATA_ROOT = Path(os.environ.get("SB_DATA_DIR", str(PROJECT_DIR / "data")))
DATA_DIR = _DATA_ROOT
RAW_DIR = _DATA_ROOT / "raw"
STAGING_DIR = _DATA_ROOT / "staging"
CURATED_DIR = _DATA_ROOT / "curated"
QUALITY_DIR = PROJECT_DIR / "data" / "quality"
DQ_FRAGMENTS_DIR = _DATA_ROOT / "quality_fragments"
VOCAB_DIR = ETL_DIR / "vocab"

# --------------------------------------------------------------------------- #
# Determinism
# --------------------------------------------------------------------------- #
SEED = 20260910

# --------------------------------------------------------------------------- #
# Marketplace-history window
# --------------------------------------------------------------------------- #
WINDOW_START = date(2025, 1, 1)      # window-month 1
WINDOW_END = date(2026, 8, 31)      # window-month 20 (data-generation date 2026-09-10)
N_MONTHS = 20

DIM_DATE_START = date(2024, 6, 1)
DIM_DATE_END = date(2027, 6, 30)

TIMEZONE = "America/Sao_Paulo"

# Baseline period (defines each zone's supply-stress tier): window-months 1-15
BASELINE_END = date(2026, 3, 31)

# --------------------------------------------------------------------------- #
# Geography — 12 zones tiling one metro (modelled on Belo Horizonte)
# --------------------------------------------------------------------------- #
# Each zone: name, macro_area, area_km2, centroid (x, y) on a synthetic 6x4 grid,
# baseline demand weight, baseline supply-attractiveness (lower -> couriers avoid).
# supply-stress tier is DERIVED from realised baseline liquidity, not set here.
ZONES = [
    # id      name              macro_area     area  cx  cy  dem_w  supply_attr
    ("Z01", "Centro",           "centre",       7.5,  2,  2,  1.35,  1.15),
    ("Z02", "Savassi",          "centre",       5.2,  3,  2,  1.55,  1.20),
    ("Z03", "Funcionarios",     "centre",       4.8,  3,  1,  1.20,  1.10),
    ("Z04", "Lourdes",          "centre",       4.0,  2,  1,  1.10,  1.05),
    ("Z05", "Pampulha",         "inner_ring",  22.0,  2,  4,  0.95,  0.80),
    ("Z06", "Cidade Nova",      "inner_ring",  11.5,  4,  3,  0.90,  0.85),
    ("Z07", "Barreiro",         "outer_ring",  28.0,  1,  1,  0.80,  0.55),
    ("Z08", "Venda Nova",       "outer_ring",  26.0,  3,  5,  0.85,  0.52),
    ("Z09", "Norte",            "outer_ring",  24.0,  4,  5,  0.70,  0.50),
    ("Z10", "Leste",            "inner_ring",  13.0,  5,  2,  0.95,  0.78),
    ("Z11", "Oeste",            "inner_ring",  15.0,  1,  3,  0.90,  0.72),
    ("Z12", "Contorno Sul",     "outer_ring",  20.0,  2,  0,  0.78,  0.58),
]
# Undirected adjacency (by zone id). Drives the cannibalisation analysis.
ZONE_ADJACENCY = [
    ("Z01", "Z02"), ("Z01", "Z03"), ("Z01", "Z04"), ("Z01", "Z11"), ("Z01", "Z06"),
    ("Z02", "Z03"), ("Z02", "Z10"), ("Z02", "Z04"),
    ("Z03", "Z06"), ("Z04", "Z11"), ("Z04", "Z12"),
    ("Z05", "Z11"), ("Z05", "Z09"), ("Z05", "Z12"),
    ("Z06", "Z08"), ("Z06", "Z10"),
    ("Z07", "Z12"), ("Z07", "Z11"),
    ("Z08", "Z09"), ("Z09", "Z10"),
    ("Z11", "Z12"),
]
# Two zones re-cut at window-month 9 (Sep 2025): a strip moves Z05<->Z11.
ZONE_REDRAW_DATE = date(2025, 9, 1)
ZONE_REDRAW_PAIR = ("Z05", "Z11")
ZONE_REDRAW_ASBOOKED_MISassign_RATE = 0.16   # share of pre-redraw orders near the border

# --------------------------------------------------------------------------- #
# Demand — orders
# --------------------------------------------------------------------------- #
ORDERS_PER_DAY_METRO_BASE = int(520 * SCALE)   # calibration default; ~15k/day at SB_SCALE~29

# Day-of-week multiplier (Mon=0 .. Sun=6) on order volume
DOW_MULT = {0: 0.86, 1: 0.88, 2: 0.92, 3: 1.00, 4: 1.28, 5: 1.42, 6: 1.20}

# Hour-of-day demand shape (0..23), normalised inside the generator.
HOUR_SHAPE = [
    0.2, 0.1, 0.05, 0.03, 0.03, 0.05, 0.15, 0.35, 0.55, 0.55, 0.70, 1.35,   # 0-11
    1.55, 1.20, 0.70, 0.55, 0.65, 1.05, 1.75, 1.95, 1.60, 1.05, 0.65, 0.40,  # 12-23
]
PEAK_HOURS = (18, 19, 20, 21)          # dinner peak — the experiment's block
LUNCH_HOURS = (11, 12, 13)

# Calendar-month seasonality (Jan..Dec) on order volume
MONTH_SEASONALITY = {
    1: 1.05, 2: 0.90, 3: 0.98, 4: 1.00, 5: 1.02, 6: 1.10,
    7: 1.08, 8: 1.00, 9: 0.98, 10: 1.03, 11: 1.06, 12: 1.12,
}
# Rainy season (Southeast): Oct-Mar. Demand up, courier supply down.
RAINY_MONTHS = {10, 11, 12, 1, 2, 3}
RAINY_DEMAND_MULT = 1.07
RAINY_SUPPLY_MULT = 0.95
RAIN_DAY_PROB_IN_SEASON = 0.32         # a given day in-season is "rainy"
RAIN_DAY_DEMAND_MULT = 1.12
RAIN_DAY_SUPPLY_MULT = 0.88

# Local events (football / shows): a random ~2 evenings/week, one zone, demand spike
EVENT_EVENINGS_PER_WEEK = 2.0
EVENT_ZONE_DEMAND_MULT = 1.6

BASKET_VALUE_BRL_MEAN = 62.0
BASKET_VALUE_BRL_CV = 0.55
DELIVERY_FEE_BRL_MEAN = 8.5
DELIVERY_FEE_BRL_SD = 2.2
SWIFTBITE_TAKE_RATE = 0.22             # of basket
PAYMENT_SUPPORT_COST_PER_ORDER_BRL = 1.1

# --------------------------------------------------------------------------- #
# Supply — couriers
# --------------------------------------------------------------------------- #
N_COURIERS_TOTAL = int(1400 * SCALE)           # ever active over the window
ACTIVE_COURIERS_WEEK_TARGET = int(360 * SCALE)  # typical week
COURIER_VEHICLE_MIX = {"bike": 0.18, "moto": 0.70, "car": 0.12}
COURIER_ACQ_CHANNEL_MIX = {"organic": 0.34, "referral": 0.26, "paid_social": 0.28, "ops_drive": 0.12}
COURIER_CAC_BRL = {"organic": 15, "referral": 40, "paid_social": 78, "ops_drive": 120}

# Session behaviour
SESSIONS_PER_ACTIVE_COURIER_WEEK = 5.2
SESSION_HOURS_MEAN = 4.3
SESSION_HOURS_CV = 0.5
# Fraction of session minutes that are "cooldown" right after a dropoff
COOLDOWN_SHARE = 0.06
# Baseline utilisation (active / logged-in) at balanced liquidity
BASE_UTILISATION = 0.66
# Service time (pickup + drive + drop) minutes, by macro_area
SERVICE_MIN_BY_AREA = {"centre": 26, "inner_ring": 34, "outer_ring": 44}
SERVICE_MIN_CV = 0.35

# Courier zone choice: multinomial-logit over zones per block.
#   utility_z = b_earn * expected_earn_z + b_home * near_home_z + b_attr * supply_attr_z + noise
COURIER_CHOICE_BETA_EARN = 0.85       # per R$/active-hour above metro mean
COURIER_CHOICE_BETA_HOME = 0.55
COURIER_CHOICE_BETA_ATTR = 1.20
COURIER_CHOICE_NOISE_SD = 0.9
# Slow metro-wide supply decline across 2026 (a competitor raising pay) — backdrop,
# differenced out by the concurrent control arm.
SUPPLY_DECLINE_PER_MONTH_FROM = date(2026, 1, 1)
SUPPLY_DECLINE_PER_MONTH = 0.010      # -1% available courier-hours per month

# --------------------------------------------------------------------------- #
# Marketplace clearing — how supply+demand -> outcomes
# --------------------------------------------------------------------------- #
# For a zone-hour with liquidity ratio L = available_courier_hours / demanded:
#   base assignment prob, ETA and cancellation are smooth functions of L.
# Calibrated so that L>=1.1 clears ~99% with p90 ETA ~48, and L~0.7 drops to
# ~86% fulfillment with p90 ETA ~78.
CLEAR_L_REF = 1.0
FULFILL_AT_L = {0.6: 0.905, 0.8: 0.955, 1.0: 0.985, 1.2: 0.994, 1.6: 0.998}
ETA_P50_AT_L = {0.6: 46, 0.8: 40, 1.0: 34, 1.2: 31, 1.6: 29}
ETA_P90_SPREAD = {0.6: 1.70, 0.8: 1.50, 1.0: 1.30, 1.2: 1.18, 1.6: 1.10}  # p90 = p50 * spread
# Cancellation split of the non-fulfilled share (no-courier is a minority of failures)
CANCEL_SPLIT = {"no_courier": 0.30, "customer": 0.42, "courier": 0.16, "restaurant": 0.12}
# Restaurant cancels are ~constant regardless of L
RESTAURANT_CANCEL_RATE = 0.006
ASSIGN_LATENCY_P90_AT_L = {0.6: 240, 0.8: 175, 1.0: 120, 1.2: 92, 1.6: 74}

# Courier pay
COURIER_BASE_PAYOUT_PER_DELIVERY_BRL = 6.4
COURIER_PAYOUT_PER_KM_BRL = 1.15
TIP_RATE = 0.35                        # share of orders that tip
TIP_MEAN_BRL = 5.0

# --------------------------------------------------------------------------- #
# The zone-hour incentive experiment
# --------------------------------------------------------------------------- #
EXPERIMENT_START = date(2026, 4, 6)    # Monday, window-month 16
EXPERIMENT_WEEKS = 10
EXPERIMENT_END = date(2026, 6, 14)     # inclusive
EXPERIMENT_FREEZE_DATE = date(2026, 4, 5)
POST_WINDOW_OBS_DAYS = 78              # 2026-06-15 .. 2026-08-31

PEAK_BLOCK_START_HOUR = 18
PEAK_BLOCK_END_HOUR = 22               # exclusive -> hours 18,19,20,21
INCENTIVE_BONUS_BRL_PER_DELIVERY = 4.5
INCENTIVE_PUSH_RADIUS_M = 2000
# 50/50 within each (zone x baseline supply-stress tier) cell, balanced on weekday/weekend
EXPERIMENT_ALLOCATION = 0.5

# Planning values recorded in doc 01 (reference only; not used to generate)
PLANNING_CONTROL_FULFILLMENT = 0.86
PLANNING_MDE_POOLED_PP = 0.013

# ========================================================================== #
#  INCENTIVE_EFFECT — the true underlying effect (SPOILER; keep out of docs/analysis)
# ========================================================================== #
INCENTIVE_EFFECT = {
    # The bonus raises the *effective available courier-hours* in a treated zone
    # during the peak block by a multiplicative supply response, BY baseline
    # supply-stress tier. This is the structural channel; fulfillment/ETA/cancel
    # effects all fall out of the clearing model from the higher L.
    "supply_response_mult_by_tier": {
        "short":    1.34,   # big pull where there is unmet demand and low attractiveness
        "balanced": 1.15,
        "long":     1.04,   # already clearing -> almost nothing, pure cost
    },
    # Of the extra courier-hours that show up in a treated zone, this share is
    # DRAWN FROM adjacent zones (cannibalisation) rather than net-new supply
    # (couriers logging on, or coming from non-adjacent far zones).
    "cannibalisation_share": 0.28,          # -> metro net lift ~ 72-85% of summed local lift
    "cannibalisation_only_if_adjacent_control": True,

    # Novelty: week-1 supply response is amplified and decays over the 10 weeks.
    "novelty_mult_week1": 1.35,             # extra on top of the settled response
    "novelty_decay_tau_weeks": 2.5,

    # Idiosyncratic noise on the per-zone-day realised supply response (log-normal sd)
    "supply_response_noise_sd": 0.10,

    # Guardrail truths (fall out of the model, listed for the calibration target):
    #   ETA p90 on treated short-tier zone-days: ~ -12 min
    #   no-courier cancel rate on treated short-tier: ~ -1.6 pp
    #   courier earnings / active hour on treated: ~ +R$3.4 (bonus + more trips)
    #   incentive cost per incremental delivered order: designed to land NEAR the
    #     delivered-order contribution margin (~R$9-11) so G1 needs a careful read.
    "target_cost_per_incremental_order_brl": 10.0,
}
# ========================================================================== #

# --------------------------------------------------------------------------- #
# Data-quality injection knobs
# --------------------------------------------------------------------------- #
DQ = {
    # Q01 datetime formats
    "ordercore_date_format_mix": {"iso": 0.55, "br_datetime": 0.45},
    "excel_serial_sources": ["payhub"],
    # Q02 timezone
    "utc_feeds": ["payhub", "boost"],          # exported with 'Z', no offset column
    # Q03 money as text
    "money_text_rate": 0.07,
    "payhub_parens_reversal_rate": 0.015,
    # Q04 GPS noise
    "gps_cadence_sec_choices": [30, 45, 60, 90],
    "gps_jitter_m_sd": 18.0,
    "gps_faraway_ping_rate": 0.004,
    "gps_null_island_rate": 0.001,
    "gps_midsession_gap_rate": 0.02,
    # Q05 duplicates
    "ordercore_retry_dupe_rate": 0.015,
    "event_at_least_once_rate": 0.012,
    "payhub_redelivered_month": "2026-05",
    # Q06 orphan courier ids
    "orphan_courier_id_rate": 0.015,
    # Q07 zone boundary redraw -> handled via ZONE_REDRAW_* above
    # Q08 encoding
    "ordercore_latin1_rate": 0.5,              # of address/restaurant text fields
}

# --------------------------------------------------------------------------- #
# Output
# --------------------------------------------------------------------------- #
WRITE_CSV_MIRROR = os.environ.get("SB_NO_CSV") != "1"
CSV_MIRROR_MAX_ROWS = 4_000_000
PARQUET_COMPRESSION = "zstd"
FLOAT_ROUND_BRL = 2
DQ_WRITE_RETRIES = 5
DQ_WRITE_BACKOFF_SEC = 0.6
