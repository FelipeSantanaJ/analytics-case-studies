"""
gen_logo.py — emit the LumaBank mark, wordmark, and per-page background PNGs.

    python assets/gen_logo.py

Outputs to powerbi/assets/:
  logo_mark_on_light.png / logo_mark_on_dark.png
  wordmark_on_light.png  / wordmark_on_dark.png
  bg_<page>.png            (full-page background per page)
  _page_heights.json       (page -> height, read in Phase 8)
"""
from __future__ import annotations

import json
from pathlib import Path
import sys

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parent))
import brand as B

OUT = Path(__file__).resolve().parents[1] / "powerbi" / "assets"
OUT.mkdir(parents=True, exist_ok=True)

_FONT_DIR = Path("C:/Windows/Fonts")


def _font(names, size):
    for n in names:
        p = _FONT_DIR / n
        if p.exists():
            return ImageFont.truetype(str(p), size)
    return ImageFont.load_default()


SEMI = lambda s: _font(["seguisb.ttf", "segoeuisb.ttf", "segoeuib.ttf", "arialbd.ttf"], s)
REG = lambda s: _font(["segoeui.ttf", "arial.ttf"], s)


# ---------------------------------------------------------------------------
def _mark(tile_hex, mark_hex=None, scale=8):
    """Rounded-square tile with an activation pulse: a rising step-line to a dot —
    the Day-7 activation moment, not a bank-vault or shield cliche."""
    mark_hex = mark_hex or B.ON_DARK
    s = 64 * scale
    im = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle([0, 0, s - 1, s - 1], radius=int(s * 0.22), fill=tile_hex)
    w = int(s * 0.045)
    pts = [(s * 0.20, s * 0.62), (s * 0.38, s * 0.62), (s * 0.38, s * 0.46),
           (s * 0.56, s * 0.46), (s * 0.56, s * 0.30), (s * 0.72, s * 0.30)]
    d.line(pts, fill=mark_hex, width=w, joint="curve")
    r = s * 0.052
    d.ellipse([s * 0.72 - r, s * 0.30 - r, s * 0.72 + r, s * 0.30 + r], fill=B.CORAL)
    return im.resize((256, 256), Image.LANCZOS)


def _wordmark(ink_hex, accent_hex=B.CORAL, h=160):
    pad = int(h * 0.18)
    f = SEMI(int(h * 0.80))
    a, b = "Luma", "Bank"
    tmp = ImageDraw.Draw(Image.new("RGBA", (10, 10)))
    wa = tmp.textbbox((0, 0), a, font=f)[2]
    wb = tmp.textbbox((0, 0), b, font=f)[2]
    im = Image.new("RGBA", (wa + wb + pad * 2, h + pad), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.text((pad, pad // 2), a, font=f, fill=ink_hex)
    d.text((pad + wa, pad // 2), b, font=f, fill=accent_hex)
    return im


def gen_brand_assets():
    _mark(B.PETROL).save(OUT / "logo_mark_on_light.png")
    _mark(B.ON_DARK, mark_hex=B.PETROL).save(OUT / "logo_mark_on_dark.png")
    _wordmark(B.PETROL_DEEP).save(OUT / "wordmark_on_light.png")
    _wordmark(B.ON_DARK).save(OUT / "wordmark_on_dark.png")
    print("  brand: mark + wordmark (on_light / on_dark)")


# ---------------------------------------------------------------------------
def _page_bg(title, subtitle, w, h):
    im = Image.new("RGB", (w, h), B.hex_to_rgb(B.PAGE_BG))
    d = ImageDraw.Draw(im)
    bh = B.BAND_H
    d.rectangle([0, 0, w, bh], fill=B.hex_to_rgb(B.PETROL_DEEP))
    d.rectangle([0, bh, w, bh + B.HAIRLINE_H], fill=B.hex_to_rgb(B.CORAL))

    wm = _wordmark(B.ON_DARK, h=120)
    th = int(bh * 0.50)
    wm = wm.resize((int(wm.width * th / wm.height), th), Image.LANCZOS)
    im.paste(wm, (26, (bh - wm.height) // 2), wm)

    lab = REG(16)
    lt = "Activation Experiment  -  Fintech Analytics"
    ltw = d.textbbox((0, 0), lt, font=lab)[2]
    d.text((w - ltw - 26, (bh - 16) // 2 - 1), lt, font=lab, fill=B.hex_to_rgb(B.ON_DARK_MUTED))

    ty = bh + 20
    d.text((30, ty), title, font=SEMI(29), fill=B.hex_to_rgb(B.INK_TITLE))
    d.text((30, ty + 39), subtitle, font=REG(14), fill=B.hex_to_rgb(B.INK_MUTED))
    d.line([(30, ty + 66), (w - 30, ty + 66)], fill=B.hex_to_rgb(B.HAIRLINE), width=1)
    return im


def gen_page_backgrounds():
    heights = {}
    for key, (title, subtitle) in B.PAGE_TITLES.items():
        hh = B.PAGE_H_EXEC if key == "01_executive" else B.PAGE_H_STANDARD
        heights[key] = hh
        _page_bg(title, subtitle, B.CANVAS_W, hh).save(OUT / f"bg_{key}.png")
        print(f"  bg_{key}.png  {B.CANVAS_W}x{hh}")
    (OUT / "_page_heights.json").write_text(json.dumps(heights, indent=2))


if __name__ == "__main__":
    print("gen_logo.py -> powerbi/assets/")
    gen_brand_assets()
    gen_page_backgrounds()
    print("done")
