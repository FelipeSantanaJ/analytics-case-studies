"""
LumaBank — ETL configuration.

Single source of truth for every tunable in the pipeline. One SEED drives every
random draw; every generator derives a named sub-seed from it (see utils.rng).

------------------------------------------------------------------------------
!!!  SPOILER  ---------------------------------------------------------------
Sections `EFFECT` and `BUG` below encode (a) the *true* underlying effect of the
onboarding experiment and (b) the exact magnitudes of the production bug that
breaks the first run. They are kept ONLY here. They must not be copied into
docs/00_scope.md, docs/01_business_context_kpis.md, docs/02_data_architecture.md,
or into any file under data_analysis/. The Phase 10 read-out has to detect and
quantify these numbers from the data as if blind.
------------------------------------------------------------------------------
"""

from __future__ import annotations

import os
from datetime import date
from pathlib import Path

# Dev-only scale knob for the signup population (calibration iterations).
# SEED-default is 1.0 (the real build). Experiment sample sizes are NEVER scaled.
SCALE = float(os.environ.get("LB_SCALE", "1.0"))

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
SEED = 20260910

# --------------------------------------------------------------------------- #
# Platform-history window
# --------------------------------------------------------------------------- #
WINDOW_START = date(2025, 1, 1)      # LumaBank public launch (month 1)
WINDOW_END = date(2026, 9, 30)       # month 21 — the outcome tail for the re-run
N_MONTHS = 21
DATA_GEN_DATE = date(2026, 9, 10)    # "today" for the build; the last ~3 weeks are near-future

# dim_date span — beyond the fact window so no event lands on a missing date row.
DIM_DATE_START = date(2024, 6, 1)
DIM_DATE_END = date(2027, 12, 31)

DEFAULT_TZ = "America/Sao_Paulo"

# --------------------------------------------------------------------------- #
# Platform scale
# --------------------------------------------------------------------------- #
N_USERS_TOTAL = int(135_000 * SCALE)   # cumulative signups across the 21 months

# Monthly signup shape (relative weights, normalised to N_USERS_TOTAL). Ramp from
# launch, Jan "organise my finances" peaks, Black-Friday/November card-acq pushes,
# a Jun-Jul winter-holiday dip. 21 values, month 1 = Jan 2025.
SIGNUP_MONTH_WEIGHTS = [
    3.0, 2.6, 3.0,      # m1-3   Jan-Mar 2025  (launch ramp; Feb Carnaval dip inside)
    3.4, 3.6, 3.2,      # m4-6   Apr-Jun 2025
    3.1, 3.4, 3.9,      # m7-9   Jul-Sep 2025
    4.4, 6.0, 5.2,      # m10-12 Oct-Dec 2025  (Nov Black Friday push, Dec 13th salary)
    6.6, 5.0, 5.4,      # m13-15 Jan-Mar 2026  (Jan peak)
    5.6, 5.8, 5.2,      # m16-18 Apr-Jun 2026
    5.5, 7.2, 7.6,      # m19-21 Jul-Sep 2026  (Jul dip then recovery; experiment months)
]

# Acquisition channels: share of signups, latent-intent shift (added to N(0,1)),
# and the control-flow Day-7 Activation baseline the calibration targets.
CHANNELS = ["paid_social", "organic", "app_store_search", "referral", "influencer"]
CHANNEL_MIX = {
    "paid_social": 0.38, "organic": 0.22, "app_store_search": 0.18,
    "referral": 0.15, "influencer": 0.07,
}
CHANNEL_INTENT_SHIFT = {
    "paid_social": -0.35, "organic": 0.30, "app_store_search": 0.05,
    "referral": 0.45, "influencer": -0.30,
}
# Órbita CRM went live in platform month 3 -> months 1-2 signups carry no
# acquisition row and land on channel "unknown".
ORBITA_GOLIVE_MONTH = 3

# BR macro-region signup weights (used with the UF/timezone vocab file).
REGION_MIX = {"SE": 0.47, "NE": 0.22, "S": 0.14, "CO": 0.09, "N": 0.08}

OS_MIX = {"Android": 0.72, "iOS": 0.28}

