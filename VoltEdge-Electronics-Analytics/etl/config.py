"""
VoltEdge Electronics — pipeline configuration.

Every constant that shapes the synthetic dataset lives here so the whole pipeline is
tunable from one place and fully reproducible from a single SEED.

All monetary anchors are in USD unless a column name says otherwise.
"""

from __future__ import annotations

import datetime as dt
from pathlib import Path

# --------------------------------------------------------------------------------------
# Reproducibility & paths
# --------------------------------------------------------------------------------------

SEED = 20240701

ETL_DIR = Path(__file__).resolve().parent
PROJECT_DIR = ETL_DIR.parent
DATA_DIR = PROJECT_DIR / "data"
RAW_DIR = DATA_DIR / "raw"
STAGING_DIR = DATA_DIR / "staging"
CURATED_DIR = DATA_DIR / "curated"
QUALITY_DIR = DATA_DIR / "quality"

for _d in (RAW_DIR, STAGING_DIR, CURATED_DIR, QUALITY_DIR):
    _d.mkdir(parents=True, exist_ok=True)

# --------------------------------------------------------------------------------------
# Time
# --------------------------------------------------------------------------------------

# Analytics extract: orders only ever fall inside this 24-month window.
WINDOW_START = dt.date(2024, 7, 1)
WINDOW_END = dt.date(2026, 6, 30)

# Year-over-year split used by the report's Comparable-Base logic.
CY_START = dt.date(2025, 7, 1)   # current year
PY_START = dt.date(2024, 7, 1)   # prior year

# dim_date spans a buffer either side (PO dates before, deliveries after).
DIM_DATE_START = dt.date(2024, 1, 1)
DIM_DATE_END = dt.date(2026, 12, 31)

# Opening inventory is seeded on this date so July 2024 is not stocked out.
INVENTORY_OPENING_DATE = dt.date(2024, 6, 30)

# --------------------------------------------------------------------------------------
# Markets
# --------------------------------------------------------------------------------------
# price_index : local list price = round_psych(usd_price * fx_anchor_inverse * price_index)
#               captures VAT-inclusive display pricing / import taxes vs the US baseline.

MARKETS = {
    "US": {
        "name": "United States",
        "currency": "USD",
        "live_date": WINDOW_START,          # live before the window; always-on in the extract
        "is_comparable_base": True,
        "price_index": 1.00,
        "locale": "en_US",
        "free_ship_threshold_local": 50,
        "warehouses": ["FC-DAL", "FC-RNO"],
        "monthly_orders_start": 3600,       # first in-window month
        "monthly_orders_end": 4700,         # last in-window month (pre-seasonality)
    },
    "UK": {
        "name": "United Kingdom",
        "currency": "GBP",
        "live_date": dt.date(2025, 1, 1),
        "is_comparable_base": False,
        "price_index": 1.03,
        "locale": "en_GB",
        "free_ship_threshold_local": 40,
        "warehouses": ["FC-BHX"],
        "monthly_orders_start": 950,
        "monthly_orders_end": 1900,
    },
    "DE": {
        "name": "Germany",
        "currency": "EUR",
        "live_date": dt.date(2025, 1, 1),
        "is_comparable_base": False,
        "price_index": 1.05,
        "locale": "de_DE",
        "free_ship_threshold_local": 40,
        "warehouses": ["FC-LEJ"],
        "monthly_orders_start": 850,
        "monthly_orders_end": 1750,
    },
    "BR": {
        "name": "Brazil",
        "currency": "BRL",
        "live_date": dt.date(2025, 7, 1),
        "is_comparable_base": False,
        "price_index": 1.18,
        "locale": "pt_BR",
        "free_ship_threshold_local": 250,
        "warehouses": ["FC-CJM"],
        "monthly_orders_start": 1150,
        "monthly_orders_end": 2900,
    },
}

# landed-cost uplift by market (import duty + inbound freight on top of the USD unit cost).
# The US is the sourcing hub and ships duty-free; the other markets carry duty, which
# offsets their slightly higher local pricing. Net effect: gross margin lands in a tight
# 12–18% band across markets — an analytical talking point for the CFO view.
MARKET_COGS_FACTOR = {"US": 1.00, "UK": 1.06, "DE": 1.06, "BR": 1.13}

