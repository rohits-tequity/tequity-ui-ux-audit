"""Shared reference data for the report scripts.

WCAG 2.2 success criteria: Level A/AA (55) and AAA (31), each tagged with the
version that introduced it (2.0 / 2.1 / 2.2), so one table can be read as 2.0,
2.1 or 2.2 conformance. 4.1.1 Parsing (removed in 2.2) is carried as a note row.
Also holds
the ACR status vocabulary, the state-coverage matrix rows, and the helpers that
derive a conformance table and coverage numbers from a findings file, so
score.py and build_report.py compute the same numbers from the same rules.
"""
from __future__ import annotations

import re

WCAG_22_AA = [
    ("1.1.1", "Non-text Content", "A", "2.0"),
    ("1.2.1", "Audio-only and Video-only (Prerecorded)", "A", "2.0"),
    ("1.2.2", "Captions (Prerecorded)", "A", "2.0"),
    ("1.2.3", "Audio Description or Media Alternative (Prerecorded)", "A", "2.0"),
    ("1.2.4", "Captions (Live)", "AA", "2.0"),
    ("1.2.5", "Audio Description (Prerecorded)", "AA", "2.0"),
    ("1.3.1", "Info and Relationships", "A", "2.0"),
    ("1.3.2", "Meaningful Sequence", "A", "2.0"),
    ("1.3.3", "Sensory Characteristics", "A", "2.0"),
    ("1.3.4", "Orientation", "AA", "2.1"),
    ("1.3.5", "Identify Input Purpose", "AA", "2.1"),
    ("1.4.1", "Use of Color", "A", "2.0"),
    ("1.4.2", "Audio Control", "A", "2.0"),
    ("1.4.3", "Contrast (Minimum)", "AA", "2.0"),
    ("1.4.4", "Resize Text", "AA", "2.0"),
    ("1.4.5", "Images of Text", "AA", "2.0"),
    ("1.4.10", "Reflow", "AA", "2.1"),
    ("1.4.11", "Non-text Contrast", "AA", "2.1"),
    ("1.4.12", "Text Spacing", "AA", "2.1"),
    ("1.4.13", "Content on Hover or Focus", "AA", "2.1"),
    ("2.1.1", "Keyboard", "A", "2.0"),
    ("2.1.2", "No Keyboard Trap", "A", "2.0"),
    ("2.1.4", "Character Key Shortcuts", "A", "2.1"),
    ("2.2.1", "Timing Adjustable", "A", "2.0"),
    ("2.2.2", "Pause, Stop, Hide", "A", "2.0"),
    ("2.3.1", "Three Flashes or Below Threshold", "A", "2.0"),
    ("2.4.1", "Bypass Blocks", "A", "2.0"),
    ("2.4.2", "Page Titled", "A", "2.0"),
    ("2.4.3", "Focus Order", "A", "2.0"),
    ("2.4.4", "Link Purpose (In Context)", "A", "2.0"),
    ("2.4.5", "Multiple Ways", "AA", "2.0"),
    ("2.4.6", "Headings and Labels", "AA", "2.0"),
    ("2.4.7", "Focus Visible", "AA", "2.0"),
    ("2.4.11", "Focus Not Obscured (Minimum)", "AA", "2.2"),
    ("2.5.1", "Pointer Gestures", "A", "2.1"),
    ("2.5.2", "Pointer Cancellation", "A", "2.1"),
    ("2.5.3", "Label in Name", "A", "2.1"),
    ("2.5.4", "Motion Actuation", "A", "2.1"),
    ("2.5.7", "Dragging Movements", "AA", "2.2"),
    ("2.5.8", "Target Size (Minimum)", "AA", "2.2"),
    ("3.1.1", "Language of Page", "A", "2.0"),
    ("3.1.2", "Language of Parts", "AA", "2.0"),
    ("3.2.1", "On Focus", "A", "2.0"),
    ("3.2.2", "On Input", "A", "2.0"),
    ("3.2.3", "Consistent Navigation", "AA", "2.0"),
    ("3.2.4", "Consistent Identification", "AA", "2.0"),
    ("3.2.6", "Consistent Help", "A", "2.2"),
    ("3.3.1", "Error Identification", "A", "2.0"),
    ("3.3.2", "Labels or Instructions", "A", "2.0"),
    ("3.3.3", "Error Suggestion", "AA", "2.0"),
    ("3.3.4", "Error Prevention (Legal, Financial, Data)", "AA", "2.0"),
    ("3.3.7", "Redundant Entry", "A", "2.2"),
    ("3.3.8", "Accessible Authentication (Minimum)", "AA", "2.2"),
    ("4.1.2", "Name, Role, Value", "A", "2.0"),
    ("4.1.3", "Status Messages", "AA", "2.1"),
]
WCAG_NEW_IN_22 = {"2.4.11", "2.5.7", "2.5.8", "3.2.6", "3.3.7", "3.3.8"}

