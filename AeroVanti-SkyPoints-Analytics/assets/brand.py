"""
AeroVanti SkyPoints visual identity — the single source of truth for colour and type.

Imported by assets/gen_logo.py (Phase 5) and powerbi/gen_report_visuals.py (Phase 8)
so the logo, page backgrounds, theme, and every scripted visual override draw from
the same values.

Identity brief
--------------
Corporate, restrained, CFO-facing. Aviation-adjacent but not a marketing page — this
is an A/B test read-out and a program-health dashboard. One brand colour (AeroVanti
sky blue), one accent (amber — treatment arm / current period / "look here"), one
comparison colour (steel — control arm / prior year / target). Muted neutrals, quiet
gridlines. One signature element on every page: a navy header band with the wordmark,
an amber hairline under it, the page title, then the content on the 3-30-300 gradient.
"""

# ---- core palette -------------------------------------------------------
BLUE        = "#0B5FA5"   # brand / primary series / tableAccent
BLUE_DEEP   = "#0A2A43"   # header band, darkest ink on light
BLUE_TINT   = "#E4EEF6"   # faint brand wash (selected slicer, hover)
AMBER       = "#E08A1E"   # single accent — treatment arm, current period
STEEL       = "#5C8CB8"   # comparison — control arm, prior year, target

# extended categorical ramp (tiers, earn sources, regions, reward categories)
DATA_COLORS = [BLUE, STEEL, AMBER, "#3E9C93", "#8E5EA8", "#6B7280",
               "#C77CA6", "#4C6EA6"]

# tier ramp (Blue / Silver / Gold / Platinum) — used where a tier legend appears
TIER_COLORS = {"Blue": "#4C6EA6", "Silver": "#9AA6B2", "Gold": "#C9922E", "Platinum": "#5B6B7A"}

# ---- neutrals & ground ------------------------------------------------
PAGE_BG        = "#EEF3F8"
CARD_BG        = "#FFFFFF"
NEUTRAL_FILL   = "#E2E8EF"
GRIDLINE       = "#E4E9EF"
HAIRLINE       = "#D3DBE3"

# ---- semantic --------------------------------------------------------
GOOD    = "#2E7D5B"
BAD     = "#C0453B"
NEUTRAL = "#8A8A99"
BRIDGE_UP    = GOOD
BRIDGE_DOWN  = BAD
BRIDGE_TOTAL = BLUE

# diverging scale (conditional formatting: vs-target, lift)
DIV_MIN = "#C0453B"
DIV_MID = "#EAD6A8"
DIV_MAX = "#2E7D5B"

# ---- text ----------------------------------------------------------
INK_TITLE  = "#12212E"
INK_BODY   = "#33404B"
INK_MUTED  = "#6C7A87"
ON_DARK    = "#F1F6FB"
ON_DARK_MUTED = "#B9C8D6"

FONT_SEMI = "Segoe UI Semibold"
FONT_REG  = "Segoe UI"
FONT_LIGHT = "Segoe UI Light"

# ---- layout constants (px, 1280-wide canvas) ------------------------
CANVAS_W = 1280
PAGE_H_STANDARD = 786  # was 720; the KPI row (frame/slicer/cards, see
                       # gen_report_visuals.py) moved down to clear the header
                       # divider, pushing content rows down with it
PAGE_H_EXEC = 860      # unchanged -- already has enough slack (70px margin)
BAND_H = 58
HAIRLINE_H = 3

PAGE_TITLES = {
    "01_executive":  ("Executive Summary",
                      "Program health, and the Flash Redemption A/B test headline."),
    "02_tiers":      ("Member Tiers and Value",
                      "Points earned and redeemed, tier movement, and the breakage liability."),
    "03_experiment": ("A/B Test Results",
                      "Is the Flash Redemption effect real, safe on the guardrails, and consistent?"),
    "04_funnel":     ("Redemption and Engagement Funnel",
                      "Where members fall out of the redeem journey, and who is at risk of lapsing."),
}


def hex_to_rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))