# --------------------------------------------------------------------------- #
# Onboarding funnel — control ("old") flow, pre-experiment steady state
# --------------------------------------------------------------------------- #
# P(reach step | reached previous), some as a logit with an intent slope.
P_PERSONAL_DATA = 0.97                       # signup_started -> personal_data
KYC_SUBMIT_A0 = 1.70                         # logit intercept: P(submit KYC | personal_data)
KYC_SUBMIT_INTENT_SLOPE = 0.85              # + per unit latent intent
KYC_REJECT_RATE = 0.105                      # of KYC submissions (control)
KYC_MANUAL_RATE = 0.045                      # of KYC submissions routed to analyst queue
KYC_DECISION_LATENCY_H_MEAN = 7.0           # approved: fast; manual: +a tail
P_ACCOUNT_GIVEN_KYC_OK = 0.995               # control: account created iff KYC approved

# Activation: P(first transaction within 7 days | account exists), control flow.
ACT_A0 = 0.60                                # logit intercept (calibrated to blended ~0.48)
ACT_INTENT_SLOPE = 0.70
ACT_CHANNEL_SHIFT = {                        # added to the activation logit
    "paid_social": -0.18, "organic": 0.16, "app_store_search": 0.00,
    "referral": 0.30, "influencer": -0.22, "unknown": 0.0,
}
# Day-1 and Day-30 are derived from the same latent time-to-activate model.
TTFT_HOURS_MEDIAN = 26.0                     # median hours to first txn among activators
TTFT_HOURS_SIGMA = 1.15                      # lognormal sigma

# Post-activation transaction stream (thinned — enough for TTFT + a platform trend).
TXN_TAIL_DAYS = 75
TXN_TAIL_PER_DAY_MEAN = 0.55                 # Poisson rate/day over the tail, x intent
TXN_FIRST_TYPE_MIX = {"pix": 0.55, "card": 0.28, "boleto": 0.07, "transfer": 0.10}
TXN_AMOUNT_BRL_MEAN = 140.0
TXN_AMOUNT_BRL_CV = 1.3

# --------------------------------------------------------------------------- #
# Risk / fraud / support (guardrail context), control-flow baselines
# --------------------------------------------------------------------------- #
FRAUD_FLAG_RATE = 0.012                      # of activated accounts, first 30 days (control)
FRAUD_INTENT_SLOPE = -0.20                  # lower intent -> slightly more fraud
FRAUD_TYPES = ["first_party", "synthetic_id", "account_takeover", "mule"]
ONBOARDING_TICKET_RATE = 0.080              # share of signups with >=1 onboarding-category ticket
TICKET_CATEGORIES = ["onboarding", "kyc", "card", "transaction", "other"]
TICKET_CHANNELS = ["chat", "email", "phone"]

# --------------------------------------------------------------------------- #
# App releases
# --------------------------------------------------------------------------- #
APP_RELEASES_PER_MONTH = 3                   # per platform, on average (noise)
APP_VERSION_START = (4, 0, 0)               # bumps minor each release
# The routine release that resets the on-device variant cache, and the hotfix.
DEPLOY_DATE = date(2026, 7, 16)             # experiment day 11
HOTFIX_DATE = date(2026, 7, 22)

# --------------------------------------------------------------------------- #
# The onboarding experiment
# --------------------------------------------------------------------------- #
EXP1_START = date(2026, 7, 6)               # Monday — original run
EXP1_PLANNED_END = date(2026, 8, 16)        # 6 weeks planned
EXP1_ENROLL_PAUSED = date(2026, 7, 22)      # enrollment stops (last signup day 2026-07-21)
EXP1_ABANDONED = date(2026, 7, 24)          # formal decision to restart
EXP2_START = date(2026, 8, 24)              # Monday — clean re-run
EXP2_END = date(2026, 9, 20)               # 4 weeks

DAY7_WINDOW_DAYS = 7

# Planning values recorded in doc 01 (reference only; not used to generate data).
PLANNING_CONTROL_DAY7 = 0.48
PLANNING_MDE_ABS_6WK = 0.030