WAREHOUSES = {
    "FC-DAL": {"market": "US", "name": "Dallas, TX", "region": "South"},
    "FC-RNO": {"market": "US", "name": "Reno, NV", "region": "West"},
    "FC-BHX": {"market": "UK", "name": "Birmingham", "region": "West Midlands"},
    "FC-LEJ": {"market": "DE", "name": "Leipzig", "region": "Saxony"},
    "FC-CJM": {"market": "BR", "name": "Cajamar, SP", "region": "Sudeste"},
}

# --------------------------------------------------------------------------------------
# Currencies & FX (USD per 1 unit of currency)
# --------------------------------------------------------------------------------------

CURRENCIES = ["USD", "EUR", "GBP", "BRL"]
REPORTING_CURRENCY = "USD"

FX_ANCHORS = {           # USD value of 1 unit
    "USD": 1.00,
    "EUR": 1.08,
    "GBP": 1.26,
    "BRL": 0.192,
}
FX_DAILY_VOL = {         # std dev of daily log-return
    "USD": 0.0,
    "EUR": 0.004,
    "GBP": 0.004,
    "BRL": 0.008,
}
FX_MEAN_REVERSION = 0.02  # pull back toward anchor each day

# --------------------------------------------------------------------------------------
# Product catalog
# --------------------------------------------------------------------------------------
# gross_margin      : target blended gross margin for the category (drives unit cost)
# return_rate       : share of units returned
# warranty_eligible : protection plan can be attached
# share             : share of order *lines* (not revenue) — accessories dominate volume,
#                     phones/laptops dominate revenue because of price
# Prices are sampled skewed toward the low end of the range (few flagships, many cheap
# models) and SKU pick within a category is popularity-weighted ~ 1/price.

CATEGORIES = {
    "Smartphones": {
        "subcategories": ["Flagship", "Mid-range", "Budget"],
        "brands": ["Nformo", "Kestrel", "Auxo", "Rivon"],
        "price_usd": (140, 1050),
        "gross_margin": 0.17,
        "return_rate": 0.12,
        "warranty_eligible": True,
        "share": 0.13,
    },
    "Laptops & Tablets": {
        "subcategories": ["Ultrabooks", "Gaming Laptops", "Tablets", "2-in-1"],
        "brands": ["Vantark", "Kestrel", "Lumeno", "Corebit"],
        "price_usd": (240, 1900),
        "gross_margin": 0.18,
        "return_rate": 0.10,
        "warranty_eligible": True,
        "share": 0.10,
    },
    "Audio": {
        "subcategories": ["Headphones", "Earbuds", "Speakers", "Soundbars"],
        "brands": ["Sonance", "Auxo", "Bassford", "Lumeno"],
        "price_usd": (18, 380),
        "gross_margin": 0.37,
        "return_rate": 0.09,
        "warranty_eligible": False,
        "share": 0.19,
    },
    "Gaming": {
        "subcategories": ["Consoles", "Controllers", "VR", "Games"],
        "brands": ["Rivon", "Playcore", "Vantark", "Nformo"],
        "price_usd": (14, 520),
        "gross_margin": 0.19,
        "return_rate": 0.08,
        "warranty_eligible": True,
        "share": 0.12,
    },
    "Smart Home": {
        "subcategories": ["Hubs", "Cameras", "Lighting", "Thermostats"],
        "brands": ["Homeon", "Kestrel", "Lumeno", "Corebit"],
        "price_usd": (20, 280),
        "gross_margin": 0.33,
        "return_rate": 0.07,
        "warranty_eligible": False,
        "share": 0.10,
    },
    "Wearables": {
        "subcategories": ["Smartwatches", "Fitness Bands"],
        "brands": ["Kestrel", "Auxo", "Pulsera", "Nformo"],
        "price_usd": (32, 520),
        "gross_margin": 0.30,
        "return_rate": 0.11,
        "warranty_eligible": True,
        "share": 0.08,
    },
    "Accessories": {
        "subcategories": ["Cables", "Chargers", "Cases", "Storage", "Power Banks"],
        "brands": ["Corebit", "Auxo", "Voltix", "Bassford"],
        "price_usd": (6, 120),
        "gross_margin": 0.50,
        "return_rate": 0.05,
        "warranty_eligible": False,
        "share": 0.28,
    },
}
PRICE_SKEW_BETA = (1.5, 3.0)     # beta(a,b) exponent on (hi/lo) — mass near the low end
SKU_POPULARITY_EXP = 0.6         # basket SKU pick weight ~ (1 / price) ** this

