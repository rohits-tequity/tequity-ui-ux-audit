#!/usr/bin/env python3
"""Measure RENDERED contrast from a full-resolution screenshot.

This settles the cases a design-file audit cannot: text over a photo, a
gradient, a video frame, a blur, or any translucent surface. It is also the only
honest way to check a focus indicator's contrast against its real surroundings.

Regions JSON, either normalised [0,1] frames straight from Argent's `describe`,
or absolute pixels:

[
  {"id": "A11Y-004", "label": "Continue button label",
   "frame": {"x":0.08,"y":0.82,"w":0.84,"h":0.06}, "normalized": true,
   "font_size": 17, "bold": true},
  {"id": "A11Y-009", "label": "Focus ring",
   "frame": {"x":120,"y":540,"w":180,"h":48}, "normalized": false,
   "non_text": true}
]

Method: crop the region, split its pixels into two luminance clusters (1-D
k-means, k=2), treat the smaller cluster as foreground and the larger as
background, take each cluster's median colour, and compute the WCAG 2.x ratio.
Reports the cluster split so a bad segmentation is visible rather than silent.

Requires Pillow. Install: pip install pillow --break-system-packages
"""
from __future__ import annotations

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "figma-design-audit", "scripts"))
try:
    from contrast import luminance, ratio  # noqa: E402
except ImportError:  # standalone fallback
    def _lin(c):
        c = c / 255.0
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4

    def luminance(rgb):
        r, g, b = rgb[:3]
        return 0.2126 * _lin(r) + 0.7152 * _lin(g) + 0.0722 * _lin(b)

    def ratio(fg, bg):
        l1, l2 = luminance(fg), luminance(bg)
        hi, lo = max(l1, l2), min(l1, l2)
        return (hi + 0.05) / (lo + 0.05)


def kmeans_1d(values, iters=25):
    """Two-cluster split on luminance. Returns (centre_lo, centre_hi, labels)."""
    lo, hi = min(values), max(values)
    if hi - lo < 1e-9:
        return lo, hi, [0] * len(values)
    c0, c1 = lo, hi
    labels = [0] * len(values)
    for _ in range(iters):
        changed = False
        for i, v in enumerate(values):
            lab = 0 if abs(v - c0) <= abs(v - c1) else 1
            if lab != labels[i]:
                changed = True
            labels[i] = lab
        g0 = [v for v, l in zip(values, labels) if l == 0]
        g1 = [v for v, l in zip(values, labels) if l == 1]
        if not g0 or not g1:
            break
        c0, c1 = sum(g0) / len(g0), sum(g1) / len(g1)
        if not changed:
            break
    return c0, c1, labels


