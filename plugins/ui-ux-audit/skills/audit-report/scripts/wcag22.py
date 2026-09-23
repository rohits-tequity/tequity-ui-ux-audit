"""Shared reference data for the report scripts.

WCAG 2.2 success criteria: Level A/AA (55) and AAA (31), each tagged with the
level, the version that introduced it and what each audit phase can settle,
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
    # "WCAG 2.2 A/AA" or "Level A and AA" means the higher level: AA includes A
    levels = re.findall(r"(?<![A-Z])(AAA|AA|A)(?![A-Z])", t.upper().replace("WCAG", ""))
    level = max(levels, key=["A", "AA", "AAA"].index) if levels else "AA"
    return (m_v.group(1) if m_v else "2.2", level)


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
# Severities that can assert a failure. Minor and info never change a status:
# minor is defined as "no user-visible failure" (finding-spec.md), and info is
# a note. They add a remark to the criterion instead.
FAILING_SEVERITIES = ("critical", "serious", "moderate")
EFFECTS = ("fails", "risk", "context")

# --------------------------------------------------------------------------- #
# What each phase can settle, per criterion.
#
#   D   the phase can show a pass or a failure
#   DR  the phase can show a failure, but only a later phase can show a pass
#   R   the phase cannot judge it at all
#
# At design stage a verdict can only be "no known failures" once every D
# criterion has been judged; DR and R criteria are listed as build checks.
# Source of truth for A/AA: figma-design-audit/references/wcag-22-figma-checks.md
# (tests/test_verdict.py fails if the two disagree). AAA follows the design-stage
# list in audit-report/references/wcag-versions.md.
# --------------------------------------------------------------------------- #
DESIGN_CHECKABILITY = {
    # Perceivable
    "1.1.1": "DR", "1.2.1": "DR", "1.2.2": "DR", "1.2.3": "DR", "1.2.4": "DR",
    "1.2.5": "DR", "1.3.1": "D", "1.3.2": "DR", "1.3.3": "D", "1.3.4": "DR",
    "1.3.5": "D", "1.4.1": "D", "1.4.2": "R", "1.4.3": "D", "1.4.4": "DR",
    "1.4.5": "D", "1.4.10": "DR", "1.4.11": "D", "1.4.12": "D", "1.4.13": "DR",
    # Operable
    "2.1.1": "R", "2.1.2": "R", "2.1.4": "R", "2.2.1": "D", "2.2.2": "D",
    "2.3.1": "D", "2.4.1": "R", "2.4.2": "DR", "2.4.3": "DR", "2.4.4": "D",
    "2.4.5": "DR", "2.4.6": "D", "2.4.7": "D", "2.4.11": "DR", "2.5.1": "D",
    "2.5.2": "R", "2.5.3": "D", "2.5.4": "D", "2.5.7": "D", "2.5.8": "D",
    # Understandable
    "3.1.1": "DR", "3.1.2": "DR", "3.2.1": "DR", "3.2.2": "DR", "3.2.3": "D",
    "3.2.4": "D", "3.2.6": "D", "3.3.1": "D", "3.3.2": "D", "3.3.3": "D",
    "3.3.4": "D", "3.3.7": "D", "3.3.8": "D",
    # Robust
    "4.1.2": "DR", "4.1.3": "DR",
    # AAA
    "1.2.6": "DR", "1.2.7": "DR", "1.2.8": "DR", "1.2.9": "R", "1.3.6": "DR",
    "1.4.6": "D", "1.4.7": "R", "1.4.8": "D", "1.4.9": "D", "2.1.3": "R",
    "2.2.3": "R", "2.2.4": "R", "2.2.5": "R", "2.2.6": "R", "2.3.2": "R",
    "2.3.3": "D", "2.4.8": "DR", "2.4.9": "D", "2.4.10": "D", "2.4.12": "DR",
    "2.4.13": "D", "2.5.5": "D", "2.5.6": "R", "3.1.3": "R", "3.1.4": "R",
    "3.1.5": "D", "3.1.6": "R", "3.2.5": "R", "3.3.5": "DR", "3.3.6": "D",
    "3.3.9": "D",
}


# The only design-checkable criteria a design can be genuinely unable to settle:
# contrast of text or boundaries over a photo, video or gradient.
INDETERMINATE_OK = {"1.4.3", "1.4.6", "1.4.11"}


def checkability(sc, phase="design"):
    """D / DR / R for a criterion in a phase.

    Design uses the table above. Source code can show a failure but never that
    something renders or behaves correctly, so every criterion is at best DR in
    the code phase. A running build can settle everything the tools can reach;
    the manual screen-reader pass is tracked separately (see level_status).
    """
    base = DESIGN_CHECKABILITY.get(sc, "R")
    if phase == "code":
        return "R" if base == "R" else "DR"
    if phase in ("runtime", "combined"):
        return "D"
    return base


def sc_of(finding):
    """First success-criterion number referenced by a finding, or None. Kept for
    callers that only need one; conformance uses wcag_refs()."""
    refs = wcag_refs(finding)
    return refs[0]["sc"] if refs else None


# Words that mean a clause is not asserting a failure of the criterion it names.
_MET = re.compile(r"\b(is met|are met|met|meets|passes|pass|satisf(y|ies)|clears)\b", re.I)
# A pass word preceded by one of these is a failure ("does not satisfy 4.5:1",
# "only meets the large-text threshold").
_NEG = re.compile(r"\b(not|never|no longer|fails?|failing|does not|doesn't|only|below|under|short of)\b", re.I)
_RISK = re.compile(r"\b(risk|once built|when built|applies if|only if|not settled|indeterminate|"
                   r"cannot be settled|to confirm|unconfirmed)\b", re.I)


def wcag_refs(finding):
    """Every WCAG criterion a finding touches, each with its effect.

    Preferred: an explicit `wcag: [{"sc": "2.5.8", "effect": "fails"}]` on the
    finding. `effect` is one of:
      fails    the finding asserts the criterion is not met here
      risk     the criterion may fail; not settled at this phase
      context  cited for reference ("2.5.8 is met at 24px")
    Legacy files have only the free-text `criterion`. Then every criterion number
    is read, clause by clause (split on ';'), and a clause that says the rule is
    met becomes context, one that hedges becomes risk. A clause is only read as
    `fails` when the finding is moderate or worse, because a minor finding is
    defined as having no user-visible failure.
    """
    sev = finding.get("severity", "minor")
    explicit = finding.get("wcag")
    out, seen = [], set()
    if isinstance(explicit, list) and explicit:
        for r in explicit:
            if not isinstance(r, dict):
                continue
            m = SC_RE.search(str(r.get("sc") or ""))
            if not m or m.group(1) in seen:
                continue
            eff = r.get("effect") if r.get("effect") in EFFECTS else "fails"
            seen.add(m.group(1))
            out.append({"sc": m.group(1), "effect": eff, "source": "explicit"})
        return out
    text = str(finding.get("criterion") or "")
    title = str(finding.get("title") or "")
    # A platform-fit finding is about a platform guideline. Any WCAG number in
    # it is context unless the author says otherwise with an explicit field.
    platform = finding.get("dimension") == "platform_fit"
    all_scs = {m.group(1) for m in SC_RE.finditer(text)}
    # "24x24, which clears WCAG but not the platform minimum": a title that says
    # WCAG is met and contrasts it with a platform number speaks for the one
    # WCAG criterion the finding cites. "Meets WCAG in dark mode but not in
    # light mode" has no platform contrast and changes nothing.
    title_generic_met = (len(all_scs) == 1 and bool(re.search(r"\bWCAG\b", title))
                         and _passes(title.split("WCAG")[0] + " ")
                         and bool(re.search(r"\bbut not\b[^.;]*\b(platform|HIG|Material|iOS|Android|\d+\s?(pt|dp))",
                                            title, re.I)))
    for clause in re.split(r";", text):
        hits = list(SC_RE.finditer(clause))
        effects = [None] * len(hits)
        tail = clause[hits[-1].end():] if hits else ""
        # right to left, so "1.4.3 and 1.4.11, both met" gives both the same
        # reading: a criterion followed only by a joiner takes the next one's
        for i in range(len(hits) - 1, -1, -1):
            m = hits[i]
            window = clause[m.end(): hits[i + 1].start() if i + 1 < len(hits) else len(clause)]
            before = clause[hits[i - 1].end() if i else 0: m.start()]
            if i + 1 < len(hits) and re.fullmatch(r"\s*(,|and|or|&|/|\s)*\s*", window):
                effects[i] = effects[i + 1]
                continue
            # a hedge at the end of a clause ("3.3.1 and 3.3.3 once built")
            # covers every criterion the clause lists
            eff = _effect(window + " " + (tail if _RISK.search(tail) else ""), before, sev, platform)
            if eff == "fails" and (_title_says_met(title, m.group(1)) or title_generic_met):
                eff = "context"
            effects[i] = eff
        for m, eff in zip(hits, effects):
            if m.group(1) in seen:
                continue
            seen.add(m.group(1))
            out.append({"sc": m.group(1), "effect": eff, "source": "inferred"})
    return out


def _passes(window):
    m = _MET.search(window)
    return bool(m and not _NEG.search(window[:m.start()]))


_CONTRAST = re.compile(r"\b(but|however|yet|while|needs?|requires?|whereas)\b", re.I)


def _title_says_met(title, sc):
    """True when the title says this criterion is met: "clears 2.5.8", "2.5.8
    is met". A pass word that belongs to something else ("passes 3:1 but 1.4.3
    needs 4.5:1") does not count."""
    for seg in re.split(r"[.;:]\s", title):
        k = seg.find(sc)
        if k < 0:
            continue
        before, after = seg[:k][-60:], seg[k + len(sc):][:40]
        mb = _MET.search(before)
        if mb and _passes(before) and not _CONTRAST.search(before[mb.end():]):
            return True
        ma = _MET.search(after)
        if ma and _passes(after) and not _CONTRAST.search(after[:ma.start()]):
            return True
    return False


