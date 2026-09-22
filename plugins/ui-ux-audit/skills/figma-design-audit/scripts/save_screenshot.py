#!/usr/bin/env python3
"""Save Figma MCP screenshots to disk without any manual export.

Figma's `get_screenshot` returns a short-lived figma.com URL that sandboxed
containers usually cannot fetch. Called with `enableBase64Response: true` it
also returns the PNG inline, and that inline entry is persisted in the session
transcript (the .jsonl under ~/.claude/projects/<cwd-slug>/). This script pulls
the PNG bytes back out of the transcript, so the pipeline stays automatic:

  1. call get_screenshot(fileKey, nodeId, enableBase64Response=true[, maxDimension]),
     or just use the preview render get_design_context already returned
  2. python3 save_screenshot.py --node 1420:3300 --out shots/sign-up.png
     python3 save_screenshot.py --asset 3a00ed30-f048 --out shots/sign-up.png
     python3 save_screenshot.py --all --out-dir shots/        (every screenshot so far)

Matching: `--node` finds the tool call by its nodeId argument and takes the image
from the matching result; `--asset` matches the asset id in the result JSON;
`--all` writes every get_screenshot image found, named by nodeId. The newest
match wins when a node was shot more than once. `--transcript` overrides the
auto-detected transcript path; `--list` prints what is available.

Only Pillow-free stdlib is needed. Exit 3 when nothing matched.
"""
from __future__ import annotations

import argparse
import base64
import glob
import json
import os
import re
import sys


def find_transcripts(explicit=None):
    if explicit:
        return [explicit]
    home = os.path.expanduser("~")
    # Claude Code slugifies the session's working directory into the project
    # folder name. Restricting the search to this project matters: without it,
    # the newest transcript holding any screenshot wins, which can be another
    # client's audit, and its screens would be written into this evidence
    # folder.
    #
    # An audit usually runs in a subdirectory of where the session started, so
    # the cwd slug alone misses the transcript. Walk up from the cwd and take
    # the first ancestor that has one. An unrelated project is never an
    # ancestor of this directory, so the confinement still holds.
    root = os.path.join(home, ".claude", "projects")
    here = os.path.abspath(os.getcwd())
    tried = []
    while True:
        slug = re.sub(r"[^A-Za-z0-9]+", "-", here)
        tried.append(slug)
        files = glob.glob(os.path.join(root, slug, "*.jsonl"))
        if files:
            files.sort(key=lambda p: os.path.getmtime(p), reverse=True)
            return files
        parent = os.path.dirname(here)
        if parent == here:
            break
        here = parent
    print(f"no transcript folder for this directory or any parent of it. Tried: "
          f"{', '.join(tried[:4])}{' ...' if len(tried) > 4 else ''}", file=sys.stderr)
    return []


def _walk_images(x, acc):
    if isinstance(x, dict):
        src = x.get("source")
        if x.get("type") == "image" and isinstance(src, dict) and src.get("data"):
            acc.append(src)
        for v in x.values():
            _walk_images(v, acc)
    elif isinstance(x, list):
        for v in x:
            _walk_images(v, acc)


def scan(transcript):
    """Yield (tool_use_id, nodeId, asset_id, image_source, ts) for every get_screenshot result."""
    calls = {}   # tool_use_id -> nodeId
    out = []
    with open(transcript, "r", encoding="utf-8", errors="replace") as fh:
        for line in fh:
            if "get_screenshot" not in line and "mcp/asset/" not in line:
                continue
            try:
                o = json.loads(line)
            except json.JSONDecodeError:
                continue
            msg = o.get("message") or {}
            content = msg.get("content") if isinstance(msg, dict) else None
            if isinstance(content, list):
                for blk in content:
                    if not isinstance(blk, dict):
                        continue
                    # get_design_context returns a preview render of the node
                    # alongside the code, so it is a screenshot the audit has
                    # already paid for. Recovering it costs no extra read.
                    if blk.get("type") == "tool_use" and str(blk.get("name", "")).endswith(
                            ("get_screenshot", "get_design_context")):
                        nid = str((blk.get("input") or {}).get("nodeId", "")).replace("-", ":")
                        calls[blk.get("id")] = nid
                    if blk.get("type") == "tool_result":
                        imgs = []
                        _walk_images(blk, imgs)
                        if not imgs:
                            continue
                        if blk.get("tool_use_id") not in calls:
                            continue   # an image from some other tool
                        text = json.dumps(blk)
                        m = re.search(r"mcp/asset/([0-9a-f-]+)\.png", text)
                        asset = m.group(1) if m else ""
                        meta = {}
                        mm = re.search(r'\{\\"image_url\\".*?\}', text)
                        if mm:
                            try:
                                meta = json.loads(mm.group(0).replace('\\"', '"'))
                            except json.JSONDecodeError:
                                meta = {}
                        out.append({
                            "tool_use_id": blk.get("tool_use_id"),
                            "nodeId": calls.get(blk.get("tool_use_id"), ""),
                            "asset": asset,
                            "source": imgs[-1],
                            "meta": meta,
                            "ts": o.get("timestamp", ""),
                        })
    return out


