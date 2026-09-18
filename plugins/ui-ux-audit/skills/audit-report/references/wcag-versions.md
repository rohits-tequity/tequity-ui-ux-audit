# WCAG versions, what the plugin covers and how to read one table three ways

## The versions

| Version | Status | A/AA criteria | AAA | What changed |
|---|---|---|---|---|
| WCAG 2.0 | W3C Recommendation 2008; ISO/IEC 40500:2012 | 38 (incl. 4.1.1) | 23 | Baseline. Section 508, AODA and most older contracts cite it |
| WCAG 2.1 | Recommendation 2018 | 50 (incl. 4.1.1) | 28 | +12 A/AA: 1.3.4, 1.3.5, 1.4.10–1.4.13, 2.1.4, 2.5.1–2.5.4, 4.1.3. Mobile, low-vision and cognitive additions. Cited by EN 301 549, ADA Title II, GIGW 3.0 |
| WCAG 2.2 | Recommendation October 2023 | 55 | 31 | +6 A/AA: 2.4.11, 2.5.7, 2.5.8, 3.2.6, 3.3.7, 3.3.8. +3 AAA: 2.4.12, 2.4.13, 3.3.9. **Removed 4.1.1 Parsing** |
| WCAG 3.0 | W3C **Working Draft** |, |, | Different structure (outcomes, not criteria; scores, not levels). Not a standard; nothing conforms to it yet. The plugin notes it and does not grade against it |

Every 2.x version is backwards compatible: content meeting 2.2 at a level meets
2.1 and 2.0 at that level. The one exception, 4.1.1 Parsing, is obsolete -
W3C's errata state that content conforming to 2.2 satisfies 4.1.1 in 2.0/2.1.

## How the plugin covers all of them at once

`wcag22.py` carries all 86 criteria of 2.2 (55 A/AA, 31 AAA), each tagged with
the version that introduced it. One evaluation therefore produces:

- a conformance table with a **since 2.0 / 2.1 / 2.2** tag on every row,
- a **per-version summary**: how many criteria each version defines and their
  statuses, so a client on a 2.0-era contract reads their column and a client
  under EN 301 549 reads the 2.1 column,
- the 4.1.1 note row, marked Not Applicable with the W3C reasoning.

Set `conformance_target` in `findings.json` to scope the table and the coverage
numbers: `"WCAG 2.0 AA"`, `"WCAG 2.1 AA"`, `"WCAG 2.2 AA"` (default), `"WCAG 2.2
AAA"`, or a Level A variant. A finding that cites a criterion beyond the target
(for example 2.4.13 Focus Appearance under an AA target) still appears, flagged
**beyond target**, so a real defect is never hidden by the scope line, it is
excluded from the coverage percentage.

## AAA at design stage, what is actually checkable

AAA is opt-in because most products do not claim it, but several AAA criteria
are cheap to measure and worth reporting as "beyond the minimum":

| SC | Design-stage check |
|---|---|
| 1.4.6 Contrast (Enhanced) | 7:1 normal / 4.5:1 large: `contrast.py` already reports the AAA pass alongside AA |
| 1.4.8 Visual Presentation | Line length ≤ 80 characters, line height ≥ 1.5, paragraph spacing ≥ 1.5× line height, no justified text, user-selectable colours |
| 1.4.9 Images of Text (No Exception) | Any raster text at all |
| 2.4.10 Section Headings | Long content broken into headed sections |
| 2.4.12 Focus Not Obscured (Enhanced) | No part of the focused element hidden by fixed UI, the analyser's overlay check with a 0% tolerance |
| 2.4.13 Focus Appearance | Focus indicator ≥ 2px perimeter equivalent and ≥ 3:1 change of contrast, spec'd per component variant |
| 2.5.5 Target Size (Enhanced) | 44×44 CSS px minimum, the iOS HIG number, so an iOS-compliant design already meets it |
| 3.1.5 Reading Level | Copy at or below lower-secondary reading level, or a simpler alternative, run the `design:ux-copy` skill's readability pass |
| 3.3.6 Error Prevention (All) | Reversible / checked / confirmed on **every** submission, not just legal and financial |
| 3.3.9 Accessible Authentication (Enhanced) | No cognitive function test at all, not even with object recognition as an alternative |

Behavioural AAA criteria (2.1.3, 2.2.3–2.2.6, 2.3.2, 3.2.5, 1.2.6–1.2.9,
1.4.7, 3.1.3, 3.1.4, 3.1.6) are Not Evaluated until runtime or manual review,
the same as their AA counterparts.

## Beyond the success criteria, the rest of the WCAG family

The plugin's judgement layer also draws on W3C material that is not a success
criterion but is how WCAG is meant to be applied:

- **WCAG-EM 1.0**, the evaluation methodology the report structure follows.
- **Understanding WCAG 2.2** and **Techniques**, the intent and sufficient
  techniques behind each criterion; cite a technique id (e.g. G18, C22) in the
  fix when it applies, because engineers can look it up.
- **WAI-ARIA 1.2** and the **ARIA Authoring Practices Guide**, how custom
  widgets satisfy 4.1.2; referenced from the code-review anti-pattern library.
- **Making Content Usable for People with Cognitive and Learning Disabilities
  (COGA)**, the plain-language and cognitive-load checks.
- **WAI Mobile Accessibility** notes, how the criteria apply on touch devices;
  reflected in the platform-guidelines thresholds.
- **ATAG 2.0 / UAAG 2.0**, apply only if the product is an authoring tool or a
  user agent; mention in Limitations when they might.

## What "strictly follow all versions" means in a report

- The target line names the version and level graded against.
- The per-version summary shows the same evaluation read as 2.0, 2.1 and 2.2.
- Every criterion the target defines has a status; Not Evaluated is a status,
  used honestly, never omitted.
- 4.1.1 is addressed explicitly.
- AAA is either graded (target says AAA) or listed as out of scope with the
  count of AAA criteria not assessed.
- WCAG 3.0 is named as a draft and not graded.
- "Compliant" or "conformant" is never claimed; "audited against" is the
  wording, because a conformance claim needs a full WCAG-EM evaluation with
  assistive-technology testing by a qualified evaluator.
