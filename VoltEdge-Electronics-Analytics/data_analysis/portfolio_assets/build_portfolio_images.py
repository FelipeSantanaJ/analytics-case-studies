"""Generate 5 portfolio images (1024x768, 4:3) for the VoltEdge case study.

  01_cover.png            branded title card  (upload FIRST -> becomes the thumbnail)
  02_growth.png           YoY growth waterfall, framed
  03_contribution.png     contribution-margin walk, framed
  04_cash.png             cash conversion cycle, framed
  05_deliverables.png     board summary + deep dive pages, mocked as stacked sheets
"""
from __future__ import annotations

import pathlib

import matplotlib.image as mpimg
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Rectangle

HERE = pathlib.Path(__file__).resolve().parent
FIG = HERE.parent / "outputs" / "figures"
DELIV = HERE.parent / "deliverables"

NAVY, INK, AMBER, BLUE, PAGE, MUTE = "#123E6E", "#10233F", "#D99311", "#2E70B0", "#EAEFF6", "#5B6B82"
W, H, DPI = 1024, 768, 100
plt.rcParams["font.family"] = "DejaVu Sans"
plt.rcParams["text.parse_math"] = False


def canvas():
    fig = plt.figure(figsize=(W / DPI, H / DPI), dpi=DPI)
    ax = fig.add_axes([0, 0, 1, 1]); ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis("off")
    return fig, ax


def framed(chart_png: str, kicker: str, takeaway: str, out: str):
    """A finding chart with a navy header + one-line takeaway."""
    fig, ax = canvas()
    ax.add_patch(Rectangle((0, 0.865), 1, 0.135, color=NAVY, zorder=1))
    ax.add_patch(Rectangle((0, 0.862), 1, 0.006, color=AMBER, zorder=2))
    ax.text(0.035, 0.957, "VOLTEDGE ELECTRONICS  ·  EXECUTIVE ANALYTICS REVIEW",
            color="#9DB4D0", fontsize=8.5, fontweight="bold", va="top")
    ax.text(0.965, 0.957, "SQL + Python · parity-checked", color="#9DB4D0", fontsize=8.5,
            fontweight="bold", va="top", ha="right", style="italic")
    ax.text(0.035, 0.918, kicker, color="white", fontsize=15.5, fontweight="bold", va="top")

    img = mpimg.imread(FIG / chart_png)
    ih, iw = img.shape[0], img.shape[1]
    top, bot = 0.845, 0.120                   # usable band: header bottom -> caption top
    wf = 0.94
    hf = wf * (iw and ih / iw) * (W / H)
    if hf > top - bot:                        # scale down to fit, keep aspect
        wf *= (top - bot) / hf; hf = top - bot
    xf = (1 - wf) / 2
    yf = bot + (top - bot - hf) / 2           # vertically centre in the band
    ax_i = fig.add_axes([xf, yf, wf, hf]); ax_i.axis("off")
    ax_i.imshow(img)

    ax.add_patch(FancyBboxPatch((0.035, 0.030), 0.93, 0.080,
                 boxstyle="round,pad=0.006,rounding_size=0.012",
                 fc=PAGE, ec="#D3DCEA", lw=1, zorder=1))
    ax.text(0.5, 0.070, takeaway, color=INK, fontsize=11.5, va="center", ha="center", zorder=2)
    fig.savefig(HERE / out, dpi=DPI)
    plt.close(fig)
    print("wrote", out)