# ========================================================================== #
#  EFFECT — the true underlying treatment effect (SPOILER; keep out of docs/analysis)
# ========================================================================== #
EFFECT = {
    # Realised control-arm Day-7 Activation in the clean re-run (blended).
    "control_day7_rerun": 0.478,

    # True absolute lift in P(Day-7 activation), treatment vs control, BY CHANNEL.
    # Largest for low-intent top-of-funnel traffic that bounces at the doc wall;
    # small for warm referral / organic.
    "ate_day7_by_channel": {
        "paid_social": 0.060,
        "influencer": 0.055,
        "app_store_search": 0.035,
        "organic": 0.018,
        "referral": 0.014,
        "unknown": 0.030,
    },
    # Channel-mix-weighted pooled ATE ~= +3.6 pp. The re-run's MDE is ~3.0 pp, so
    # the effect is detectable but the CI is wide — the deep dive makes the point
    # that the 6-week design would have pinned it far tighter.

    # Novelty: treatment's first-week activation is inflated and decays.
    "novelty_mult_week1": 1.35,             # week-1 extra lift x settled effect
    "novelty_decay_tau_weeks": 2.0,

    # Guardrails — true effects, treatment vs control. Both are inside their
    # non-inferiority bounds (KYC +1.5 pp, fraud +0.5 pp) but only just: the
    # one-sided 95% upper bound sits a hair under the margin. Risk & Compliance
    # should read this as "not a clean pass".
    "kyc_reject_delta_pp": 0.004,           # control 9.0% -> treatment ~9.4%
    "fraud_flag_delta_pp": 0.0010,          # control 1.2% -> treatment ~1.3%
    "onboarding_ticket_delta_per_1k": 8.0,  # treatment ~ +8 tickets / 1k signups (directional)

    # The treatment flow also shifts *where* users drop: fewer bounce before an
    # account exists, more sit in limited state without ever verifying.
    "treatment_account_first": True,
    "treatment_limited_never_verified_share": 0.13,
    "treatment_kyc_submit_lift": 0.06,     # + P(submit KYC) — deferred, but still lower urgency
}
# ========================================================================== #

# ========================================================================== #
#  BUG — the production incident (SPOILER; keep out of docs/analysis)
# ========================================================================== #
BUG = {
    # BUG01 — the 2026-07-16 mobile release resets the on-device variant cache for
    # a share of users assigned BEFORE the deploy who open the app within N days.
    "reset_share": 0.15,
    "reset_open_window_days": 5,

    # BUG02 — of the reset users, a fraction get a fresh assignment row on next
    # open; its arm is a re-hash with a different salt -> ~flip_rate land opposite.
    "reswitch_share": 0.40,
    "reswitch_flip_rate": 0.50,

    # BUG03 — signups ON/AFTER the deploy fall into a biased fallback. Share starts
    # high and (narratively) decays as the hotfix rolls; in practice enrollment is
    # paused 2 days later so the original run sees it near-constant. The fallback
    # arm is a deterministic function of UF+timezone, not the RNG.
    "fallback_share_0": 0.72,
    "fallback_decay_days": 6,
    # UF-hash -> arm skew: fraction of fallback users sent to TREATMENT, by macro
    # region. Not 50/50, and strongly correlated with geography — this is what the
    # root-cause analysis has to quantify.
    "fallback_treat_frac_by_region": {
        "SE": 0.78, "S": 0.72, "CO": 0.55, "NE": 0.42, "N": 0.35,
    },
}
# ========================================================================== #

# --------------------------------------------------------------------------- #
# SRM monitoring runbook thresholds (doc 01 §9) — used to stamp fact_srm_daily
# --------------------------------------------------------------------------- #
SRM_WARN_P = 0.01
SRM_ALERT_P = 0.001
SRM_TRAILING_DAYS = 7

# --------------------------------------------------------------------------- #
# Data-quality injection knobs
# --------------------------------------------------------------------------- #
DQ = {
    "users_snapshot_monthly": True,           # Lumen Core re-dumps every user every month
    "users_snapshot_extra_dupe_rate": 0.15,   # extra intra-month duplicate rows
    "txn_monthly_overlap_days": 3,            # overlapping date ranges across monthly files
    "txn_amount_text_rate": 0.06,            # share of rows with amount exported as text
    "orbita_latin1_cidade": True,
    "riskguard_utc_no_offset": True,
    "flagfox_exposure_at_least_once_rate": 0.08,
    "trilha_step_at_least_once_rate": 0.05,
    "trilha_missing_terminal_step_rate": 0.03,
    "riskguard_orphan_user_rate": 0.015,
    "excel_serial_date_sources": ["beacon"],
    "epoch_ms_sources": ["lumencore_txn"],
    "epoch_s_sources": ["riskguard_fraud"],
    "event_dupe_rate": 0.01,                  # generic at-least-once duplication
    "mojibake_name_rate": 0.5,
}

# --------------------------------------------------------------------------- #
# Output
# --------------------------------------------------------------------------- #
WRITE_CSV_MIRROR = os.environ.get("LB_NO_CSV") != "1"
CSV_MIRROR_MAX_ROWS = 3_000_000
PARQUET_COMPRESSION = "zstd"
FLOAT_ROUND_BRL = 2
DQ_WRITE_RETRIES = 5
DQ_WRITE_BACKOFF_SEC = 0.6
