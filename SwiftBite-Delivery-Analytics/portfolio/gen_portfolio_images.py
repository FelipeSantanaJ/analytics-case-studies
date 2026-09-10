"""Generate the 5 portfolio / gallery images (1600x820) for the SwiftBite Delivery case study.

  gallery_1_dashboard.png   branded cover with the headline result (upload FIRST -> thumbnail)
  gallery_2_pipeline.png    the medallion ETL pipeline (6 systems -> raw -> staging -> curated)
  gallery_3_model.png       the curated star schema (dims around the zone-hour / zone-day facts)
  gallery_4_dax.png         key DAX measures, rendered as code cards
  gallery_5_report.png      the 4-page report structure — one business question per page

    python portfolio/gen_portfolio_images.py
"""
from __future__ import annotations

import pathlib
import sys

import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch, Rectangle

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "assets"))
import brand as B  # noqa: E402

GREEN, DEEP, TANG, STONE = B.GREEN, B.GREEN_DEEP, B.TANGERINE, B.STONE
INK, PAGE, MUTE, LINE = B.INK_TITLE, B.PAGE_BG, B.INK_MUTED, B.HAIRLINE
W, H, DPI = 1600, 820, 100
plt.rcParams["font.family"] = "DejaVu Sans"
plt.rcParams["text.parse_math"] = False


def canvas(bg=PAGE):
    fig = plt.figure(figsize=(W / DPI, H / DPI), dpi=DPI)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis("off")
    ax.add_patch(Rectangle((0, 0), 1, 1, color=bg, zorder=-1))
    return fig, ax


def band(ax, kicker, title):
    ax.add_patch(Rectangle((0, 0.88), 1, 0.12, color=DEEP, zorder=1))
    ax.add_patch(Rectangle((0, 0.876), 1, 0.005, color=TANG, zorder=2))
    ax.text(0.035, 0.958, kicker, color="#B7C7BD", fontsize=9, fontweight="bold", va="top")
    ax.text(0.965, 0.958, "SwiftBite Delivery  ·  Marketplace Analytics", color="#B7C7BD",
            fontsize=9, fontweight="bold", va="top", ha="right", style="italic")
    ax.text(0.035, 0.918, title, color="white", fontsize=16, fontweight="bold", va="top")


def box(ax, x, y, w, h, text, fc="white", ec=LINE, tc=INK, fs=10.5, bold=False):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.004,rounding_size=0.012",
                                fc=fc, ec=ec, lw=1.2, zorder=3))
    ax.text(x + w / 2, y + h / 2, text, color=tc, fontsize=fs, ha="center", va="center",
            zorder=4, fontweight="bold" if bold else "normal", wrap=True)


def arrow(ax, x0, y0, x1, y1, color=STONE):
    ax.add_patch(FancyArrowPatch((x0, y0), (x1, y1), arrowstyle="-|>", mutation_scale=16,
                                 color=color, lw=1.6, zorder=2))


# --------------------------------------------------------------------------- #
def cover():
    fig, ax = canvas(INK)
    ax.add_patch(Rectangle((0, 0.985), 1, 0.03, color=TANG))
    ax.text(0.07, 0.83, "M A R K E T P L A C E   ·   S U P P L Y - S I D E   E X P E R I M E N T",
            color=TANG, fontsize=12, fontweight="bold")
    ax.text(0.07, 0.68, "SwiftBite Delivery", color="white", fontsize=44, fontweight="bold")
    ax.text(0.07, 0.59, "Does a zone-hour courier incentive fix supply-short liquidity —"
            " and is it worth it?", color="#C6D5CD", fontsize=18)
    rows = [
        ("Fulfillment lift", "+1.87 pp   (cluster CI [+1.27, +2.46] · RI p = 3e-4 · wild-boot agrees)"),
        ("Where it works", "supply-short + balanced zones   (arm x tier interaction p = 0.004)"),
        ("Side effect", "neighbour-zone drag ~17%  ·  not statistically significant"),
        ("The catch (G1)", "R$ 281 per incremental delivered order  vs  R$ 10 margin  ->  don't ship the flat bonus"),
    ]
    for i, (k, v) in enumerate(rows):
        y = 0.44 - i * 0.086
        ax.add_patch(Rectangle((0.07, y - 0.004), 0.006, 0.058, color=TANG))
        ax.text(0.093, y + 0.04, k, color="#8FB0A3", fontsize=11, fontweight="bold", va="top")
        ax.text(0.093, y + 0.010, v, color="white", fontsize=13.5, va="top")
    ax.text(0.07, 0.045, "Synthetic seeded data  ·  medallion ETL -> semantic model (TMDL) -> "
            "4-page Power BI report -> dual-track zone-day read-out", color="#7C9A8D", fontsize=10.5)
    fig.savefig(HERE / "gallery_1_dashboard.png", dpi=DPI); plt.close(fig)
    print("wrote gallery_1_dashboard.png")