N_PRODUCTS = 300
PRODUCT_DISCONTINUE_RATE = 0.15   # share of SKUs retired at some point in the window
WARRANTY_ATTACH_RATE = 0.08       # of eligible orders
WARRANTY_PRICE_PCT = 0.12         # protection plan price as % of item price
WARRANTY_COST_PCT = 0.35          # cost of servicing the plan as % of its price

ACCESSORY_BASKET_PROB = {         # P(add an accessory) given a primary category
    "Smartphones": 0.55,
    "Laptops & Tablets": 0.45,
    "Gaming": 0.50,
    "Audio": 0.20,
    "Smart Home": 0.25,
    "Wearables": 0.30,
    "Accessories": 0.10,
}

# --------------------------------------------------------------------------------------
# Order shaping
# --------------------------------------------------------------------------------------

ORDER_LINES_WEIGHTS = {1: 0.55, 2: 0.27, 3: 0.11, 4: 0.05, 5: 0.02}
UNITS_PER_LINE_WEIGHTS = {1: 0.86, 2: 0.10, 3: 0.03, 4: 0.01}

# deeper seasonality: soft Q1, mid-year sale (Jul), back-to-school (Sep), big Q4
SEASONALITY_BY_MONTH = {
    1: 0.72, 2: 0.78, 3: 0.93, 4: 0.86, 5: 0.98, 6: 1.03,
    7: 1.20, 8: 1.02, 9: 1.12, 10: 1.18, 11: 2.05, 12: 1.66,
}
DOW_MULTIPLIER = {0: 1.10, 1: 1.12, 2: 1.05, 3: 1.02, 4: 0.98, 5: 0.85, 6: 0.90}  # Mon=0
BLACK_FRIDAY_MULT = 3.4      # applied to the BF/CyberMonday stretch
BF_WINDOW_DAYS = 5

DEMAND_WAVE_AMPLITUDE = 0.13   # slow sinusoidal swing on top of the growth ramp
DEMAND_WAVE_PERIOD_M = 6.5     # months per wave cycle
DEMAND_MONTH_NOISE = 0.10     # month-to-month random noise (std)
DEMAND_HOT_MONTH_P = 0.06     # chance of an above-trend spike month
DEMAND_SOFT_MONTH_P = 0.06    # chance of a below-trend soft month (stockout / slow)

COMPARABLE_BASE_MOM_GROWTH = 0.022   # underlying month-over-month growth, US baseline

# Promotional periods -> higher discount depth & order volume
PROMO_PERIODS = [
    ("2024-07-08", "2024-07-14", "Mid-Year Sale 2024", 0.14),
    ("2024-11-25", "2024-12-02", "Black Friday / Cyber Monday 2024", 0.18),
    ("2024-12-20", "2024-12-26", "Holiday Countdown 2024", 0.12),
    ("2025-03-17", "2025-03-23", "Spring Tech Days 2025", 0.11),
    ("2025-07-07", "2025-07-13", "Mid-Year Sale 2025", 0.15),
    ("2025-11-24", "2025-12-01", "Black Friday / Cyber Monday 2025", 0.19),
    ("2025-12-19", "2025-12-25", "Holiday Countdown 2025", 0.12),
    ("2026-03-16", "2026-03-22", "Spring Tech Days 2026", 0.11),
]
BASE_DISCOUNT_RATE = 0.06          # everyday promotional discount depth
DISCOUNT_ORDER_SHARE = 0.45       # share of orders that carry any discount (non-promo)

# --------------------------------------------------------------------------------------
# Customers
# --------------------------------------------------------------------------------------

N_CUSTOMERS_TARGET = 90000
RETURNING_ORDER_SHARE_START = 0.34   # share of orders from existing customers, window start
RETURNING_ORDER_SHARE_END = 0.54     # ... window end (base matures)
RETURNING_SHARE_WAVE_AMP = 0.11      # oscillation so new vs returning revenue weave / cross repeatedly
RETURNING_SHARE_WAVE_PERIOD_M = 6.0
PRE_WINDOW_CUSTOMER_SHARE = 0.22     # US customers acquired before the extract window
CUSTOMER_EMAIL_NULL_RATE = 0.02
CUSTOMER_DUP_ROW_RATE = 0.015
MARKETING_CONSENT_RATE = 0.62

