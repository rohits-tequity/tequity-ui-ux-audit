#!/usr/bin/env python3
"""Validate a report brand theme against the contrast rules the report claims.

The report states its own contrast figures, so a fork that swaps the palette
must not quietly break them. This checks every text token against the surface
it is used on, in both modes, and the accents used as fills against their
background at the non-text threshold.

  theme_check.py                          # the default theme
  theme_check.py --theme neutral
  theme_check.py --theme path/to/theme.mybrand.css

Exit 0 when every pair passes, 1 otherwise. Wire it into CI when you fork.
"""
from __future__ import annotations

import argparse
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "figma-design-audit", "scripts"))

REQUIRED = ["ink", "ink-soft", "ink-2", "cream", "cream-1", "cream-2",
            "teal-50", "teal-100", "teal-200", "teal-300", "teal-400", "teal-500", "teal-700",
            "coral-100", "coral-300", "coral-500", "coral-700",
            "orange-100", "orange-300", "orange-500", "orange-700"]

# (label, foreground token, background token, threshold)
# 4.5 for body text, 3.0 for non-text (fills, rings, bars) per WCAG 1.4.11
PAIRS = [
    ("body text, dark mode", "cream", "ink", 4.5),
    ("body text, light mode", "ink", "cream", 4.5),
    ("critical severity, dark", "coral-300", "ink", 4.5),
    ("accent text, dark", "orange-300", "ink", 4.5),
    ("grade A, dark", "teal-100", "ink", 4.5),
    ("info severity, dark", "teal-100", "ink", 4.5),
    ("body text on a card, dark", "cream", "ink-2", 4.5),
    ("heading, light mode", "ink", "cream-1", 4.5),
    ("grade A, light", "teal-500", "cream", 4.5),
    ("critical severity, light", "coral-700", "cream", 4.5),
    ("accent text, light", "orange-700", "cream", 4.5),
    ("teal fill on cream (bars)", "teal-500", "cream", 3.0),
    ("coral fill on cream (bars)", "coral-500", "cream", 3.0),
    ("accent fill on ink (rings)", "orange-500", "ink", 3.0),
    ("border on card, light", "cream-2", "cream-1", 1.2),
]


def load(path_or_name):
    cand = path_or_name
    if os.sep not in cand and not cand.endswith(".css"):
        cand = os.path.join(HERE, "..", "assets", f"theme.{cand}.css")
    if not os.path.exists(cand):
        print(f"theme not found: {path_or_name}", file=sys.stderr)
        raise SystemExit(2)
    raw = re.sub(r"/\*.*?\*/", "", open(cand, encoding="utf-8").read(), flags=re.S)
    return dict(re.findall(r"--tq-([a-z0-9-]+):\s*(#[0-9a-fA-F]{6})", raw)), cand


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--theme", default="tequity")
    a = ap.parse_args(argv)
    from contrast import evaluate

    tok, path = load(a.theme)
    print(f"theme: {path}")
    missing = [k for k in REQUIRED if k not in tok]
    if missing:
        print(f"FAIL missing token(s): {', '.join(missing)}", file=sys.stderr)
        return 1
    bad = 0
    for label, fg, bg, need in PAIRS:
        r = evaluate(tok[fg], tok[bg], 16, False)["ratio"]
        ok = r >= need
        bad += not ok
        print(f"  {'pass' if ok else 'FAIL'} {r:>6.2f}:1  (needs {need})  {label}  "
              f"[{tok[fg]} on {tok[bg]}]")
    print(f"{len(PAIRS) - bad} of {len(PAIRS)} pairs pass" if bad else
          f"all {len(PAIRS)} pairs pass")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
