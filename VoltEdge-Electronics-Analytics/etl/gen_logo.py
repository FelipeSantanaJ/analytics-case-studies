"""
Generate the VoltEdge Electronics logo (a lightning bolt + wordmark) as PNGs.

Outputs to powerbi/assets/:
  voltedge-logo-light.png   white mark + wordmark, for dark headers
  voltedge-logo-dark.png    navy mark + wordmark, for light backgrounds
  voltedge-icon-light.png    bolt only, white
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

OUT = Path(__file__).resolve().parent.parent / "powerbi" / "assets"
OUT.mkdir(parents=True, exist_ok=True)

SCALE = 4                                  # supersample then downscale for clean edges
NAVY = (14, 42, 78, 255)                   # #0E2A4E
WHITE = (255, 255, 255, 255)
BLUE = (46, 112, 176, 255)                 # #2E70B0 accent for the wordmark tail

FONT_PATH = r"C:\Windows\Fonts\seguisb.ttf"   # Segoe UI Semibold


def _bolt(draw: ImageDraw.ImageDraw, x: int, y: int, w: int, h: int, fill) -> None:
    """A chunky lightning bolt inside the (x, y, w, h) box."""
    pts = [
        (0.56, 0.00), (0.16, 0.56), (0.44, 0.56), (0.34, 1.00),
        (0.84, 0.40), (0.54, 0.40), (0.70, 0.00),
    ]
    poly = [(x + px * w, y + py * h) for px, py in pts]
    draw.polygon(poly, fill=fill)


def _render(mark_fill, text_fill, tail_fill, name: str, icon_only: bool = False) -> None:
    pad = 8 * SCALE
    icon_h = 116 * SCALE
    icon_w = int(icon_h * 0.72)
    if icon_only:
        W = icon_w + 2 * pad
        H = icon_h + 2 * pad
    else:
        text = "VOLTEDGE"
        font = ImageFont.truetype(FONT_PATH, 78 * SCALE)
        tb = font.getbbox(text)
        tw, th = tb[2] - tb[0], tb[3] - tb[1]
        gap = 18 * SCALE
        W = pad + icon_w + gap + tw + pad
        H = max(icon_h, th) + 2 * pad

    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    iy = (H - icon_h) // 2
    _bolt(d, pad, iy, icon_w, icon_h, mark_fill)

    if not icon_only:
        tx = pad + icon_w + gap
        ty = (H - th) // 2 - tb[1]
        # "VOLT" solid, "EDGE" in the accent tint for a subtle two-tone
        d.text((tx, ty), "VOLT", font=font, fill=text_fill)
        vb = font.getbbox("VOLT")
        d.text((tx + (vb[2] - vb[0]), ty), "EDGE", font=font, fill=tail_fill)

    img = img.resize((W // SCALE, H // SCALE), Image.LANCZOS)
    img.save(OUT / name)
    print(f"  {name}  {img.size[0]}x{img.size[1]}")


HEADER_NAVY = (14, 42, 78, 255)            # #0E2A4E
HEADER_RULE = (46, 112, 176, 255)          # #2E70B0
HEADER_W, HEADER_H = 1280, 60
PAGE_W = 1280
PAGE_H_EXEC, PAGE_H_STD = 1240, 1000       # must match gen_report_visuals
PAGE_BG = (234, 239, 246, 255)             # #EAEFF6 - matches the theme page background

PAGE_TITLES = {
    "executive-summary": "Executive Summary",
    "sales-performance": "Sales Performance",
    "marketing-acquisition": "Marketing & Acquisition",
    "website-digital": "Website & Digital",
    "logistics-fulfillment": "Logistics & Fulfillment",
    "crm-customer": "CRM & Customer",
    "product-inventory": "Product & Inventory",
}


def _draw_header_band(d: ImageDraw.ImageDraw, title: str, band_h: int) -> None:
    """Draw the brand header (bolt + VOLTEDGE + divider + page title + rule) into the
    top `band_h` pixels of an already-scaled canvas. Coordinates are in scaled units."""
    S = SCALE
    W = HEADER_W * S
    d.rectangle([0, 0, W, band_h], fill=HEADER_NAVY)
    d.rectangle([0, band_h - 3 * S, W, band_h], fill=HEADER_RULE)          # accent rule

    icon_h = 30 * S
    icon_w = int(icon_h * 0.72)
    ix, iy = 26 * S, (band_h - icon_h) // 2 - 2 * S
    _bolt(d, ix, iy, icon_w, icon_h, WHITE)

    x = ix + icon_w + 14 * S
    wm_font = ImageFont.truetype(FONT_PATH, 24 * S)
    d.text((x, (band_h - 24 * S) // 2 - 2 * S), "VOLTEDGE", font=wm_font, fill=WHITE)
    wb = wm_font.getbbox("VOLTEDGE")
    x += (wb[2] - wb[0]) + 16 * S

    d.line([(x, 14 * S), (x, band_h - 17 * S)], fill=(120, 145, 180, 255), width=max(1, S))
    x += 16 * S

    t_font = ImageFont.truetype(FONT_PATH, 20 * S)
    tb = t_font.getbbox(title)
    d.text((x, (band_h - (tb[3] - tb[1])) // 2 - tb[1] - 2 * S), title, font=t_font,
           fill=(226, 235, 246, 255))


def _header(slug: str, title: str) -> None:
    S = SCALE
    img = Image.new("RGBA", (HEADER_W * S, HEADER_H * S), HEADER_NAVY)
    _draw_header_band(ImageDraw.Draw(img), title, HEADER_H * S)
    img = img.resize((HEADER_W, HEADER_H), Image.LANCZOS)
    img.save(OUT / f"header-{slug}.png")
    print(f"  header-{slug}.png  {HEADER_W}x{HEADER_H}")


def _page_bg(slug: str, title: str) -> None:
    """Full-canvas page background: brand header band on top, theme page colour below.
    Used as the page background image (image *visuals* don't render a bound
    RegisteredResource reliably through pbir; a page background does)."""
    S = SCALE
    page_h = PAGE_H_EXEC if slug == "executive-summary" else PAGE_H_STD
    img = Image.new("RGBA", (PAGE_W * S, page_h * S), PAGE_BG)
    _draw_header_band(ImageDraw.Draw(img), title, HEADER_H * S)
    img = img.resize((PAGE_W, page_h), Image.LANCZOS)
    img.save(OUT / f"pagebg-{slug}.png")
    print(f"  pagebg-{slug}.png  {PAGE_W}x{page_h}")


def main() -> None:
    _render(WHITE, WHITE, (200, 219, 240, 255), "voltedge-logo-light.png")
    _render(NAVY, NAVY, BLUE, "voltedge-logo-dark.png")
    _render(WHITE, WHITE, WHITE, "voltedge-icon-light.png", icon_only=True)
    for slug, title in PAGE_TITLES.items():
        _header(slug, title)
        _page_bg(slug, title)
    print(f"assets written to {OUT}")


if __name__ == "__main__":
    main()
