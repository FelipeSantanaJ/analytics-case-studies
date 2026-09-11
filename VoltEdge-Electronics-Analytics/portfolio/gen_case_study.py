"""Generate a 7-page LinkedIn-carousel PDF (1080x1350) summarising the case study.

  python portfolio/gen_case_study.py

Output: portfolio/VoltEdge-Electronics-case-study.pdf

Layout is shared byte-for-byte across all five portfolio projects — only the CONFIG
block below (colours + copy) changes per project. Every number in CONFIG traces back
to data_analysis/findings/ and data_analysis/deliverables/ — nothing here is invented.
"""
from __future__ import annotations
import pathlib
from PIL import Image, ImageDraw, ImageFont

HERE = pathlib.Path(__file__).resolve().parent

# ============================================================== CONFIG (per project) ===
PROJECT = "VOLTEDGE ELECTRONICS"
AUTHOR = "FELIPE SANTANA · SENIOR DATA & PRODUCT ANALYST"
OUT_NAME = "VoltEdge-Electronics-case-study.pdf"

DEEP = (14, 42, 78)          # VoltEdge NAVY #0E2A4E
ACCENT = (217, 147, 17)      # VoltEdge AMBER #D99311

COVER = dict(
    headline=["Growth looked like +137%.", "The real number was +40%."],
    sub="How I found the $4.4M hiding in the balance sheet — and why growing "
        "faster would have made it worse.",
    footer="Fictional consumer-electronics retailer · synthetic data · real methodology",
)

PAGES = [
    dict(section="01 — THE PROBLEM", kind="stat",
         stat="+137%", bold="total revenue growth over 24 months.",
         body="But three of VoltEdge's four markets launched inside the window. "
              "Leadership needed to know if the business is actually growing — or if "
              "new-market expansion is just masking a flat core."),
    dict(section="02 — THE APPROACH", kind="metrics",
         bold="Split every growth number two ways: Total, and Comparable Base.",
         metrics=[
             ("PRIMARY METRIC", "Comparable Base — US-only, like-for-like, the one "
                                 "market live the whole window"),
             ("GUARDRAILS", "Contribution margin · cash conversion cycle · returns rate "
                             "· promo-day gross profit"),
         ]),
    dict(section="03 — THE SETUP", kind="cards",
         bold="Why a raw year-over-year number would have been misleading.",
         cards=[("294", "SKUS"), ("24", "MONTHS"), ("4", "MARKETS")],
         body="Growth is reported two ways because three of four markets go live inside "
              "the window — a raw YoY number would just be counting new geographies, "
              "not real growth."),
    dict(section="04 — WHAT HAPPENED", kind="stat_callout",
         stat="+40%", stat_sub="US like-for-like growth — not the +137% total",
         callout="Contribution margin just reached break-even. The real constraint "
                 "isn't the P&L — it's a 134-day cash conversion cycle, with ~$4.4M "
                 "freeable from inventory alone."),
    dict(section="05 — THE CATCH", kind="bold_callout",
         bold="Returns are a $1.65M margin drag, and promo days cost ~$0.3M/yr "
              "in gross profit.",
         callout="Small next to the $4.4M cash number — but real, and 63% of the "
                 "returns drag is controllable."),
]

CALL = dict(
    section="06 — THE CALL",
    headline=["Fix working capital", "before chasing more growth.",
              "$4.4M beats every other lever."],
    sub="Full methodology, numbers, and code — link in my Featured section.",
)
# ========================================================= end CONFIG (per project) ===

W, H = 1080, 1350
MARGIN = 78
TOTAL_PAGES = len(PAGES) + 2  # cover + content pages + call

CREAM = (242, 240, 234)
INK = (26, 26, 26)
BODY_GRAY = (90, 90, 90)
CALLOUT_BG = (237, 231, 216)
CALLOUT_TEXT = (63, 57, 46)
DOT_OFF_LIGHT = (198, 194, 184)
DOT_OFF_DARK = (70, 82, 94)
KICKER_ON_DARK = (159, 182, 204)
SUB_ON_DARK = (201, 214, 226)
FOOTER_ON_DARK = (130, 148, 166)
COUNTER_GRAY = (150, 150, 150)
FOOTER_ON_LIGHT = (140, 140, 140)

FONT_DIR = pathlib.Path(r"C:\Windows\Fonts")
SERIF = FONT_DIR / "georgia.ttf"
SERIF_B = FONT_DIR / "georgiab.ttf"
MONO = FONT_DIR / "consola.ttf"
MONO_B = FONT_DIR / "consolab.ttf"
SANS = FONT_DIR / "segoeui.ttf"
SANS_B = FONT_DIR / "segoeuib.ttf"


def font(path: pathlib.Path, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(path), size)


