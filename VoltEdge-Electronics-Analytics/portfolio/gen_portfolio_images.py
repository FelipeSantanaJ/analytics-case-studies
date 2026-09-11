"""Generate 5 portfolio / gallery images (3200x1640) for the VoltEdge Electronics case study.

  01_dashboard_executive_summary.png   branded title card (upload FIRST -> becomes the thumbnail)
  02_pipeline_raw_to_refined.png       medallion ETL pipeline diagram
  03_bus_matrix.png                    dimensional model bus matrix (facts x dims)
  04_dax_semantic_layer.png            167-measure DAX library — folders + signature measures
  05_report_structure.png              7-page report map, one question per page

Same brand header (bolt + VOLTEDGE wordmark + divider + page title + rule) as the report
page backgrounds in `etl/gen_logo.py` — reproduced here so the portfolio images stay a
self-contained script.  python portfolio/gen_portfolio_images.py
"""
from __future__ import annotations
import pathlib

from PIL import Image, ImageDraw, ImageFont

HERE = pathlib.Path(__file__).resolve().parent

NAVY = (14, 42, 78, 255)          # #0E2A4E
BLUE = (46, 112, 176, 255)        # #2E70B0
DEEP = (18, 62, 110, 255)         # #123E6E
AMBER = (217, 147, 17, 255)       # #D99311
INK = (18, 33, 46, 255)           # #12212E
MUTE = (100, 112, 127, 255)       # #64707F
LINE = (220, 228, 239, 255)       # #DCE4EF
FILL = (234, 239, 246, 255)       # #EAEFF6
WHITE = (255, 255, 255, 255)
KICKER_BLUE = (158, 182, 204, 255)

W, H = 3200, 1640

FONT_DIR = pathlib.Path(r"C:\Windows\Fonts")
F_SEMIBOLD = FONT_DIR / "seguisb.ttf"
F_REGULAR = FONT_DIR / "segoeui.ttf"
F_BOLD = FONT_DIR / "segoeuib.ttf"
F_ITALIC = FONT_DIR / "segoeuii.ttf"


def font(path: pathlib.Path, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(path), size)


def canvas(bg=FILL) -> tuple[Image.Image, ImageDraw.ImageDraw]:
    img = Image.new("RGB", (W, H), bg)
    return img, ImageDraw.Draw(img)


def bolt(d: ImageDraw.ImageDraw, x: float, y: float, w: float, h: float, fill) -> None:
    """A chunky lightning bolt inside the (x, y, w, h) box (matches etl/gen_logo.py)."""
    pts = [
        (0.56, 0.00), (0.16, 0.56), (0.44, 0.56), (0.34, 1.00),
        (0.84, 0.40), (0.54, 0.40), (0.70, 0.00),
    ]
    d.polygon([(x + px * w, y + py * h) for px, py in pts], fill=fill)