def pipeline():
    fig, ax = canvas()
    band(ax, "DATA ENGINEERING", "Seeded medallion pipeline — one SEED, fully reproducible")
    srcs = ["OrderCore\norders · status", "RiderApp\nsessions · offers", "Trace\nGPS pings",
            "Dispatch\nassignment funnel", "PayHub\npayments · payouts", "Boost\nincentive campaigns"]
    for i, s in enumerate(srcs):
        box(ax, 0.03, 0.74 - i * 0.115, 0.20, 0.09, s, fc="white", fs=9)
    box(ax, 0.30, 0.30, 0.14, 0.42, "raw/\nmessy exports\n(8 DQ classes)", fc="#EDEFEA", fs=9.5)
    box(ax, 0.48, 0.30, 0.14, 0.42, "staging/\ntyped · parsed\ndeduped · tz-fixed", fc="#E7EFEA", fs=9.5)
    box(ax, 0.66, 0.24, 0.15, 0.54, "curated/\nKimball star\ndim + fact\nzone-hour spine\nzone-day tables",
        fc=GREEN, tc="white", fs=9.5, bold=True)
    box(ax, 0.84, 0.34, 0.13, 0.34, "data_analysis/\nSQL + Python\nparity-checked\nread-out",
        fc=DEEP, tc="white", fs=9.5, bold=True)
    for i in range(6):
        arrow(ax, 0.23, 0.785 - i * 0.115, 0.30, 0.51)
    arrow(ax, 0.44, 0.51, 0.48, 0.51)
    arrow(ax, 0.62, 0.51, 0.66, 0.51)
    arrow(ax, 0.81, 0.51, 0.84, 0.51, color=GREEN)
    ax.text(0.5, 0.06, "01_generate_raw  ->  02_clean_stage  ->  03_build_curated  ->  dq_checks "
            "(13/13 hard checks pass, 0 warnings)", color=MUTE, fontsize=10.5, ha="center")
    fig.savefig(HERE / "gallery_2_pipeline.png", dpi=DPI); plt.close(fig)
    print("wrote gallery_2_pipeline.png")


def model():
    fig, ax = canvas()
    band(ax, "DATA MODELLING", "Curated star — TMDL, generated from code · 15 tables · 28 relationships")
    box(ax, 0.34, 0.52, 0.15, 0.13, "fact_zone_hour\nliquidity spine", fc=GREEN, tc="white", fs=9.5, bold=True)
    box(ax, 0.52, 0.52, 0.15, 0.13, "fact_experiment\n_zone_day  (~840)", fc=GREEN, tc="white", fs=9.5, bold=True)
    box(ax, 0.34, 0.34, 0.15, 0.12, "fact_order\nfact_delivery", fc="#E7EFEA", fs=9.5)
    box(ax, 0.52, 0.34, 0.15, 0.12, "fact_courier\n_shift_block", fc="#E7EFEA", fs=9.5)
    dims = [("dim_zone\n(+ adjacency bridge)", 0.06, 0.66), ("dim_time_block\n(peak flag)", 0.06, 0.44),
            ("dim_date\n(experiment phase/week)", 0.06, 0.22), ("dim_courier", 0.78, 0.66),
            ("dim_incentive_campaign", 0.78, 0.44), ("dim_customer · dim_restaurant", 0.78, 0.22)]
    for txt, x, y in dims:
        box(ax, x, y, 0.16, 0.11, txt, fc="white", fs=9)
        arrow(ax, x + 0.16 if x < 0.5 else x, y + 0.055, 0.34 if x < 0.5 else 0.67,
              0.52 if y > 0.4 else 0.40)
    ax.text(0.5, 0.06, "fact_order role-plays dim_zone x3 (dropoff-current active) · all facts "
            "join dim_date[date_key] · adjacency drives the cannibalisation measures",
            color=MUTE, fontsize=10, ha="center")
    fig.savefig(HERE / "gallery_3_model.png", dpi=DPI); plt.close(fig)
    print("wrote gallery_3_model.png")