def _effect(window, before, sev, platform):
    """window: the words after this criterion number; before: the words between
    the previous number (or the clause start) and this one ("meets 1.4.11",
    "Risk: SC 1.4.4")."""
    mb = _MET.search(before)
    if _passes(window) or (mb and _passes(before) and not _CONTRAST.search(before[mb.end():])
                           and not SC_RE.search(before[mb.end():])):
        return "context"
    if _RISK.search(window) or _RISK.search(before):
        return "risk"
    if platform:
        return "context"
    return "fails" if sev in FAILING_SEVERITIES else "risk"


def lint_findings(data):
    """Problems a findings file must not ship with. Returns (errors, warnings).

    The severity floor: an explicit `fails` on a criterion at or below the target
    level needs moderate or worse. A Level A failure on the primary path is
    serious by the rubric; the linter cannot see "primary path", so it enforces
    only the floor it can check.
    """
    errors, warnings = [], []
    for f in data.get("findings", []):
        fid = f.get("id") or "?"
        sev = f.get("severity", "minor")
        for r in wcag_refs(f):
            if r["source"] == "explicit" and r["effect"] == "fails" and sev not in FAILING_SEVERITIES:
                errors.append(f"{fid}: asserts a failure of {r['sc']} but is rated {sev}. "
                              f"A WCAG failure is moderate or worse; if it is only a risk, "
                              f"set effect to risk or context.")
        if not f.get("wcag") and SC_RE.search(str(f.get("criterion") or "")):
            txt = str(f.get("criterion"))
            ttl = str(f.get("title") or "")
            if (_MET.search(txt) or _RISK.search(txt) or f.get("dimension") == "platform_fit"
                    or re.search(r"\bif\b", txt, re.I) or (_MET.search(ttl) and "WCAG" in ttl)):
                warnings.append(f"{fid}: criterion text hedges ('{txt[:70]}'); read as "
                                f"{', '.join(r['sc'] + '=' + r['effect'] for r in wcag_refs(f))}. "
                                f"Add an explicit wcag field to be sure.")
    ev = data.get("evaluated") or {}
    for sc in ev.get("indeterminate") or []:
        if sc not in INDETERMINATE_OK:
            errors.append(f"evaluated.indeterminate {sc}: only contrast over imagery can be indeterminate at "
                          f"design ({', '.join(sorted(INDETERMINATE_OK))}); judge {sc} or leave it Not Evaluated")
        elif not ((ev.get("remarks") or {}).get(sc) or "").strip():
            errors.append(f"evaluated.indeterminate {sc} needs a remark saying why the design cannot settle it "
                          f"(for example: text over a photo on Question 3)")
    fails_by_sc = {}
    for f in data.get("findings", []):
        if f.get("severity", "minor") in FAILING_SEVERITIES:
            for r in wcag_refs(f):
                if r["effect"] == "fails":
                    fails_by_sc.setdefault(r["sc"], []).append(f.get("id"))
    for row in data.get("conformance") or []:
        sc, st = row.get("sc"), row.get("status")
        if st in ("Does Not Support", "Partially Supports") and not fails_by_sc.get(sc):
            errors.append(f"conformance row {sc} says {st} but no finding fails it. "
                          f"Every failing status needs a finding with the evidence.")
        if st in ("Supports", "Not Applicable") and fails_by_sc.get(sc):
            errors.append(f"conformance row {sc} says {st} while "
                          f"{', '.join(map(str, fails_by_sc[sc]))} fails it.")
    return errors, warnings


