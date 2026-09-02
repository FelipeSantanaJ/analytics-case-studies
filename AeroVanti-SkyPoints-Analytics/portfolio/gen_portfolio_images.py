"""Generate 5 portfolio / gallery images (1600x820) for the AeroVanti SkyPoints case study.

  01_cover.png          branded title card  (upload FIRST -> becomes the thumbnail)
  02_ab_effect.png      Flash Redemption effect by tier (forest), framed + takeaway
  03_novelty.png        weekly novelty decay, framed + takeaway
  04_hoarding.png       redemption reach + liability trajectory, framed + takeaway
  05_deliverables.png   board summary + deep dive, mocked as stacked sheets

Reads the PNGs from ../data_analysis/outputs/figures/.  python portfolio/gen_portfolio_images.py
"""
from __future__ import annotations
import pathlib

import matplotlib.image as mpimg
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Rectangle

HERE = pathlib.Path(__file__).resolve().parent
FIG = HERE.parent / "data_analysis" / "outputs" / "figures"

NAVY, INK, AMBER, BLUE, PAGE, MUTE = "#0A2A43", "#12212E", "#E08A1E", "#0B5FA5", "#EEF3F8", "#6C7A87"
W, H, DPI = 1600, 820, 100
plt.rcParams["font.family"] = "DejaVu Sans"
plt.rcParams["text.parse_math"] = False


def canvas():
    fig = plt.figure(figsize=(W / DPI, H / DPI), dpi=DPI)
    ax = fig.add_axes([0, 0, 1, 1]); ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis("off")
    return fig, ax


def framed(chart_png, kicker, takeaway, out):
    fig, ax = canvas()
    ax.add_patch(Rectangle((0, 0.87), 1, 0.13, color=NAVY, zorder=1))
    ax.add_patch(Rectangle((0, 0.866), 1, 0.005, color=AMBER, zorder=2))
    ax.text(0.035, 0.958, "AEROVANTI SKYPOINTS  ·  FLASH REDEMPTION A/B TEST READ-OUT",
            color="#9EB6CC", fontsize=9, fontweight="bold", va="top")
    ax.text(0.965, 0.958, "SQL + Python · parity-checked", color="#9EB6CC", fontsize=9,
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
                 boxstyle="round,pad=0.006,rounding_size=0.012", fc=PAGE, ec="#D3DBE3", lw=1, zorder=1))
    ax.text(0.5, 0.069, takeaway, color=INK, fontsize=12, va="center", ha="center", zorder=2)
    fig.savefig(HERE / out, dpi=DPI); plt.close(fig); print("wrote", out)


def cover():
    fig, ax = canvas()
    ax.add_patch(Rectangle((0, 0), 1, 1, color=INK))
    ax.add_patch(Rectangle((0, 0.985), 1, 0.03, color=AMBER))
    ax.text(0.07, 0.82, "A I R L I N E   L O Y A L T Y   ·   A / B   T E S T   R E A D - O U T",
            color=AMBER, fontsize=12, fontweight="bold")
    ax.text(0.07, 0.66, "AeroVanti SkyPoints", color="white", fontsize=44, fontweight="bold")
    ax.text(0.07, 0.57, "Should Flash Redemption roll out — and to whom?", color="#C9D6E2",
            fontsize=19)
    for i, (k, v) in enumerate([
        ("Redemption-rate lift", "+2.7 pp pooled  ·  +3.2 pp re-weighted"),
        ("Where it works", "Blue + Silver  (interaction p = 0.0007)"),
        ("Durable effect", "≈ +1.5 pp  (half the headline is a launch bump)"),
        ("Guardrails", "disengagement −2.0 pp  ·  redemptions shallower −R$19"),
    ]):
        y = 0.42 - i * 0.083
        ax.add_patch(Rectangle((0.07, y - 0.005), 0.006, 0.055, color=AMBER))
        ax.text(0.093, y + 0.037, k, color="#8FA6BC", fontsize=11, fontweight="bold", va="top")
        ax.text(0.093, y + 0.008, v, color="white", fontsize=15, va="top")
    ax.text(0.07, 0.045, "Synthetic seeded data  ·  medallion ETL → semantic model → Power BI → "
            "dual-track analysis", color="#7C93A9", fontsize=10.5)
    fig.savefig(HERE / "01_cover.png", dpi=DPI); plt.close(fig); print("wrote 01_cover.png")


def deliverables():
    fig, ax = canvas()
    ax.add_patch(Rectangle((0, 0), 1, 1, color=PAGE))
    ax.add_patch(Rectangle((0, 0.87), 1, 0.13, color=NAVY))
    ax.add_patch(Rectangle((0, 0.866), 1, 0.005, color=AMBER))
    ax.text(0.035, 0.94, "TWO DELIVERABLES", color="white", fontsize=16, fontweight="bold", va="top")
    ax.text(0.035, 0.90, "decision-first board summary  +  exhaustive dual-track deep dive",
            color="#9EB6CC", fontsize=10.5, va="top")
    for i, (title, lines) in enumerate([
        ("board_summary.pdf", ["Recommendation: roll out to Blue + Silver",
                               "+2.7 pp lift · concentrated in low tiers",
                               "guardrails: 1 favourable, 1 watch", "one chart per point"]),
        ("deep_dive_A / B.md", ["8 findings · SQL + Python parity",
                                "SRM + balance · power · CI · interaction",
                                "novelty decay · heterogeneity",
                                "hoarding funnel · liability sensitivity"]),
    ]):
        x = 0.09 + i * 0.46
        for d in (0.02, 0.012, 0.0):
            ax.add_patch(FancyBboxPatch((x + d, 0.12 - d), 0.36, 0.62,
                         boxstyle="round,pad=0.004,rounding_size=0.01",
                         fc="white", ec="#D3DBE3", lw=1))
        ax.add_patch(Rectangle((x, 0.70), 0.36, 0.04, color=NAVY))
        ax.text(x + 0.015, 0.72, title, color="white", fontsize=11, fontweight="bold", va="center")
        for j, ln in enumerate(lines):
            ax.text(x + 0.02, 0.63 - j * 0.075, "•  " + ln, color=INK, fontsize=10.5, va="top")
    ax.text(0.035, 0.05, "Every number computed twice — pandas + DuckDB — and asserted equal.",
            color=MUTE, fontsize=10.5)
    fig.savefig(HERE / "05_deliverables.png", dpi=DPI); plt.close(fig); print("wrote 05_deliverables.png")


if __name__ == "__main__":
    cover()
    framed("06_forest.png", "The effect is concentrated in the lower tiers",
           "Blue +3.8 pp and Silver +2.2 pp are significant; Gold and Platinum are not. "
           "Arm x tier interaction p = 0.0007 — the gradient is real.", "02_ab_effect.png")
    framed("05_novelty.png", "Roughly half the headline is a launch bump",
           "The weekly treatment-control increment trends down (-0.044 pp/week, p = 0.017). "
           "Durable effect ~ +1.5 pp — the number for the business case.", "03_novelty.png")
    framed("07_hoarding.png", "Why it matters: members hoard, and it costs",
           "Only 32% of active members have ever redeemed; the co-brand card issues 55% of "
           "all points. Point liability R$25.7M, +/- R$2.6M per 10 pp of breakage assumption.",
           "04_hoarding.png")
    deliverables()
    print("\n5 portfolio images -> portfolio/")
