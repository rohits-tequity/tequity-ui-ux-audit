#!/usr/bin/env python3
"""Attach screenshots and marker frames to findings from Figma metadata alone.

After `save_screenshot.py` (per-screen PNGs named <node-id>.png) and
`crop_frames.py` (thumbnails of every frame plus screens.json), this script:

  1. resolves each finding's `location.node_id` to a node in the metadata,
     walks up to the top-level screen, and computes the node's pixel frame
     relative to that screen;
  2. when a screenshot of that screen exists, sets `evidence.image`,
     `evidence.frame` = [x, y, w, h] and `evidence.normalized` = false so
     build_report.py draws the coral marker at the exact node;
  3. fills `screens_detail`: full screenshots for screens that have one,
     thumbnails (`thumb: true`) for the rest, plus `flow_map` for the section
     image, so Section 2 shows every screen without a manual export.

  evidence_frames.py --findings audit/findings.json --metadata audit/onboarding/metadata.xml \
      --shots audit/shots [--screens-json audit/shots/screens.json] [--flow-map audit/shots/2288-13444.png] [--force]

Node ids in `location.node_id` may be a list: "1420:3412, I2217:9134;5:555 and 1420:3455".
Instance-internal ids (`I<instance>;<child>`) resolve to the instance node, because
metadata does not expand instance internals; the marker then outlines the instance.
The first id that resolves to a screen with a screenshot wins; a finding whose ids
all sit on screens without a screenshot is left as it was and listed in the summary.
Paths written into findings.json are relative to the findings file's directory.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import xml.etree.ElementTree as ET

ID_RE = re.compile(r"I?\d+:\d+(?:;\d+:\d+)*")


def _reject_xml_entities(path, limit=4 << 20):
    """Refuse a metadata file that declares a DOCTYPE or entities.

    ElementTree expands internal entities, so a crafted file can blow memory up
    (the billion laughs pattern). Figma metadata never needs a DOCTYPE, so the
    cheapest correct answer is to refuse one rather than add a dependency. The
    window is generous because the prolog can be padded with comments to push a
    DOCTYPE past a short prefix check.
    """
    with open(path, "rb") as fh:
        head = fh.read(limit).lower()
    for bad in (b"<!doctype", b"<!entity"):
        if bad in head:
            raise SystemExit(f"{path}: refusing XML that declares {bad.decode()}; "
                             "Figma metadata does not need one")


def index_metadata(path):
    _reject_xml_entities(path); root = ET.parse(path).getroot()
    nodes = {}  # id -> {abs_x, abs_y, w, h, screen_id, name}

    def walk(el, ox, oy, screen_id, depth):
        for ch in el:
            try:
                x, y = float(ch.get("x", 0)), float(ch.get("y", 0))
                w, h = float(ch.get("width", 0)), float(ch.get("height", 0))
            except (TypeError, ValueError):
                continue
            ax, ay = ox + x, oy + y
            sid = ch.get("id") if depth == 0 else screen_id
            nodes[ch.get("id")] = {"x": ax, "y": ay, "w": w, "h": h, "screen": sid, "name": ch.get("name", ""),
                                   "tag": ch.tag}
            walk(ch, ax, ay, sid, depth + 1)

    walk(root, 0.0, 0.0, None, 0)
    return root, nodes


def candidates(node_id_field):
    ids = []
    for m in ID_RE.findall(str(node_id_field or "")):
        base = m.split(";")[0].lstrip("I")
        if base not in ids:
            ids.append(base)
    return ids


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--findings", required=True)
    ap.add_argument("--metadata", required=True)
    ap.add_argument("--shots", required=True, help="directory with <node-id>.png full screenshots")
    ap.add_argument("--screens-json", help="screens.json from crop_frames.py (thumbnails for every frame)")
    ap.add_argument("--flow-map", help="section screenshot to show as the flow overview")
    ap.add_argument("--force", action="store_true", help="overwrite evidence.image/frame already set")
    ap.add_argument("--min-marker", type=float, default=8.0, help="grow markers smaller than this many px")
    a = ap.parse_args(argv)

    fdir = os.path.dirname(os.path.abspath(a.findings))
    rel = lambda p: os.path.relpath(os.path.abspath(p), fdir)
    data = json.load(open(a.findings))
    root, nodes = index_metadata(a.metadata)

    shots = {}
    for fn in os.listdir(a.shots):
        m = re.fullmatch(r"(\d+)-(\d+)\.png", fn)
        if m:
            shots[f"{m.group(1)}:{m.group(2)}"] = os.path.join(a.shots, fn)

    attached, left = [], []
    for f in data.get("findings", []):
        ev = f.setdefault("evidence", {})
        if ev.get("frame") and ev.get("image") and not a.force:
            continue
        loc = f.get("location") or {}
        done = False
        for nid in candidates(loc.get("node_id")) + candidates(loc.get("node")):
            n = nodes.get(nid)
            if not n:
                continue
            scr_id = n["screen"] or nid
            if scr_id not in shots:
                continue
            scr = nodes[scr_id]
            x, y = n["x"] - scr["x"], n["y"] - scr["y"]
            w, h = n["w"], n["h"]
            if w < a.min_marker or h < a.min_marker:
                gx, gy = max(0, (a.min_marker - w) / 2), max(0, (a.min_marker - h) / 2)
                x, y, w, h = x - gx, y - gy, w + 2 * gx, h + 2 * gy
            ev["image"] = rel(shots[scr_id])
            ev["frame"] = [round(x, 1), round(y, 1), round(w, 1), round(h, 1)]
            ev["normalized"] = False
            ev.setdefault("caption", f"{scr['name']} ({scr_id}): {n['name'] or n['tag']} {nid} outlined")
            ev.setdefault("alt", f"{scr['name']} screen with {n['name'] or 'the node'} outlined for {f.get('id')}")
            attached.append((f.get("id"), scr["name"], nid))
            done = True
            break
        if not done:
            left.append((f.get("id"), loc.get("node_id")))

    # screens_detail: merge existing entries with what the crops give us
    if a.screens_json:
        crops = json.load(open(a.screens_json))
        existing = {d.get("node_id"): d for d in data.get("screens_detail") or [] if d.get("node_id")}
        detail = []
        for c in crops:
            d = existing.get(c["id"], {"name": c["name"], "node_id": c["id"], "extracted": False})
            d["name"] = d.get("name") or c["name"]
            if c["id"] in shots:
                d["image"] = rel(shots[c["id"]])
                d.pop("thumb", None)
            else:
                d["image"] = rel(c["image"])
                d["thumb"] = True
            d.setdefault("depth", "colour, type, tokens and geometry" if d.get("extracted") else "geometry only")
            # short alias so finding locations like "D04 to D09" match this screen
            short = re.split(r"\s*[·|:]\s*", d["name"])[0].strip()
            if short and short != d["name"]:
                d.setdefault("aliases", [short])
            detail.append(d)
        # keep entries the crops did not cover (e.g. grouped rows) at the end
        covered = {d["node_id"] for d in detail}
        detail += [d for d in data.get("screens_detail") or [] if d.get("node_id") not in covered and d.get("image")]
        data["screens_detail"] = detail
        data["screen_count"] = len([d for d in detail if not d.get("thumb")]) + len([d for d in detail if d.get("thumb")])
    if a.flow_map:
        data["flow_map"] = {"image": rel(a.flow_map), "caption": f"{root.get('name', 'Section')} ({root.get('id')}): every frame in the audited section, rendered from Figma"}

    json.dump(data, open(a.findings, "w"), indent=2, ensure_ascii=False)
    print(json.dumps({"attached": len(attached), "without_screenshot": len(left),
                      "screens_detail": len(data.get("screens_detail") or [])}))
    for t in attached:
        print(f"  marked {t[0]:<9} on {t[1]} via {t[2]}")
    for t in left:
        print(f"  no shot {t[0]:<9} ids: {t[1]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