def dax():
    fig, ax = canvas()
    band(ax, "SEMANTIC LAYER", "DAX measure library — 69 measures, generated into TMDL")
    cards = [
        ("Fulfillment Lift (pp)", "( [Fulfillment (Treated) %] - [Fulfillment (Control) %] ) * 100"),
        ("Fulfillment Lift SE (pp)", "SQRT ( DIVIDE(VAR.S_t, n_t) + DIVIDE(VAR.S_c, n_c) ) * 100"),
        ("G1 Incentive Cost per Incremental Order", "DIVIDE ( [Incentive Spend - Experiment (BRL)],\n"
         "         [Incremental Delivered Orders] )"),
        ("Cannibalisation - Adjacent-Control Gap (pp)", "( AVG(ff | control & adjacent-to-treated)\n"
         "  - AVG(ff | control & not adjacent) ) * 100"),
        ("Liquidity Ratio", "DIVIDE ( [Available Courier-Hours], [Demanded Courier-Hours] )"),
        ("Exec Insight", "\"Fulfillment \" & FORMAT(lift,\"+0.0\") & \" pp\" & IF(sig,\" (95%)\",\"\")\n"
         " & \" · cost/incr order R$ \" & FORMAT(g1,\"0.00\") & IF(g1<cm,\" — below\",\" — above\") & \" margin\""),
    ]
    for i, (name, code) in enumerate(cards):
        x = 0.035 + (i % 2) * 0.49
        y = 0.60 - (i // 2) * 0.245
        ax.add_patch(FancyBboxPatch((x, y), 0.455, 0.21, boxstyle="round,pad=0.006,rounding_size=0.012",
                                    fc="white", ec=LINE, lw=1.2))
        ax.add_patch(Rectangle((x, y + 0.165), 0.455, 0.045, color=GREEN))
        ax.text(x + 0.014, y + 0.187, name, color="white", fontsize=10, fontweight="bold", va="center")
        ax.text(x + 0.014, y + 0.078, code, color=INK, fontsize=8.3, va="center",
                family="DejaVu Sans Mono")
    ax.text(0.5, 0.055, "One source of truth in etl/pbi_measures.py -> injected into _Measures.tmdl "
            "-> rendered to docs/06_dax_measures.md", color=MUTE, fontsize=10, ha="center")
    fig.savefig(HERE / "gallery_4_dax.png", dpi=DPI); plt.close(fig)
    print("wrote gallery_4_dax.png")


def report():
    fig, ax = canvas()
    band(ax, "THE REPORT", "4 pages · one business question per page · Power BI as code (PBIR)")
    pages = [
        ("Executive Overview", "Is the marketplace healthy, and\ndid the incentive earn its cost?",
         "6 KPIs · fulfillment trend · Exec\nInsight · lift by tier · novelty"),
        ("Marketplace Health", "Where and when does liquidity\nbreak?",
         "fulfillment by zone · liquidity\nzone x daypart matrix · ETA by\nhour · cancels by cause"),
        ("Pricing & Incentive\nExperiment", "Real, safe, and not just\ncannibalising neighbours?",
         "lift by tier · fulfillment by arm ·\nnovelty curve · guardrail table"),
        ("Courier Economics", "Earnings, utilisation, elasticity\nto the bonus",
         "earnings by daypart · utilisation\nby zone · supply vs demand ·\ncost per order by tier"),
    ]
    for i, (title, q, viz) in enumerate(pages):
        x = 0.035 + i * 0.243
        ax.add_patch(FancyBboxPatch((x, 0.12), 0.225, 0.62, boxstyle="round,pad=0.006,rounding_size=0.012",
                                    fc="white", ec=LINE, lw=1.2))
        ax.add_patch(Rectangle((x, 0.685), 0.225, 0.055, color=DEEP))
        ax.text(x + 0.014, 0.712, title, color="white", fontsize=9.5, fontweight="bold", va="center")
        ax.text(x + 0.014, 0.60, q, color=TANG, fontsize=8.6, va="top", style="italic")
        ax.text(x + 0.014, 0.44, viz, color=INK, fontsize=8.4, va="top")
        ax.add_patch(Rectangle((x + 0.014, 0.15), 0.197, 0.006, color=TANG))
    ax.text(0.5, 0.055, "gen_report_visuals.py -> _report_layout.json -> pbir CLI -> "
            "SwiftBiteDelivery.Report (56 visuals · pbir validate passes)", color=MUTE,
            fontsize=10, ha="center")
    fig.savefig(HERE / "gallery_5_report.png", dpi=DPI); plt.close(fig)
    print("wrote gallery_5_report.png")


if __name__ == "__main__":
    cover(); pipeline(); model(); dax(); report()
    print("\n5 portfolio images -> portfolio/")
