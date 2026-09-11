"""Generate 5 portfolio / gallery images (1600x820) for the LumaBank case study.

  01_cover.png            branded title card  (upload FIRST -> becomes the thumbnail)
  02_the_break.png        SRM alert timeline, framed + takeaway
  03_fallback_bias.png    post-deploy regional bias, framed + takeaway
  04_heterogeneity.png    clean re-run effect by channel, framed + takeaway
  05_deliverables.png     board summary + deep dive, mocked as stacked sheets

Reads the PNGs from ../data_analysis/outputs/figures/.  python portfolio/gen_portfolio_images.py
"""
from __future__ import annotations
import pathlib
import sys

import matplotlib.image as mpimg
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Rectangle

HERE = pathlib.Path(__file__).resolve().parent
FIG = HERE.parent / "data_analysis" / "outputs" / "figures"
sys.path.insert(0, str(HERE.parent))
from assets.brand import PETROL, PETROL_DEEP, PETROL_TINT, CORAL, STONE, PAGE_BG  # noqa: E402

INK, MUTE = "#12211F", "#5B6B67"
W, H, DPI = 1600, 820, 100
plt.rcParams["font.family"] = "DejaVu Sans"
plt.rcParams["text.parse_math"] = False


def canvas():
    fig = plt.figure(figsize=(W / DPI, H / DPI), dpi=DPI)
    ax = fig.add_axes([0, 0, 1, 1]); ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis("off")
    return fig, ax


def framed(chart_png, kicker, takeaway, out):
    fig, ax = canvas()
    ax.add_patch(Rectangle((0, 0.87), 1, 0.13, color=PETROL_DEEP, zorder=1))
    ax.add_patch(Rectangle((0, 0.866), 1, 0.005, color=CORAL, zorder=2))
    ax.text(0.035, 0.958, "LUMABANK  ·  DAY-7 ACTIVATION EXPERIMENT — THE INCIDENT READ-OUT",
            color="#9FC2BC", fontsize=9, fontweight="bold", va="top")
    ax.text(0.965, 0.958, "SQL + Python · parity-checked", color="#9FC2BC", fontsize=9,
            fontweight="bold", va="top", ha="right", style="italic")
    ax.text(0.035, 0.918, kicker, color="white", fontsize=16, fontweight="bold", va="top")

    img = mpimg.imread(FIG / chart_png)
    ih, iw = img.shape[0], img.shape[1]
    top, bot = 0.85, 0.13
    wf = 0.9
    hf = wf * (ih / iw) * (W / H)
    if hf > top - bot:
        wf *= (top - bot) / hf; hf = top - bot
    xf = (1 - wf) / 2
    yf = bot + (top - bot - hf) / 2
    axi = fig.add_axes([xf, yf, wf, hf]); axi.axis("off"); axi.imshow(img)

    ax.add_patch(FancyBboxPatch((0.035, 0.028), 0.93, 0.082,
                 boxstyle="round,pad=0.006,rounding_size=0.012", fc=PAGE_BG, ec="#D8D2C4", lw=1, zorder=1))
    ax.text(0.5, 0.069, takeaway, color=INK, fontsize=12, va="center", ha="center", zorder=2)
    fig.savefig(HERE / out, dpi=DPI); plt.close(fig); print("wrote", out)