def wrap(d: ImageDraw.ImageDraw, text: str, f: ImageFont.FreeTypeFont, maxw: float) -> list[str]:
    words, lines, cur = text.split(), [], ""
    for w_ in words:
        trial = (cur + " " + w_).strip()
        if d.textlength(trial, font=f) <= maxw:
            cur = trial
        else:
            lines.append(cur)
            cur = w_
    if cur:
        lines.append(cur)
    return lines


def tracked(d: ImageDraw.ImageDraw, xy: tuple[float, float], text: str,
            f: ImageFont.FreeTypeFont, fill, tracking: float = 0) -> None:
    x, y = xy
    for ch in text:
        d.text((x, y), ch, font=f, fill=fill)
        x += d.textlength(ch, font=f) + tracking


def dots(d: ImageDraw.ImageDraw, page_idx: int, dark: bool, right: bool = False) -> None:
    r, gap = 4, 17
    y = H - 78
    off = DOT_OFF_DARK if dark else DOT_OFF_LIGHT
    x0 = W - MARGIN - (TOTAL_PAGES - 1) * gap if right else MARGIN
    for i in range(TOTAL_PAGES):
        x = x0 + i * gap
        d.ellipse([x - r, y - r, x + r, y + r], fill=ACCENT if i == page_idx else off)


def kicker_counter(d: ImageDraw.ImageDraw, kicker: str, counter: str | None, dark: bool) -> None:
    kf = font(MONO_B, 15)
    tracked(d, (MARGIN, 88), kicker.upper(), kf, KICKER_ON_DARK if dark else DEEP, tracking=2.5)
    if counter:
        cf = font(MONO_B, 15)
        cw = d.textlength(counter, font=cf)
        d.text((W - MARGIN - cw, 88), counter, font=cf, fill=KICKER_ON_DARK if dark else COUNTER_GRAY)


def footer(d: ImageDraw.ImageDraw, dark: bool) -> None:
    f = font(MONO, 13)
    d.text((MARGIN, H - 84), AUTHOR, font=f, fill=FOOTER_ON_DARK if dark else FOOTER_ON_LIGHT)


# ------------------------------------------------------------------------- page 1 ---
def render_cover() -> Image.Image:
    img = Image.new("RGB", (W, H), DEEP)
    d = ImageDraw.Draw(img)
    kicker_counter(d, f"CASE STUDY · {PROJECT}", None, dark=True)

    hf = font(SERIF_B, 56)
    y = 420
    for line in COVER["headline"]:
        d.text((MARGIN, y), line, font=hf, fill=(255, 255, 255))
        y += 68

    sf = font(SANS, 25)
    y += 34
    for line in wrap(d, COVER["sub"], sf, W - 2 * MARGIN):
        d.text((MARGIN, y), line, font=sf, fill=SUB_ON_DARK)
        y += 36

    ff = font(MONO, 14)
    d.text((MARGIN, H - 152), COVER["footer"], font=ff, fill=FOOTER_ON_DARK)

    sw_f = font(MONO_B, 14)
    txt = "SWIPE \u2192"
    tw = d.textlength(txt, font=sw_f)
    d.text((W - MARGIN - tw, H - 84), txt, font=sw_f, fill=KICKER_ON_DARK)
    dots(d, 0, dark=True)
    return img


# --------------------------------------------------------------- pages 2-6 building blocks ---
def giant_stat(d: ImageDraw.ImageDraw, y: int, stat: str, stat_sub: str | None = None) -> int:
    sf = font(SERIF_B, 104)
    d.text((MARGIN, y), stat, font=sf, fill=ACCENT)
    bbox = d.textbbox((MARGIN, y), stat, font=sf)
    if stat_sub:
        ssf = font(SANS, 19)
        d.text((MARGIN, bbox[3] + 14), stat_sub, font=ssf, fill=BODY_GRAY)
        return bbox[3] + 14 + 34
    return bbox[3] + 30


def bold_line(d: ImageDraw.ImageDraw, y: int, text: str, size: int = 33) -> int:
    f = font(SERIF_B, size)
    for line in wrap(d, text, f, W - 2 * MARGIN):
        d.text((MARGIN, y), line, font=f, fill=INK)
        y += int(size * 1.28)
    return y + 14


def body_text(d: ImageDraw.ImageDraw, y: int, text: str, size: int = 21) -> int:
    f = font(SANS, size)
    for line in wrap(d, text, f, W - 2 * MARGIN):
        d.text((MARGIN, y), line, font=f, fill=BODY_GRAY)
        y += int(size * 1.45)
    return y


