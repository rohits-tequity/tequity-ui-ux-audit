#!/usr/bin/env python3
"""WCAG 2.x contrast ratios for colour pairs.

Usage:
  contrast.py --pair "#1a1a1a" "#ffffff" [--font-size 14] [--bold]
  contrast.py --json pairs.json          # [{"id":..,"fg":..,"bg":..,"font_size":..,"bold":..}]

Emits JSON: ratio, the AA/AAA thresholds that apply, and pass/fail.
Alpha on the foreground is composited over the background before measuring.
"""
from __future__ import annotations

import argparse
import json
import re
import sys

NAMED = {
    "white": "#ffffff", "black": "#000000", "red": "#ff0000", "green": "#008000",
    "blue": "#0000ff", "grey": "#808080", "gray": "#808080", "transparent": "#00000000",
}


def parse_color(value):
    """Return (r, g, b, a) floats 0-255 / 0-1, or None if unparseable."""
    if value is None:
        return None
    s = str(value).strip().lower()
    s = NAMED.get(s, s)
    m = re.fullmatch(r"#([0-9a-f]{3,8})", s)
    if m:
        h = m.group(1)
        if len(h) == 3:
            h = "".join(c * 2 for c in h)
        elif len(h) == 4:
            h = "".join(c * 2 for c in h)
        if len(h) == 6:
            return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16), 1.0)
        if len(h) == 8:
            return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16), int(h[6:8], 16) / 255.0)
        return None
    m = re.fullmatch(r"rgba?\(([^)]+)\)", s)
    if m:
        parts = [p.strip() for p in re.split(r"[,\s/]+", m.group(1)) if p.strip()]
        if len(parts) < 3:
            return None

        def chan(p):
            if p.endswith("%"):
                return float(p[:-1]) * 255.0 / 100.0
            return float(p)

        r, g, b = (chan(p) for p in parts[:3])
        a = 1.0
        if len(parts) > 3:
            a = float(parts[3][:-1]) / 100.0 if parts[3].endswith("%") else float(parts[3])
        return (r, g, b, a)
    return None


def _lin(c):
    c = c / 255.0
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def luminance(rgb):
    r, g, b = rgb[:3]
    return 0.2126 * _lin(r) + 0.7152 * _lin(g) + 0.0722 * _lin(b)


def composite(fg, bg):
    """Alpha-composite fg over an opaque bg."""
    a = fg[3]
    if a >= 1.0:
        return fg[:3]
    return tuple(fg[i] * a + bg[i] * (1 - a) for i in range(3))


def ratio(fg, bg):
    l1, l2 = luminance(fg), luminance(bg)
    hi, lo = max(l1, l2), min(l1, l2)
    return (hi + 0.05) / (lo + 0.05)


def is_large(font_size, bold):
    if font_size is None:
        return False
    return font_size >= 24 or (bold and font_size >= 18.66)


def evaluate(fg_raw, bg_raw, font_size=None, bold=False, non_text=False, opacity=1.0):
    fg, bg = parse_color(fg_raw), parse_color(bg_raw)
    if fg is None or bg is None:
        return {
            "status": "indeterminate",
            "reason": "unparseable colour",
            "fg": fg_raw, "bg": bg_raw,
        }
    if opacity is not None and opacity < 1.0:
        fg = (fg[0], fg[1], fg[2], fg[3] * float(opacity))
    fg_c = composite(fg, bg[:3])
    r = ratio(fg_c, bg[:3])
    if non_text:
        aa, aaa, kind = 3.0, 3.0, "non-text (SC 1.4.11)"
    elif is_large(font_size, bold):
        aa, aaa, kind = 3.0, 4.5, "large text (SC 1.4.3)"
    else:
        aa, aaa, kind = 4.5, 7.0, "normal text (SC 1.4.3)"
    return {
        "status": "measured",
        "fg": fg_raw, "bg": bg_raw, "effective_fg": [round(v, 1) for v in fg_c],
        "font_size": font_size, "bold": bold, "opacity": opacity,
        "kind": kind, "ratio": round(r, 2),
        "aa_threshold": aa, "aaa_threshold": aaa,
        "passes_aa": r >= aa, "passes_aaa": r >= aaa,
        "shortfall": None if r >= aa else round(aa - r, 2),
    }


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--pair", nargs=2, metavar=("FG", "BG"))
    ap.add_argument("--json", help="file of pair objects")
    ap.add_argument("--font-size", type=float, default=None)
    ap.add_argument("--bold", action="store_true")
    ap.add_argument("--non-text", action="store_true")
    a = ap.parse_args(argv)

    if a.pair:
        out = evaluate(a.pair[0], a.pair[1], a.font_size, a.bold, a.non_text)
    elif a.json:
        with open(a.json) as f:
            items = json.load(f)
        out = []
        for it in items:
            res = evaluate(
                it.get("fg"), it.get("bg"), it.get("font_size"),
                bool(it.get("bold")), bool(it.get("non_text")),
                it.get("opacity", 1.0),
            )
            res["id"] = it.get("id")
            out.append(res)
    else:
        ap.error("pass --pair or --json")
    json.dump(out, sys.stdout, indent=2)
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
