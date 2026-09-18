#!/usr/bin/env python3
"""Turn confirmed findings into a reproducible scorecard.

The point of scoring in a script rather than by judgement: the same findings
always produce the same numbers, and the deduction model is inspectable. Two
audits of the same screen are comparable, and a re-audit after fixes shows real
movement instead of a fresh opinion.

Input JSON:
{
  "screens": ["Checkout"],
  "platform": "ios",
  "conformance_target": "WCAG 2.2 AA",
  "phase": "design" | "runtime" | "combined",
  "findings": [
     {"id":"A11Y-001","severity":"critical","dimension":"accessibility", ...}
  ],
  "coverage": {"criteria_applicable": 50, "criteria_evaluated": 34,
               "states_applicable": 28, "states_present": 11}
}

Output: scorecard JSON consumed by the report template.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from collections import defaultdict

DIMENSIONS = {
    "accessibility":        {"label": "Accessibility (WCAG 2.2 AA)", "weight": 30},
    "interaction_states":   {"label": "Interaction & States",        "weight": 20},
    "robustness":           {"label": "Robustness & Edge Cases",     "weight": 15},
    "content_copy":         {"label": "Content & Copy",              "weight": 15},
    "visual_system":        {"label": "Visual & Design System",      "weight": 12},
    "platform_fit":         {"label": "Platform Fit",                "weight": 8},
}

DEDUCTION = {"critical": 30, "serious": 15, "moderate": 6, "minor": 2, "info": 0}
DEFAULT_SEVERITY = "minor"

# Severity caps on the OVERALL band. Without these, the weighted mean hides a
# critical finding inside one dimension and the panel can print "Ship-ready"
# next to "Do not release". The worst finding sets the ceiling; the deductions
# then decide where under that ceiling the score lands.
OVERALL_CAP = {"critical": 54, "serious": 79, "moderate": 89}


def sev_of(finding):
    s = finding.get("severity", DEFAULT_SEVERITY)
    return s if s in DEDUCTION else DEFAULT_SEVERITY


def sev_rank(severity):
    """Lower is worse. Unknown severities sort with the default."""
    keys = list(DEDUCTION)
    return keys.index(severity) if severity in keys else keys.index(DEFAULT_SEVERITY)

BANDS = [
    (90, "A", "Ship-ready", "Minor polish only; nothing blocking."),
    (80, "B", "Ship with fixes", "No blockers, but a named list to clear first."),
    (70, "C", "Needs work", "Real defects that users will hit; fix before release."),
    (55, "D", "At risk", "Serious gaps across dimensions; re-review after fixes."),
    (0,  "E", "Not releasable", "Critical failures; treat as unfinished."),
]

# Findings that can only be settled at runtime, they cap confidence, not score.
RUNTIME_ONLY_HINT = "requires"


def band(score):
    for floor, grade, label, note in BANDS:
        if score >= floor:
            return {"grade": grade, "label": label, "note": note, "floor": floor}
    return {"grade": "E", "label": "Not releasable", "note": "", "floor": 0}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--findings", required=True, help="input JSON (see docstring)")
    ap.add_argument("--out", required=True)
    ap.add_argument("--config", help="intake brief (.audit/config.json); supplies scope when the "
                                     "findings file does not carry one")
    a = ap.parse_args(argv)

    with open(a.findings) as f:
        data = json.load(f)

    # The brief is the source of truth for scope. Reading it here means the
    # phase skill does not have to copy it into findings.json.
    if a.config and os.path.exists(a.config):
        try:
            with open(a.config) as f:
                cfg = json.load(f)
            if not data.get("scope") and cfg.get("scope"):
                data["scope"] = cfg["scope"]
        except (OSError, ValueError) as e:
            print(f"  note: config not read ({e})")

    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from wcag22 import resolve_scope
    scope = resolve_scope(data)
    if scope["unknown"]:
        print(f"ERROR: unknown dimension(s) in scope: {scope['unknown']}. "
              f"Valid: {', '.join(DIMENSIONS)}", file=sys.stderr)
        return 1
    in_scope = set(scope["dimensions"])

    all_findings = data.get("findings", [])

    # A finding with no dimension used to be coerced to accessibility. That is
    # harmless at full scope and dangerous under a narrow one, where the
    # coercion decides whether the finding is scored at all.
    bad = [str(fi.get("id")) for fi in all_findings
           if (fi.get("dimension") or "") not in DIMENSIONS]
    if bad:
        if scope["is_full"]:
            print(f"  WARNING: {len(bad)} finding(s) have no valid dimension, scored as "
                  f"accessibility: {', '.join(bad[:6])}")
        else:
            print(f"ERROR: scope is narrowed to {scope['label']}, so every finding needs an "
                  f"explicit dimension. Missing or unknown on: {', '.join(bad)}", file=sys.stderr)
            return 1

    for fi in all_findings:
        dim = fi.get("dimension") if fi.get("dimension") in DIMENSIONS else "accessibility"
        fi["in_scope"] = dim in in_scope
    findings = [fi for fi in all_findings if fi.get("in_scope")]
    out_of_scope = [fi for fi in all_findings if not fi.get("in_scope")]
    by_dim = defaultdict(list)
    for fi in findings:
        dim = fi.get("dimension") or "accessibility"
        if dim not in DIMENSIONS:
            dim = "accessibility"
        by_dim[dim].append(fi)

    dims = []
    for key, meta in DIMENSIONS.items():
        if key not in in_scope:
            continue
        items = by_dim.get(key, [])
        deducted = sum(DEDUCTION[sev_of(fi)] for fi in items)
        score = max(0, 100 - deducted)
        counts = defaultdict(int)
        for fi in items:
            counts[sev_of(fi)] += 1
        dims.append({
            "key": key,
            "label": meta["label"],
            "weight": meta["weight"],
            "score": score,
            "band": band(score),
            "finding_count": len(items),
            "counts": dict(counts),
            "deducted": deducted,
            "worst": min((sev_of(fi) for fi in items), key=sev_rank, default=None),
        })

    total_weight = sum(d["weight"] for d in dims)
    weighted = round(sum(d["score"] * d["weight"] for d in dims) / total_weight, 1)

    sev_counts = defaultdict(int)
    for fi in findings:
        sev_counts[sev_of(fi)] += 1

    worst = min((sev_of(fi) for fi in findings), key=sev_rank, default=None)
    cap = OVERALL_CAP.get(worst)
    overall = min(weighted, cap) if cap is not None else weighted
    cap_applied = None
    if cap is not None and overall < weighted:
        cap_applied = {
            "worst_severity": worst, "cap": cap, "uncapped": weighted,
            "reason": f"one or more {worst} findings cap the overall band",
        }

    # Coverage: derive it from the conformance rules unless the author supplied
    # explicit numbers. Deriving keeps score.py and build_report.py in agreement.
    cov = data.get("coverage") or {}
    if not cov:
        try:
            sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
            from wcag22 import derive_coverage
            cov = derive_coverage(data)
        except Exception as e:  # never let coverage derivation block scoring
            print(f"  note: coverage not derived ({e}); reporting as unknown")
            cov = {}
    crit_app = cov.get("criteria_applicable") or 0
    crit_eval = cov.get("criteria_evaluated") or 0
    st_app = cov.get("states_applicable") or 0
    st_present = cov.get("states_present") or 0
    coverage = {
        "criteria_applicable": crit_app,
        "criteria_evaluated": crit_eval,
        "criteria_coverage_pct": round(100 * crit_eval / crit_app, 1) if crit_app else None,
        "criteria_not_evaluated": max(0, crit_app - crit_eval),
        "states_applicable": st_app,
        "states_present": st_present,
        "state_coverage_pct": round(100 * st_present / st_app, 1) if st_app else None,
    }

    # Coverage cap: an audit that evaluated almost nothing cannot print an A.
    # Under 20% of applicable criteria evaluated caps the band at D; zero
    # evaluated and zero findings is "not assessable", not "ship-ready".
    cov_pct = coverage.get("criteria_coverage_pct")
    a11y_scoped = "accessibility" in in_scope
    # WCAG coverage says nothing about an audit that was never asked to grade
    # WCAG, so it neither caps the band nor declares the audit unassessable.
    not_assessable = a11y_scoped and coverage.get("criteria_evaluated", 0) == 0 and not findings
    if a11y_scoped and cov_pct is not None and cov_pct < 20 and overall > 69:
        cap_applied = {
            "worst_severity": worst, "cap": 69, "uncapped": overall,
            "reason": f"only {cov_pct}% of applicable criteria were evaluated",
        }
        overall = 69.0

    phase = data.get("phase", "design")
    runtime_pending = sum(1 for fi in findings if fi.get(RUNTIME_ONLY_HINT))
    if phase == "code":
        confidence = "Source-level only, nothing rendered or run"
        confidence_note = (
            "Findings come from the source code. Rendered contrast, real hit "
            "areas, focus behaviour and assistive-technology output are Not "
            "Evaluated until the implementation audit runs.")
    elif phase == "design":
        confidence = "Provisional, design stage only"
        confidence_note = (
            "Behavioural criteria (screen reader output, keyboard and focus "
            "behaviour, real reflow, rendered contrast over imagery, motion "
            "timing) are Not Evaluated. Run the implementation audit to confirm.")
    elif phase == "runtime":
        confidence = "Runtime-verified, design intent not checked"
        confidence_note = (
            "Measured against the running build. Design-source conformance and "
            "token drift were not evaluated.")
    else:
        confidence = "Combined, design and runtime"
        confidence_note = (
            "Both the design source and the running build were evaluated. "
            "Remaining gaps are listed under Limitations.")
    if a11y_scoped and coverage["criteria_coverage_pct"] is not None and coverage["criteria_coverage_pct"] < 60:
        confidence += f" (only {coverage['criteria_coverage_pct']}% of applicable criteria evaluated)"
    if not scope["is_full"]:
        confidence_note += (f" This audit was scoped to {scope['label']}; "
                            f"{', '.join(scope['excluded_labels'])} "
                            f"{'was' if len(scope['excluded_labels']) == 1 else 'were'} not assessed.")

    # Top risks: worst severity first, then heaviest dimension.
    top = sorted(
        findings,
        key=lambda fi: (sev_rank(sev_of(fi)),
                        -DIMENSIONS.get(fi.get("dimension", "accessibility"),
                                        {"weight": 0})["weight"]),
    )[:5]

    blockers = [fi for fi in findings if sev_of(fi) == "critical"]

    # A narrow scope keeps its real number: an accessibility audit that scores
    # 92 against WCAG did score 92 against WCAG, and deflating it would make
    # the figure mean nothing. What a narrow scope cannot do is speak for the
    # product, so the band label is qualified and the release line says plainly
    # that this is not a release decision.
    overall_band_out = dict(band(overall))
    if not scope["is_full"]:
        short = scope["label"].replace(" only", "").lower()
        overall_band_out["label"] = f"{overall_band_out['label']} on {short}"
        overall_band_out["note"] = (
            f"Graded on {short} alone. {', '.join(scope['excluded_labels'])} "
            f"{'was' if len(scope['excluded_labels']) == 1 else 'were'} outside the agreed scope, "
            f"so this grade is not a verdict on the product as a whole.")

    # One place decides the release line, so the wording can stay honest under
    # a narrow scope without the conditional turning into a puzzle.
    short = scope["label"].replace(" only", "").lower()
    if not_assessable:
        recommendation = "Insufficient coverage, not assessable"
    elif scope["is_full"]:
        recommendation = ("Do not release" if blockers else
                          "Release after clearing the listed fixes" if sev_counts.get("serious") else
                          "Releasable")
    elif blockers:
        recommendation = f"Do not release: blocking {short} findings"
    elif sev_counts.get("serious"):
        recommendation = f"Clear the listed {short} fixes first"
    else:
        recommendation = f"No {short} blockers found; not a product-wide release decision"

    out = {
        "screens": data.get("screens", []),
        "platform": data.get("platform"),
        "conformance_target": data.get("conformance_target", "WCAG 2.2 AA"),
        "phase": phase,
        "overall_score": overall,
        "overall_band": overall_band_out,
        "overall_uncapped": weighted,
        "cap_applied": cap_applied,
        "dimensions": dims,
        "severity_counts": dict(sev_counts),
        # finding_total and finding_ids cover EVERY finding in the file: they are
        # the proof that this scorecard was built from this findings file, which
        # build_report checks. What was scored is scored_total.
        "finding_total": len(all_findings),
        "finding_ids": sorted(str(fi.get("id")) for fi in all_findings),
        "scored_total": len(findings),
        "scope": {"label": scope["label"], "dimensions": scope["dimensions"],
                  "excluded": scope["excluded"], "excluded_labels": scope["excluded_labels"],
                  "is_full": scope["is_full"]},
        "out_of_scope_ids": sorted(str(fi.get("id")) for fi in out_of_scope),
        "out_of_scope_counts": {k: v for k, v in
                                ((sv, sum(1 for fi in out_of_scope if sev_of(fi) == sv))
                                 for sv in DEDUCTION) if v},
        "coverage": coverage,
        "confidence": confidence,
        "confidence_note": confidence_note,
        "runtime_pending": runtime_pending,
        "not_assessable": not_assessable,
        "release_recommendation": recommendation,
        "worst_severity": worst,
        "blocker_count": len(blockers),
        "top_risks": [
            {"id": fi.get("id"), "severity": fi.get("severity"),
             "dimension": fi.get("dimension"), "title": fi.get("title") or fi.get("detail")}
            for fi in top
        ],
        "scoring_model": {
            "deductions_per_finding": DEDUCTION,
            "dimension_weights": {k: v["weight"] for k, v in DIMENSIONS.items() if k in in_scope},
            "dimension_weights_full": {k: v["weight"] for k, v in DIMENSIONS.items()},
            "bands": [{"min": b[0], "grade": b[1], "label": b[2]} for b in BANDS],
            "overall_caps": OVERALL_CAP,
            "note": "Each dimension starts at 100 and loses points per finding by "
                    "severity, floored at 0. Overall is the weighted mean, then "
                    "capped by the worst single finding: any critical caps the "
                    "overall at 54 (band E), any serious at 79 (band C), any "
                    "moderate at 89 (band B). Coverage and confidence are "
                    "reported separately and never inflate the score. When the "
                    "audit is scoped to fewer dimensions, the weights above are "
                    "re-normalised over those dimensions and findings outside "
                    "them are listed but not scored.",
        },
    }
    with open(a.out, "w") as f:
        json.dump(out, f, indent=2)
    print(f"overall {overall} ({out['overall_band']['grade']}: "
          f"{out['overall_band']['label']}) -> {a.out}")
    if cap_applied:
        print(f"  capped from {weighted}, {cap_applied['reason']}")
    print(f"  recommendation: {out['release_recommendation']}")
    for d in dims:
        print(f"  {d['label']:<32} {d['score']:>3}  ({d['finding_count']} findings)")
    if not scope["is_full"]:
        print(f"  scope: {scope['label']} · {len(findings)} of {len(all_findings)} findings scored")
        if out_of_scope:
            print(f"  outside scope, reported but not scored: {', '.join(out['out_of_scope_ids'])}")
        # weights are re-normalised over the scoped dimensions, say so out loud
        print(f"  weights re-normalised over {', '.join(scope['dimensions'])}")
    print(f"  confidence: {confidence}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