def cover():
    fig, ax = canvas()
    ax.add_patch(Rectangle((0, 0), 1, 1, color=PETROL_DEEP))
    ax.add_patch(Rectangle((0, 0.985), 1, 0.03, color=CORAL))
    ax.text(0.07, 0.82, "F I N T E C H   O N B O A R D I N G   ·   A / B   T E S T   R E A D - O U T",
            color=CORAL, fontsize=12, fontweight="bold")
    ax.text(0.07, 0.66, "LumaBank Activation", color="white", fontsize=44, fontweight="bold")
    ax.text(0.07, 0.57, "The experiment that broke mid-flight — and how it was rescued",
            color="#CFE0DC", fontsize=19)
    for i, (k, v) in enumerate([
        ("Day-7 Activation lift (clean re-run)", "+4.58 pp  ·  95% CI [+2.55, +6.62]  ·  p = 1.0e-5"),
        ("The break", "SRM ALERT 2026-07-18, 2 days after a mobile deploy corrupts randomisation"),
        ("The call", "restart clean in a shorter window — truncate/exclude MDEs couldn't be trusted"),
        ("Guardrails", "KYC rejection: non-inferior  ·  flagged fraud: NOT established"),
    ]):
        y = 0.42 - i * 0.083
        ax.add_patch(Rectangle((0.07, y - 0.005), 0.006, 0.055, color=CORAL))
        ax.text(0.093, y + 0.037, k, color="#8FB3AB", fontsize=11, fontweight="bold", va="top")
        ax.text(0.093, y + 0.008, v, color="white", fontsize=15, va="top")
    ax.text(0.07, 0.045, "Synthetic seeded data  ·  medallion ETL -> semantic model -> Power BI -> "
            "dual-track analysis", color="#7C9A93", fontsize=10.5)
    fig.savefig(HERE / "01_cover.png", dpi=DPI); plt.close(fig); print("wrote 01_cover.png")


def deliverables():
    fig, ax = canvas()
    ax.add_patch(Rectangle((0, 0), 1, 1, color=PAGE_BG))
    ax.add_patch(Rectangle((0, 0.87), 1, 0.13, color=PETROL_DEEP))
    ax.add_patch(Rectangle((0, 0.866), 1, 0.005, color=CORAL))
    ax.text(0.035, 0.94, "TWO DELIVERABLES", color="white", fontsize=16, fontweight="bold", va="top")
    ax.text(0.035, 0.90, "decision-first board summary  +  exhaustive dual-track deep dive",
            color="#9FC2BC", fontsize=10.5, va="top")
    for i, (title, lines) in enumerate([
        ("board_summary.pdf", ["Recommendation: monitored rollout,",
                               "fraud circuit-breaker attached",
                               "+4.58 pp lift · guardrail split shown",
                               "one chart per point"]),
        ("deep_dive.pdf", ["5 findings · SQL + Python parity",
                           "SRM monitoring · root cause · decision",
                           "day-by-day incident timeline",
                           "power/MDE recomputed for the re-run"]),
    ]):
        x = 0.09 + i * 0.46
        for d in (0.02, 0.012, 0.0):
            ax.add_patch(FancyBboxPatch((x + d, 0.12 - d), 0.36, 0.62,
                         boxstyle="round,pad=0.004,rounding_size=0.01",
                         fc="white", ec="#D8D2C4", lw=1))
        ax.add_patch(Rectangle((x, 0.70), 0.36, 0.04, color=PETROL_DEEP))
        ax.text(x + 0.015, 0.72, title, color="white", fontsize=11, fontweight="bold", va="center")
        for j, ln in enumerate(lines):
            ax.text(x + 0.02, 0.63 - j * 0.075, "•  " + ln, color=INK, fontsize=10.5, va="top")
    ax.text(0.035, 0.05, "Every number computed twice — pandas + DuckDB — and asserted equal.",
            color=MUTE, fontsize=10.5)
    fig.savefig(HERE / "05_deliverables.png", dpi=DPI); plt.close(fig); print("wrote 05_deliverables.png")


if __name__ == "__main__":
    cover()
    framed("02_srm_break.png", "The daily SRM check catches it two days after the deploy",
           "Trailing-7d p-value crosses the 0.001 ALERT threshold on 2026-07-18; the cumulative "
           "test never gets there — diluted by 10 clean pre-deploy days. Both tests exist for a reason.",
           "02_the_break.png")
    framed("03_fallback_bias.png", "The fallback doesn't just skew the split — it skews it by region",
           "Southeast signups land 76.5% in treatment after the deploy; the North lands 35.3%. "
           "A single pooled SRM number would have hidden this geography.", "03_fallback_bias.png")
    framed("05_heterogeneity_forest.png", "The clean re-run: a real lift, concentrated where designed",
           "+4.58 pp overall, clears the recomputed 2.92 pp MDE. paid_social's +6.2 pp is individually "
           "significant; the formal channel-interaction test (p=0.52) isn't — yet.", "04_heterogeneity.png")
    deliverables()
    print("\n5 portfolio images -> portfolio/")
