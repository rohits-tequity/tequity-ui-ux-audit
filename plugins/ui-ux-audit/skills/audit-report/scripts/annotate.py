#!/usr/bin/env python3
"""Mark a finding's region on a screenshot and crop around it.

  annotate.py --image shots/checkout.png --out evidence/a11y-001.png \
              --frame 0.08,0.82,0.84,0.06 --normalized --label A11Y-001 \
              [--label2 "3.44:1, needs 4.5:1"] [--pad 0.6] [--dim]

Draws a coral outline with a label chip, optionally dims everything outside the
region, and crops to the region plus padding so the reader sees the context
without hunting. Used automatically by build_report.py when a finding's
evidence carries `frame` (normalized [0,1] frames straight from Argent's
`describe`, or pixel frames from Figma metadata) and the image is a raw
screenshot. Also callable by hand for a design-file screenshot.

Colours are the report's own: coral #ed4746 for the marker, ink #191818 for the
chip text, cream #f7f7f2 chip. Requires Pillow.
"""
from __future__ import annotations

import argparse
import os
import sys

CORAL = (237, 71, 70)
INK = (25, 24, 24)
CREAM = (247, 247, 242)


def _font(size):
    from PIL import ImageFont
    for cand in ("Inter-SemiBold.ttf", "Inter.ttf", "DejaVuSans-Bold.ttf", "DejaVuSans.ttf",
                 "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
                 "/System/Library/Fonts/Helvetica.ttc", "Arial.ttf"):
        try:
            return ImageFont.truetype(cand, size)
        except Exception:
            continue
    return ImageFont.load_default()


def annotate(image_path, out_path, frame, normalized=True, label="", label2="", pad=0.6,
             dim=False, min_width=480, stroke=None, max_label2=44, min_pad=48):
    from PIL import Image, ImageDraw

    im = Image.open(image_path).convert("RGBA")
    W, H = im.size
    x, y, w, h = frame
    if normalized:
        x, y, w, h = x * W, y * H, w * W, h * H
    x, y, w, h = int(x), int(y), max(1, int(w)), max(1, int(h))
    x, y = max(0, min(x, W - 1)), max(0, min(y, H - 1))
    w, h = min(w, W - x), min(h, H - y)

    stroke = stroke or max(3, round(min(W, H) / 220))
    overlay = Image.new("RGBA", im.size, (0, 0, 0, 0))
    od = ImageDraw.Draw(overlay)
    if dim:
        od.rectangle([0, 0, W, H], fill=(25, 24, 24, 110))
        od.rectangle([x, y, x + w, y + h], fill=(0, 0, 0, 0))
        im = Image.alpha_composite(im, overlay)
        overlay = Image.new("RGBA", im.size, (0, 0, 0, 0))
        od = ImageDraw.Draw(overlay)

    r = max(6, stroke * 2)
    od.rounded_rectangle([x - stroke, y - stroke, x + w + stroke, y + h + stroke],
                         radius=r, outline=CORAL + (255,), width=stroke)

    if label or label2:
        fs = max(14, round(min(W, H) / 40))
        f1, f2 = _font(fs), _font(max(11, round(fs * 0.8)))
        text1, text2 = label or "", label2 or ""
        # keep the chip readable: a long measured value is trimmed, and it is
        # dropped entirely when it would still run past the image edge
        if len(text2) > max_label2:
            text2 = text2[:max_label2 - 3].rstrip(" ,;:") + "..."
        tw1 = od.textlength(text1, font=f1) if text1 else 0
        tw2 = od.textlength(text2, font=f2) if text2 else 0
        if tw2 + fs * 1.2 > W:
            text2, tw2 = "", 0
        padx, pady = round(fs * 0.6), round(fs * 0.35)
        cw = int(max(tw1, tw2) + padx * 2)
        ch = int((fs if text1 else 0) + (round(fs * 0.8) if text2 else 0) + pady * 2 + (pady if text1 and text2 else 0))
        cx = max(0, min(x - stroke, W - cw))
        cy = y - stroke - ch - round(stroke * 1.5)
        if cy < 0:  # no room above: put the chip inside the region's top-left
            cy = y + stroke
        od.rounded_rectangle([cx, cy, cx + cw, cy + ch], radius=round(fs * 0.4), fill=CORAL + (255,))
        ty = cy + pady
        if text1:
            od.text((cx + padx, ty), text1, font=f1, fill=CREAM + (255,))
            ty += fs + (pady if text2 else 0)
        if text2:
            od.text((cx + padx, ty), text2, font=f2, fill=CREAM + (255,))

    im = Image.alpha_composite(im, overlay)

    # crop: region plus padding, at least min_width wide, clamped to the image
    px, py = max(min_pad, int(w * pad) + stroke * 4), max(min_pad, int(h * pad) + stroke * 4)
    cx0, cy0 = max(0, x - px), max(0, y - py - (ch if (label or label2) else 0))
    cx1, cy1 = min(W, x + w + px), min(H, y + h + py)
    if cx1 - cx0 < min_width:
        extra = (min_width - (cx1 - cx0)) // 2
        cx0, cx1 = max(0, cx0 - extra), min(W, cx1 + extra)
    crop = im.crop((cx0, cy0, cx1, cy1)).convert("RGB")
    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    crop.save(out_path, optimize=True)
    return {"out": out_path, "crop_px": [cx0, cy0, cx1 - cx0, cy1 - cy0],
            "region_px": [x, y, w, h], "image_size": [W, H]}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--image", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--frame", required=True, help="x,y,w,h")
    ap.add_argument("--normalized", action="store_true", help="frame is in [0,1] fractions (Argent describe)")
    ap.add_argument("--label", default="")
    ap.add_argument("--label2", default="")
    ap.add_argument("--pad", type=float, default=0.6)
    ap.add_argument("--dim", action="store_true")
    a = ap.parse_args(argv)
    try:
        import PIL  # noqa: F401
    except ImportError:
        print("Pillow is required: pip install pillow --break-system-packages", file=sys.stderr)
        return 2
    frame = tuple(float(v) for v in a.frame.split(","))
    if len(frame) != 4:
        ap.error("--frame needs x,y,w,h")
    res = annotate(a.image, a.out, frame, a.normalized, a.label, a.label2, a.pad, a.dim)
    print(res)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
