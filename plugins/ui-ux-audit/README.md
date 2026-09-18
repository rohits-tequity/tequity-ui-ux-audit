# ui-ux-audit

Evidence-backed UI/UX and accessibility auditing for Figma designs, UI code and
running apps, with one industry-format report, a reproducible score, and a
verification gate so nothing reaches the report on the author's say-so.

**Grades against WCAG 2.2 AA by default** and reads the same evaluation as
WCAG 2.0, 2.1 and 2.2 side by side (every criterion is tagged with the version
that introduced it; 4.1.1 Parsing is handled explicitly). All 86 criteria of 2.2
are carried, set the target to `WCAG 2.2 AAA` to grade the 31 AAA criteria too.
WCAG 3.0 is a Working Draft and is noted, not graded. Plus Apple HIG, Material 3
and Nielsen's heuristics. **Reports in ACR/VPAT vocabulary** following WCAG-EM.
See `skills/audit-orchestrator/references/standards-map.md` and
`skills/audit-report/references/wcag-versions.md`.

## Quickstart: audit one Figma screen

Say, in the chat:

> Audit this Figma screen for accessibility and UX before we build it:
> https://www.figma.com/design/AbC123/Checkout?node-id=12-345
> Platform: React Native. User: returning customer paying a saved biller,
> primary path Select biller → Amount → Review → Confirm. Themes: light and dark.

Paste less and the intake skill asks for the rest as multiple choice (with a
free-text option), records your answers in `.audit/config.json`, and never asks
the same thing twice. The output choice (artifact, HTML, PDF, PDF theme) is
recorded there too and is then binding for every report.

It will:

1. Detect what you gave (Figma link, PR, repo path, running app) and which phases apply.
2. Check your Figma seat (`whoami`) and tell you the call budget before spending it.
3. Make the cached reads (metadata, variables, design context per screen, one section render and one render per screen that carries a finding), run `analyze_design.py`, and pull every screenshot straight from the MCP response with `save_screenshot.py`, `crop_frames.py` and `evidence_frames.py`. No manual exports.
4. Classify the measurements against WCAG 2.2, the platform rules and the
   checkout archetype; route copy and design-system questions to the matching
   installed skills.
5. Send every candidate through the `audit-verifier` agent; rejected ones go to
   the cleared-items appendix, not the body.
6. Score, build, lint, and publish the report as an artifact; tell you the
   grade, blockers and the most expensive fix in one line.

For the built app: *"Audit the running app on the simulator"* (needs Argent on
the Mac, see Setup). For source: *"Review this PR for a11y and performance."*
For several screens or phases at once: *"Run a full audit of …"*, the
orchestrator plans the fan-out and the cheap/strong model split.

## What you get

One report in seven sections, each opening with a box that says what the
section contains. A Figma audit and an app audit use the same skeleton but
different content: the design report talks about screens, tokens and missing
frames; the runtime report talks about devices, states exercised and
behaviour. Delivered as an artifact link, an HTML file, and a PDF in the brand
print theme (dark theme on request).

1. **Overview**: scope line, verdict panel (grade, release recommendation, severity chips, dimension bars, coverage), main points, decisions needed.
2. **Screens reviewed**: every screen, what was extracted, findings per screen; a marked-screenshot gallery when images are supplied.
3. **Accessibility**: the WCAG criteria judged in this phase and their status, the deferred ones in one line, then the findings.
4. **Design quality** (or Usability and platform fit for an app): interaction, copy, platform and design-system findings.
5. **Missing screens and states** (or Behaviour under real conditions): the state grid relevant to the phase, then findings.
6. **Fix plan**: who owns what, retest plan, limitations.
7. **About this audit**: standards and versions, scope and reviewer, per-version WCAG summary, the full conformance table, scoring model, glossary, references, cleared candidates.

The score is capped by the worst finding (a critical caps the report at E), so
the grade and the release recommendation can never disagree.

## Inputs, what to give, and what happens if you don't

