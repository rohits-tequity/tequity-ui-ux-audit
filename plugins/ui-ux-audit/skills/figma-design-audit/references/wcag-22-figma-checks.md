# WCAG 2.2 AA, what is checkable in a Figma file

The A/AA set below is the complete WCAG 2.2 list, which is a superset of 2.0 and
2.1 at the same level. The report tags each row with the version that introduced
it and shows a per-version summary. For the 31 AAA criteria and which of them are
checkable at design stage, read `audit-report/references/wcag-versions.md`.

Status vocabulary follows the ACR / VPAT convention so findings map cleanly onto
a conformance table: **Supports**, **Partially Supports**, **Does Not Support**,
**Not Applicable**, **Not Evaluated**. At design stage most behavioural criteria
are legitimately **Not Evaluated**, record them as such rather than guessing.

`D` = determinable from the design file. `R` = runtime only. `D/R` = the design
can be shown to fail, but only runtime can show it passes.

The same tags drive the verdict. The machine copy is `DESIGN_CHECKABILITY` in
`audit-report/scripts/wcag22.py`; keep the two in step. At design stage the
verdict says GO only when every `D` criterion has a status (Supports, Not
Applicable, or a failing finding) on the declared sample. `D/R` and `R` rows are
listed as build checks and never block a design GO.

## Perceivable

| SC | Level | Where | Design-stage check |
|---|---|---|---|
| 1.1.1 Non-text Content | A | D/R | Every image, icon, chart and avatar node must carry an alt-text spec (layer description, annotation, or a documented `accessibilityLabel` prop). Icon-only buttons with no label spec → Does Not Support. |
| 1.2.x Time-based Media | A/AA | D/R | Video/audio placeholders must spec captions, transcript and audio-description slots. |
| 1.3.1 Info and Relationships | A | D | Heading levels declared (H1→H6 with no skipped level), lists as lists, form fields paired with persistent labels, groups named. Font size alone is not a heading. |
| 1.3.2 Meaningful Sequence | A | D/R | Compare DOM/layer order against visual order sorted by (y, x). A mismatch is a reading-order risk, flag for runtime confirmation. |
| 1.3.3 Sensory Characteristics | A | D | Copy must not rely on "the button on the right" / "the green one". |
| 1.3.4 Orientation | AA | D/R | Landscape frame must exist unless orientation lock is essential and justified. |
| 1.3.5 Identify Input Purpose | AA | D | Each input specs an autocomplete/`textContentType` token. |
| 1.4.1 Use of Color | A | D | Any state, status, error, required-field marker, link or chart series distinguished by colour alone → Does Not Support. Needs a second channel: icon, text, weight, underline, pattern. |
| 1.4.2 Audio Control | A | R | Auto-playing audio behaviour; Not Applicable when the product has no audio. |
| 1.4.3 Contrast (Minimum) | AA | D | Computed: ≥4.5:1 body text, ≥3:1 for ≥18.66px bold or ≥24px regular. Text over an image or gradient is **indeterminate**: list 1.4.3 under `evaluated.indeterminate` with a remark naming the screens, so it moves to the build checks (runtime pixel probe) instead of blocking the verdict. Only 1.4.3, 1.4.6 and 1.4.11 may be indeterminate. |
| 1.4.4 Resize Text | AA | D/R | The analyser flags text nodes whose parent frame leaves under ~15% vertical slack, no room to grow at a larger font scale. Geometry inference, confirmed at runtime. |
| 1.4.5 Images of Text | AA | D | Flattened/raster text, text baked into an illustration or a screenshot used as content. |
| 1.4.10 Reflow | AA | D/R | Check a 320px-equivalent frame exists; flag absolute positioning, fixed pixel widths and horizontally-scrolling content regions. |
| 1.4.11 Non-text Contrast | AA | D | ≥3:1 for interactive component boundaries against the adjacent background, icon glyphs, focus indicators, chart strokes, input borders, toggle tracks. Commonly missed on disabled-looking-but-enabled controls and 1px hairline borders. |
| 1.4.12 Text Spacing | AA | D | Line height ≥1.5× font size for body, paragraph spacing ≥2× font size, letter spacing ≥0.12em and word spacing ≥0.16em must not clip. Tight 1.0–1.2 line heights on body copy are the usual failure. |
| 1.4.13 Content on Hover or Focus | AA | D/R | Tooltips, popovers and menus must spec dismissible / hoverable / persistent behaviour. |

## Operable

