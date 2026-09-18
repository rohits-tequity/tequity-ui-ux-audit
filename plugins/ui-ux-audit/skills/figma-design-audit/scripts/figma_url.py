#!/usr/bin/env python3
"""Turn a Figma URL into the fileKey / nodeId pair the MCP tools want.

  figma_url.py "https://www.figma.com/design/AbC123.../Checkout?node-id=12-345&t=xyz"
  → {"fileKey": "AbC123...", "nodeId": "12:345", "kind": "design", ...}

Handles /design/, /file/ (legacy), /branch/<branchKey>/ (branch key becomes the
fileKey), /board/ (FigJam), /slides/, /make/. Says plainly when a URL has no
node-id, because the design audit cannot run without one.
"""
from __future__ import annotations

import json
import re
import sys
from urllib.parse import parse_qs, urlparse


def parse(url: str) -> dict:
    u = urlparse(url.strip())
    if "figma.com" not in u.netloc:
        return {"ok": False, "error": "not a figma.com URL", "url": url}

    parts = [p for p in u.path.split("/") if p]
    kind = parts[0] if parts else None
    if kind not in ("design", "file", "board", "slides", "make", "proto"):
        return {"ok": False, "error": f"unrecognised Figma path kind '{kind}'", "url": url}

    file_key = parts[1] if len(parts) > 1 else None
    branch_key = None
    if "branch" in parts:
        i = parts.index("branch")
        if i + 1 < len(parts):
            branch_key = parts[i + 1]

    q = parse_qs(u.query)
    node_raw = (q.get("node-id") or q.get("node_id") or [None])[0]
    node_id = node_raw.replace("-", ":") if node_raw else None

    if kind == "make" and not node_id:
        node_id = "0:1"  # Make files: get_design_context accepts 0:1

    out = {
        "ok": True,
        "url": url,
        "kind": kind,
        "fileKey": branch_key or file_key,
        "originalFileKey": file_key,
        "branchKey": branch_key,
        "nodeId": node_id,
        "supports_design_audit": kind in ("design", "file") and bool(node_id),
    }
    if not node_id:
        out["warning"] = ("no node-id in URL, ask for a node-specific link "
                          "(select the frame in Figma, then Copy link to selection)")
    if kind in ("board", "slides"):
        out["warning"] = f"{kind} files are not design files; get_metadata/get_variable_defs are unsupported"
    return out


def main(argv=None):
    argv = argv if argv is not None else sys.argv[1:]
    if not argv:
        print(__doc__)
        return 2
    results = [parse(a) for a in argv]
    json.dump(results[0] if len(results) == 1 else results, sys.stdout, indent=2)
    print()
    return 0 if all(r.get("ok") for r in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