# ---------- 01 cover ----------
def cover():
    fig, ax = canvas()
    ax.add_patch(Rectangle((0, 0), 1, 1, color=INK))
    ax.add_patch(Rectangle((0, 0.995), 1, 0.02, color=AMBER))
    ax.text(0.07, 0.80, "E X E C U T I V E   A N A L Y T I C S   R E V I E W", color=AMBER,
            fontsize=13, fontweight="bold")
    ax.text(0.07, 0.685, "VoltEdge Electronics", color="white", fontsize=44, fontweight="bold")
    ax.text(0.07, 0.60, "DTC electronics retailer  ·  24-month, multi-market star schema",
            color="#C4D2E6", fontsize=13.5)
    ax.text(0.07, 0.558, "Every metric built twice — SQL (DuckDB) and Python (pandas), reconciled to the cent",
            color="#8FA6C4", fontsize=11.5)

    chips = [
        ("+137% / +40%", "YoY — total vs US like-for-like"),
        ("$4.4M", "cash trapped in inventory"),
        ("break-even", "contribution margin (CY)"),
        ("10", "parity-checked findings"),
    ]
    x0, w, gap = 0.07, 0.205, 0.017
    for i, (big, small) in enumerate(chips):
        x = x0 + i * (w + gap)
        ax.add_patch(FancyBboxPatch((x, 0.30), w, 0.17,
                     boxstyle="round,pad=0.004,rounding_size=0.02",
                     fc="#1B335A", ec="#2C4A78", lw=1))
        ax.text(x + w / 2, 0.408, big, color="white", fontsize=16.5, fontweight="bold", ha="center")
        ax.text(x + w / 2, 0.345, small, color="#A9BCD6", fontsize=8.7, ha="center")

    ax.text(0.07, 0.16, "Growth · margin · working capital · marketing/CAC · retention · returns · fulfilment",
            color="#C4D2E6", fontsize=11)
    ax.text(0.07, 0.075, "DuckDB   ·   pandas   ·   matplotlib   ·   Power BI",
            color=AMBER, fontsize=11, fontweight="bold")
    fig.savefig(HERE / "01_cover.png", dpi=DPI)
    plt.close(fig)
    print("wrote 01_cover.png")


# ---------- 05 deliverables ----------
def deliverables():
    import pymupdf
    pages = []
    for name, idx in [("board_summary.pdf", 0), ("board_summary.pdf", 2), ("deep_dive.pdf", 2)]:
        d = pymupdf.open(DELIV / name)
        pix = d[idx].get_pixmap(dpi=150)
        p = HERE / f"_tmp_{name}_{idx}.png"
        pix.save(p); pages.append(p); d.close()

    fig, ax = canvas()
    ax.add_patch(Rectangle((0, 0), 1, 1, color=PAGE))
    ax.add_patch(Rectangle((0, 0.865), 1, 0.135, color=NAVY))
    ax.add_patch(Rectangle((0, 0.862), 1, 0.006, color=AMBER))
    ax.text(0.035, 0.955, "VOLTEDGE ELECTRONICS  ·  EXECUTIVE ANALYTICS REVIEW",
            color="#9DB4D0", fontsize=8.5, fontweight="bold", va="top")
    ax.text(0.035, 0.918, "Client-ready deliverables — board summary + deep dive",
            color="white", fontsize=15.5, fontweight="bold", va="top")

    # three sheets fanned, back to front, with a soft drop shadow
    specs = [(0.485, 0.30, 0.30), (0.335, 0.235, 0.315), (0.135, 0.145, 0.335)]  # x, y, width
    for (x, y, w), img_path in zip(specs, reversed(pages)):
        im = mpimg.imread(img_path)
        ih, iw = im.shape[0], im.shape[1]
        h = w * (ih / iw) * (W / H)
        ax.add_patch(Rectangle((x + 0.007, y - 0.012), w, h, color="#0e234012", zorder=1))
        axi = fig.add_axes([x, y, w, h]); axi.axis("off"); axi.imshow(im, zorder=2)
        axi.add_patch(Rectangle((0, 0), 1, 1, transform=axi.transAxes, fill=False,
                                ec="#B9C6DA", lw=1.2, zorder=3))

    ax.text(0.035, 0.055,
            "Decision-first board summary  ·  exhaustive deep dive (method on both tracks, evidence, "
            "limitations, recommendations)  ·  themed to the client's reporting identity  ·  reproducible scripts",
            color=INK, fontsize=9.6, va="center", wrap=True)
    fig.savefig(HERE / "05_deliverables.png", dpi=DPI)
    plt.close(fig)
    for p in pages:
        p.unlink(missing_ok=True)
    print("wrote 05_deliverables.png")


cover()
framed("2026-09_02_yoy_growth_waterfall.png",
       "Is the growth real, or just new markets opening?",
       "+137% headline, but 77% is expansion — the core US business grew +40% and missed plan.",
       "02_growth.png")
framed("2026-09_03_contribution_margin.png",
       "Can VoltEdge afford its growth?",
       "At break-even after marketing, shipping & payments (+$325k CY vs −$365k PY). UK the only loss-maker.",
       "03_contribution.png")
framed("2026-09_06_cash_conversion_cycle.png",
       "Where is the cash going?",
       "Cash conversion cycle ≈134 days — ~$4.4M frozen in inventory (DIO 158d vs a 45–75 benchmark).",
       "04_cash.png")
deliverables()
print("\nUpload order: 01_cover.png first (thumbnail), then 02–05.")