| SC | Level | Where | Design-stage check |
|---|---|---|---|
| 2.1.1 Keyboard / 2.1.2 No Trap | A | R | Not Evaluated at design stage, but a modal or drawer with no documented close affordance and no focus-trap spec is a design defect worth raising. |
| 2.1.4 Character Key Shortcuts | A | R | Single-key shortcuts; usually Not Applicable on touch products. |
| 2.4.1 Bypass Blocks | A | R | Skip links and landmarks; web behaviour, runtime only. |
| 2.4.2 Page Titled | A | D/R | Every screen shows a title that says what it is; the announced title is runtime. |
| 2.4.3 Focus Order | A | D/R | Design must declare a tab/focus order for each screen. Absent → Not Evaluated with a design gap noted. |
| 2.4.4 Link Purpose | A | D | "Click here", "Learn more", "View" with no context. |
| 2.4.5 Multiple Ways | AA | D/R | More than one way to reach a screen (nav plus search, or index); Not Applicable to a linear flow. |
| 2.4.6 Headings and Labels | AA | D | Headings and labels describe their content; no duplicates that mean different things. |
| 2.4.7 Focus Visible | AA | D | Every interactive component must have a `focus-visible` variant in the component set. A component set with default/hover/pressed/disabled but no focus state → Does Not Support. |
| 2.4.11 Focus Not Obscured (Min) | AA (2.2) | D/R | Sticky headers, bottom bars, FABs and toasts overlapping focusable content. Geometry check: does any fixed overlay intersect an interactive node's bounds? |
| 2.5.2 Pointer Cancellation | A | R | Actions fire on release, not on press; behaviour, runtime only. |
| 2.5.1 Pointer Gestures | A | D | Any multipoint or path-based gesture (pinch, swipe-to-delete, slider drag) needs a single-pointer alternative. |
| 2.5.3 Label in Name | A | D | The visible label text must be contained in the spec'd accessible name. |
| 2.5.4 Motion Actuation | A | D | Shake, tilt, device-motion triggers need a UI alternative. |
| 2.5.7 Dragging Movements | AA (2.2) | D | Reorder lists, sliders, swipe-to-dismiss, drag-to-upload need a non-dragging path. |
| 2.5.8 Target Size (Minimum) | AA (2.2) | D | ≥24×24 CSS px, or smaller with ≥24px spacing between target centres. Judge 2.5.8 at 24px. Platform minima (44pt, 48dp) are stricter and belong in a separate `platform_fit` finding that cites 2.5.8 as context, never as a WCAG failure (see platform-guidelines.md). |
| 2.2.1 Timing / 2.2.2 Pause Stop Hide | A | D | Auto-advancing carousels, countdowns, auto-dismissing toasts carrying essential info, session timeouts: need extend/pause/stop. |
| 2.3.1 Three Flashes | A | D | Flashing or strobing animation specs. |
| 2.3.3 Animation from Interactions | AAA | D | Parallax, large-motion transitions: spec a reduced-motion variant. Worth raising at AA even though it is AAA. |

## Understandable

| SC | Level | Where | Design-stage check |
|---|---|---|---|
| 3.1.1 / 3.1.2 Language | A/AA | D/R | Language of page and of any foreign-language passage declared. |
| 3.2.1 / 3.2.2 On Focus, On Input | A | D/R | No change of context on focus or on input: a flow that auto-submits or auto-advances when a field is filled is a design-visible failure; a pass needs runtime. |
| 3.2.3 Consistent Navigation | AA | D | Nav order and placement identical across screens in the set. |
| 3.2.4 Consistent Identification | AA | D | The same action carries the same label and icon everywhere. Two labels for one action is the common drift. |
| 3.2.6 Consistent Help | A (2.2) | D | Help/support entry point in the same relative position on every screen that has one. |
| 3.3.1 Error Identification | A | D | Errors identified in **text**, not just a red border or red text. |
| 3.3.2 Labels or Instructions | A | D | Persistent visible labels. Placeholder-as-label → Does Not Support. Required fields, formats and constraints stated up front, not only after failure. |
| 3.3.3 Error Suggestion | AA | D | Error copy says how to fix it, not only that it is wrong. |
| 3.3.4 Error Prevention | AA | D | Legal, financial and data-deleting actions need reversible / checked / confirmed. |
| 3.3.7 Redundant Entry | A (2.2) | D | Multi-step flows must not re-ask for information already given. |
| 3.3.8 Accessible Authentication (Min) | AA (2.2) | D | No cognitive function test without an alternative: allow paste into OTP and password fields, support password managers, no transcription-only puzzles. |

## Robust

| SC | Level | Where | Design-stage check |
|---|---|---|---|
| 4.1.2 Name, Role, Value | A | D/R | Every custom control needs a spec'd role, accessible name and state. Icon-only controls, custom toggles, segmented controls and star ratings are the recurring gaps. |
| 4.1.3 Status Messages | AA | D/R | Toasts, inline validation, loading and "3 results found" need a live-region spec. |

## Beyond WCAG, record separately, do not label as WCAG failures

- **EN 301 549** adds non-web-document and hardware clauses; note applicability if the client is EU public sector.
- **Cognitive accessibility** (COGA): plain-language target ≈ grade 8, one primary action per screen, no unexplained jargon, progress indication in multi-step flows.
- **Reduced motion, reduced transparency, increased contrast, bold text** OS settings each need a spec'd variant.