def median_color(pixels):
    if not pixels:
        return None
    n = len(pixels)
    return tuple(sorted(p[i] for p in pixels)[n // 2] for i in range(3))


def is_large(font_size, bold):
    if not font_size:
        return False
    return font_size >= 24 or (bold and font_size >= 18.66)


def probe(img, region, sample_cap=40000):
    from PIL import Image  # noqa: F401  (import guarded by caller)

    W, H = img.size
    f = region["frame"]
    if region.get("normalized", True):
        x, y = int(f["x"] * W), int(f["y"] * H)
        w, h = int(f["w"] * W), int(f["h"] * H)
    else:
        x, y, w, h = int(f["x"]), int(f["y"]), int(f["w"]), int(f["h"])
    x, y = max(0, x), max(0, y)
    w, h = max(1, min(w, W - x)), max(1, min(h, H - y))

    crop = img.crop((x, y, x + w, y + h)).convert("RGB")
    raw = crop.tobytes()
    px = [(raw[i], raw[i + 1], raw[i + 2]) for i in range(0, len(raw), 3)]
    if len(px) > sample_cap:
        step = len(px) // sample_cap + 1
        px = px[::step]
    if len(px) < 8:
        return {"id": region.get("id"), "status": "too_small",
                "reason": f"region is {w}x{h}px after clipping"}

    lums = [luminance(p) for p in px]
    c0, c1, labels = kmeans_1d(lums)
    g0 = [p for p, l in zip(px, labels) if l == 0]
    g1 = [p for p, l in zip(px, labels) if l == 1]
    if not g0 or not g1:
        return {"id": region.get("id"), "status": "uniform",
                "reason": "region is a single flat colour, no fg/bg pair to measure"}

    # background = the larger cluster; foreground = the smaller (text or glyph)
    if len(g0) >= len(g1):
        bg_px, fg_px = g0, g1
    else:
        bg_px, fg_px = g1, g0
    fg, bg = median_color(fg_px), median_color(bg_px)
    r = ratio(fg, bg)

    non_text = bool(region.get("non_text"))
    fs, bold = region.get("font_size"), bool(region.get("bold"))
    if non_text:
        req, kind = 3.0, "non-text (SC 1.4.11)"
    elif is_large(fs, bold):
        req, kind = 3.0, "large text (SC 1.4.3)"
    else:
        req, kind = 4.5, "normal text (SC 1.4.3)"

    fg_frac = len(fg_px) / (len(fg_px) + len(bg_px))
    # A plausible text region puts 3-50% of its pixels in the foreground cluster.
    # Outside that, the crop probably caught an image or a boundary.
    quality = "ok" if 0.03 <= fg_frac <= 0.5 else "suspect"

    return {
        "id": region.get("id"),
        "label": region.get("label"),
        "status": "measured",
        "crop_px": [x, y, w, h],
        "foreground": list(fg), "background": list(bg),
        "foreground_pixel_fraction": round(fg_frac, 3),
        "cluster_luminance": [round(min(c0, c1), 4), round(max(c0, c1), 4)],
        "kind": kind,
        "ratio": round(r, 2), "required": req,
        "passes": r >= req,
        "shortfall": None if r >= req else round(req - r, 2),
        "segmentation_quality": quality,
        "note": ("Foreground fraction is outside the plausible range for text: "
                 "tighten the crop to the glyphs and re-measure before reporting."
                 if quality == "suspect" else None),
    }


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--image", required=True, help="full-resolution PNG (screenshot --scale 1.0)")
    ap.add_argument("--regions", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)

    try:
        from PIL import Image
    except ImportError:
        print("Pillow is required: pip install pillow --break-system-packages",
              file=sys.stderr)
        return 2

    img = Image.open(a.image)
    with open(a.regions) as f:
        regions = json.load(f)

    results = [probe(img, r) for r in regions]
    measured = [r for r in results if r["status"] == "measured"]
    fails = [r for r in measured if not r["passes"]]
    suspect = [r for r in measured if r["segmentation_quality"] == "suspect"]

    out = {
        "image": a.image,
        "image_size": list(img.size),
        "method": "1-D k-means (k=2) over pixel luminance; median colour per "
                  "cluster; WCAG 2.x relative-luminance ratio",
        "caveat": "Measures what was rendered in this screenshot on this device "
                  "at this scale. Anti-aliasing and subpixel rendering shift the "
                  "foreground cluster slightly; treat a ratio within 0.2 of the "
                  "threshold as inconclusive and crop tighter.",
        "summary": {"regions": len(results), "measured": len(measured),
                    "failing": len(fails), "suspect_segmentation": len(suspect)},
        "results": results,
    }
    with open(a.out, "w") as f:
        json.dump(out, f, indent=2)

    print(f"{len(measured)}/{len(results)} region(s) measured -> {a.out}")
    for r in measured:
        flag = "FAIL" if not r["passes"] else "pass"
        q = "" if r["segmentation_quality"] == "ok" else "  [suspect crop]"
        print(f"  {flag} {r['ratio']}:1 (need {r['required']}) "
              f"{r.get('label') or r.get('id') or ''}{q}")
    for r in results:
        if r["status"] != "measured":
            print(f"  skipped {r.get('id')}: {r['status']}, {r.get('reason')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
