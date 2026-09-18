# What only runtime can settle

These are the criteria the design audit had to mark **Not Evaluated**. Closing
them is the whole point of this phase. Anything still unresolved after this phase
stays Not Evaluated in the report, it does not quietly become Supports.

| Criterion | Runtime check | Evidence |
|---|---|---|
| 1.1.1 Non-text Content | Every image/icon node in `describe` has an accessible name, or is correctly hidden | tree excerpt |
| 1.3.1 Info and Relationships | Roles present and correct: headings are headings, lists are lists, fields are paired with labels | tree excerpt |
| 1.3.2 Meaningful Sequence | Actual tree order vs visual order | tree + screenshot |
| 1.4.3 / 1.4.11 Contrast | `pixel_probe.py` on the rendered screenshot, settles text over images, gradients, video and translucency | ratio + crop |
| 1.4.4 Resize Text | Largest OS font scale, re-capture, look for clipping and unreachable controls | before/after |
| 1.4.10 Reflow | Smallest supported width, split view, foldable; no two-axis scrolling | screenshot |
| 1.4.12 Text Spacing | Apply the spacing overrides and check nothing clips | before/after |
| 1.4.13 Content on Hover/Focus | Tooltip/popover is dismissible, hoverable and persistent | sequence |
| 2.1.1 / 2.1.2 Keyboard | Tab through every control; nothing unreachable, nothing trapped | focus order list |
| 2.4.3 Focus Order | Recorded focus order vs visual order | list + screenshots |
| 2.4.7 Focus Visible | An indicator is visible at every focus stop. 2.4.7 sets no ratio, measure the indicator's contrast under **SC 1.4.11** (≥3:1), and note **SC 2.4.13 Focus Appearance** (AAA, WCAG 2.2) if the client wants the size and change-of-contrast thresholds too | crops + ratios |
| 2.4.11 Focus Not Obscured | Focus moved behind a sticky bar or keyboard | screenshot |
| 2.5.1 / 2.5.7 Gestures, Dragging | A single-pointer, non-dragging alternative actually exists | sequence |
| 2.5.3 Label in Name | Visible label is contained in the accessible name | tree vs screenshot |
| 2.5.8 Target Size | Point-space frames from `native-describe-screen`, including hit-slop as implemented | frames |
| 2.2.1 / 2.2.2 Timing | Timeouts, auto-dismiss, carousels, can the user extend, pause, stop | timing log |
| 2.3.3 Animation | Reduced-motion setting honoured; durations measured | profiler trace |
| 3.2.x Consistency | Same action, same name and position, across the real navigation | tree excerpts |
| 3.3.1 / 3.3.3 Errors | Trigger each validation failure; is the error in text, near the field, with a fix | screenshots |
| 3.3.7 Redundant Entry | Walk the multi-step flow; is anything re-asked | sequence |
| 3.3.8 Accessible Authentication | Paste into OTP and password fields; password manager fill | sequence |
| 4.1.2 Name, Role, Value | Every custom control's role, name and state, including after state changes | tree before/after |
| 4.1.3 Status Messages | Toasts and inline validation exposed as live regions | tree at the moment of change |

## Still not settled, even at runtime, be explicit

- **VoiceOver / TalkBack announcement text and order.** Argent reads the
  accessibility tree, not the speech output. Report the tree facts and require a
  manual screen-reader pass. This is the single largest honest gap in the whole
  pipeline; state it in Limitations every time.
- **Switch Control, Voice Control, external keyboard on iOS**, manual.
- **Braille display output**, manual.
- **Cognitive load, comprehension, real task success**, needs users, not tools.
  Recommend a 5-participant usability test if the stakes justify it; the
  `design:user-research` skill plans it.
- **Colour-vision simulation**, approximate from screenshots at best; never
  claim a pass from a filter.

## Reconciling with the design audit

For each design-stage finding: confirmed (keep the id, attach runtime
evidence, upgrade confidence to `observed`), resolved in code (close it as a
false positive and say so, this builds trust in the rest of the report), or
still indeterminate (keep it Not Evaluated with the reason).

Runtime findings with no design-stage counterpart are the interesting ones: they
are the gap between what was specified and what was built. Call that out
explicitly in the overview, because it is a process finding, not just a defect.
