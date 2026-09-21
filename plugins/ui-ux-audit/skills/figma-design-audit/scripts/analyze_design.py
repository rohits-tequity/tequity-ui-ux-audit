#!/usr/bin/env python3
"""Deterministic measurement pass over cached Figma payloads.

Inputs (all optional, but supply what you have):
  --metadata        get_metadata XML  -> geometry checks
  --design-context  get_design_context text -> colour / type checks
  --variables       get_variable_defs JSON -> token conformance
  --platform        ios | android | web | rn   (default web)

Output: JSON with `measurements` (raw numbers) and `findings` (candidate
findings, each with evidence). Findings are CANDIDATES: the skill classifies,
confirms and may drop them. Nothing here is presented to the user unchanged.

Every finding carries `basis` so the report can say how it was determined, and
`confidence` (measured | inferred) so nothing guessed is reported as fact.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import xml.etree.ElementTree as ET
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from contrast import evaluate as contrast_eval, parse_color  # noqa: E402

# "rn" grades against the stricter of iOS and Android on every axis, because a
# React Native screen ships to both.
PLATFORM_TARGET = {"ios": 44.0, "android": 48.0, "web": 24.0, "rn": 48.0}
PLATFORM_BODY_TYPE = {"ios": 17.0, "android": 14.0, "web": 16.0, "rn": 17.0}
WCAG_TARGET_MIN = 24.0
ABSOLUTE_TYPE_FLOOR = 11.0  # below this, text is illegible on any platform

INTERACTIVE_RE = re.compile(
    r"\b(button|btn|cta|link|tab|chip|toggle|switch|checkbox|radio|input|field|"
    r"select|dropdown|picker|slider|stepper|fab|icon[-_ ]?button|iconbtn|close|"
    r"menu|nav[-_ ]?item|list[-_ ]?item|row|card|avatar[-_ ]?button|pressable|"
    r"touchable)\b", re.I)
OVERLAY_RE = re.compile(
    r"\b(header|appbar|app[-_ ]?bar|navbar|topbar|bottom[-_ ]?bar|tabbar|"
    r"tab[-_ ]?bar|toolbar|fab|sheet|snackbar|toast|banner|sticky|overlay|"
    r"modal|dialog)\b", re.I)
ICON_ONLY_RE = re.compile(r"\b(icon|glyph|chevron|arrow|close|more|kebab|ellipsis)\b", re.I)
IMAGE_RE = re.compile(r"\b(image|img|photo|picture|illustration|avatar|thumbnail|hero|banner|video)\b", re.I)

NAMED_COLORS = "white|black|red|green|blue|gray|grey|transparent"
# Literal colours. A bare colour WORD only counts in a value position (after a
# ':' or '=' and not part of a hyphenated identifier), otherwise Tailwind and
# BEM class names like "bg-blue-500" register as hardcoded colours.
COLOR_RE = re.compile(
    r"(#[0-9a-fA-F]{3,8}\b|rgba?\([^)]*\)"
    rf"|(?<=[:=])\s*[\"']?(?:{NAMED_COLORS})\b(?![-\w]))", re.I)
FONT_SIZE_RE = re.compile(r"font[-_]?size\s*[:=]\s*[\"']?\s*([0-9.]+)\s*(px|pt|sp|rem|em)?", re.I)
LINE_HEIGHT_RE = re.compile(r"line[-_]?height\s*[:=]\s*[\"']?\s*([0-9.]+)\s*(px|pt|sp|rem|em|%)?", re.I)
FONT_WEIGHT_RE = re.compile(r"font[-_]?weight\s*[:=]\s*[\"']?\s*([0-9]{3}|bold|semibold|medium|regular)", re.I)
OPACITY_RE = re.compile(r"opacity\s*[:=]\s*[\"']?\s*([0-9.]+)", re.I)
VAR_REF_RE = re.compile(r"(var\(--[^)]+\)|\$[A-Za-z][\w./-]+|tokens?\.[\w.]+|\{[\w./-]+\})")
SPACING_RE = re.compile(
    r"(?:padding|margin|gap|row-gap|column-gap)[\w-]*\s*[:=]\s*[\"']?([^;\"'\n]+)", re.I)
RADIUS_RE = re.compile(r"border[-_]?radius\s*[:=]\s*[\"']?\s*([0-9.]+)", re.I)


def _read_xml(path, limit=4 << 20):
    """Return the XML document from a saved Figma metadata response.

    The MCP wraps its XML in prose: a "Currently selected nodes:" preamble and
    an "IMPORTANT: ..." note after the closing tag. Saving the response
    verbatim is the right thing to do, so the trimming happens here rather than
    asking every caller to hand-edit the cache. The entity check runs on the
    whole file, not just the slice, so nothing can hide in the prose either.
    """
    with open(path, "rb") as fh:
        raw = fh.read(limit)
    low = raw.lower()
    for bad in (b"<!doctype", b"<!entity"):
        if bad in low:
            raise SystemExit(f"{path}: refusing XML that declares {bad.decode()}; "
                             "Figma metadata does not need one")
    text = raw.decode("utf-8", "replace")
    start = text.find("<")
    end = text.rfind(">")
    if start < 0 or end < start:
        raise SystemExit(f"{path}: no XML element found in the saved response")
    return text[start:end + 1]


def find_colors(s):
    """Every colour literal in a string, in order, normalised."""
    return [m.group(0).strip().strip("\"'") for m in COLOR_RE.finditer(s)]


def declarations(text):
    """Yield (line_number, declaration) so `a: x; b: y` is two units, not one.

    Line-at-a-time parsing mispairs foreground and background when a rule is
    written on one line; splitting on ';' fixes that. A '}' yields a scope
    marker so a background does not leak into every later rule.
    """
    for i, line in enumerate(text.splitlines(), 1):
        for part in re.split(r"[;{]", line):
            part = part.strip()
            if part:
                yield i, part
        if "}" in line:
            yield i, "\x00SCOPE_END"


# --------------------------------------------------------------------------- #
# Tailwind / JSX normaliser
# --------------------------------------------------------------------------- #
# Figma's get_design_context returns React + Tailwind with arbitrary values,
# not CSS. Rewrite each className into a CSS-like block on the same line so the
# declaration parser sees `color: ...; font-size: ...; background: ...` and the
# scope logic pairs foreground with the element's own or enclosing background.
# Double-quoted or template-literal className only: Tailwind font classes carry
# single quotes inside (font-['DM_Sans:Regular']), so a quote-agnostic pattern
# would cut the class list short.
TW_CLASS_RE = re.compile(r'className=(?:"([^"]*)"|\{`([^`]*)`\}|\{"([^"]*)"\})')
TW_VAR_FALLBACK_RE = re.compile(r"var\((--[\w/\\-]+),\s*([^)]+)\)")
TW_WEIGHT = {"font-thin": 100, "font-extralight": 200, "font-light": 300, "font-normal": 400,
             "font-medium": 500, "font-semibold": 600, "font-bold": 700, "font-extrabold": 800}
TW_NAMED_BG = {"bg-white": "#ffffff", "bg-black": "#000000", "bg-transparent": "transparent"}


def _tw_value(v):
    """Resolve `var(--x,#hex)` to `var(--x) #hex` so the var reference is kept
    (not hardcoded) and the fallback is the measurable colour."""
    v = v.replace("_", " ")
    m = TW_VAR_FALLBACK_RE.search(v)
    if m:
        return f"{m.group(2).strip()} /* {m.group(1)} */ var({m.group(1)})"
    return v


def tailwind_to_css(text):
    if "className=" not in text:
        return text
    out_lines = []
    for line in text.splitlines():
        m = TW_CLASS_RE.search(line)
        if not m:
            out_lines.append(line)
            continue
        decls = []
        classes = next((g for g in m.groups() if g is not None), "")
        for cls in classes.split():
            c = cls.strip()
            if c.startswith("text-[color:"):
                decls.append("color: " + _tw_value(c[len("text-[color:"):-1]))
            elif c.startswith("text-[") and c.endswith("px]"):
                decls.append("font-size: " + c[6:-1])
            elif c.startswith("text-[#") or c.startswith("text-[rgb") or c.startswith("text-[var"):
                decls.append("color: " + _tw_value(c[6:-1]))
            elif c.startswith("leading-["):
                v = c[9:-1]
                if v != "normal":
                    decls.append("line-height: " + v)
            elif c.startswith("bg-[") and not c.startswith("bg-[url") and "gradient" not in c:
                decls.append("background: " + _tw_value(c[4:-1]))
            elif c in TW_NAMED_BG:
                decls.append("background: " + TW_NAMED_BG[c])
            elif c in TW_WEIGHT:
                decls.append(f"font-weight: {TW_WEIGHT[c]}")
            elif c.startswith("border-[") and ("#" in c or "var(" in c or "rgb" in c):
                decls.append("border-color: " + _tw_value(c[8:-1]))
            elif c.startswith("rounded-[") or c.startswith("rounded-t") or c.startswith("rounded-b"):
                if "[" in c:
                    decls.append("border-radius: " + _tw_value(c[c.index("[") + 1:-1]))
            elif c.startswith(("p-[", "px-[", "py-[", "pl-[", "pr-[", "pt-[", "pb-[", "gap-[")):
                decls.append("padding: " + _tw_value(c[c.index("[") + 1:-1]))
            elif c.startswith("opacity-[") or c.startswith("opacity-"):
                v = c.split("-", 1)[1].strip("[]")
                if v.isdigit():
                    decls.append(f"opacity: {int(v) / 100}")
            elif c.startswith("tracking-["):
                decls.append("letter-spacing: " + c[10:-1])
            elif c.startswith(("h-[", "w-[", "size-[")):
                decls.append(("height" if c[0] == "h" else "width" if c[0] == "w" else "size") + ": " + _tw_value(c[c.index("[") + 1:-1]))
        css = "{ " + "; ".join(decls) + "; }" if decls else "{ }"
        out_lines.append(line[:m.start()] + css + line[m.end():])
    return "\n".join(out_lines)


def fnum(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


# --------------------------------------------------------------------------- #
# metadata (geometry)
# --------------------------------------------------------------------------- #

def parse_metadata(path):
    """Tolerant XML walk: collect every element that carries geometry."""
    nodes = []
    try:
        root = ET.fromstring(_read_xml(path))
    except ET.ParseError as e:
        return nodes, f"metadata XML unparseable: {e}"

    def attr(el, *names):
        for n in names:
            for k, v in el.attrib.items():
                if k.lower() == n:
                    return v
        return None

    def walk(el, parent, depth, order):
        nid = attr(el, "id", "guid", "nodeid", "node-id")
        name = attr(el, "name", "label") or el.tag
        x, y = fnum(attr(el, "x", "left")), fnum(attr(el, "y", "top"))
        w, h = fnum(attr(el, "width", "w")), fnum(attr(el, "height", "h"))
        # Figma metadata coordinates are relative to the parent. Keep absolute
        # coordinates too, so intersections and distances are only ever
        # computed in one coordinate space, and remember which top-level
        # screen the node belongs to so nodes on different screens never
        # "overlap".
        ax = (parent["ax"] if parent and parent.get("ax") is not None else 0.0) + (x or 0.0) if x is not None else None
        ay = (parent["ay"] if parent and parent.get("ay") is not None else 0.0) + (y or 0.0) if y is not None else None
        in_comp = bool(parent and parent.get("in_component")) or el.tag in ("component", "component-set")
        rec = {
            "id": nid, "name": name, "type": el.tag,
            "x": x, "y": y, "w": w, "h": h,
            "ax": ax, "ay": ay,
            "screen": (parent["screen"] if parent and parent.get("screen") else nid) if depth > 0 else None,
            "in_component": in_comp,
            # keep the parent RECORD, not its name, two layers called "Label"
            # must not resolve to the same parent
            "parent": parent["name"] if parent else None,
            "parent_id": parent["id"] if parent else None,
            "parent_h": parent["h"] if parent else None,
            "depth": depth, "order": order[0],
            "text": (el.text or "").strip() or attr(el, "characters", "text") or "",
        }
        order[0] += 1
        has_geom = w is not None and h is not None
        if has_geom:
            nodes.append(rec)
        for child in list(el):
            walk(child, rec if has_geom else parent, depth + 1, order)

    walk(root, None, 0, [0])
    if not nodes:
        return nodes, "metadata XML parsed but no element carried width/height, geometry NOT EVALUATED"
    return nodes, None


def is_interactive(n):
    hay = f"{n.get('name') or ''} {n.get('type') or ''}"
    return bool(INTERACTIVE_RE.search(hay))


def geometry_findings(nodes, platform, include_components=False):
    plat_min = PLATFORM_TARGET.get(platform, 24.0)
    findings = []
    measurements = {"node_count": len(nodes), "platform_target_min": plat_min}

    inter = [n for n in nodes if is_interactive(n)]
    measurements["interactive_node_count"] = len(inter)
    # component and component-set definitions are specs, not screens: their
    # geometry is graded once where the instance is used, not per variant
    comp = [n for n in inter if n.get("in_component")]
    if comp and not include_components:
        measurements["interactive_in_component_definitions_skipped"] = len(comp)
        inter = [n for n in inter if not n.get("in_component")]

    # --- target size ------------------------------------------------------- #
    for n in inter:
        w, h = n["w"], n["h"]
        if w is None or h is None:
            continue
        smaller = min(w, h)
        if smaller < WCAG_TARGET_MIN:
            sev, crit = "serious", "WCAG 2.2 SC 2.5.8 (Target Size Minimum)"
        elif smaller < plat_min:
            sev, crit = "moderate", f"{platform.upper()} platform minimum {plat_min:g}"
        else:
            continue
        findings.append({
            "check": "target_size", "severity": sev, "criterion": crit,
            "node": n["name"], "node_id": n["id"], "confidence": "inferred",
            "basis": "layer name matched an interactive pattern; frame size from get_metadata",
            "measured": {"width": w, "height": h, "required": max(WCAG_TARGET_MIN, plat_min)},
            "detail": f"{w:g}x{h:g} against a {max(WCAG_TARGET_MIN, plat_min):g} minimum",
            "fix": "Increase the frame, or add padding / hitSlop so the tappable area reaches the minimum without changing the glyph size.",
        })

    # --- target spacing ---------------------------------------------------- #
    for i, a in enumerate(inter):
        if None in (a["ax"], a["ay"], a["w"], a["h"]):
            continue
        ax, ay = a["ax"] + a["w"] / 2, a["ay"] + a["h"] / 2
        best = None
        for j, b in enumerate(inter):
            if i == j or None in (b["ax"], b["ay"], b["w"], b["h"]) or b.get("screen") != a.get("screen"):
                continue
            bx, by = b["ax"] + b["w"] / 2, b["ay"] + b["h"] / 2
            d = ((ax - bx) ** 2 + (ay - by) ** 2) ** 0.5
            if best is None or d < best[0]:
                best = (d, b)
        if best and best[0] < WCAG_TARGET_MIN and min(a["w"], a["h"]) < WCAG_TARGET_MIN:
            findings.append({
                "check": "target_spacing", "severity": "serious",
                "criterion": "WCAG 2.2 SC 2.5.8 (spacing exception)",
                "node": a["name"], "node_id": a["id"], "confidence": "inferred",
                "basis": "centre-to-centre distance between adjacent interactive frames",
                "measured": {"distance": round(best[0], 1), "required": WCAG_TARGET_MIN,
                             "neighbour": best[1]["name"]},
                "detail": f"{round(best[0], 1)}px from '{best[1]['name']}' while itself under 24px",
                "fix": "Separate the targets to at least 24px centre-to-centre, or enlarge both to 24x24.",
            })

    # --- overlay occlusion (SC 2.4.11) ------------------------------------- #
    overlays = [n for n in nodes if OVERLAY_RE.search(n.get("name") or "")]
    for ov in overlays:
        if None in (ov["ax"], ov["ay"], ov["w"], ov["h"]):
            continue
        for n in inter:
            if n is ov or None in (n["ax"], n["ay"], n["w"], n["h"]) or n.get("screen") != ov.get("screen"):
                continue
            if n.get("parent_id") == ov["id"] or ov.get("parent_id") == n["id"]:
                continue  # a control inside its own bar is not obscured by it
            ox2, oy2 = ov["ax"] + ov["w"], ov["ay"] + ov["h"]
            nx2, ny2 = n["ax"] + n["w"], n["ay"] + n["h"]
            ix = max(0, min(ox2, nx2) - max(ov["ax"], n["ax"]))
            iy = max(0, min(oy2, ny2) - max(ov["ay"], n["ay"]))
            if ix > 0 and iy > 0 and (ix * iy) / max(1.0, n["w"] * n["h"]) > 0.15:
                findings.append({
                    "check": "focus_obscured", "severity": "moderate",
                    "criterion": "WCAG 2.2 SC 2.4.11 (Focus Not Obscured)",
                    "node": n["name"], "node_id": n["id"], "confidence": "inferred",
                    "basis": "bounding-box intersection between a fixed overlay and an interactive node",
                    "measured": {"overlay": ov["name"],
                                 "overlap_fraction": round((ix * iy) / (n["w"] * n["h"]), 2)},
                    "detail": f"'{ov['name']}' covers part of '{n['name']}'",
                    "fix": "Add scroll padding equal to the overlay height, or scroll the focused element clear of it.",
                })
                break

    # --- reading order (SC 1.3.2) ----------------------------------------- #
    ordered = [n for n in nodes if n["x"] is not None and n["y"] is not None and n.get("text")]
    if len(ordered) > 2:
        visual = sorted(ordered, key=lambda n: (round(n["y"] / 8), n["x"]))
        inversions = [
            {"layer_position": i, "visual_position": visual.index(n), "node": n["name"]}
            for i, n in enumerate(ordered)
            if abs(visual.index(n) - i) > 1
        ]
        measurements["reading_order_inversions"] = len(inversions)
        if inversions:
            findings.append({
                "check": "reading_order", "severity": "moderate",
                "criterion": "WCAG SC 1.3.2 (Meaningful Sequence)",
                "node": "screen", "node_id": None, "confidence": "inferred",
                "basis": "layer order compared against nodes sorted top-to-bottom, left-to-right",
                "measured": {"inversions": len(inversions), "examples": inversions[:5]},
                "detail": f"{len(inversions)} node(s) sit in a different layer order than visual order",
                "fix": "Reorder layers to match the intended reading order, or declare an explicit focus/reading order in the handoff spec. Confirm at runtime.",
            })

    # --- text growth slack (SC 1.4.4) ------------------------------------- #
    # A text node whose parent frame is the same height has nowhere to grow when
    # the user raises the system font size. Measured from geometry alone.
    tight_containers = []
    for n in nodes:
        is_text = (n.get("type", "").upper() == "TEXT"
                   or re.search(r"\b(text|label|title|caption|body)\b",
                                n.get("name") or "", re.I))
        if not is_text or n["h"] is None or n.get("parent_h") is None:
            continue
        slack = n["parent_h"] - n["h"]
        if 0 <= slack < max(4.0, n["h"] * 0.15):
            tight_containers.append({
                "node": n["name"], "node_id": n["id"],
                "text_height": n["h"], "container": n["parent"],
                "container_id": n["parent_id"],
                "container_height": n["parent_h"], "slack": round(slack, 1),
            })
    measurements["tight_text_containers"] = len(tight_containers)
    if tight_containers:
        findings.append({
            "check": "text_growth_slack", "severity": "moderate",
            "criterion": "WCAG SC 1.4.4 (Resize Text)",
            "node": "screen", "node_id": None, "confidence": "inferred",
            "basis": "text node height compared against its parent frame height; "
                     "less than 15% slack means no room for a larger font scale",
            "measured": {"count": len(tight_containers),
                         "examples": tight_containers[:8]},
            "detail": f"{len(tight_containers)} text node(s) sit in a container "
                      f"with no vertical slack for font scaling",
            "fix": "Use a minimum height with auto-layout rather than a fixed "
                   "height, so the container grows with the text.",
            "requires": "runtime_font_scale_pass",
        })

    # --- alt text / icon-only controls ------------------------------------ #
    for n in nodes:
        nm = n.get("name") or ""
        if IMAGE_RE.search(nm) and not re.search(r"\b(alt|label|a11y|aria|decorative)\b", nm, re.I):
            findings.append({
                "check": "alt_text_spec", "severity": "serious",
                "criterion": "WCAG SC 1.1.1 (Non-text Content)",
                "node": nm, "node_id": n["id"], "confidence": "inferred",
                "basis": "image-like layer with no alt/label/decorative annotation in its name",
                "measured": {},
                "detail": "No alt-text or decorative marking specified in the design",
                "fix": "Annotate the layer with its alt text, or mark it decorative so it is hidden from assistive tech.",
            })
    for n in (x for x in nodes if is_interactive(x)):
        nm = n.get("name") or ""
        if ICON_ONLY_RE.search(nm) and not n.get("text") and not re.search(r"\b(label|a11y|aria)\b", nm, re.I):
            findings.append({
                "check": "accessible_name_spec", "severity": "serious",
                "criterion": "WCAG SC 4.1.2 (Name, Role, Value)",
                "node": nm, "node_id": n["id"], "confidence": "inferred",
                "basis": "interactive icon layer with no visible text and no accessible-name annotation",
                "measured": {},
                "detail": "Icon-only control with no accessible name specified",
                "fix": "Specify accessibilityLabel / aria-label in the component spec.",
            })

    return findings, measurements


# --------------------------------------------------------------------------- #
# design context (colour + type)
# --------------------------------------------------------------------------- #

def analyze_design_context(text, variables, platform):
    findings = []
    measurements = {}
    lines = text.splitlines()
    token_values = {}
    for k, v in (variables or {}).items():
        c = parse_color(v)
        if c:
            token_values[str(v).strip().lower()] = k
    allowed_colors = set(token_values.keys())

    colors = find_colors(text)
    measurements["colour_literal_count"] = len(colors)
    measurements["unique_colour_literals"] = len(set(c.lower() for c in colors))

    # hardcoded colours: a literal in a declaration with no variable reference
    hardcoded = defaultdict(list)
    for lineno, decl in declarations(text):
        if decl == "\x00SCOPE_END" or VAR_REF_RE.search(decl):
            continue
        for c in find_colors(decl):
            norm = c.lower()
            if allowed_colors and norm in allowed_colors:
                continue  # value matches a token even if referenced literally
            hardcoded[norm].append(lineno)
    if hardcoded:
        findings.append({
            "check": "hardcoded_colour", "severity": "minor",
            "criterion": "Design-system conformance",
            "node": "screen", "node_id": None, "confidence": "measured",
            "basis": "colour literal in the design-context payload with no variable reference on the same line",
            "measured": {"count": sum(len(v) for v in hardcoded.values()),
                         "values": dict(list(hardcoded.items())[:15])},
            "detail": f"{len(hardcoded)} distinct colour value(s) used without a token",
            "fix": "Bind these to existing variables, or add the value to the system if it is genuinely new.",
        })

    # type scale
    sizes = [fnum(m[0]) for m in FONT_SIZE_RE.findall(text)]
    sizes = [s for s in sizes if s]
    measurements["font_sizes"] = sorted(set(sizes))
    body_min = PLATFORM_BODY_TYPE.get(platform, 16.0)
    below_floor = sorted({s for s in sizes if s < ABSOLUTE_TYPE_FLOOR})
    if below_floor:
        findings.append({
            "check": "font_size_floor", "severity": "serious",
            "criterion": f"Absolute legibility floor ({ABSOLUTE_TYPE_FLOOR:g})",
            "node": "screen", "node_id": None, "confidence": "measured",
            "basis": "font-size values parsed from the design-context payload",
            "measured": {"values": below_floor, "floor": ABSOLUTE_TYPE_FLOOR},
            "detail": f"Text at {', '.join(f'{s:g}' for s in below_floor)}: "
                      f"below the {ABSOLUTE_TYPE_FLOOR:g} absolute floor",
            "fix": "Raise above the floor, or remove the content if it is not worth reading.",
        })
    below_body = sorted({s for s in sizes
                         if ABSOLUTE_TYPE_FLOOR <= s < body_min})
    if below_body:
        findings.append({
            "check": "font_size_body", "severity": "minor",
            "criterion": f"{platform.upper()} body type guidance ({body_min:g})",
            "node": "screen", "node_id": None, "confidence": "inferred",
            "basis": "font-size values below the platform body size; whether each "
                     "is body copy or a legitimate caption needs confirmation",
            "measured": {"values": below_body, "platform_body_min": body_min},
            "detail": f"Text at {', '.join(f'{s:g}' for s in below_body)}: "
                      f"under the {body_min:g} platform body size",
            "fix": "Use the body type token for body copy; confirm the rest are "
                   "intentional captions or labels.",
        })

    # line height ratios
    pairs = []
    for i, line in enumerate(lines):
        fs = FONT_SIZE_RE.search(line)
        # Prefer a line-height declared on the same element (same line after the
        # Tailwind normaliser); only then look at neighbouring lines.
        lh = LINE_HEIGHT_RE.search(line)
        if fs and not lh:
            window = "\n".join(lines[max(0, i - 3): i + 4])
            lh = LINE_HEIGHT_RE.search(window)
        if fs and lh:
            f, l = fnum(fs.group(1)), fnum(lh.group(1))
            if not f or not l:
                continue
            unit = (lh.group(2) or "").lower()
            if unit == "%":
                ratio_v = l / 100.0
            elif unit in ("em", "rem") or l < 4:
                ratio_v = l
            else:
                ratio_v = l / f
            pairs.append({"font_size": f, "line_height": l, "ratio": round(ratio_v, 2), "line": i + 1})
    tight = [p for p in pairs if p["ratio"] < 1.5 and p["font_size"] <= 20]
    measurements["line_height_samples"] = pairs[:40]
    if tight:
        findings.append({
            "check": "line_height", "severity": "moderate",
            "criterion": "WCAG SC 1.4.12 (Text Spacing)",
            "node": "screen", "node_id": None, "confidence": "measured",
            "basis": "line-height divided by font-size for body-sized text",
            "measured": {"samples": tight[:10], "required_ratio": 1.5},
            "detail": f"{len(tight)} body text style(s) under a 1.5 line-height ratio",
            "fix": "Set body line height to at least 1.5x and confirm the container absorbs the extra height.",
        })

    # Contrast pairs. Declaration-level parsing, so `color: X; background: Y`
    # on one line pairs correctly; the background resets at each scope end.
    # Two passes per scope: find the scope's background first, then evaluate
    # each foreground against it. A single pass mispairs `color: X; background: Y`
    # because the foreground is read before the background exists.
    scopes, current = [], []
    for lineno, decl in declarations(text):
        if decl == "\x00SCOPE_END":
            if current:
                scopes.append(current)
            current = []
        else:
            current.append((lineno, decl))
    if current:
        scopes.append(current)

    contrast_results = []
    inherited_bg = None      # a page-level background carries into later scopes
    for scope in scopes:
        scope_bg = None
        for lineno, decl in scope:
            if re.search(r"background(-color)?\s*[:=]", decl, re.I):
                cs = find_colors(decl)
                if cs:
                    scope_bg = cs[-1]
        if scope_bg:
            inherited_bg = scope_bg
        bg_current = scope_bg or inherited_bg
        for lineno, decl in scope:
            if re.search(r"background(-color)?\s*[:=]", decl, re.I):
                continue
            if not re.search(r"(^|[^-\w])(color|tint|fill)\s*[:=]", decl, re.I):
                continue
            cs = find_colors(decl)
            if not cs:
                continue
            fg = cs[-1]
            window = "\n".join(lines[max(0, lineno - 6): lineno + 5])
            fs = FONT_SIZE_RE.search(window)
            fw = FONT_WEIGHT_RE.search(window)
            op = OPACITY_RE.search(window)
            bold = False
            if fw:
                w = fw.group(1).lower()
                bold = w in ("bold", "semibold") or (w.isdigit() and int(w) >= 600)
            if not bg_current:
                contrast_results.append({
                    "line": lineno, "fg": fg, "bg": None, "status": "indeterminate",
                    "reason": "no background colour resolved in scope (image, "
                              "gradient, translucency or inherited)",
                })
                continue
            pfg, pbg = parse_color(fg), parse_color(bg_current)
            if pfg and pbg and pfg[:3] == pbg[:3]:
                # Identical colour on both sides is a parsing artefact (an
                # inherited background matched against the same value), not a
                # 1:1 contrast failure.
                continue
            res = contrast_eval(
                fg, bg_current,
                fnum(fs.group(1)) if fs else None, bold, False,
                fnum(op.group(1)) if op else 1.0,
            )
            res["line"] = lineno
            res["bg_source"] = "scope" if scope_bg else "inherited"
            contrast_results.append(res)

    measurements["contrast_results"] = contrast_results
    fails = [r for r in contrast_results if r.get("status") == "measured" and not r.get("passes_aa")]
    indet = [r for r in contrast_results if r.get("status") == "indeterminate"]
    for r in fails:
        # SC 1.4.3 is Level AA, so the rubric rates a contrast failure `serious`.
        # Escalation to `critical` requires the blocked-primary-task test, which
        # a script cannot evaluate, the classification step decides that.
        findings.append({
            "check": "contrast", "severity": "serious",
            "confidence": "measured" if r.get("bg_source") == "scope" else "inferred",
            "bg_source": r.get("bg_source"),
            "escalate_if": "on a primary path and the text is essential to "
                           "completing the task (ratio "
                           f"{r['ratio']} is {'far below' if r['ratio'] < 3.0 else 'below'} "
                           "the threshold)",
            "criterion": "WCAG SC 1.4.3 (Contrast Minimum)",
            "node": f"text @ line {r['line']}", "node_id": None,
            "basis": "WCAG 2.x relative-luminance ratio, alpha composited"
                     + ("" if r.get("bg_source") == "scope"
                        else "; background inherited from an enclosing rule: "
                             "confirm the real backdrop"),
            "measured": {"ratio": r["ratio"], "required": r["aa_threshold"],
                         "fg": r["fg"], "bg": r["bg"], "kind": r["kind"],
                         "shortfall": r["shortfall"]},
            "detail": f"{r['ratio']}:1 against a {r['aa_threshold']}:1 requirement ({r['kind']})",
            "fix": "Darken the foreground or lighten the background token until the ratio clears the threshold. Recompute in every variable mode.",
        })
    if indet:
        findings.append({
            "check": "contrast_indeterminate", "severity": "info",
            "criterion": "WCAG SC 1.4.3: Not Evaluated",
            "node": "screen", "node_id": None, "confidence": "measured",
            "basis": "text colour with no resolvable background in the design payload",
            "measured": {"count": len(indet), "lines": [r["line"] for r in indet][:20]},
            "detail": f"{len(indet)} text colour(s) sit over an unresolved backdrop, contrast cannot be determined from the design",
            "fix": "Measure these at runtime with a pixel probe (implementation-audit skill). Do not report them as passing.",
            "requires": "runtime_pixel_probe",
        })

    # spacing scale drift
    spac = []
    for m in SPACING_RE.findall(text):
        for tok in re.findall(r"(-?[0-9.]+)\s*(px|pt|dp|rem)?", m):
            v = fnum(tok[0])
            if v is not None and v != 0:
                spac.append(abs(v))
    if spac:
        base = 4 if any(abs(v) % 4 == 0 for v in spac) else None
        off = sorted({v for v in spac if base and v % base != 0 and v < 200})
        measurements["spacing_values"] = sorted(set(spac))[:60]
        if off:
            findings.append({
                "check": "spacing_scale", "severity": "minor",
                "criterion": "Design-system conformance",
                "node": "screen", "node_id": None, "confidence": "measured",
                "basis": f"spacing values not divisible by the inferred {base}px base unit",
                "measured": {"off_scale": off[:20], "base_unit": base},
                "detail": f"{len(off)} spacing value(s) off the {base}px scale",
                "fix": "Snap to the nearest scale step or justify the exception in the system docs.",
            })

    radii = sorted({fnum(v) for v in RADIUS_RE.findall(text) if fnum(v) is not None})
    measurements["radii"] = radii
    if len(radii) > 5:
        findings.append({
            "check": "radius_drift", "severity": "minor",
            "criterion": "Design-system conformance",
            "node": "screen", "node_id": None, "confidence": "measured",
            "basis": "distinct border-radius values in one screen",
            "measured": {"values": radii},
            "detail": f"{len(radii)} distinct corner radii on a single screen",
            "fix": "Reduce to the system's radius tokens.",
        })

    return findings, measurements


# --------------------------------------------------------------------------- #
# variables (token hygiene, mode coverage)
# --------------------------------------------------------------------------- #

def analyze_variables(variables):
    findings, measurements = [], {}
    if not variables:
        return findings, measurements
    measurements["variable_count"] = len(variables)
    colour_vars = {k: v for k, v in variables.items() if parse_color(v)}
    measurements["colour_variable_count"] = len(colour_vars)

    by_value = defaultdict(list)
    for k, v in colour_vars.items():
        by_value[str(v).strip().lower()].append(k)
    dupes = {v: ks for v, ks in by_value.items() if len(ks) > 1}
    if dupes:
        findings.append({
            "check": "duplicate_tokens", "severity": "minor",
            "criterion": "Design-system conformance",
            "node": "variables", "node_id": None, "confidence": "measured",
            "basis": "two or more variables resolving to the identical colour value",
            "measured": {"groups": {k: v for k, v in list(dupes.items())[:10]}},
            "detail": f"{len(dupes)} colour value(s) exposed under more than one token name",
            "fix": "Alias the duplicates to one source token so a future colour change lands once.",
        })

    modes = sorted({m.group(1).lower() for k in variables
                    for m in [re.search(r"\b(light|dark)\b", k, re.I)] if m})
    measurements["modes_detected"] = modes
    if len(modes) == 1:
        findings.append({
            "check": "mode_coverage", "severity": "moderate",
            "criterion": "Dark-mode / mode parity",
            "node": "variables", "node_id": None, "confidence": "inferred",
            "basis": "only one colour mode is discoverable in the variable names",
            "measured": {"modes": modes},
            "detail": f"Only the '{modes[0]}' mode appears in the token set",
            "fix": "Define the counterpart mode and re-run every contrast check in it.",
        })
    return findings, measurements


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--metadata")
    ap.add_argument("--design-context")
    ap.add_argument("--variables")
    ap.add_argument("--platform", default="web",
                    choices=["ios", "android", "web", "rn"])
    ap.add_argument("--out", required=True)
    ap.add_argument("--include-components", action="store_true",
                    help="also grade geometry inside component and component-set definitions (off: instances only)")
    a = ap.parse_args(argv)

    findings, measurements, notes = [], {"platform": a.platform}, []

    if a.metadata and os.path.exists(a.metadata):
        nodes, err = parse_metadata(a.metadata)
        if err:
            notes.append(err)
        f, m = geometry_findings(nodes, a.platform, a.include_components)
        findings += f
        measurements.update(m)
    else:
        notes.append("no metadata payload: geometry checks NOT EVALUATED")

    variables = None
    if a.variables and os.path.exists(a.variables):
        with open(a.variables) as fh:
            raw = json.load(fh)
        variables = raw if isinstance(raw, dict) else {
            str(i): v for i, v in enumerate(raw)}
        f, m = analyze_variables(variables)
        findings += f
        measurements.update(m)
    else:
        notes.append("no variable payload: token conformance NOT EVALUATED")

    if a.design_context and os.path.exists(a.design_context):
        with open(a.design_context, errors="replace") as fh:
            text = fh.read()
        if "className=" in text:
            text = tailwind_to_css(text)
            notes.append("design context was Tailwind/JSX; normalised to CSS declarations before analysis")
        f, m = analyze_design_context(text, variables, a.platform)
        findings += f
        measurements.update(m)
    else:
        notes.append("no design-context payload: colour and type checks NOT EVALUATED")

    for i, f in enumerate(findings, 1):
        f.setdefault("id", f"M-{i:03d}")

    counts = defaultdict(int)
    for f in findings:
        counts[f["severity"]] += 1

    out = {
        "platform": a.platform,
        "notes": notes,
        "severity_counts": dict(counts),
        "measurements": measurements,
        "findings": findings,
    }
    with open(a.out, "w") as fh:
        json.dump(out, fh, indent=2)
    print(f"{len(findings)} candidate finding(s) -> {a.out}")
    for k in ("critical", "serious", "moderate", "minor", "info"):
        if counts.get(k):
            print(f"  {k}: {counts[k]}")
    for n in notes:
        print(f"  note: {n}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