def callout_box(d: ImageDraw.ImageDraw, y: int, text: str, size: int = 19) -> int:
    f = font(SANS, size)
    pad_x, pad_y = 32, 22
    lines = wrap(d, text, f, W - 2 * MARGIN - 2 * pad_x)
    box_h = pad_y * 2 + int(size * 1.5) * len(lines)
    d.rounded_rectangle([MARGIN, y, W - MARGIN, y + box_h], radius=8, fill=CALLOUT_BG)
    d.rectangle([MARGIN, y, MARGIN + 5, y + box_h], fill=ACCENT)
    ty = y + pad_y
    for line in lines:
        d.text((MARGIN + pad_x, ty), line, font=f, fill=CALLOUT_TEXT)
        ty += int(size * 1.5)
    return y + box_h + 20


def metric_box(d: ImageDraw.ImageDraw, y: int, label: str, text: str) -> int:
    lf = font(MONO_B, 14)
    tf = font(SANS, 20)
    pad_x, pad_y = 30, 22
    lines = wrap(d, text, tf, W - 2 * MARGIN - 2 * pad_x)
    box_h = pad_y * 2 + 26 + int(20 * 1.4) * len(lines)
    d.rounded_rectangle([MARGIN, y, W - MARGIN, y + box_h], radius=10,
                         outline=(214, 209, 196), width=2, fill=(255, 255, 255))
    tracked(d, (MARGIN + pad_x, y + pad_y), label, lf, ACCENT, tracking=2)
    ty = y + pad_y + 30
    for line in lines:
        d.text((MARGIN + pad_x, ty), line, font=tf, fill=INK)
        ty += int(20 * 1.4)
    return y + box_h + 22


def stat_cards(d: ImageDraw.ImageDraw, y: int, cards: list[tuple[str, str]]) -> int:
    n = len(cards)
    gap = 20
    cw = (W - 2 * MARGIN - gap * (n - 1)) / n
    ch = 130
    for i, (num, label) in enumerate(cards):
        x = MARGIN + i * (cw + gap)
        d.rounded_rectangle([x, y, x + cw, y + ch], radius=10,
                             outline=(214, 209, 196), width=2, fill=(255, 255, 255))
        nf = font(SERIF_B, 34)
        d.text((x + 22, y + 20), num, font=nf, fill=INK)
        lf = font(MONO, 13)
        tracked(d, (x + 22, y + 78), label, lf, BODY_GRAY, tracking=1)
    return y + ch + 30


def render_content(idx: int, page: dict) -> Image.Image:
    img = Image.new("RGB", (W, H), CREAM)
    d = ImageDraw.Draw(img)
    kicker_counter(d, page["section"], f"{idx:02d} / {TOTAL_PAGES:02d}", dark=False)

    y = 300
    kind = page["kind"]
    if kind == "stat":
        y = giant_stat(d, y, page["stat"])
        y = bold_line(d, y, page["bold"])
        y = body_text(d, y, page["body"])
    elif kind == "metrics":
        y = bold_line(d, y, page["bold"], size=36)
        y += 20
        for label, text in page["metrics"]:
            y = metric_box(d, y, label, text)
    elif kind == "cards":
        y = bold_line(d, y, page["bold"], size=36)
        y += 10
        y = stat_cards(d, y, page["cards"])
        y = body_text(d, y, page["body"])
    elif kind == "stat_callout":
        y = giant_stat(d, y, page["stat"], page.get("stat_sub"))
        y += 20
        y = callout_box(d, y, page["callout"])
    elif kind == "bold_callout":
        y = bold_line(d, y, page["bold"], size=38)
        y += 20
        y = callout_box(d, y, page["callout"])

    footer(d, dark=False)
    dots(d, idx - 1, dark=False, right=True)
    return img


# ------------------------------------------------------------------------- page 7 ---
def render_call() -> Image.Image:
    img = Image.new("RGB", (W, H), DEEP)
    d = ImageDraw.Draw(img)
    kicker_counter(d, CALL["section"], f"{TOTAL_PAGES:02d} / {TOTAL_PAGES:02d}", dark=True)

    hf = font(SERIF_B, 46)
    y = 460
    for line in CALL["headline"]:
        d.text((MARGIN, y), line, font=hf, fill=(255, 255, 255))
        y += 58

    sf = font(SANS, 23)
    y += 34
    for line in wrap(d, CALL["sub"], sf, W - 2 * MARGIN):
        d.text((MARGIN, y), line, font=sf, fill=SUB_ON_DARK)
        y += 34

    footer(d, dark=True)
    dots(d, TOTAL_PAGES - 1, dark=True, right=True)
    return img


def main() -> None:
    pages = [render_cover()]
    for i, page in enumerate(PAGES, start=2):
        pages.append(render_content(i, page))
    pages.append(render_call())

    out = HERE / OUT_NAME
    pages[0].save(out, save_all=True, append_images=pages[1:])
    print(f"wrote {out}  ({len(pages)} pages, {W}x{H})")


if __name__ == "__main__":
    main()
