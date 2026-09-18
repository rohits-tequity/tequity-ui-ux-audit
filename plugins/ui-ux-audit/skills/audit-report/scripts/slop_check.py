#!/usr/bin/env python3
"""Deterministic language and evidence lint for audit findings and report prose.

Runs automatically inside build_report.py; also callable on its own:

  slop_check.py --findings audit/findings.json            # lint the data
  slop_check.py --html audit/report.html                  # lint rendered prose

Exit 0 = clean, 1 = failures. Every hit names the field or line, so a cheap
model (or a human) can fix it without judgement calls. The judgement half -
"does this finding deserve its severity", belongs to the audit-verifier agent,
not here.
"""
from __future__ import annotations

import argparse
import html
import json
import re
import sys

FILLER = [
    r"\bin today'?s\b", r"\bit is important to note\b", r"\bthis report aims\b",
    r"\bunderscores?\b", r"\bhighlights? the importance\b", r"\bserves? as a testament\b",
    r"\bmoreover\b", r"\bfurthermore\b", r"\brobust and scalable\b", r"\bseamless(ly)?\b",
    r"\bleverag(e|es|ing)\b", r"\bdelve\b", r"\b(digital|competitive|evolving|changing) landscape\b|\blandscape of\b", r"\bpotentially concerning\b",
    r"\bmay possibly\b", r"\bbest[- ]in[- ]class\b", r"\bcutting[- ]edge\b",
    r"\bstate[- ]of[- ]the[- ]art\b", r"\bgame[- ]chang", r"\bholistic\b", r"\bsynerg",
    r"\bcrucial\b", r"\bvital\b", r"\bplays a (key|vital|crucial) role\b",
    r"\bit'?s worth noting\b", r"\bneedless to say\b", r"\bas mentioned (above|earlier)\b",
    r"\bensure(s)? that\b.*\bensure", r"\bgoing forward\b", r"\bat the end of the day\b",
    r"\bindustry best practices?\b(?!\s*\()",  # allowed only when a clause follows in parens
]
HEDGES = [r"\bmay\b", r"\bmight\b", r"\bcould\b", r"\bpotentially\b", r"\bpossibly\b",
          r"\bseems?\b", r"\bappears? to\b", r"\bit is likely\b"]
VAGUE_FIX = [r"^\s*(improve|enhance|fix|address|consider|look into|revisit|optimi[sz]e)\b[^0-9#]*$"]
# Template placeholders look like {{UPPER_SNAKE}}; JSX like hitSlop={{top:14}} is legitimate.
PLACEHOLDERS = [r"\{\{\s*[A-Z][A-Z0-9_]*\s*\}\}", r"\bTODO\b", r"\bTBD\b", r"\bLorem\b", r"\bXXX\b", r"\bFIXME\b"]
EM_DASH = "\u2014"
NUMBER_RE = re.compile(r"\d")
MAX_WORDS_OVERVIEW = 30
MAX_WORDS_FIX = 45


def hits(patterns, text):
    return [p for p in patterns if re.search(p, text or "", re.I)]


def word_count(s):
    return len(re.findall(r"\b\w+\b", s or ""))


