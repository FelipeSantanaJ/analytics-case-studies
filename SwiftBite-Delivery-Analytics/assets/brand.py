"""
SwiftBite Delivery visual identity — the single source of truth for colour and type.

Imported by assets/gen_logo.py (Phase 5), powerbi/gen_semantic_model.py /
gen_report_visuals.py (Phases 6/8) and data_analysis/deliverables/build_deliverables.py
(Phase 10) so the logo, page backgrounds, the theme.json, every scripted visual
override and the board deliverables all draw from the same values.

Identity brief
--------------
Corporate, restrained, operations- and finance-facing. Delivery-adjacent but not a
marketing page — this is a marketplace-liquidity diagnosis and a randomized
incentive-experiment read-out. One brand colour (forest green — "moving, fresh"),
one accent (tangerine — the treated zone / current period / "look here"), one
comparison colour (cool stone — the control arm / prior period / target). Warm-neutral
ground, quiet gridlines. One signature element on every page: a deep-green header band
with the wordmark, a tangerine hairline under it, the page title + its one business
question, then the content on the 3-30-300 gradient.
"""

# ---- core palette -------------------------------------------------------
GREEN        = "#1E6B4F"   # brand / primary series / tableAccent
GREEN_DEEP   = "#113A2C"   # header band, darkest ink on light
GREEN_TINT   = "#E4EFEA"   # faint brand wash (selected slicer, hover)
TANGERINE    = "#E8823C"   # single accent — treated zone, current period, "look here"
STONE        = "#8090A0"   # comparison — control arm, prior period, target, secondary series

# extended categorical ramp (zones, dayparts, cuisines, channels)
DATA_COLORS = [GREEN, STONE, TANGERINE, "#3E9C93", "#8E5EA8", "#C9922E",
               "#C77CA6", "#6B7280"]

# baseline supply-stress tier ramp — supply-short zones read "hot"
TIER_COLORS = {"short": "#E8823C", "balanced": "#8090A0", "long": "#1E6B4F"}

# experiment arm
ARM_COLORS = {"treatment": "#E8823C", "control": "#8090A0"}

# ---- neutrals & ground ------------------------------------------------
PAGE_BG        = "#F2F4F1"   # warm-neutral, faintly green off-white
CARD_BG        = "#FFFFFF"
NEUTRAL_FILL   = "#E4E8E3"   # bar "rest", disabled
GRIDLINE       = "#E6E9E4"
HAIRLINE       = "#D6DAD3"

# ---- semantic (ETA, cancel rate, idle ratio, incentive cost = lower is better) ----
GOOD    = "#2E7D5B"
BAD     = "#C0453B"
NEUTRAL = "#8A8A99"
BRIDGE_UP    = GOOD
BRIDGE_DOWN  = BAD
BRIDGE_TOTAL = GREEN

# diverging scale (conditional formatting: vs-target, lift, spillover)
DIV_MIN = "#C0453B"
DIV_MID = "#EAD9C4"
DIV_MAX = "#2E7D5B"

# ---- text ----------------------------------------------------------
INK_TITLE  = "#17241E"
INK_BODY   = "#33403A"
INK_MUTED  = "#6B7A72"
ON_DARK    = "#F0F5F1"
ON_DARK_MUTED = "#B7C7BD"

FONT_SEMI  = "Segoe UI Semibold"
FONT_REG   = "Segoe UI"
FONT_LIGHT = "Segoe UI Light"

# ---- layout constants (px, 1280-wide canvas) ----------------------
CANVAS_W = 1280
PAGE_H_STANDARD = 780  # was 720; bumped to fit the KPI row below the header
                       # divider (y=144) without cards/sliders overlapping it
                       # or each other — see gen_report_visuals.py kpi_frame
PAGE_H_EXEC = 860
BAND_H = 58          # header band height
HAIRLINE_H = 3       # tangerine rule under the band

WORDMARK = "SwiftBite"
TAGLINE = "Marketplace Analytics"

PAGE_TITLES = {
    "01_executive":  ("Executive Overview",
                      "Is the marketplace healthy, and did the zone-hour incentive earn its cost?"),
    "02_health":     ("Marketplace Health",
                      "Where and when does liquidity break — fulfillment, ETA, idle supply vs unmet demand?"),
    "03_experiment": ("Pricing & Incentive Experiment",
                      "Is the incentive real, safe on the guardrails, and not just cannibalising neighbour zones?"),
    "04_courier":    ("Courier Economics",
                      "What do couriers earn, how utilised is supply, and how elastic is it to the bonus?"),
}


def hex_to_rgb(h: str) -> tuple[int, int, int]:
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))