def _finding_in_scope(f, dims):
    d = f.get("dimension")
    d = d if d in ALL_DIMENSIONS else "accessibility"
    return d in dims


def derive_conformance(data):
    """Build the ACR-style table from a findings file.

    Precedence per criterion:
      1. an explicit row in data["conformance"] (list of {sc, status, remarks})
      2. an in-scope finding with effect `fails`: critical or serious gives
         Does Not Support, moderate gives Partially Supports
      3. data["evaluated"]["supports"] / ["not_applicable"] lists
      4. Not Evaluated
    Findings with effect risk or context, findings rated minor or info, and
    findings outside the agreed scope never change a status; they add a remark.
    A criterion whose only findings were fixed (data["resolved"]) stays Not
    Evaluated unless the auditor re-checked it and listed it under supports:
    one fixed instance does not show the criterion holds everywhere.
    Returns a list of row dicts in WCAG order.
    """
    explicit = {r["sc"]: r for r in (data.get("conformance") or []) if r.get("sc")}
    ev = data.get("evaluated") or {}
    supports = set(ev.get("supports") or [])
    not_applicable = set(ev.get("not_applicable") or [])
    ev_remarks = ev.get("remarks") or {}
    # A design-checkable criterion the design genuinely cannot settle on this
    # sample (text over a photo or gradient for 1.4.3) is recorded here with a
    # reason. It stays Not Evaluated but moves to the build checks for this
    # round, instead of holding the verdict at NOT DECIDED forever.
    indeterminate = {k for k in (ev.get("indeterminate") or [])
                     if isinstance(k, str) and k in INDETERMINATE_OK and (ev_remarks.get(k) or "").strip()}
    dims = set(resolve_scope(data)["dimensions"])
    phase = data.get("phase", "design")

    failing, noting = {}, {}
    for f in data.get("findings", []):
        in_scope = _finding_in_scope(f, dims)
        for r in wcag_refs(f):
            sev = f.get("severity", "minor")
            if in_scope and r["effect"] == "fails" and sev in FAILING_SEVERITIES:
                failing.setdefault(r["sc"], []).append(f)
            else:
                why = ("outside the agreed scope" if not in_scope else
                       "risk" if r["effect"] == "risk" else
                       "context" if r["effect"] == "context" else f"{sev}, no failure asserted")
                noting.setdefault(r["sc"], []).append((f, why))
    resolved_by_sc = {}
    for rz in data.get("resolved") or []:
        if not isinstance(rz, dict):
            continue
        scs = rz.get("sc") or []
        if isinstance(scs, str):
            scs = [scs]
        if not isinstance(scs, list):
            continue
        for sc in scs:
            m = SC_RE.search(str(sc))
            if m:
                resolved_by_sc.setdefault(m.group(1), []).append(rz)

    def note_text(sc):
        parts = [f"{f.get('id')}: {why}" for f, why in noting.get(sc, [])]
        parts += [f"{rz.get('id')}: fix verified" for rz in resolved_by_sc.get(sc, [])]
        return "; ".join(parts)

    rows = []
    target = data.get("conformance_target", "WCAG 2.2 AA")
    for sc, name, level, introduced in criteria_for(target):
        ids = [f.get("id") for f in failing.get(sc, []) if f.get("id")]
        note_ids = [f.get("id") for f, _ in noting.get(sc, []) if f.get("id")]
        if sc in explicit:
            r = explicit[sc]
            status = r.get("status") if r.get("status") in STATUSES else "Not Evaluated"
            remarks = r.get("remarks", "")
        elif sc in failing:
            fs = failing[sc]
            worst = min((f.get("severity", "minor") for f in fs), key=SEVERITY_ORDER.index)
            status = "Does Not Support" if worst in ("critical", "serious") else "Partially Supports"
            remarks = "; ".join(
                f"{f.get('id')}: {f.get('title') or f.get('detail') or ''}".strip() for f in fs)
        elif sc in not_applicable:
            status, remarks = "Not Applicable", ev_remarks.get(sc, "")
        elif sc in supports:
            status, remarks = "Supports", ev_remarks.get(sc, "")
        else:
            status, remarks = "Not Evaluated", ""
            if sc in indeterminate:
                remarks = ("Indeterminate at this phase: " + str(ev_remarks.get(sc) or "no reason recorded")
                           + ". Moved to the build checks.")
            if resolved_by_sc.get(sc):
                remarks = "Fix verified for " + ", ".join(
                    str(rz.get("id")) for rz in resolved_by_sc[sc]) + "; criterion not re-checked across the sample."
        extra = note_text(sc)
        if extra and extra not in remarks:
            remarks = (remarks + " | " if remarks else "") + "Noted: " + extra
        rows.append({"sc": sc, "name": name, "level": level, "status": status,
                     "remarks": remarks[:600], "finding_ids": ids, "note_ids": note_ids,
                     "introduced": introduced, "new_in_22": sc in WCAG_NEW_IN_22,
                     "beyond_target": False,
                     "checkability": ("DR" if sc in indeterminate and status == "Not Evaluated"
                                      else checkability(sc, phase))})

    # Criteria cited as failing beyond the target level (a AAA criterion under
    # an AA target) are still shown, flagged, so a real defect is never hidden
    # by the scope line. They never enter the level verdict.
    in_table = {r["sc"] for r in rows}
    lookup = {r[0]: r for r in WCAG_22_AA + WCAG_22_AAA}
    for sc, fs in failing.items():
        if sc in in_table or sc not in lookup:
            continue
        _, name, level, introduced = lookup[sc]
        worst = min((f.get("severity", "minor") for f in fs), key=SEVERITY_ORDER.index)
        rows.append({"sc": sc, "name": name, "level": level,
                     "status": "Does Not Support" if worst in ("critical", "serious") else "Partially Supports",
                     "remarks": ("Beyond the audit's target, reported because a finding cites it. " +
                                 "; ".join(f"{f.get('id')}: {f.get('title') or ''}" for f in fs))[:500],
                     "finding_ids": [f.get("id") for f in fs], "note_ids": [],
                     "introduced": introduced, "new_in_22": sc in WCAG_NEW_IN_22,
                     "beyond_target": True, "checkability": checkability(sc, phase)})
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