def lint_findings(data):
    fails, warns = [], []
    ids = [f.get("id") for f in data.get("findings", [])]
    for f in data.get("findings", []):
        fid = f.get("id") or "<no id>"
        for fld in ("title", "user_impact", "fix", "retest"):
            v = f.get(fld)
            if not v:
                fails.append(f"{fid}.{fld}: missing")
                continue
            for p in hits(FILLER, v):
                fails.append(f"{fid}.{fld}: filler phrase /{p}/")
            for p in hits(PLACEHOLDERS, v):
                fails.append(f"{fid}.{fld}: placeholder /{p}/")
            if EM_DASH in v:
                fails.append(f"{fid}.{fld}: em dash; use a colon, comma or full stop")
        fix = f.get("fix") or ""
        if fix and hits(VAGUE_FIX, fix):
            fails.append(f"{fid}.fix: vague, names no current value, proposed value or number: '{fix[:60]}'")
        if fix and not NUMBER_RE.search(fix) and not re.search(r"[`#]|token|prop|accessibility|aria|role|label", fix, re.I):
            warns.append(f"{fid}.fix: contains no value, token or prop name, check it is concrete")
        if word_count(fix) > MAX_WORDS_FIX:
            warns.append(f"{fid}.fix: {word_count(fix)} words, split it")
        if f.get("confidence") == "measured":
            for fld in ("title", "user_impact"):
                for p in hits(HEDGES, f.get(fld)):
                    fails.append(f"{fid}.{fld}: hedge /{p}/ on a measured finding")
        ev = f.get("evidence") or {}
        if ev.get("measured") is None and not ev.get("image"):
            fails.append(f"{fid}.evidence: neither a measured value nor an image")
        if ev.get("measured") is not None and ev.get("required") is None and f.get("dimension") == "accessibility":
            warns.append(f"{fid}.evidence: measured value has no threshold beside it")
        loc = f.get("location") or {}
        if not any(loc.get(k) for k in ("node_id", "node", "file", "component", "screen")):
            fails.append(f"{fid}.location: nothing locatable (node, node_id, file, component)")
        prefix = str(fid).split("-")[0].upper()
        expected = {"A11Y": "accessibility", "EDGE": "robustness", "DS": "visual_system",
                    "PERF": "interaction_states"}.get(prefix)
        if expected and f.get("dimension") and f.get("dimension") != expected:
            warns.append(f"{fid}: id prefix {prefix}- usually means dimension '{expected}' but dimension is "
                         f"'{f.get('dimension')}', the report groups by dimension, so check which part it should land in")
        if f.get("severity") not in ("critical", "serious", "moderate", "minor", "info"):
            fails.append(f"{fid}.severity: '{f.get('severity')}' is not in the enum")
        if f.get("severity") == "critical" and not re.search(
                r"level a\b|primary|blocks?|cannot|data loss|unreachable",
                f"{f.get('criterion','')} {f.get('user_impact','')}", re.I):
            warns.append(f"{fid}: rated critical but impact text does not mention a blocked primary task, Level A failure or data loss")
    if len(ids) != len(set(ids)):
        fails.append("duplicate finding ids")
    for i, b in enumerate(data.get("overview") or [], 1):
        for p in hits(FILLER, b):
            fails.append(f"overview[{i}]: filler /{p}/")
        if EM_DASH in b:
            fails.append(f"overview[{i}]: em dash; use a colon, comma or full stop")
        if word_count(b) > MAX_WORDS_OVERVIEW:
            warns.append(f"overview[{i}]: {word_count(b)} words, over {MAX_WORDS_OVERVIEW}")
        if not NUMBER_RE.search(b) and i <= 3:
            warns.append(f"overview[{i}]: no number in a lead bullet, is it a fact or a topic?")
    for i, l in enumerate(data.get("limitations") or [], 1):
        if EM_DASH in l:
            fails.append(f"limitations[{i}]: em dash; use a colon, comma or full stop")
        if re.search(r"further testing (is )?recommended|additional testing", l, re.I) and word_count(l) < 14:
            fails.append(f"limitations[{i}]: generic, say what was not tested and why")
    return fails, warns


def lint_html(text):
    fails, warns = [], []
    plain = html.unescape(re.sub(r"<style>.*?</style>", "", text, flags=re.S))
    plain = re.sub(r"<[^>]+>", " ", plain)
    for p in PLACEHOLDERS:
        for m in re.finditer(p, plain):
            fails.append(f"html: placeholder /{p}/ near '{plain[max(0,m.start()-30):m.end()+30].strip()}'")
    for p in FILLER:
        for m in re.finditer(p, plain, re.I):
            fails.append(f"html: filler /{p}/ near '{plain[max(0,m.start()-30):m.end()+30].strip()}'")
    for m in list(re.finditer(EM_DASH, plain))[:20]:
        fails.append(f"html: em dash near '{plain[max(0,m.start()-30):m.end()+30].strip()}'")
    if re.search(r"<table[^>]*style=\"[^\"]*display\s*:\s*block", text, re.I) or re.search(r"table\s*\{[^}]*display\s*:\s*block", text, re.I):
        fails.append("html: display:block on a table element")
    # Only embedded resources must be local; outbound links (references, W3C) are fine.
    ext = [m.group(0) for m in re.finditer(r"src=\"https?://[^\"]+", text)]
    if ext:
        warns.append(f"html: {len(ext)} external resource(s) loaded by src; evidence must be embedded as data: URIs")
    return fails, warns


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--findings")
    ap.add_argument("--html")
    ap.add_argument("--quiet", action="store_true")
    a = ap.parse_args(argv)
    fails, warns = [], []
    if a.findings:
        f, w = lint_findings(json.load(open(a.findings)))
        fails += f; warns += w
    if a.html:
        f, w = lint_html(open(a.html, encoding="utf-8").read())
        fails += f; warns += w
    if not a.findings and not a.html:
        ap.error("pass --findings and/or --html")
    if not a.quiet:
        for x in fails:
            print(f"FAIL  {x}")
        for x in warns:
            print(f"warn  {x}")
    print(f"slop-check: {len(fails)} fail, {len(warns)} warn")
    return 1 if fails else 0


if __name__ == "__main__":
    raise SystemExit(main())
