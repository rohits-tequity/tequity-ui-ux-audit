#!/usr/bin/env python3
"""Verdict and WCAG-engine tests. Run: python3 tests/test_verdict.py

Every fixture is built in a temporary directory from an invented product
("Lumen Pay"), so no audit data ever lives in the repo. Each test states the
rule it proves.
"""
from __future__ import annotations

import copy
import json
import os
import re
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.join(HERE, "..", "scripts")
sys.path.insert(0, SCRIPTS)
import wcag22 as w  # noqa: E402

TMP = tempfile.mkdtemp(prefix="verdict-")
D_22 = [sc for sc, *_ in w.criteria_for("WCAG 2.2 AA") if w.checkability(sc) == "D"]
FAILS = []


def base(findings, supports=None, **kw):
    d = {"product": "Lumen Pay (test)", "screens": ["Pay"], "platform": "rn",
         "phase": "design", "conformance_target": "WCAG 2.2 AA",
         "findings": findings,
         "evaluated": {"supports": list(D_22 if supports is None else supports),
                       "sample": ["Pay"]}}
    d.update(kw)
    return d


def f(fid, sev, dim="accessibility", **kw):
    x = {"id": fid, "severity": sev, "dimension": dim, "title": f"{fid} test finding",
         "location": {"screen": "Pay"}, "user_impact": "x", "fix": "Set `a` from 1 to 2",
         "retest": "x", "confidence": "measured", "evidence": {"measured": "1", "required": "2"}}
    x.update(kw)
    return x


def score(d, name):
    p = os.path.join(TMP, name + ".json")
    out = os.path.join(TMP, name + ".sc.json")
    json.dump(d, open(p, "w"))
    r = subprocess.run([sys.executable, os.path.join(SCRIPTS, "score.py"),
                        "--findings", p, "--out", out], capture_output=True, text=True)
    if r.returncode:
        return None, r
    return json.load(open(out)), r