SEGMENTS = {"Consumer": 0.78, "Prosumer": 0.16, "SMB": 0.06}
LOYALTY_TIERS = ["Standard", "Silver", "Gold"]   # assigned in curated from spend

ACQUISITION_CHANNEL_SHARE = {   # start-of-window mix; Organic/Email/Direct grow over time
    "Paid Search": 0.30,
    "Paid Social": 0.24,
    "Organic Search": 0.14,
    "Direct": 0.10,
    "Email": 0.06,
    "Affiliate": 0.09,
    "Display": 0.05,
    "Referral": 0.02,
}
CHANNEL_MIX_DRIFT = {           # additive change to share across the full window
    "Paid Search": -0.06,
    "Paid Social": -0.04,
    "Organic Search": +0.05,
    "Direct": +0.03,
    "Email": +0.03,
    "Affiliate": -0.01,
    "Display": -0.01,
    "Referral": +0.01,
}

# --------------------------------------------------------------------------------------
# Channels (web + attribution) — conversion-rate multipliers vs the market baseline CR
# --------------------------------------------------------------------------------------

BASELINE_CONVERSION_RATE = 0.019
CHANNEL_CR_MULT = {
    "Paid Search": 1.05,
    "Paid Social": 0.75,
    "Organic Search": 1.20,
    "Direct": 1.55,
    "Email": 1.70,
    "Affiliate": 1.10,
    "Display": 0.45,
    "Referral": 1.25,
}
DEVICE_SHARE = {"Mobile": 0.62, "Desktop": 0.31, "Tablet": 0.07}
DEVICE_CR_MULT = {"Mobile": 0.80, "Desktop": 1.45, "Tablet": 1.00}
BOUNCE_RATE_RANGE = (0.34, 0.55)
PAGES_PER_SESSION_RANGE = (3.0, 6.0)
ADD_TO_CART_RATE_RANGE = (0.08, 0.14)
WEB_MISSING_DAY_RATE = 0.015

# --------------------------------------------------------------------------------------
# Marketing spend
# --------------------------------------------------------------------------------------

TARGET_MER = 10.0
TARGET_MER_START = 6.5   # marketing efficiency ramps up over the window
TARGET_MER_END = 14.0   # (brand builds, organic grows) -> spend falls from ~16% to ~7% of revenue                       # Net Revenue / total marketing spend (blended)
PAID_SPEND_SHARE = {                   # split of paid media budget
    "Paid Search": 0.44,
    "Paid Social": 0.34,
    "Display": 0.12,
    "Affiliate": 0.10,                 # commission, booked in other_marketing_spend
}
AFFILIATE_COMMISSION_PCT = 0.08
EMAIL_TOOLING_MONTHLY_USD = {"US": 2200, "UK": 900, "DE": 900, "BR": 700}
CPM_RANGE_USD = {"Paid Search": (0, 0), "Paid Social": (6, 14), "Display": (2, 6)}
CPC_RANGE_USD = {"Paid Search": (0.55, 1.70), "Paid Social": (0.35, 1.10), "Display": (0.15, 0.55)}
CTR_RANGE = {"Paid Search": (0.03, 0.07), "Paid Social": (0.008, 0.02), "Display": (0.003, 0.008)}
CAC_INFLATION_OVER_WINDOW = 0.0       # media gets ~15% less efficient end vs start

# --------------------------------------------------------------------------------------
# Payment methods
# --------------------------------------------------------------------------------------
# base_share is renormalised over methods available in each market; drift is additive over
# the window (e.g. Pix grows, Amex shrinks).