# Level AAA success criteria in WCAG 2.2 (31). Off by default; included when the
# conformance target names AAA. Each carries the version that introduced it.
WCAG_22_AAA = [
    ("1.2.6", "Sign Language (Prerecorded)", "AAA", "2.0"),
    ("1.2.7", "Extended Audio Description (Prerecorded)", "AAA", "2.0"),
    ("1.2.8", "Media Alternative (Prerecorded)", "AAA", "2.0"),
    ("1.2.9", "Audio-only (Live)", "AAA", "2.0"),
    ("1.3.6", "Identify Purpose", "AAA", "2.1"),
    ("1.4.6", "Contrast (Enhanced)", "AAA", "2.0"),
    ("1.4.7", "Low or No Background Audio", "AAA", "2.0"),
    ("1.4.8", "Visual Presentation", "AAA", "2.0"),
    ("1.4.9", "Images of Text (No Exception)", "AAA", "2.0"),
    ("2.1.3", "Keyboard (No Exception)", "AAA", "2.0"),
    ("2.2.3", "No Timing", "AAA", "2.0"),
    ("2.2.4", "Interruptions", "AAA", "2.0"),
    ("2.2.5", "Re-authenticating", "AAA", "2.0"),
    ("2.2.6", "Timeouts", "AAA", "2.1"),
    ("2.3.2", "Three Flashes", "AAA", "2.0"),
    ("2.3.3", "Animation from Interactions", "AAA", "2.1"),
    ("2.4.8", "Location", "AAA", "2.0"),
    ("2.4.9", "Link Purpose (Link Only)", "AAA", "2.0"),
    ("2.4.10", "Section Headings", "AAA", "2.0"),
    ("2.4.12", "Focus Not Obscured (Enhanced)", "AAA", "2.2"),
    ("2.4.13", "Focus Appearance", "AAA", "2.2"),
    ("2.5.5", "Target Size (Enhanced)", "AAA", "2.1"),
    ("2.5.6", "Concurrent Input Mechanisms", "AAA", "2.1"),
    ("3.1.3", "Unusual Words", "AAA", "2.0"),
    ("3.1.4", "Abbreviations", "AAA", "2.0"),
    ("3.1.5", "Reading Level", "AAA", "2.0"),
    ("3.1.6", "Pronunciation", "AAA", "2.0"),
    ("3.2.5", "Change on Request", "AAA", "2.0"),
    ("3.3.5", "Help", "AAA", "2.0"),
    ("3.3.6", "Error Prevention (All)", "AAA", "2.0"),
    ("3.3.9", "Accessible Authentication (Enhanced)", "AAA", "2.2"),
]

# 4.1.1 Parsing exists in 2.0 and 2.1 but was removed in 2.2. W3C's position:
# content that meets 2.2 satisfies 4.1.1 in 2.0/2.1 by definition. Reported as
# a note row so a 2.0/2.1-scoped reader sees it addressed, never as a gap.
WCAG_OBSOLETE = [("4.1.1", "Parsing (obsolete in 2.2; satisfied by conforming to 2.2)", "A", "2.0")]

VERSIONS = ["2.0", "2.1", "2.2"]


def parse_target(target):
    """'WCAG 2.2 AA' -> ('2.2', 'AA'). Defaults to 2.2 AA; unknown text falls back."""
    t = str(target or "")
    m_v = re.search(r"\b(2\.[012])\b", t)
    m_l = re.search(r"\b(AAA|AA|A)\b", t.upper())
    return (m_v.group(1) if m_v else "2.2", m_l.group(1) if m_l else "AA")


def criteria_for(target):
    """All criteria in scope for a target, in document order."""
    ver, level = parse_target(target)
    rows = list(WCAG_22_AA)
    if level == "AAA":
        rows += WCAG_22_AAA
    if level == "A":
        rows = [r for r in rows if r[2] == "A"]
    rows = [r for r in rows if VERSIONS.index(r[3]) <= VERSIONS.index(ver)]
    rows.sort(key=lambda r: tuple(int(x) for x in r[0].split(".")))
    return rows