def build(d, sc, name):
    p = os.path.join(TMP, name + ".json")
    s = os.path.join(TMP, name + ".sc.json")
    json.dump(d, open(p, "w"))
    json.dump(sc, open(s, "w"))
    out = os.path.join(TMP, name + ".html")
    r = subprocess.run([sys.executable, os.path.join(SCRIPTS, "build_report.py"),
                        "--findings", p, "--scorecard", s, "--out", out,
                        "--config", os.path.join(TMP, "none.json")],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    return open(out, encoding="utf-8").read()


def check(name, cond, detail=""):
    print(("ok   " if cond else "FAIL ") + name + ("" if cond else f"  ({detail})"))
    if not cond:
        FAILS.append(name)


def gate(d, name):
    sc, r = score(d, name)
    assert sc, r.stderr
    return sc["verdict"]["gate"], sc


# --- gate rows, first match wins ------------------------------------------ #
g, sc = gate(base([f("DS-001", "minor", "visual_system")]), "go")
check("minor only, every D criterion judged -> GO", g == "GO", g)
check("GO at design with no known failures -> design done", sc["verdict"]["design_done"])

g, _ = gate(base([f("DS-001", "minor", "visual_system")], supports=D_22[:-3]), "nd")
check("unjudged D criteria, nothing failing -> NOT DECIDED", g == "NOT DECIDED", g)

g, _ = gate(base([f("A11Y-001", "serious", wcag=[{"sc": "4.1.2", "effect": "fails"}])],
                 supports=[]), "nogo-lowcov")
check("a known serious failure decides NO-GO even at low coverage", g == "NO-GO", g)

g, sc = gate(base([f("A11Y-001", "moderate", wcag=[{"sc": "2.5.8", "effect": "fails"}])],
                  supports=[x for x in D_22 if x != "2.5.8"]), "fix")
check("moderate failing an AA criterion -> GO WITH FIXES", g == "GO WITH FIXES", g)
check("... and the AA level reads Fails", sc["verdict"]["at_target"]["status"] == "Fails")
check("... and no design done", not sc["verdict"]["design_done"])

g, _ = gate(base([f("A11Y-001", "moderate", wcag=[{"sc": "1.4.3", "effect": "fails"}])],
                 supports=D_22[:12]), "fix-unjudged")
check("a moderate failure never hides unjudged criteria: NOT DECIDED", g == "NOT DECIDED", g)
d = base([f(f"DS-{i:03d}", "minor", "visual_system") for i in range(1, 17)], supports=[],
         phase="code", scope={"dimensions": ["accessibility"]})
g, _ = gate(d, "code-hole")
check("almost nothing judged is NOT DECIDED whatever the score", g == "NOT DECIDED", g)
g, sc = gate(base([f("DS-001", "minor", "visual_system")], scope={"dimensions": ["accessibility"]}), "a11y-done")
check("a narrowed scope never declares design done", g == "GO" and not sc["verdict"]["design_done"])
d = base([f("A11Y-008", "info", wcag=[{"sc": "1.4.3", "effect": "risk"}])],
         supports=[x for x in D_22 if x != "1.4.3"])
d["evaluated"]["indeterminate"] = ["1.4.3"]
d["evaluated"]["remarks"] = {"1.4.3": "text over the aurora gradient on Question 3"}
g, sc = gate(d, "indet")
check("text over imagery recorded as indeterminate moves to build checks: GO",
      g == "GO" and "1.4.3" in sc["verdict"]["handoff_criteria"], (g, sc["verdict"]["handoff_criteria"]))

d = base([], supports=D_22[:13])
d["evaluated"]["indeterminate"] = [x for x in D_22[13:]]
d["evaluated"]["remarks"] = {x: "cannot tell" for x in D_22[13:]}
_, r = score(d, "indet-abuse")
check("indeterminate is limited to contrast over imagery", r.returncode == 1 and "only contrast" in r.stderr,
      r.stderr[-200:])
d = base([], supports=[x for x in D_22 if x != "1.4.3"])
d["evaluated"]["indeterminate"] = ["1.4.3"]
_, r = score(d, "indet-noremark")
check("indeterminate without a reason is refused", r.returncode == 1, r.returncode)
for crit, title, want in (
        ("WCAG 2.2 SC 1.4.3", "Label passes 3:1 but 1.4.3 needs 4.5:1", "fails"),
        ("1.4.3 and 1.4.11, both met in dark mode", "", "context"),
        ("WCAG 2.2 SC 2.5.8; Android 48dp / iOS 44pt",
         "Checkboxes are now 24x24, which clears WCAG but not the platform minimum", "context")):
    refs = w.wcag_refs(f("A11Y-013", "moderate", criterion=crit, title=title))
    check(f"legacy '{(title or crit)[:38]}' reads {want}", refs and all(x["effect"] == want for x in refs), refs)
refs = w.wcag_refs(f("A11Y-014", "serious", criterion="2.4.7 Focus Visible: no focus variant; meets 1.4.11 elsewhere"))
check("a pass word before a criterion makes that one context, not a failure",
      [(x["sc"], x["effect"]) for x in refs] == [("2.4.7", "fails"), ("1.4.11", "context")], refs)

# --- minor never changes a status ----------------------------------------- #
g, sc = gate(base([f("A11Y-002", "minor", criterion="WCAG 2.2 SC 2.5.8 Target Size")]), "minor-sc")
rows = w.derive_conformance(base([f("A11Y-002", "minor", criterion="WCAG 2.2 SC 2.5.8")]))
r258 = next(r for r in rows if r["sc"] == "2.5.8")
check("a minor citing 2.5.8 leaves it Supports and GO", g == "GO" and r258["status"] == "Supports",
      f"{g} {r258['status']}")
_, r = score(base([f("A11Y-003", "minor", wcag=[{"sc": "2.5.8", "effect": "fails"}])]), "floor")
check("severity floor: a minor claiming a WCAG failure is refused", r.returncode == 1, r.returncode)

# --- parsing the free-text criterion ------------------------------------- #
refs = w.wcag_refs(f("A11Y-004", "serious",
                     criterion="WCAG 2.2 SC 4.1.2 Name, Role, Value, Level A; SC 2.5.8 Target Size, Level AA"))
check("every SC in a criterion is read, not only the first",
      [x["sc"] for x in refs] == ["4.1.2", "2.5.8"] and all(x["effect"] == "fails" for x in refs), refs)
refs = w.wcag_refs(f("UX-002", "moderate", "platform_fit",
                     criterion="iOS HIG 44pt (Does Not Support); WCAG 2.2 SC 2.5.8 is met at 24px"))
check("'2.5.8 is met' is context, not a failure", refs == [{"sc": "2.5.8", "effect": "context", "source": "inferred"}], refs)
refs = w.wcag_refs(f("EDGE-003", "moderate", "robustness",
                     criterion="WCAG 2.2 SC 1.4.4 Resize Text, Level AA (design-stage risk)"))
check("'risk' hedges to risk", refs and refs[0]["effect"] == "risk", refs)
refs = w.wcag_refs(f("A11Y-009", "moderate", title="Checkboxes are 24x24, which clears 2.5.8 but not 44pt",
                     criterion="WCAG 2.2 SC 2.5.8; iOS 44pt"))
check("a title saying this criterion is met makes it context", refs and refs[0]["effect"] == "context", refs)
refs = w.wcag_refs(f("A11Y-011", "moderate", title="Caption contrast meets WCAG in dark mode but not in light mode",
                     criterion="WCAG 2.2 SC 1.4.3"))
check("a vague 'meets WCAG' title never hides a failure", refs and refs[0]["effect"] == "fails", refs)
_, warns = w.lint_findings({"findings": [f("A11Y-011", "moderate", title="Caption meets WCAG in dark mode",
                                            criterion="WCAG 2.2 SC 1.4.3")]})
check("... and the linter asks for an explicit wcag field", bool(warns), warns)
for crit, want in (("WCAG 2.2 SC 1.4.3; does not satisfy 4.5:1", "fails"),
                   ("WCAG 2.2 SC 1.4.3 only meets the large-text threshold", "fails"),
                   ("passes 3:1 but 1.4.3 needs 4.5:1", "fails"),
                   ("WCAG 2.2 SC 1.4.1 fails if the user is colour blind", "fails"),
                   ("WCAG 2.2 SC 3.3.1 and 3.3.3 once built", "risk")):
    refs = w.wcag_refs(f("A11Y-012", "serious", criterion=crit))
    check(f"legacy text '{crit[:40]}' reads {want}", refs and all(x["effect"] == want for x in refs), refs)
refs = w.wcag_refs(f("UX-009", "moderate", "platform_fit", criterion="Android 48dp; WCAG 2.5.8 at 24px"))
check("a platform-fit finding never infers a WCAG failure", refs and refs[0]["effect"] == "context", refs)
check("'WCAG 2.2 A/AA' targets AA", w.parse_target("WCAG 2.2 A/AA") == ("2.2", "AA"))

# --- platform guideline vs WCAG ------------------------------------------ #
g, sc = gate(base([f("UX-001", "serious", "platform_fit", criterion="iOS HIG 44pt",
                     wcag=[{"sc": "2.5.8", "effect": "context"}])]), "platform")
check("a serious platform miss blocks the go-ahead", g == "NO-GO", g)
check("... but WCAG still reads no known failures",
      sc["verdict"]["at_target"]["status"] == "No known failures", sc["verdict"]["at_target"]["status"])

# --- scope --------------------------------------------------------------- #
d = base([f("A11Y-001", "serious", "platform_fit", wcag=[{"sc": "2.5.8", "effect": "fails"}])],
         scope={"dimensions": ["accessibility"]})
rows = w.derive_conformance(d)
check("an out-of-scope finding never changes a WCAG status",
      next(r for r in rows if r["sc"] == "2.5.8")["status"] == "Supports")
g, sc = gate(d, "oos")
check("... and the gate is GO on the scoped dimensions, qualified",
      g == "GO" and "not for the product as a whole" in sc["verdict"]["line"], sc["verdict"]["line"])
g, sc = gate(base([f("DS-001", "minor", "visual_system")],
                  scope={"dimensions": ["visual_system", "content_copy"]}), "ds-only")
check("design-system-only scope: WCAG not assessed, never design done",
      not sc["verdict"]["wcag_assessed"] and not sc["verdict"]["design_done"])

# --- info never hides an explicit Supports -------------------------------- #
rows = w.derive_conformance(base([f("A11Y-008", "info", wcag=[{"sc": "1.4.3", "effect": "risk"}])]))
r143 = next(r for r in rows if r["sc"] == "1.4.3")
check("info finding keeps 1.4.3 Supports and adds a remark",
      r143["status"] == "Supports" and "A11Y-008" in r143["remarks"], r143)

# --- target-aware grid ---------------------------------------------------- #
d21 = base([], supports=[sc for sc, *_ in w.criteria_for("WCAG 2.1 AA") if w.checkability(sc) == "D"],
           conformance_target="WCAG 2.1 AA")
_, sc = gate(d21, "t21")
grid = sc["verdict"]["grid"]
check("2.1 target: the 2.2 row is Not targeted",
      all(grid["2.2"][lvl]["status"] == "Not targeted" for lvl in ("A", "AA", "AAA")))
check("2.1 target: AAA is Not targeted", grid["2.1"]["AAA"]["status"] == "Not targeted")
dA = base([], conformance_target="WCAG 2.2 A")
_, sc = gate(dA, "tA")
check("Level A target: AA is Not targeted", sc["verdict"]["grid"]["2.2"]["AA"]["status"] == "Not targeted")

# --- resolved fixes never flip a criterion to Supports --------------------- #
d = base([], supports=[x for x in D_22 if x != "1.4.11"],
         resolved=[{"id": "A11Y-010", "sc": ["1.4.11"], "outcome": "fixed"}])
r = next(r for r in w.derive_conformance(d) if r["sc"] == "1.4.11")
check("a verified fix alone leaves the criterion Not Evaluated", r["status"] == "Not Evaluated"
      and "not re-checked" in r["remarks"], r)

# --- explicit conformance rows need evidence ------------------------------ #
_, r = score(base([], conformance=[{"sc": "1.4.3", "status": "Does Not Support"}]), "badrow")
check("a failing conformance row with no finding is refused", r.returncode == 1)

# --- the words the report must never use ---------------------------------- #
banned = re.compile(r"\b(met|conformant|compliant|certified)\b", re.I)
for name in ("go", "fix", "platform", "t21"):
    sc = json.load(open(os.path.join(TMP, name + ".sc.json")))
    v = sc["verdict"]
    text = " ".join([v["line"], v["wcag_line"]] + [c["status"] for r_ in v["grid"].values() for c in r_.values()])
    check(f"no conformance claim in verdict ({name})", not banned.search(text), text)

# --- rendering ------------------------------------------------------------ #
dgo = base([f("DS-001", "minor", "visual_system")], overview=["x 1"], limitations=["x"])
sc, _ = score(dgo, "go-r")
html = build(dgo, sc, "go-r")
check("GO report says Design done", "Design done" in html)
check("GO report prints no grade letter", 'class="grade-letter"' not in html)
check("GO report shows AA (incl. A)", "AA (incl. A)" in html)
dng = base([f("A11Y-001", "serious", wcag=[{"sc": "4.1.2", "effect": "fails"}])], overview=["x 1"],
           limitations=["x"])
sc, _ = score(dng, "nogo-r")
html = build(dng, sc, "nogo-r")
check("NO-GO report never says Design done", "Design done" not in html)
check("NO-GO card is tagged as blocking", "Blocks go-ahead: no-go" in html)
legacy = copy.deepcopy(sc)
for k in ("verdict", "finding_blocks", "schema_version"):
    legacy.pop(k, None)
legacy["scoring_model"].pop("version", None)
html = build(dng, legacy, "legacy")
check("a pre-0.8 scorecard still builds and says it predates the verdict",
      "predates the verdict model" in html)

# --- the two copies of the checkability table agree ----------------------- #
md = open(os.path.join(HERE, "..", "..", "figma-design-audit", "references",
                       "wcag-22-figma-checks.md"), encoding="utf-8").read()
mismatch = []
for line in md.splitlines():
    cells = [c.strip() for c in line.split("|")]
    if len(cells) < 5 or not re.match(r"\d\.\d", cells[1]):
        continue
    tag = cells[3].replace("/", "")
    for sc_ in re.findall(r"\b\d\.\d\.\d{1,2}\b", cells[1]):
        if w.DESIGN_CHECKABILITY.get(sc_) != tag:
            mismatch.append(f"{sc_}: md {tag} vs py {w.DESIGN_CHECKABILITY.get(sc_)}")
check("wcag-22-figma-checks.md agrees with DESIGN_CHECKABILITY", not mismatch, mismatch)

print(f"\n{len(FAILS)} failed" if FAILS else "\nall verdict tests passed")
sys.exit(1 if FAILS else 0)
