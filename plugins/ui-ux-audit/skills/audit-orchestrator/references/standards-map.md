# Standards map, what this plugin grades against, and how it relates to law

Grading target: **WCAG 2.2 Level AA**, the W3C Recommendation (October 2023).
Regulations lag the standard; grading against 2.2 AA meets or exceeds every
current legal baseline below. When a client is subject to a specific regime,
state it in the report header and note any criterion the regime does not yet
require, so the finding is presented as "beyond the legal minimum" rather than
as a compliance failure.

| Regime | Scope | References | Notes for the report |
|---|---|---|---|
| ISO/IEC 40500 | International standard | WCAG 2.0 (identical text) | Procurement documents often cite this; 2.2 AA is a superset |
| EN 301 549 (EU) | ICT procurement; basis of the European Accessibility Act, in force for most products and services from 28 June 2025 | WCAG 2.1 AA for web and mobile apps, plus non-web and hardware clauses | Mobile apps are explicitly in scope. Note 2.2-only criteria as "beyond EN 301 549 v3.2.1" |
| ADA Title II rule (US, 2024) | State and local government web and mobile | WCAG 2.1 AA | Compliance dates 2026–2027 by entity size |
| Section 508 (US federal) | Federal ICT procurement | WCAG 2.0 AA (Revised 508) | ACR/VPAT vocabulary comes from here |
| AODA (Ontario) | Public and large private orgs | WCAG 2.0 AA | |
| UK Public Sector Bodies (Websites and Mobile Applications) Accessibility Regulations 2018 | Public sector | Legal text references EN 301 549 → WCAG 2.1 AA; the GDS monitoring body has tested against WCAG 2.2 AA since 2024 | Report both: the legal floor and the standard the monitor applies |
| RPwD Act 2016 + GIGW 3.0 (India) | Government and public-facing digital services | WCAG 2.1 AA (GIGW 3.0) | Relevant for Indian banking and fintech clients; RBI and IBA guidance on accessible banking also refers to WCAG |
| JIS X 8341-3 (Japan) | Public and private | WCAG 2.0/2.1 aligned | |
| DDA / Australian government | Public sector | WCAG 2.1 AA | |

## Beyond WCAG, what "industry grade" adds

WCAG is a floor for accessibility; it is silent on usability. This plugin adds:

| Area | Source | Where it lives in the plugin |
|---|---|---|
| Platform conformance | Apple Human Interface Guidelines; Material 3 | `figma-design-audit/references/platform-guidelines.md` |
| Usability heuristics and severity | Nielsen's 10 heuristics and 0–4 severity scale; ISO 9241-110 dialogue principles | `ux-heuristics-and-edge-cases.md`, `finding-spec.md` |
| Evaluation method | WCAG-EM 1.0 (scope → explore → sample → evaluate → report) | `audit-report/SKILL.md` |
| Reporting vocabulary | ACR / VPAT 2.5 (Supports / Partially Supports / Does Not Support / Not Applicable / Not Evaluated) | `wcag22.py`, conformance table |
| Component behaviour | WAI-ARIA Authoring Practices Guide patterns | `ui-code-review/references/anti-patterns-rn-react.md` |
| Cognitive accessibility | W3C COGA "Making Content Usable" | plain-language and cognitive-load checks in the heuristics file |
| Mobile-specific guidance | W3C Mobile Accessibility Task Force notes; platform accessibility docs (iOS Accessibility, Android Accessibility) | platform guidelines and RN specifics |
| Human-centred design process | ISO 9241-210 | the user-story input and the archetype file |

## What "best in class" means here, honestly

- Grading against the current W3C Recommendation, not a superseded version.
- Reporting in the vocabulary procurement and legal teams already use.
- Measuring rather than eyeballing, and publishing the measurement.
- Separating measured from inferred from not-evaluated, every time.
- Verifying findings with an agent that argues against them.
- Making the score reproducible and the re-audit comparable.

What it is **not**: a certification. A conformance claim requires a full
WCAG-EM evaluation across a representative sample by a qualified evaluator,
including assistive-technology testing that this plugin cannot automate. The
report should say "audited against WCAG 2.2 AA" and never "WCAG 2.2 AA
compliant" unless a human evaluator has completed the manual passes listed
under Limitations.
