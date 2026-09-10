"""
gen_logo.py — emit the Voxa+ mark, wordmark, and per-page background PNGs.

    python assets/gen_logo.py

Outputs to powerbi/assets/:
  logo_mark_on_light.png / logo_mark_on_dark.png     (square glyph, transparent)
  wordmark_on_light.png  / wordmark_on_dark.png      (Voxa+ lockup, transparent)
  bg_<page>.png                                       (full-page background per page)
  _page_heights.json                                  (page -> height, read in Phase 8)
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

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
REG  = lambda s: _font(["segoeui.ttf", "arial.ttf"], s)
LIGHT = lambda s: _font(["segoeuil.ttf", "segoeui.ttf", "arial.ttf"], s)


# ---------------------------------------------------------------------------
def _mark(fg, plus=B.AMBER, scale=8):
    """A rounded-square tile with a play triangle + a small plus. `fg` is the tile."""
    s = 64 * scale
    im = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    r = int(s * 0.22)
    d.rounded_rectangle([0, 0, s - 1, s - 1], radius=r, fill=fg)
    # play triangle (white), optically centred
    w = s
    tri = [(w * 0.40, w * 0.32), (w * 0.40, w * 0.68), (w * 0.70, w * 0.50)]
    d.polygon(tri, fill=B.ON_DARK if fg != B.ON_DARK else B.VIOLET)
    # plus, top-right
    px, py, pl, pt = w * 0.78, w * 0.22, w * 0.12, max(2, int(w * 0.035))
    d.line([(px - pl / 2, py), (px + pl / 2, py)], fill=plus, width=pt)
    d.line([(px, py - pl / 2), (px, py + pl / 2)], fill=plus, width=pt)
    return im.resize((256, 256), Image.LANCZOS)


def _wordmark(ink, plus=B.AMBER, h=160):
    pad = int(h * 0.18)
    f = SEMI(int(h * 0.82))
    txt = "Voxa"
    tmp = Image.new("RGBA", (10, 10))
    dd = ImageDraw.Draw(tmp)
    wv = dd.textbbox((0, 0), txt, font=f)[2]
    wp = dd.textbbox((0, 0), "+", font=f)[2]
    im = Image.new("RGBA", (wv + wp + pad * 2 + int(h * 0.12), h + pad), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.text((pad, pad // 2), txt, font=f, fill=ink)
    d.text((pad + wv + int(h * 0.06), pad // 2), "+", font=f, fill=plus)
    return im


def gen_brand_assets():
    _mark(B.VIOLET).save(OUT / "logo_mark_on_light.png")
    _mark(B.ON_DARK).save(OUT / "logo_mark_on_dark.png")
    _wordmark(B.VIOLET_DEEP).save(OUT / "wordmark_on_light.png")
    _wordmark(B.ON_DARK).save(OUT / "wordmark_on_dark.png")
    print("  brand: mark + wordmark (on_light / on_dark)")


# ---------------------------------------------------------------------------
def _page_bg(title, subtitle, w, h):
    im = Image.new("RGB", (w, h), B.hex_to_rgb(B.PAGE_BG))
    d = ImageDraw.Draw(im)
    band_h = B.BAND_H
    d.rectangle([0, 0, w, band_h], fill=B.hex_to_rgb(B.VIOLET_DEEP))
    d.rectangle([0, band_h, w, band_h + B.HAIRLINE_H], fill=B.hex_to_rgb(B.AMBER))

    # wordmark in the band (left)
    wm = _wordmark(B.ON_DARK, h=120)
    target_h = int(band_h * 0.52)
    wm = wm.resize((int(wm.width * target_h / wm.height), target_h), Image.LANCZOS)
    im.paste(wm, (28, (band_h - wm.height) // 2), wm)

    # small mark to the right of the wordmark
    mk = _mark(B.ON_DARK).resize((int(band_h * 0.5), int(band_h * 0.5)), Image.LANCZOS)
    # (kept subtle; wordmark already reads)

    # a quiet label on the band, right side
    lab = REG(17)
    lt = "Subscriber Churn Diagnosis"
    ltw = d.textbbox((0, 0), lt, font=lab)[2]
    d.text((w - ltw - 28, (band_h - 17) // 2 - 1), lt, font=lab, fill=B.hex_to_rgb(B.ON_DARK_MUTED))

    # page title + subtitle on the light body
    ty = band_h + 22
    d.text((32, ty), title, font=SEMI(30), fill=B.hex_to_rgb(B.INK_TITLE))
    d.text((32, ty + 40), subtitle, font=REG(15), fill=B.hex_to_rgb(B.INK_MUTED))

    # faint baseline rule under the title zone
    d.line([(32, ty + 70), (w - 32, ty + 70)], fill=B.hex_to_rgb(B.HAIRLINE), width=1)
    return im


def gen_page_backgrounds():
    heights = {}
    for key, (title, subtitle) in B.PAGE_TITLES.items():
        h = B.PAGE_H_EXEC if key == "01_executive" else B.PAGE_H_STANDARD
        heights[key] = h
        _page_bg(title, subtitle, B.CANVAS_W, h).save(OUT / f"bg_{key}.png")
        print(f"  bg_{key}.png  {B.CANVAS_W}x{h}")
    (OUT / "_page_heights.json").write_text(json.dumps(heights, indent=2))


if __name__ == "__main__":
    print("gen_logo.py -> powerbi/assets/")
    gen_brand_assets()
    gen_page_backgrounds()
    print("done")