STATUSES = ["Supports", "Partially Supports", "Does Not Support",
            "Not Applicable", "Not Evaluated"]

# One row per screen in the coverage matrix. Mirrors
# figma-design-audit/references/ux-heuristics-and-edge-cases.md.
STATES = [
    "Empty (first run)", "Empty (filtered to nothing)", "Loading: initial",
    "Loading: more / pagination", "Partial / stale", "Error: network",
    "Error: server", "Error: validation", "Error: permission denied",
    "Offline", "Success / confirmation", "Disabled", "Read-only",
    "Long content", "Truncation", "Zero / negative / very large numbers",
    "Localisation (long strings)", "RTL mirroring", "Largest font scale",
    "Dark mode", "High contrast", "Reduced motion", "Rotation / split view",
    "Small screen (320px)", "Keyboard open", "Slow network", "Interrupted",
    "Session expired", "Rapid / double tap", "Deep link entry",
]

SC_RE = re.compile(r"\b(\d\.\d\.\d{1,2})\b")
SEVERITY_ORDER = ["critical", "serious", "moderate", "minor", "info"]


def sc_of(finding):
    """Success-criterion number referenced by a finding, or None."""
    m = SC_RE.search(str(finding.get("criterion") or ""))
    return m.group(1) if m else None


def derive_conformance(data):
    """Build the ACR-style table from a findings file.

    Precedence per criterion:
      1. an explicit row in data["conformance"] (list of {sc, status, remarks})
      2. findings that cite the criterion → Does Not Support (critical/serious)
         or Partially Supports (moderate/minor); info-only → Not Evaluated
      3. data["evaluated"]["supports"] / ["not_applicable"] lists
      4. Not Evaluated
    Returns a list of row dicts in WCAG order.
    """
    explicit = {r["sc"]: r for r in (data.get("conformance") or []) if r.get("sc")}
    ev = data.get("evaluated") or {}
    supports = set(ev.get("supports") or [])
    not_applicable = set(ev.get("not_applicable") or [])

    by_sc = {}
    for f in data.get("findings", []):
        sc = sc_of(f)
        if sc:
            by_sc.setdefault(sc, []).append(f)

    rows = []
    target = data.get("conformance_target", "WCAG 2.2 AA")
    for sc, name, level, introduced in criteria_for(target):
        if sc in explicit:
            r = explicit[sc]
            status = r.get("status") if r.get("status") in STATUSES else "Not Evaluated"
            remarks = r.get("remarks", "")
            ids = [f.get("id") for f in by_sc.get(sc, []) if f.get("id")]
        elif sc in by_sc:
            fs = by_sc[sc]
            worst = min((f.get("severity", "minor") for f in fs),
                        key=lambda s: SEVERITY_ORDER.index(s) if s in SEVERITY_ORDER else 3)
            ids = [f.get("id") for f in fs if f.get("id")]
            if worst in ("critical", "serious"):
                status = "Does Not Support"
            elif worst in ("moderate", "minor"):
                status = "Partially Supports"
            else:
                status = "Not Evaluated"
            remarks = "; ".join(
                f"{f.get('id')}: {f.get('title') or f.get('detail') or ''}".strip()
                for f in fs)[:600]
        elif sc in not_applicable:
            status, remarks, ids = "Not Applicable", ev.get("remarks", {}).get(sc, ""), []
        elif sc in supports:
            status, remarks, ids = "Supports", ev.get("remarks", {}).get(sc, ""), []
        else:
            status, remarks, ids = "Not Evaluated", "", []
        rows.append({"sc": sc, "name": name, "level": level, "status": status,
                     "remarks": remarks, "finding_ids": ids,
                     "introduced": introduced, "new_in_22": sc in WCAG_NEW_IN_22,
                     "beyond_target": False})

    # Criteria the findings cite that sit beyond the target level (e.g. a AAA
    # criterion under an AA target) are still shown, flagged, so a real defect
    # is never hidden by the scope line.
    in_scope = {r["sc"] for r in rows}
    lookup = {r[0]: r for r in WCAG_22_AA + WCAG_22_AAA}
    for sc, fs in by_sc.items():
        if sc in in_scope or sc not in lookup:
            continue
        _, name, level, introduced = lookup[sc]
        worst = min((f.get("severity", "minor") for f in fs),
                    key=lambda s: SEVERITY_ORDER.index(s) if s in SEVERITY_ORDER else 3)
        rows.append({"sc": sc, "name": name, "level": level,
                     "status": "Does Not Support" if worst in ("critical", "serious") else "Partially Supports",
                     "remarks": "Beyond the audit's target level, reported because a finding cites it. " +
                                "; ".join(f"{f.get('id')}: {f.get('title') or ''}" for f in fs)[:500],
                     "finding_ids": [f.get("id") for f in fs], "introduced": introduced,
                     "new_in_22": sc in WCAG_NEW_IN_22, "beyond_target": True})
    rows.sort(key=lambda r: tuple(int(x) for x in r["sc"].split(".")))
    return rows


