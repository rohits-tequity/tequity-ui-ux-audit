#!/usr/bin/env python3
"""Classify what the user handed over and decide which audit phases apply.

  detect_inputs.py "https://www.figma.com/design/AbC/Checkout?node-id=12-345" \
                   "https://github.com/org/repo/pull/42" "./src/screens/Checkout.tsx" \
                   "running on the iOS simulator" [--config .audit/config.json]

Prints JSON: detected inputs, the phases they imply, what is still missing for
each phase, and the questions the intake skill should ask. Reads and merges a
previous .audit/config.json so answered questions are not asked again.

Deterministic on purpose. The skill uses the output to decide which MCQs to
show; it does not guess platform, user story or output format.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..",
                                "figma-design-audit", "scripts"))
try:
    from figma_url import parse as parse_figma
except Exception:  # keep the detector usable even if the helper moves
    parse_figma = None

PR_RE = re.compile(r"https?://(github\.com|gitlab\.com|bitbucket\.org)/[^/\s]+/[^/\s]+/(pull|merge_requests|pull-requests)/\d+", re.I)
REPO_RE = re.compile(r"(https?://(github\.com|gitlab\.com|bitbucket\.org)/[^/\s]+/[^/\s]+/?$)|(\.git$)", re.I)
CODE_EXT = (".tsx", ".ts", ".jsx", ".js", ".kt", ".swift", ".dart", ".vue", ".css", ".scss", ".html")
DIFF_RE = re.compile(r"^(diff --git|@@ |\+\+\+ |--- )", re.M)
WEB_URL_RE = re.compile(r"^https?://", re.I)
RUNTIME_WORDS = re.compile(r"\b(simulator|emulator|running app|on device|testflight|apk|ipa|build \d|staging|prod(uction)? app|argent)\b", re.I)
REPORT_WORDS = re.compile(r"\b(report|scorecard|write[- ]?up|summary|pdf|artifact|deck)\b", re.I)
PLATFORM_WORDS = [
    ("rn", re.compile(r"\b(react native|react-native|\brn\b|expo)\b", re.I)),
    ("ios", re.compile(r"\b(ios|iphone|ipad|swiftui|uikit|xcode)\b", re.I)),
    ("android", re.compile(r"\b(android|kotlin|compose|material ?3|pixel)\b", re.I)),
    ("web", re.compile(r"\b(web|next\.?js|react web|browser|chrome|website|landing page)\b", re.I)),
]
THEME_WORDS = re.compile(r"\b(light|dark)\b", re.I)
OUTPUT_WORDS = re.compile(r"\b(pdf|artifact|html file|print|client|compliance|legal)\b", re.I)
TARGET_RE = re.compile(r"WCAG\s*(2\.[012])\s*(AAA|AA|A)\b", re.I)
# Scope hints. Both are confirmed by the scope question; neither decides alone.
SCOPE_A11Y_WORDS = re.compile(
    r"\b(vpat|acr|conformance (statement|report|only)|accessibility only|"
    r"only (the )?accessibility|a11y only|wcag only|just wcag|section 508 (report|statement))\b", re.I)
SCOPE_DS_WORDS = re.compile(
    r"\b(design system only|token (audit|drift) only|only (the )?design system|"
    r"brand consistency only)\b", re.I)


def classify(token):
    t = token.strip()
    if not t:
        return None
    if "figma.com" in t:
        info = parse_figma(t) if parse_figma else {"ok": True, "nodeId": None}
        return {"kind": "figma", "value": t, "figma": info, "phase": "design",
                "usable": bool(info.get("supports_design_audit")) if info else False}
    if PR_RE.search(t):
        return {"kind": "pull_request", "value": t, "phase": "code", "usable": True}
    if REPO_RE.search(t):
        return {"kind": "repository", "value": t, "phase": "code", "usable": True}
    if DIFF_RE.search(t):
        return {"kind": "diff", "value": t[:80] + ("..." if len(t) > 80 else ""), "phase": "code", "usable": True}
    if t.lower().endswith(CODE_EXT) or os.path.isdir(t) or (os.path.exists(t) and not t.lower().endswith((".png", ".jpg", ".pdf"))):
        return {"kind": "path", "value": t, "phase": "code", "usable": True,
                "exists": os.path.exists(t)}
    if t.lower().endswith((".png", ".jpg", ".jpeg")):
        return {"kind": "screenshot", "value": t, "phase": "runtime", "usable": os.path.exists(t),
                "note": "a screenshot alone supports pixel measurement only; no tree or behaviour"}
    if WEB_URL_RE.search(t):
        return {"kind": "web_url", "value": t, "phase": "runtime", "usable": True,
                "note": "runtime audit of a web page needs a Chromium reachable by Argent, or the built-in browser tools"}
    if RUNTIME_WORDS.search(t):
        return {"kind": "runtime_hint", "value": t, "phase": "runtime", "usable": True}
    return {"kind": "text", "value": t, "phase": None, "usable": False}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("inputs", nargs="*")
    ap.add_argument("--config", default=".audit/config.json")
    ap.add_argument("--free-text", default="", help="the user's message, for platform/theme/target hints")
    a = ap.parse_args(argv)

    prev = {}
    if os.path.exists(a.config):
        try:
            prev = json.load(open(a.config))
        except Exception:
            prev = {}

    items = [c for c in (classify(t) for t in a.inputs) if c]
    # the prose itself can carry a phase ("audit the running app on the simulator")
    if a.free_text.strip():
        ft = classify(a.free_text)
        if ft and ft.get("phase") and not any(i.get("phase") == ft["phase"] for i in items):
            ft["kind"] = ft["kind"] if ft["kind"] != "text" else "prose"
            items.append(ft)
    text = " ".join([a.free_text] + [i["value"] for i in items if i["kind"] == "text"])

    phases = sorted({i["phase"] for i in items if i.get("phase") and i.get("usable")})
    wants_report_only = bool(REPORT_WORDS.search(text)) and not phases

    # hints from prose
    platform = prev.get("platform")
    for key, rx in PLATFORM_WORDS:
        if rx.search(text):
            platform = platform or key
    themes = prev.get("themes")
    if THEME_WORDS.search(text) and not themes:
        low = text.lower()
        themes = [t for t in ("light", "dark") if t in low] or None
    m = TARGET_RE.search(text)
    target = prev.get("conformance_target") or (f"WCAG {m.group(1)} {m.group(2).upper()}" if m else None)
    # A request phrased as pure conformance work ("VPAT", "ACR", "conformance
    # statement", "WCAG audit only") implies the narrow scope. It is a hint the
    # question still confirms, never a silent decision.
    scope_hint = None
    if SCOPE_A11Y_WORDS.search(text):
        scope_hint = {"label": "Accessibility only", "dimensions": ["accessibility"]}
    elif SCOPE_DS_WORDS.search(text):
        scope_hint = {"label": "Design system only", "dimensions": ["visual_system", "content_copy"]}

    figma_unusable = [i for i in items if i["kind"] == "figma" and not i["usable"]]
    missing_paths = [i for i in items if i["kind"] in ("path", "screenshot") and not (i.get("exists", True) and i.get("usable", True))]

    # what each phase still needs before it can run
    needs = {}
    if "design" in phases:
        needs["design"] = [k for k, v in {
            "platform": platform, "user_story": prev.get("user_story"),
            "themes": themes, "devices": prev.get("devices"),
            "conformance_target": target, "design_system": ("design_system" in prev) or None,
            "scope": prev.get("scope"),
        }.items() if not v]
    if "code" in phases:
        needs["code"] = [k for k, v in {"platform": platform, "user_story": prev.get("user_story"),
                                        "scope": prev.get("scope")}.items() if not v]
    if "runtime" in phases:
        needs["runtime"] = [k for k, v in {
            "platform": platform, "device_reachable": prev.get("device_reachable"),
            "user_story": prev.get("user_story"), "themes": themes,
            "scope": prev.get("scope"),
        }.items() if not v]
    output_hint = None
    if not prev.get("output"):
        m_out = OUTPUT_WORDS.findall(text)
        if m_out:
            low = {x.lower() for x in m_out}
            output_hint = {"formats": ["artifact", "html"] + (["pdf"] if low & {"pdf", "print", "client", "compliance", "legal"} else [])}
    common_missing = [k for k, v in {"output": prev.get("output") or output_hint, "audience": prev.get("audience")}.items() if not v]
    if output_hint and "pdf" in output_hint["formats"] and not (prev.get("output") or {}).get("pdf_theme"):
        common_missing.append("pdf_theme")

    questions = []
    if not phases and not wants_report_only and not figma_unusable and not missing_paths:
        questions.append("what_to_audit")
    if figma_unusable:
        questions.append("figma_node_link")
    if len(phases) > 1:
        questions.append("phase_order")
    for k in ("platform", "user_story", "themes", "devices", "scope", "conformance_target", "design_system", "device_reachable"):
        if any(k in v for v in needs.values()):
            questions.append(k)
    questions += common_missing
    baseline = os.path.join(os.path.dirname(a.config) or ".", "previous-scorecard.json")
    if os.path.exists(baseline) and not prev.get("re_audit"):
        questions.append("re_audit")

    out = {
        "inputs": items,
        "phases_detected": phases,
        "report_only": wants_report_only,
        "hints": {"platform": platform, "themes": themes, "conformance_target": target,
                  "output": output_hint, "scope": scope_hint},
        "problems": (
            [f"Figma link has no node-id: {i['value']}" for i in figma_unusable]
            + [f"path does not exist: {i['value']}" for i in missing_paths]
        ),
        "needs": needs,
        "questions_to_ask": list(dict.fromkeys(questions)),  # ordered, de-duplicated
        "previous_config": prev,
    }
    json.dump(out, sys.stdout, indent=2)
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
