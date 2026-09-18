# Skill composition and agent routing

This plugin owns audit judgement, measurement and reporting. It delegates
everything another skill already does better. Duplicating a skill's content here
would mean two copies to keep current, and the other copy is usually the one the
user has installed.

## Routing table

| Concern | Delegate to | Notes |
|---|---|---|
| General code correctness, security, error handling | `engineering:code-review` | Run it alongside this skill on a PR; this skill covers only the UI layer |
| PR hygiene, SOP compliance, description quality, criticality tags | `pr-review-guardian:pr-review` | Owns the PR-process half of a review |
| Reviewing AI-written or junior code for comprehension | `anthropic-skills:pr-review-understanding` | Explainer-first review plus a comprehension quiz for the author |
| Current web platform APIs, CSS, layout, Core Web Vitals | `modern-web-guidance:modern-web-guidance` | **Mandatory** before answering any HTML/CSS/DOM question, the platform moves faster than model weights |
| WCAG pass over a design or page | `design:accessibility-review` | Use its rubric and review flow rather than writing a parallel one. Note it is scoped to **WCAG 2.1 AA**, so the six 2.2 additions this plugin grades against: 2.4.11, 2.5.7, 2.5.8, 3.2.6, 3.3.7, 3.3.8, are outside it and stay this plugin's responsibility. Say which standard each finding came from |
| Usability, hierarchy and consistency feedback | `design:design-critique` | Good for the qualitative half of the visual dimension |
| Component API, variant and state documentation; naming drift | `design:design-system` | Owns design-system judgement |
| Developer handoff specs, interaction states, breakpoints | `design:design-handoff` | The design audit's findings often become handoff gaps |
| UI copy: labels, errors, empty states, CTAs | `design:ux-copy` | Do not improvise copy rules |
| Planning a usability test when tooling cannot answer the question | `design:user-research` | For comprehension and task-success questions |
| Synthesising support tickets or test notes into themes | `design:research-synthesis` | Turns qualitative input into audit evidence |
| Test strategy for the findings | `engineering:testing-strategy` | Converts findings into a regression suite |
| Chart, dashboard and score-bar rendering | `dataviz` | Load before drawing the rating panel |
| Artifact page structure, theming, layout | `artifact-design` | Load before writing the report page |
| Removing AI-writing tells from the report prose | `anthropic-skills:humanizer` | The final language pass |
| Device mechanics: simulator setup, interaction loops, screenshot diffing, profiling | Argent's own bundled skills | `argent-ios-simulator-setup`, `argent-android-emulator-setup`, `argent-device-interact`, `argent-test-ui-flow`, `argent-screenshot-diff`, `argent-qa-flows`, `argent-create-flow`, `argent-react-native-profiler`, `argent-native-profiler` |
| Reading the Figma design-to-code contract | Figma's `figma-design-to-code` skill | Required by `get_design_context` before calling it |

If a listed skill is not installed, do the work inline using this plugin's
references and say which skill would have covered it better. Do not silently
produce a thinner version of it.

## Public UI/UX skill libraries, how to borrow

Third-party UI/UX skill libraries (for example the widely-shared
`ui-ux-pro-max`) are useful for their category priority model and their
anti-pattern lists. Two conventions worth adopting, and both are already baked
into this plugin:

1. **Category priority.** Accessibility and touch/interaction are CRITICAL;
   performance, layout, navigation are HIGH; typography, colour, motion, forms
   are MEDIUM; charts and decorative polish are LOW. Spend the review budget in
   that order. This plugin's dimension weights encode the same ordering.
2. **Never present a general best practice as a verified match.** If a
   recommendation does not come from a measured value or a named clause, label
   it as general guidance. An unsourced recommendation stated with the same
   confidence as a measured failure is what makes an audit untrustworthy.

Borrow rules, not verdicts. Anything taken from an external library still has to
pass this plugin's evidence gate before it can appear as a finding.

## Agent routing

| Agent | Model | Used for |
|---|---|---|
| `evidence-collector` | cheap | Figma extraction, grep sweeps, running scripts, device state walks. Mechanical, parallelisable, output is files |
| `audit-verifier` | strong | The mandatory adversarial gate over every finding before it reaches the report |
| `consistency-checker` | cheap | Deterministic checks of the assembled report against the findings data |

Classification, severity, systemic detection and the executive overview stay
with the orchestrating session on a mid or strong model. See
`audit-orchestrator/SKILL.md` for the fan-out plan and the full routing rules.

The division is always the same: cheap models for work whose output can be
checked by looking at it, strong models for work that is judgement, and a
separate agent, never the author, for verification.