def version_summary(rows):
    """Status counts as seen from each WCAG version's A/AA (or scoped) set.

    A 2.0-scoped reader wants to know: of the criteria that exist in 2.0, how
    many Does Not Support. Criteria introduced later are simply out of that
    reader's scope, so each version's numbers only include what it defines.
    """
    out = {}
    for ver in VERSIONS:
        sub = [r for r in rows if VERSIONS.index(r["introduced"]) <= VERSIONS.index(ver)]
        c = {k: 0 for k in STATUSES}
        for r in sub:
            c[r["status"]] += 1
        out[ver] = {"total": len(sub), **c}
    return out


def derive_coverage(data):
    """Criteria and state coverage from the same rules build_report uses."""
    rows = [r for r in derive_conformance(data) if not r.get("beyond_target")]
    applicable = [r for r in rows if r["status"] != "Not Applicable"]
    evaluated = [r for r in applicable if r["status"] != "Not Evaluated"]

    matrix = data.get("state_matrix") or {}
    states_applicable = states_present = 0
    for screen, cells in matrix.items():
        for state, val in (cells or {}).items():
            v = (val.get("status") if isinstance(val, dict) else val) or ""
            v = str(v).strip().lower()
            if v in ("n/a", "na", "not applicable"):
                continue
            states_applicable += 1
            if v == "present":
                states_present += 1

    return {
        "criteria_applicable": len(applicable),
        "criteria_evaluated": len(evaluated),
        "states_applicable": states_applicable,
        "states_present": states_present,
    }


# --------------------------------------------------------------------------- #
# Audit scope
#
# Every audit grades six dimensions by default. A client can ask for a narrower
# question ("grade WCAG conformance only"), which the intake records in
# `.audit/config.json` as:
#
#   "scope": {"label": "Accessibility only", "dimensions": ["accessibility"]}
#
# There is no preset table to keep in sync: the intake writes the dimension
# list it chose, and an absent or empty scope means the full six, so every
# findings file written before scope existed keeps scoring the same way.
#
# Scope narrows what is SCORED, never what is reported: a finding outside the
# scope stays in `findings`, is marked `in_scope: false` by the scorer, and is
# printed in its own clearly labelled section. Nothing is silently dropped.
# --------------------------------------------------------------------------- #

ALL_DIMENSIONS = ["accessibility", "interaction_states", "robustness",
                  "content_copy", "visual_system", "platform_fit"]

DIMENSION_LABELS = {
    "accessibility": "Accessibility",
    "interaction_states": "Interaction & States",
    "robustness": "Robustness & Edge Cases",
    "content_copy": "Content & Copy",
    "visual_system": "Visual & Design System",
    "platform_fit": "Platform Fit",
}


def resolve_scope(data):
    """Return {label, dimensions, excluded, is_full} for a findings/config dict.

    Unknown dimension names are reported rather than dropped, so a typo in the
    brief cannot quietly shrink the audit.
    """
    raw = data.get("scope") or {}
    if isinstance(raw, list):           # tolerate a bare list
        raw = {"dimensions": raw}
    dims = [d for d in (raw.get("dimensions") or []) if d]
    unknown = [d for d in dims if d not in ALL_DIMENSIONS]
    dims = [d for d in ALL_DIMENSIONS if d in dims]  # canonical order
    if not dims:
        dims = list(ALL_DIMENSIONS)
    is_full = len(dims) == len(ALL_DIMENSIONS)
    excluded = [d for d in ALL_DIMENSIONS if d not in dims]
    names = [DIMENSION_LABELS[d] for d in dims]
    listed = names[0] if len(names) == 1 else ", ".join(names[:-1]) + " and " + names[-1]
    label = raw.get("label") or ("Full audit" if is_full else listed + " only")
    return {"label": label, "dimensions": dims, "excluded": excluded,
            "is_full": is_full, "unknown": unknown,
            "excluded_labels": [DIMENSION_LABELS[d] for d in excluded]}