PAYMENT_METHODS = [
    # name                group          scheme       mdr    fixed  settle  inst  maxN  markets                 base_share  drift
    ("Visa Credit",       "Card",        "Visa",       0.022, 0.00,  4,     True, 12,  ["US", "UK", "DE", "BR"], 0.24,     -0.02),
    ("Visa Debit",        "Card",        "Visa",       0.011, 0.00,  3,     False, 1,  ["US", "UK", "DE", "BR"], 0.14,     -0.01),
    ("Mastercard Credit", "Card",        "Mastercard", 0.022, 0.00,  4,     True, 12,  ["US", "UK", "DE", "BR"], 0.18,     -0.01),
    ("Mastercard Debit",  "Card",        "Mastercard", 0.011, 0.00,  3,     False, 1,  ["US", "UK", "DE", "BR"], 0.10,      0.00),
    ("Amex",              "Card",        "Amex",       0.034, 0.00,  6,     True,  6,  ["US", "UK"],             0.09,     -0.03),
    ("Elo Credit",        "Card",        "Elo",        0.026, 0.00,  4,     True, 12,  ["BR"],                   0.20,     -0.02),
    ("Hipercard Credit",  "Card",        "Hipercard",  0.028, 0.00,  4,     True, 12,  ["BR"],                   0.08,      0.00),
    ("PayPal",            "Digital Wallet", None,      0.029, 0.30,  1,     False, 1,  ["US", "UK", "DE"],       0.11,      0.00),
    ("Apple Pay",         "Digital Wallet", None,      0.020, 0.00,  3,     False, 1,  ["US", "UK", "DE", "BR"], 0.06,     +0.03),
    ("Google Pay",        "Digital Wallet", None,      0.020, 0.00,  3,     False, 1,  ["US", "UK", "DE", "BR"], 0.04,     +0.02),
    ("Klarna",            "BNPL",        None,         0.045, 0.30,  2,     True,  4,  ["UK", "DE"],             0.07,     +0.04),
    ("Clearpay",          "BNPL",        None,         0.045, 0.30,  2,     True,  4,  ["UK"],                   0.03,     +0.02),
    ("SEPA Direct Debit", "Bank Transfer", None,       0.008, 0.25,  3,     False, 1,  ["DE"],                   0.14,      0.00),
    ("Pix",               "Pix",         None,         0.0045, 0.00, 0,     False, 1,  ["BR"],                   0.22,     +0.10),
    ("Boleto Bancario",   "Boleto",      None,         0.0,   3.49,  3,     False, 1,  ["BR"],                   0.10,     -0.03),
]
BOLETO_UNPAID_RATE = 0.12             # boletos never paid -> order cancelled
INSTALLMENT_INTEREST_FREE_MAX = 6     # up to 6x "sem juros" (merchant funded)
MERCHANT_FINANCING_MONTHLY_PCT = 0.018
BR_INSTALLMENT_ORDER_SHARE = 0.78     # BR credit-card orders that are instalment plans
BR_INSTALLMENT_N_WEIGHTS = {2: 0.12, 3: 0.18, 4: 0.14, 6: 0.24, 10: 0.14, 12: 0.18}

# --------------------------------------------------------------------------------------
# Suppliers & procurement
# --------------------------------------------------------------------------------------

N_SUPPLIERS = 15
SUPPLIER_TERMS_DAYS = [30, 45, 60]
SUPPLIER_TERMS_WEIGHTS = [0.45, 0.35, 0.20]
SUPPLIER_LEAD_TIME_RANGE = (7, 45)
SUPPLIER_ONTIME_RANGE = (0.82, 0.98)
SUPPLIER_COUNTRIES = ["CN", "VN", "MY", "KR", "TW", "MX", "US", "DE"]
TARGET_WEEKS_OF_COVER = 3         # planning cover for the PO engine (keeps DIO in a sane band)
PO_PAY_DELAY_RANGE = (-2, 5)          # days around the payment-due date
COST_DRIFT_MONTHLY_STD = 0.006       # supplier unit-cost random walk (std of monthly step)
COST_MEAN_REVERSION = 0.15
COST_SCALE_IMPROVEMENT_MONTHLY = 0.004   # unit costs drift down ~0.4%/mo (better sourcing terms)           # pull unit cost back toward its base each month
PO_MIN_PAIR_DEMAND = 20              # only stock a SKU/market pair selling >= this many units
PO_CASE_PACK = 10                    # POs rounded up to a multiple of this

# --------------------------------------------------------------------------------------
# Logistics
# --------------------------------------------------------------------------------------