def save(entry, out_path, confine_to=None):
    data = base64.b64decode(entry["source"]["data"])
    if confine_to:
        root = os.path.realpath(confine_to)
        if os.path.commonpath([root, os.path.realpath(out_path)]) != root:
            raise SystemExit(f"refusing to write outside {confine_to}: {out_path}")
    os.makedirs(os.path.dirname(os.path.abspath(out_path)) or ".", exist_ok=True)
    with open(out_path, "wb") as fh:
        fh.write(data)
    return len(data)


def safe_name(node_id):
    """A Figma node id is digits and a colon. Anything else is not one, and must
    not reach a path: the value comes from a tool call recorded in the
    transcript, so a crafted one could otherwise climb out of the output
    directory and write an attacker-chosen file."""
    name = re.sub(r"[^A-Za-z0-9:_-]", "", str(node_id or "")).replace(":", "-")
    return name[:64] or "screenshot"


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--transcript")
    ap.add_argument("--node", help="nodeId of the get_screenshot call, e.g. 1420:3300")
    ap.add_argument("--asset", help="asset id (or prefix) from the result URL")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--out")
    ap.add_argument("--out-dir", default="shots")
    ap.add_argument("--list", action="store_true")
    a = ap.parse_args(argv)

    entries = []
    for t in find_transcripts(a.transcript):
        try:
            entries += scan(t)
        except OSError:
            continue
        if entries and not a.transcript:
            break  # the newest transcript that has screenshots is the live one

    if a.list or not (a.node or a.asset or a.all):
        for e in entries:
            m = e["meta"]
            print(f"{e['nodeId'] or '?':>12}  asset={e['asset'][:8]}  {m.get('width','?')}x{m.get('height','?')}  "
                  f"(original {m.get('original_width','?')}x{m.get('original_height','?')})  {e['ts']}")
        if not entries:
            print("no get_screenshot results with inline images found; call get_screenshot with enableBase64Response=true", file=sys.stderr)
            return 3
        return 0

    if a.all:
        seen = {}
        for e in entries:  # later entries overwrite earlier ones for the same node
            seen[e["nodeId"] or e["asset"]] = e
        written = []
        for key, e in seen.items():
            p = os.path.join(a.out_dir, safe_name(key) + ".png")
            n = save(e, p, confine_to=a.out_dir)
            written.append({"nodeId": e["nodeId"], "path": p, "bytes": n, **e["meta"]})
        print(json.dumps(written, indent=2))
        return 0 if written else 3

    want = None
    for e in reversed(entries):
        if a.node and e["nodeId"] == a.node.replace("-", ":"):
            want = e
            break
        if a.asset and e["asset"].startswith(a.asset):
            want = e
            break
    if not want:
        print("no matching screenshot in the transcript", file=sys.stderr)
        return 3
    out = a.out or os.path.join(a.out_dir, safe_name(want["nodeId"] or want["asset"]) + ".png")
    n = save(want, out, confine_to=os.path.dirname(os.path.abspath(out)) or ".")
    print(json.dumps({"nodeId": want["nodeId"], "path": out, "bytes": n, **want["meta"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
