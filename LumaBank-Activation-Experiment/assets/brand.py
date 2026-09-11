"""
LumaBank visual identity — the single source of truth for colour and type.

Imported by assets/gen_logo.py (Phase 5) and powerbi/gen_report_visuals.py (Phase 8)
so the logo, page backgrounds, theme, and every scripted visual override draw from
the same values.

Identity brief
--------------
Trust-first fintech, not a marketing page — this is an incident read-out and an
experiment integrity monitor as much as a dashboard. Deliberately **not** blue
(AeroVanti, VoltEdge) and not violet or forest green (Voxa+, SwiftBite): the brand
colour is a deep **petrol / teal-ink** — cool and steady without being "just another
bank blue" — paired with a single warm **coral** accent (treatment arm / current
period / "look here" / the break) against a **stone** comparison colour (control arm
/ prior period). Warm-neutral ground, not the cool blue-grey of the sibling projects.
One signature element on every page: a petrol header band with the wordmark, a coral
hairline under it, the page title, then the content on the 3-30-300 gradient.
"""

# ---- core palette -------------------------------------------------------
PETROL       = "#0E4A52"   # brand / primary series / tableAccent
PETROL_DEEP  = "#0A333A"   # header band, darkest ink on light
PETROL_TINT  = "#E3EEEC"   # faint brand wash (selected slicer, hover)
CORAL        = "#E2624B"   # single accent — treatment arm, current period, the break
STONE        = "#93A29C"   # comparison — control arm, prior period, target

# extended categorical ramp (channels, regions, KYC outcomes, cohorts)
DATA_COLORS = [PETROL, STONE, CORAL, "#C99A3E", "#7A5C7E", "#5B6B72",
               "#C77C6E", "#3B5B73"]

# acquisition-channel ramp (paid_social / organic / app_store_search / referral / influencer)
CHANNEL_COLORS = {
    "paid_social": "#3B5B73", "organic": PETROL, "app_store_search": "#7A5C7E",
    "referral": "#C99A3E", "influencer": "#C77C6E", "unknown": "#9AA0A0",
}

# experiment-arm ramp — used everywhere an arm legend appears
ARM_COLORS = {"control": STONE, "treatment": CORAL, "ambiguous": "#B9B4A8"}

# SRM alert-state ramp
ALERT_COLORS = {"ok": "#3C8073", "warn": "#C99A3E", "alert": "#C0453B"}

# ---- neutrals & ground ------------------------------------------------
PAGE_BG        = "#F3F1EC"   # warm off-white — not AeroVanti/VoltEdge's cool blue-grey
CARD_BG        = "#FFFFFF"
NEUTRAL_FILL   = "#E7E3DA"
GRIDLINE       = "#E9E5DC"
HAIRLINE       = "#D8D2C4"

# ---- semantic --------------------------------------------------------
GOOD    = "#3C8073"   # teal-green (distinct from SwiftBite's forest green #1E6B4F)
BAD     = "#C0453B"
NEUTRAL = "#8A8F8A"
BRIDGE_UP    = GOOD
BRIDGE_DOWN  = BAD
BRIDGE_TOTAL = PETROL

# diverging scale (conditional formatting: guardrail deltas, vs-target)
DIV_MIN = "#C0453B"
DIV_MID = "#EDE3CF"
DIV_MAX = "#3C8073"

# ---- text ----------------------------------------------------------
INK_TITLE     = "#17211F"
INK_BODY      = "#3A4441"
INK_MUTED     = "#6E7A76"
ON_DARK       = "#F1F6F4"
ON_DARK_MUTED = "#BFCAC6"

FONT_SEMI  = "Segoe UI Semibold"
FONT_REG   = "Segoe UI"
FONT_LIGHT = "Segoe UI Light"

# ---- layout constants (px, 1280-wide canvas) ------------------------
CANVAS_W = 1280
PAGE_H_STANDARD = 720
PAGE_H_EXEC = 860
BAND_H = 58
HAIRLINE_H = 3

PAGE_TITLES = {
    "01_executive": ("Executive Overview",
                     "Is new-user activation healthy, and did the (re-run) onboarding "
                     "experiment conclude?"),
    "02_funnel": ("Onboarding & Activation Funnel",
                  "Where do new users drop between signup, KYC and first transaction?"),
    "03_integrity": ("Experiment Integrity Monitor",
                      "Can the experiment be trusted — allocation, SRM, contamination?"),
    "04_readout": ("Experiment Readout",
                   "Did the re-run onboarding work, safely, for every channel?"),
}


def hex_to_rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))