CARRIERS = {
    "US": [("UPS", 3.4, 0.94), ("FedEx", 3.1, 0.93), ("USPS", 4.0, 0.90)],
    "UK": [("Royal Mail", 3.0, 0.92), ("DPD", 2.6, 0.95), ("Evri", 3.6, 0.87)],
    "DE": [("DHL", 2.8, 0.95), ("Hermes", 3.5, 0.88), ("DPD", 2.9, 0.93)],
    "BR": [("Correios", 4.8, 0.83), ("Jadlog", 4.3, 0.88), ("Loggi", 3.8, 0.90)],
}
SHIP_COST_PER_ORDER_USD = (5.0, 15.0)
PROMISED_DAYS_BUFFER = 2              # promised date = expected transit + buffer (affects the late flag only, not delivery time)
SLIGHTLY_LATE_SHARE = 0.055          # seeded slice of orders whose promise is pulled in so they land 1-2 days late
                                     # -> on-time settles near ~95% with many small misses (avg delivery days unchanged)
PEAK_DELAY_INFLATION = 1.06           # Q4 transit-time multiplier (kept gentle: monthly avg stays in the 4-5 day band)

# --------------------------------------------------------------------------------------
# Returns & support
# --------------------------------------------------------------------------------------

RETURN_REASONS = {
    "Defective / not working": 0.28,
    "Changed my mind": 0.24,
    "Not as described": 0.15,
    "Found better price": 0.12,
    "Arrived late": 0.08,
    "Wrong item shipped": 0.07,
    "Damaged in transit": 0.06,
}
RETURN_RESTOCK_SHARE = 0.55          # returned units put back into sellable stock
RETURN_LAG_DAYS_RANGE = (2, 30)

SUPPORT_TICKET_PER_ORDER_RATE = 0.14
SUPPORT_CATEGORIES = {
    "Where is my order": 0.30,
    "Return / refund": 0.22,
    "Product question": 0.16,
    "Damaged / defective": 0.13,
    "Billing / payment": 0.10,
    "Account / login": 0.05,
    "Other": 0.04,
}
SUPPORT_PRIORITY = {"Low": 0.5, "Medium": 0.35, "High": 0.15}
SUPPORT_RES_HOURS_RANGE = (1, 96)
SUPPORT_FCR_RATE = 0.74
CSAT_RANGE = (1, 5)

# --------------------------------------------------------------------------------------
# Targets / plan
# --------------------------------------------------------------------------------------

# The plan is a real growth plan, not "actual + noise": current-year months are planned as
# the prior-year actual grown by PLAN_YOY_GROWTH; pre-CY months (no in-window PY) are
# planned close to actual. Actuals then land a bit above the plan (revenue is growing
# faster than planned), with month-to-month swing from PLAN_MONTH_NOISE.
PLAN_YOY_GROWTH = 0.40                    # planned YoY growth for CY months (actual runs a touch ahead)
PLAN_MONTH_NOISE = 0.12                   # +/- swing on the monthly plan
PRE_CY_ATTAINMENT_RANGE = (0.96, 1.07)    # pre-CY months: plan ~ actual (slight miss/beat)
TARGET_METRICS = ["Net Revenue", "Orders", "New Customers", "Blended CAC", "Gross Margin %"]

# --------------------------------------------------------------------------------------
# Injected data-quality noise (raw layer only)
# --------------------------------------------------------------------------------------

DQ = {
    "order_line_dup_rate": 0.005,
    "order_missing_customer_rate": 0.003,
    "negative_qty_rate": 0.002,
    "psp_unmatched_rate": 0.010,
    "order_without_psp_rate": 0.004,
    "product_category_typo_rate": 0.30,     # share of product rows using a non-canonical spelling
    "sku_missing_from_master_rate": 0.02,   # order SKUs absent from the ERP master
    "inventory_snapshot_variance_rate": 0.03,
    "latin1_encoding_rows": 400,            # BR rows written as latin-1 in one file
    "web_negative_sessions_rate": 0.003,
}

CATEGORY_TYPOS = {
    "Smartphones": ["smart phones", "Smart-Phones", "SMARTPHONES"],
    "Laptops & Tablets": ["Laptops and Tablets", "laptops & tablets", "Laptop/Tablet"],
    "Audio": ["audio", "AUDIO", "Audio "],
    "Gaming": ["gaming", "Games & Gaming", "GAMING"],
    "Smart Home": ["smart home", "Smart-Home", "SmartHome"],
    "Wearables": ["wearables", "Wearable Tech", "WEARABLES"],
    "Accessories": ["accessories", "Accessory", "ACCESSORIES"],
}
