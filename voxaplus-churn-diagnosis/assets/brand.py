"""
Voxa+ visual identity — the single source of truth for colour and type.

Imported by assets/gen_logo.py (Phase 5) and etl/gen_report_visuals.py (Phase 8)
so the logo, the page backgrounds, the theme, and every scripted visual override
draw from the same values.

Identity brief
--------------
Corporate, restrained, board-facing. Media-adjacent (a streaming service) but not
flashy — this is a churn diagnosis for the board, not a marketing page.
One brand colour, one accent (attention / current period), one comparison colour
(prior year / target). Muted neutrals, quiet gridlines. One signature element on
every page: a deep-violet header band with the wordmark, an amber hairline under
it, then the page title with the Currency + Market slicers, an Analysis-Period
slicer, a row of six KPI cards, then two content rows (3-30-300).
"""

# ---- core palette -------------------------------------------------------
VIOLET        = "#4B2E83"   # brand / primary series / tableAccent
VIOLET_DEEP   = "#241348"   # header band, darkest ink on light
VIOLET_TINT   = "#EDE9F5"   # faint brand wash (selected slicer, hover)
AMBER         = "#E6A23C"   # single accent — current period, "look here"
STEEL         = "#5B7FB0"   # comparison — prior year, target, secondary series

# extended categorical ramp (channels, tiers, markets, genres)
DATA_COLORS = [VIOLET, STEEL, AMBER, "#3E9C93", "#8E5EA8", "#6B7280",
               "#C77CA6", "#4C6EA6"]

# ---- neutrals & ground ------------------------------------------------
PAGE_BG        = "#F2F1F7"   # page background (light body)
CARD_BG        = "#FFFFFF"
NEUTRAL_FILL   = "#E5E3EF"   # bar "rest", disabled
GRIDLINE       = "#E7E5EF"
HAIRLINE       = "#D9D6E4"

# ---- semantic (churn is lower-is-better in most contexts) ------------
GOOD    = "#2E7D5B"
BAD     = "#C0453B"
NEUTRAL = "#8A8A99"
# waterfall / bridge sentiment (matches KPI delta colours)
BRIDGE_UP   = GOOD
BRIDGE_DOWN = BAD
BRIDGE_TOTAL = VIOLET

# diverging scale (conditional formatting: retention, vs-target)
DIV_MIN = "#C0453B"
DIV_MID = "#EFC48A"
DIV_MAX = "#2E7D5B"

# ---- text ----------------------------------------------------------
INK_TITLE  = "#1E1A33"
INK_BODY   = "#3A3646"
INK_MUTED  = "#77738A"
ON_DARK    = "#F4F2FA"
ON_DARK_MUTED = "#C6BEDD"

FONT_SEMI = "Segoe UI Semibold"
FONT_REG  = "Segoe UI"
FONT_LIGHT = "Segoe UI Light"

# ---- layout constants (px, 1280-wide canvas) ------------------------
CANVAS_W = 1280
PAGE_H_STANDARD = 720
PAGE_H_EXEC = 900
BAND_H = 60          # header band height
HAIRLINE_H = 3       # amber rule under the band

PAGE_TITLES = {
    "01_executive":      ("Executive Summary",
                          "How bad is the churn spike, and is it still going?"),
    "02_retention":      ("Subscriber Retention and Cohorts",
                          "Which cohorts, tenures, plans and sources are churning?"),
    "03_engagement":     ("Content and Engagement",
                          "Did viewing drop before people cancelled?"),
    "04_pricing":        ("Pricing and Plans",
                          "Did a price or plan change trigger it?"),
    "05_acquisition":    ("Acquisition Quality and Channels",
                          "Did the quality of who we acquire shift?"),
    "06_experience":     ("Customer Experience, Billing and App Quality",
                          "Payment failures or app problems forcing people out?"),
    "07_market":         ("Market Context",
                          "Is this global, or concentrated in one market?"),
}


def hex_to_rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))
