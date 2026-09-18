#!/usr/bin/env python3
"""Cut every top-level screen out of one section/page screenshot.

One `get_screenshot` of the section that holds the flow (1 Figma read) plus the
metadata already fetched for the audit gives a per-screen PNG for every frame,
so the report gallery never depends on manual exports or on one read per
screen.

  crop_frames.py --image shots/section.png --metadata audit/onboarding/metadata.xml \
                 --out-dir shots/frames [--min-size 200] [--screens-json out.json]

How the mapping works: the metadata root (`<section>` or `<frame>`) has canvas
x, y, width, height. Its direct children carry coordinates relative to that
root. The rendered PNG is the root at scale s = rendered_width / root_width
(1.0 when Figma rendered at natural size) plus an equal margin on each side
when the rendered size exceeds root size times s. Each child frame is cropped at
(margin + child.x * s, margin + child.y * s, child.w * s, child.h * s).

The script also writes `--screens-json`: a list of {id, name, width, height,
image} entries that build_report.py accepts as `screens_detail`, and a
`frames.json` map id -> pixel frame inside the section image, which annotate.py
can use to mark a finding on the section shot or on the per-frame crop.

Frames smaller than --min-size on either edge (annotation stickies, loose
components) are skipped and listed under "skipped".
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import xml.etree.ElementTree as ET


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


def slug(s):
    s = re.sub(r"[^A-Za-z0-9]+", "-", s).strip("-").lower()
    return s or "frame"


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--image", required=True)
    ap.add_argument("--metadata", required=True)
    ap.add_argument("--out-dir", default="shots/frames")
    ap.add_argument("--min-size", type=int, default=200)
    ap.add_argument("--screens-json")
    ap.add_argument("--only", help="comma-separated node ids to crop")
    ap.add_argument("--kinds", default="frame,component,instance,group",
                    help="element tags treated as screens")
    a = ap.parse_args(argv)

    try:
        from PIL import Image
    except ImportError:
        print("Pillow is required: pip install pillow --break-system-packages", file=sys.stderr)
        return 2

    _reject_xml_entities(a.metadata); root = ET.parse(a.metadata).getroot()
    rw, rh = float(root.get("width")), float(root.get("height"))
    im = Image.open(a.image).convert("RGB")
    W, H = im.size
    s = min(W / rw, H / rh)
    mx, my = (W - rw * s) / 2, (H - rh * s) / 2

    kinds = set(a.kinds.split(","))
    only = set(x.replace("-", ":") for x in a.only.split(",")) if a.only else None
    os.makedirs(a.out_dir, exist_ok=True)
    screens, frames, skipped = [], {}, []
    for child in root:
        if child.tag not in kinds:
            continue
        nid = child.get("id")
        if only and nid not in only:
            continue
        x, y = float(child.get("x")), float(child.get("y"))
        w, h = float(child.get("width")), float(child.get("height"))
        if w < a.min_size or h < a.min_size:
            skipped.append({"id": nid, "name": child.get("name"), "width": w, "height": h})
            continue
        px = (round(mx + x * s), round(my + y * s), round(w * s), round(h * s))
        box = (max(0, px[0]), max(0, px[1]), min(W, px[0] + px[2]), min(H, px[1] + px[3]))
        if box[2] <= box[0] or box[3] <= box[1]:
            skipped.append({"id": nid, "name": child.get("name"), "reason": "outside image"})
            continue
        if not re.fullmatch(r"I?\d+:\d+(?:;\d+:\d+)*", nid or ""):
            skipped.append({"id": nid, "name": child.get("name"), "reason": "not a Figma node id"})
            continue
        out = os.path.join(a.out_dir, f"{slug(child.get('name'))}--{nid.replace(':', '-')}.png")
        im.crop(box).save(out, optimize=True)
        frames[nid] = {"x": px[0], "y": px[1], "w": px[2], "h": px[3], "scale": s}
        screens.append({"id": nid, "name": child.get("name"), "width": int(w), "height": int(h),
                        "image": out, "canvas": {"x": x, "y": y}})

    with open(os.path.join(a.out_dir, "frames.json"), "w") as fh:
        json.dump({"image": a.image, "scale": s, "margin": [mx, my], "frames": frames}, fh, indent=2)
    if a.screens_json:
        with open(a.screens_json, "w") as fh:
            json.dump(screens, fh, indent=2)
    print(json.dumps({"scale": s, "margin": [mx, my], "cropped": len(screens),
                      "skipped": len(skipped), "out_dir": a.out_dir}))
    for sc in screens:
        print(f"  {sc['id']:>12}  {sc['width']}x{sc['height']}  {sc['name']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