def header(d: ImageDraw.ImageDraw, title: str, kicker: str, band_h: int = 190) -> None:
    d.rectangle([0, 0, W, band_h], fill=NAVY)
    d.rectangle([0, band_h - 8, W, band_h], fill=BLUE)

    icon_h, icon_w = 62, 45
    ix, iy = 55, (band_h - icon_h) // 2 - 4
    bolt(d, ix, iy, icon_w, icon_h, WHITE)

    x = ix + icon_w + 26
    wm = font(F_BOLD, 46)
    d.text((x, (band_h - 46) // 2 - 6), "VOLT", font=wm, fill=WHITE)
    vb = d.textlength("VOLT", font=wm)
    d.text((x + vb, (band_h - 46) // 2 - 6), "EDGE", font=wm, fill=(174, 202, 230, 255))
    x += vb + d.textlength("EDGE", font=wm) + 32

    d.line([(x, 30), (x, band_h - 40)], fill=(120, 145, 180, 255), width=2)
    x += 32

    t = font(F_SEMIBOLD, 40)
    d.text((x, (band_h - 40) // 2 - 6), title, font=t, fill=(226, 235, 246, 255))

    k = font(F_SEMIBOLD, 20)
    kw = d.textlength(kicker, font=k)
    d.text((W - 55 - kw, 40), kicker, font=k, fill=KICKER_BLUE)


def footer_strip(img: Image.Image, d: ImageDraw.ImageDraw, items: list[tuple[str, str]],
                  y: int, h: int = 150) -> None:
    d.rectangle([55, y, W - 55, y + h], fill=NAVY)
    n = len(items)
    colw = (W - 110) / n
    tt = font(F_BOLD, 26)
    tb = font(F_REGULAR, 22)
    for i, (title, body) in enumerate(items):
        x = 55 + i * colw + 45
        d.text((x, y + 35), title, font=tt, fill=WHITE)
        wrapped = wrap(body, tb, colw - 90, d)
        for j, line in enumerate(wrapped[:2]):
            d.text((x, y + 78 + j * 30), line, font=tb, fill=(196, 212, 232, 255))


def wrap(text: str, f: ImageFont.FreeTypeFont, maxw: float, d: ImageDraw.ImageDraw) -> list[str]:
    words, lines, cur = text.split(), [], ""
    for w_ in words:
        trial = (cur + " " + w_).strip()
        if d.textlength(trial, font=f) <= maxw:
            cur = trial
        else:
            lines.append(cur); cur = w_
    if cur:
        lines.append(cur)
    return lines


def rounded(d: ImageDraw.ImageDraw, box, radius=16, fill=WHITE, outline=LINE, width=2) -> None:
    d.rounded_rectangle(box, radius=radius, fill=fill, outline=outline, width=width)


def save(img: Image.Image, name: str) -> None:
    img.save(HERE / name)
    print(f"  wrote {name}  {img.size[0]}x{img.size[1]}")


# ---------------------------------------------------------------- 01 cover ---
def cover() -> None:
    img, d = canvas(bg=NAVY)
    d.rectangle([0, 0, W, 10], fill=BLUE)

    k = font(F_SEMIBOLD, 26)
    d.text((110, 150), "C O N S U M E R   E L E C T R O N I C S   ·   E X E C U T I V E   A N A L Y T I C S",
            font=k, fill=BLUE)

    h1 = font(F_BOLD, 96)
    d.text((105, 260), "VoltEdge Electronics", font=h1, fill=WHITE)

    sub = font(F_REGULAR, 38)
    d.text((110, 400), "Is the business actually growing, is it profitable,", font=sub, fill=(201, 214, 226, 255))
    d.text((110, 448), "and where is cash and margin leaking?", font=sub, fill=(201, 214, 226, 255))

    stats = [
        ("Net Revenue", "$31.35M over 24 months"),
        ("Growth", "+137% total  ·  only +40% US like-for-like"),
        ("The real constraint", "~134-day cash conversion cycle  ·  ~$4.4M freeable"),
        ("Contribution margin", "reached break-even this period"),
    ]
    y0 = 610
    kt = font(F_BOLD, 24)
    vt = font(F_REGULAR, 34)
    for i, (kk, vv) in enumerate(stats):
        y = y0 + i * 165
        d.rectangle([110, y, 122, y + 105], fill=AMBER)
        d.text((150, y), kk, font=kt, fill=(143, 166, 188, 255))
        d.text((150, y + 40), vv, font=vt, fill=WHITE)

    ft = font(F_REGULAR, 24)
    d.text((110, H - 90),
            "Fictional company · synthetic seeded data · medallion ETL → semantic model → "
            "Power BI → dual-track analysis", font=ft, fill=(140, 160, 180, 255))
    save(img, "01_dashboard_executive_summary.png")


# -------------------------------------------------------------- 02 pipeline ---
def pipeline() -> None:
    img, d = canvas()
    header(d, "From raw exports to a BI-ready star schema", "MEDALLION ETL")

    kick = font(F_BOLD, 30)
    d.text((55, 235), "RAW  →  STAGING  →  CURATED  →  MODEL  →  REPORT", font=kick, fill=DEEP)

    stages = [
        ("Source systems", "12 simulated", (100, 112, 127, 255), [
            "Storefront / OMS, ERP, Procurement, WMS",
            "Payment processor, CRM, Support desk",
            "Web analytics, Google Ads, Meta Ads",
            "Carrier tracking, Finance (FX & targets)"]),
        ("Bronze", "data/raw/", (168, 122, 20, 255), [
            "Source-faithful analyst exports",
            "5 date formats + Excel serials",
            "Money strings, x3 category spellings",
            "Latin-1 file, missing SKUs, ledger drift"]),
        ("Silver", "data/staging/", (100, 112, 127, 255), [
            "20 typed stg_* tables",
            "Parse, type, de-duplicate, standardize",
            "Currency & category normalization",
            "Customer identity, PSP reconciliation"]),
        ("Gold", "data/curated/", (30, 110, 70, 255), [
            "Kimball star: 16 dims, 12 facts",
            "Moving-average COGS from PO receipts",
            "Installments exploded, snapshot from ledger",
            "Parquet + CSV, USD on every money column"]),
        ("Power BI", "semantic model", NAVY, [
            "28 tables, ~65 relationships",
            "167 DAX measures in 14 folders",
            "Multi-currency reporting selector",
            "7-page executive report"]),
    ]
    labels = ["01_generate_raw.py", "02_clean_stage.py", "03_build_curated.py", "gen_semantic_model.py"]

    n = len(stages)
    gap = 40
    cw = (W - 110 - gap * (n - 1)) / n
    y0, ch = 300, 900
    for i, (title, sub, band, bullets) in enumerate(stages):
        x = 55 + i * (cw + gap)
        rounded(d, [x, y0, x + cw, y0 + ch], radius=10)
        d.rectangle([x, y0, x + cw, y0 + 90], fill=band)
        tt = font(F_BOLD, 28)
        d.text((x + 26, y0 + 18), title, font=tt, fill=WHITE)
        st = font(F_REGULAR, 22)
        d.text((x + 26, y0 + 54), sub, font=st, fill=(230, 233, 238, 255))
        bt = font(F_REGULAR, 21)
        by = y0 + 130
        for b in bullets:
            d.ellipse([x + 26, by + 8, x + 34, by + 16], fill=DEEP)
            for j, line in enumerate(wrap(b, bt, cw - 80, d)):
                d.text((x + 46, by + j * 28), line, font=bt, fill=INK)
            by += 28 * len(wrap(b, bt, cw - 80, d)) + 38
        if i < n - 1:
            ax = x + cw + gap / 2
            d.polygon([(ax - 14, y0 + ch / 2 - 20), (ax + 16, y0 + ch / 2),
                       (ax - 14, y0 + ch / 2 + 20)], fill=(170, 185, 205, 255))
            lb = font(F_REGULAR, 15)
            tw = int(d.textlength(labels[i], font=lb)) + 6
            tag = Image.new("RGBA", (tw, 20), (0, 0, 0, 0))
            ImageDraw.Draw(tag).text((3, 0), labels[i], font=lb, fill=DEEP)
            tag = tag.rotate(90, expand=True)
            img.paste(tag, (int(ax - tag.width / 2), int(y0 + ch / 2 - 90 - tag.height)), tag)

    footer_strip(img, d, [
        ("Deterministic", "single seed in config.py — byte-identical re-runs"),
        ("DQ gate", "null keys, referential integrity, accounting identities, value bands — a violation fails the build"),
        ("~10 minutes", "full pipeline, raw to report"),
    ], y0 + ch + 40)
    save(img, "02_pipeline_raw_to_refined.png")


# ------------------------------------------------------------ 03 bus matrix ---
def bus_matrix() -> None:
    img, d = canvas()
    header(d, "Dimensional model — the bus matrix", "KIMBALL STAR SCHEMA")

    kick = font(F_BOLD, 26)
    d.text((55, 235), "WHICH DIMENSION TOUCHES WHICH FACT", font=kick, fill=DEEP)

    dims = ["date", "market", "customer", "product", "supplier", "channel",
            "campaign", "payment", "carrier", "warehouse", "currency"]
    facts = {
        "fact_order_lines":       {"date", "market", "customer", "product", "channel", "carrier", "warehouse", "currency"},
        "fact_orders":            {"date", "market", "customer", "channel", "payment", "carrier", "warehouse", "currency"},
        "fact_payment_schedule":  {"date", "market", "currency"},
        "fact_returns":           {"date", "market", "customer", "product", "currency"},
        "fact_purchase_orders":   {"date", "market", "product", "supplier", "warehouse"},
        "fact_inventory_movement": {"date", "market", "product", "warehouse"},
        "fact_inventory_snapshot": {"date", "market", "product", "warehouse"},
        "fact_marketing_spend":   {"date", "market", "channel", "campaign"},
        "fact_web_traffic_daily": {"date", "market", "channel"},
        "fact_support_tickets":   {"date", "market", "customer"},
        "fact_exchange_rate":     {"date", "currency"},
        "fact_target":            {"date", "market"},
    }

    x0, y0 = 55, 290
    labelw = 480
    colw = (W - 110 - labelw) / len(dims)
    rowh = 82
    headh = 110

    rounded(d, [x0, y0, W - 55, y0 + headh + rowh * len(facts)], radius=10)
    d.rectangle([x0, y0, x0 + labelw, y0 + headh], fill=DEEP)
    cf = font(F_SEMIBOLD, 19)
    for j, dim in enumerate(dims):
        cx = x0 + labelw + j * colw
        d.rectangle([cx, y0, cx + colw, y0 + headh], fill=NAVY)
        tw = int(d.textlength(dim, font=cf)) + 6
        lbl = Image.new("RGBA", (tw, 26), (0, 0, 0, 0))
        ImageDraw.Draw(lbl).text((3, 0), dim, font=cf, fill=WHITE)
        lbl = lbl.rotate(90, expand=True)
        img.paste(lbl, (int(cx + colw / 2 - lbl.width / 2), int(y0 + headh - 14 - lbl.height)), lbl)
    lf = font(F_SEMIBOLD, 21)
    d.text((x0 + labelw - 20, y0 + headh - 14), "fact rows / dimension columns", font=font(F_REGULAR, 15),
            fill=(210, 222, 236, 255), anchor="rb")

    for i, (fact, touches) in enumerate(facts.items()):
        ry = y0 + headh + i * rowh
        if i % 2:
            d.rectangle([x0, ry, W - 55, ry + rowh], fill=(244, 247, 251, 255))
        d.text((x0 + 28, ry + rowh / 2), fact, font=lf, fill=INK, anchor="lm")
        for j, dim in enumerate(dims):
            cx = x0 + labelw + j * colw + colw / 2
            if dim in touches:
                r = 13
                d.ellipse([cx - r, ry + rowh / 2 - r, cx + r, ry + rowh / 2 + r], fill=BLUE)
        d.line([x0, ry, W - 55, ry], fill=LINE, width=1)
    for j in range(len(dims) + 1):
        cx = x0 + labelw + j * colw if j < len(dims) else x0 + labelw
        d.line([cx, y0, cx, y0 + headh + rowh * len(facts)], fill=(255, 255, 255, 255) if j == len(dims) else LINE, width=1)

    ny = y0 + headh + rowh * len(facts) + 30
    bt = font(F_BOLD, 30)
    nt = font(F_REGULAR, 24)
    d.text((x0, ny), "16", font=bt, fill=DEEP)
    d.text((x0 + 60, ny + 4), "conformed dimensions", font=nt, fill=INK)
    d.text((x0 + 470, ny), "12", font=bt, fill=DEEP)
    d.text((x0 + 520, ny + 4), "fact tables", font=nt, fill=INK)
    d.text((x0 + 780, ny), "~65", font=bt, fill=DEEP)
    d.text((x0 + 860, ny + 4), "relationships", font=nt, fill=INK)
    note = ("One active dim_date join — ship / delivery / due / paid roles are inactive, "
            "switched on with USERELATIONSHIP")
    for k, line in enumerate(wrap(note, nt, 1100, d)):
        d.text((x0 + 1160, ny + k * 30), line, font=nt, fill=MUTE)
    save(img, "03_bus_matrix.png")


# -------------------------------------------------------- 04 DAX semantic layer ---
def dax_layer() -> None:
    img, d = canvas()
    header(d, "The semantic layer — 167 DAX measures", "MODEL AS CODE")

    folders = [
        ("01 Sales", 22), ("02 Time Intelligence", 15), ("03 Comparable Base", 7),
        ("04 Targets vs Plan", 18), ("05 Reporting Currency", 5), ("06 Payments & Cash", 14),
        ("07 Price / Volume / Mix", 7), ("08 Marketing & Acquisition", 16),
        ("09 Website & Funnel", 17), ("10 Logistics & Fulfillment", 10),
        ("11 Working Capital & Inventory", 15), ("12 CRM & Retention", 9),
        ("13 Support & Returns", 9), ("00 Selectors", 3),
    ]
    lk = font(F_BOLD, 28)
    d.text((55, 235), "14 DISPLAY FOLDERS", font=lk, fill=DEEP)

    colw, gap = (1550 - 30) / 2, 20
    cardh, vgap = 95, 22
    ft = font(F_SEMIBOLD, 24)
    ct = font(F_BOLD, 24)
    for i, (name, count) in enumerate(folders):
        col, row = i % 2, i // 2
        x = 55 + col * (colw + gap)
        y = 300 + row * (cardh + vgap)
        rounded(d, [x, y, x + colw, y + cardh])
        d.text((x + 32, y + cardh / 2), name, font=ft, fill=INK, anchor="lm")
        r = 34
        cx, cy = x + colw - 60, y + cardh / 2
        d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=BLUE)
        d.text((cx, cy), str(count), font=ct, fill=WHITE, anchor="mm")

    rk = font(F_BOLD, 28)
    rx0 = 55 + 1550 + 40
    d.text((rx0, 235), "SIGNATURE MEASURES", font=rk, fill=DEEP)
    measures = [
        ("Net Revenue (USD)", "Gross Sales (USD) − Returns (USD)"),
        ("Gross Profit (USD)", "Net Revenue − COGS + Returns COGS Recovered"),
        ("Contribution Margin (USD)", "Gross Profit − Marketing − Shipping Cost − Payment Cost"),
        ("Cash Conversion Cycle", "DIO + DSO − DPO  (period-consistent)"),
        ("Net Revenue YoY % · Comparable Base", "like-for-like: markets live the whole CY + PY span"),
    ]
    mw = W - 55 - rx0
    mh, mvgap = 155, 20
    mt = font(F_BOLD, 26)
    mb = font(F_REGULAR, 21)
    for i, (name, formula) in enumerate(measures):
        y = 300 + i * (mh + mvgap)
        rounded(d, [rx0, y, rx0 + mw, y + mh])
        d.rectangle([rx0, y, rx0 + 8, y + mh], fill=DEEP)
        d.text((rx0 + 40, y + 32), name, font=mt, fill=INK)
        for j, line in enumerate(wrap(formula, mb, mw - 80, d)):
            d.text((rx0 + 40, y + 82 + j * 28), line, font=mb, fill=MUTE)

    strip_y = 300 + 7 * (cardh + vgap) + 20
    d.rectangle([55, strip_y, W - 55, strip_y + 150], fill=NAVY)
    big = font(F_BOLD, 64)
    d.text((90, strip_y + 42), "167", font=big, fill=WHITE)
    small = font(F_REGULAR, 24)
    note = ("measures — each with its DAX and format string, generated from a single "
            "Python file (pbi_measures.py) and auto-documented")
    for k, line in enumerate(wrap(note, small, 2200, d)):
        d.text((280, strip_y + 55 + k * 32), line, font=small, fill=(200, 214, 232, 255))
    save(img, "04_dax_semantic_layer.png")


# ------------------------------------------------------- 05 report structure ---
def report_structure() -> None:
    img, d = canvas()
    header(d, "Report structure — one question per page", "7 PAGES · ~150 VISUALS")

    pages = [
        ("1", "Executive Summary", "Are we hitting plan, is growth real, where does the money go?",
         "KPI row with vs-target deltas · Key Insights · CM% monthly + trailing-12M · four bridges · Budget scorecard"),
        ("2", "Sales Performance", "Revenue booked vs cash actually received — what moved revenue?",
         "Revenue booked vs cash · price / volume / mix waterfall · orders"),
        ("3", "Marketing & Acquisition", "Is acquisition paying back, and where are customers coming from?",
         "On-site funnel · spend vs CAC by month · new customers by channel"),
        ("4", "Website & Digital", "How well does the store convert its traffic?",
         "Sessions & conversion · AOV · add-to-cart & abandonment · device mix"),
        ("5", "Logistics & Fulfillment", "Can operations support the growth, and where is cash tied up?",
         "On-time % & delivery days · carrier scorecard · DIO / DSO / DPO / CCC"),
        ("6", "CRM & Customer", "Are we keeping the customers we acquire?",
         "Cohort retention · churn · repeat rate · support volume & CSAT"),
        ("7", "Product & Inventory", "Which SKUs carry the margin, and where is stock stuck?",
         "Margin % & return rate by category · weeks of cover · aged inventory"),
    ]
    colw, gap = (W - 110 - 40) / 2, 40
    cardh, vgap = 275, 30
    badge_w = 130
    nt = font(F_BOLD, 44)
    tt = font(F_SEMIBOLD, 32)
    qt = font(F_ITALIC, 24)
    ct = font(F_REGULAR, 21)
    for i, (num, title, question, content) in enumerate(pages):
        col, row = i % 2, i // 2
        x = 55 + col * (colw + gap)
        y = 260 + row * (cardh + vgap)
        d.rounded_rectangle([x, y, x + badge_w, y + cardh], radius=16, fill=DEEP)
        d.rounded_rectangle([x + badge_w - 16, y, x + colw, y + cardh], radius=16, fill=WHITE, outline=LINE, width=2)
        d.text((x + badge_w / 2, y + cardh / 2), num, font=nt, fill=WHITE, anchor="mm")
        tx = x + badge_w + 30
        d.text((tx, y + 32), title, font=tt, fill=DEEP)
        for k, line in enumerate(wrap(question, qt, colw - badge_w - 60, d)):
            d.text((tx, y + 88 + k * 34), line, font=qt, fill=INK)
        cy = y + 88 + 34 * len(wrap(question, qt, colw - badge_w - 60, d)) + 26
        for k, line in enumerate(wrap(content, ct, colw - badge_w - 60, d)):
            d.text((tx, cy + k * 30), line, font=ct, fill=MUTE)

    strip_y = 260 + 4 * (cardh + vgap) + 10
    footer_strip(img, d, [
        ("Multi-currency", "whole report re-denominates into USD / EUR / GBP / BRL from one control"),
        ("Budget vs actual", "every KPI shows a colour-coded gap to plan"),
        ("One design system", "navy signature bar, restrained palette, 3-30-300 layout, theme-driven"),
    ], strip_y, h=150)
    save(img, "05_report_structure.png")


if __name__ == "__main__":
    cover()
    pipeline()
    bus_matrix()
    dax_layer()
    report_structure()
    print("\n5 portfolio images -> portfolio/")