| Input | Why it matters | If missing |
|---|---|---|
| Output: artifact / HTML / PDF, PDF theme (brand or dark) | Binding for every report once recorded | Artifact + HTML; asked once about PDF |
| Audience (manager, designer, developer, client) | Shapes "How to read this report" and the standards block | All four rows shown |
| Figma URL **with node-id** | The three MCP reads need a node | Asked for; the audit cannot start |
| Platform (ios / android / rn / web) | Target-size and type thresholds | Asked for |
| User story: persona + constraints, goal, primary path, success, UI type | Loads the archetype checks; decides what is `critical` | Asked for; the audit runs generic checks only and says so |
| Themes and device classes | Contrast recomputes per theme; layout per device | Defaults to light + dark and the smallest supported phone; other cells listed as Not Evaluated |
| Design system name | Token-conformance checks | Skipped, noted |
| Scope: which dimensions are graded | Re-normalises the weights, drops the sections nobody commissioned, prints anything found outside the scope unscored | All six dimensions |
| Conformance target (`WCAG 2.0/2.1/2.2`, `A/AA/AAA`) | Scopes the table and coverage; per-version summary always shown | `WCAG 2.2 AA` |
| Legal regime (EU / US / India …) | Report header maps the target to the regime | Reported against the target only |
| Previous `scorecard.json` | Delta on the panel, carried-forward ids | First-audit report |
| `.audit/lessons.md` | Verifier-established rules that filter known false positives | Nothing filtered |

## Using your own brand

The report ships with the Tequity palette. Only the raw palette is themed, so
pointing it at your own is one file and one flag:

```bash
cp skills/audit-report/assets/theme.neutral.css theme.mybrand.css
# edit the 21 colour slots, then check them against the report's own claims
python3 skills/audit-report/scripts/theme_check.py --theme theme.mybrand.css
python3 skills/audit-report/scripts/build_report.py ... --theme theme.mybrand.css
```

Set `output.theme` in `.audit/config.json` to make it the default for a project.
The slot names (teal, coral, orange) are roles rather than colour claims: teal
is the calm or pass end, coral is the alarm end, orange is the accent between
them. Every semantic token, both light and dark modes and the print translation
are derived from those slots, and `theme_check.py` refuses a palette that breaks
the contrast figures the report prints about itself.

## What gets graded

Six dimensions, weighted: accessibility 30, interaction and states 20,
robustness and edge cases 15, content and copy 15, visual and design system 12,
platform fit 8. WCAG sets the bar for the accessibility dimension only; the
other five come from the Nielsen heuristics, Apple HIG and Material 3, the state
coverage matrix and token conformance. A client who wants a pure conformance
deliverable picks the narrow scope at intake and the score covers that dimension
alone.

## Skills

| Skill | Phase | Use it for |
|---|---|---|
| `audit-intake` | first | Detects inputs, asks only the missing questions as MCQs, records the brief and the binding output choice in `.audit/config.json` |
| `audit-orchestrator` | any | Multi-screen / multi-phase: plan, matrix, model routing, verification gate, baselines, lessons |
| `figma-design-audit` | before code | Figma node → measured findings against WCAG 2.2 AA, HIG/Material, heuristics, archetype |
| `ui-code-review` | code | RN / React / web source: a11y props, hit slop, font scaling, motion, states, performance, tokens |
| `implementation-audit` | after build | Runtime via Argent: real a11y trees, rendered contrast, reflow, focus, visual regression, profiling |
| `audit-report` | deliverable | `score.py` → `build_report.py` (lint included) → artifact |

## Agents

| Agent | Model | Role |
|---|---|---|
| `evidence-collector` | haiku | Extraction, grep sweeps, script runs, device walks. Parallel per screen. No judgement |
| `audit-verifier` | opus | Mandatory gate: argues against every finding → CONFIRMED / WEAKENED / UNVERIFIED / REJECTED |
| `consistency-checker` | haiku | Last mechanical pass over the built report |

Cheap models get work whose output can be checked by looking at it. Severity,
verification and the overview never go to a cheap model.

## Scripts