LEVELS = ["A", "AA", "AAA"]
LEVEL_LABEL = {"A": "Level A", "AA": "Level AA (includes A)", "AAA": "Level AAA (includes AA)"}


def level_status(rows, target, phase="design", manual_sr_pass=False):
    """The WCAG answer, per version and per level, in words that never claim
    conformance.

    For each WCAG version and each level up to the target (a level includes the
    ones below it, because AA conformance requires A):
      Fails            a criterion is Does Not Support or Partially Supports
      Incomplete       a criterion this phase can settle (D) is still Not Evaluated
      No known failures, N build checks pending
                       every D criterion judged, the rest wait for a later phase
      No failures found
                       runtime or combined phase, nothing Not Evaluated, and the
                       manual screen-reader pass recorded
      Not targeted     a version or level above the audit's target
    Returns {version: {level: {status, fails[], unjudged[], pending, total}}}.
    """
    t_ver, t_lvl = parse_target(target)
    base = [r for r in rows if not r.get("beyond_target")]
    out = {}
    for ver in VERSIONS:
        out[ver] = {}
        for lvl in LEVELS:
            if VERSIONS.index(ver) > VERSIONS.index(t_ver) or LEVELS.index(lvl) > LEVELS.index(t_lvl):
                out[ver][lvl] = {"status": "Not targeted", "fails": [], "unjudged": [],
                                 "pending": 0, "total": 0}
                continue
            sub = [r for r in base
                   if VERSIONS.index(r["introduced"]) <= VERSIONS.index(ver)
                   and LEVELS.index(r["level"]) <= LEVELS.index(lvl)]
            fails = [r["sc"] for r in sub if r["status"] in ("Does Not Support", "Partially Supports")]
            open_ = [r for r in sub if r["status"] == "Not Evaluated"]
            unjudged = [r["sc"] for r in open_ if r.get("checkability", checkability(r["sc"], phase)) == "D"]
            pending = len(open_) - len(unjudged)
            if fails:
                status = "Fails"
            elif unjudged:
                status = "Incomplete"
            elif phase in ("runtime", "combined") and not open_ and manual_sr_pass:
                status = "No failures found"
            else:
                status = "No known failures"
            out[ver][lvl] = {"status": status, "fails": fails, "unjudged": unjudged,
                             "pending": pending, "total": len(sub)}
    return out


def derive_coverage(data):
    """Criteria and state coverage from the same rules build_report uses."""
    rows = [r for r in derive_conformance(data) if not r.get("beyond_target")]
    applicable = [r for r in rows if r["status"] != "Not Applicable"]
    evaluated = [r for r in applicable if r["status"] != "Not Evaluated"]
    d_rows = [r for r in applicable if r.get("checkability") == "D"]
    d_eval = [r for r in d_rows if r["status"] != "Not Evaluated"]

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
        "checkable_applicable": len(d_rows),
        "checkable_evaluated": len(d_eval),
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