| Script | Does |
|---|---|
| `audit-intake/scripts/detect_inputs.py` | Classifies pasted links, paths and hints into phases; lists only the questions still unanswered |
| `figma-design-audit/scripts/figma_url.py` | URL → fileKey / nodeId; branch URLs (`/design/<key>/branch/<branchKey>/…`); flags links with no node |
| `figma-design-audit/scripts/contrast.py` | WCAG contrast with alpha, thresholds that apply |
| `figma-design-audit/scripts/analyze_design.py` | Geometry, colour, type, token, slack, order, alt-text measurement over cached Figma payloads |
| `figma-design-audit/scripts/save_screenshot.py` | Writes `get_screenshot` inline renders (enableBase64Response) from the session transcript to PNG files; `--list`, `--node`, `--all` |
| `figma-design-audit/scripts/crop_frames.py` | Cuts every top-level frame out of one section render using metadata coordinates; writes `screens.json` and `frames.json` |
| `figma-design-audit/scripts/evidence_frames.py` | Resolves each finding's node id to a pixel frame on its screen, sets `evidence.image/frame`, fills `screens_detail` and `flow_map` |
| `implementation-audit/scripts/pixel_probe.py` | Rendered contrast from a screenshot (settles text-over-image). Needs Pillow |
| `audit-report/scripts/score.py` | Findings → scorecard with caps and derived coverage |
| `audit-report/scripts/build_report.py` | Data → HTML report + artifact body + A4 PDF (`--pdf`) + executive cut (`--executive-pdf`); embeds and marks evidence; runs the lint and the print-parity check |
| `audit-report/scripts/slop_check.py` | Language and evidence lint, em dash ban included (also standalone) |
| `audit-report/scripts/annotate.py` | Draws the finding's outline, id and measured value on a screenshot and crops around it; the builder calls it for any evidence with a `frame` |
| `audit-report/scripts/theme_check.py` | Validates a brand palette against the contrast rules the report claims, 15 pairs, exits non-zero on a failure |
| `audit-report/scripts/wcag22.py` | All 86 WCAG 2.2 criteria with since-version tags, ACR statuses, state rows, target parsing, shared derivation |

All pure Python 3.9+. `pip install pillow --break-system-packages` is needed
only for `pixel_probe.py` and for image downscaling in the builder.

## Setup

**Figma**: Figma MCP connected. Reads are rate-limited by seat: a Starter plan
or a View/Collab seat gets roughly **20 calls per month**; Dev and Full seats
200–600 per day. Three reads per screen per theme. The skill states the cap
before spending.

**Argent** (runtime phase only):

```bash
npx @swmansion/argent init      # then restart the editor/app
```

Node ≥ 20.12. iOS needs macOS + Xcode; Android needs `adb` + an emulator image.
React trees and profiling need a dev build with Metro. It runs where the device
is, not in a cloud container or over a file bridge. Telemetry is on by default
(`argent telemetry disable`). This plugin's `.mcp.json` declares the `argent`
stdio server; Argent's own skills handle device mechanics.

## Honest limits

- **The PDF is the artifact, printed.** Same structure, same proportions, one
  rem type scale scaled once; only the palette and the effects paper cannot
  carry are translated. The builder warns if a print rule re-grids a component
  or sets a px font size. `--pdf-theme dark` if you want the dark palette on
  paper too.
- **Scope is not a pass.** An audit graded on fewer dimensions says so on the
  verdict panel and in the appendix, the grade label reads "on accessibility"
  rather than bare, and the release line says it is not a product-wide
  decision. Anything found outside the scope is still printed, unscored. What
  the audit never looked at is never described as passing.
- **Not a certification.** A conformance claim needs a full WCAG-EM evaluation
  with assistive-technology testing by a qualified evaluator. The report says
  "audited against WCAG 2.2 AA", never "compliant".
- **No screen-reader speech.** Argent reads the accessibility tree; VoiceOver
  and TalkBack announcements need a manual pass. Every report says so.
- **Design stage cannot pass behavioural criteria.** Keyboard, focus, reflow,
  motion and contrast over imagery are Not Evaluated until runtime.
- **Screenshot resolution follows the seat.** The MCP's inline render is capped
  at 2000px on the long edge, so a section render gives thumbnails and each
  screen shown in full costs one more read. On a Starter / View seat that means
  choosing which screens get full-size evidence; the report says which.
- **Runtime phase exercised against Argent's tool contract, not yet against a
  live device in this repo.** The `implementation-audit` skill follows Argent's
  published tool schemas and QA practices; the first run on a real simulator
  should be treated as a shakedown and its lessons written to `.audit/lessons.md`.
- **No autonomous learning.** The plugin does not improve itself. It reads
  `.audit/lessons.md` (rules the verifier established) and `.audit/` baselines,
  and gets better per project because those files do.

## Re-auditing

Keep in the repo: `.audit/previous-scorecard.json`, `.audit/lessons.md`,
finding ids and their state, visual-regression baselines, Argent flow names.
Pass `--baseline` to the builder and the panel leads with the delta.
