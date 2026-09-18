# Finding specification

## Required fields

| Field | Type | Rule |
|---|---|---|
| `id` | string | Prefix by kind: `A11Y-` accessibility, `UX-` usability, `DS-` design system, `EDGE-` state and edge case, `PERF-` performance, `CODE-` source-level finding from the code review. Stable across re-audits so fixes can be tracked. The analyser stamps candidates `M-nnn` before classification; those ids are internal and must be replaced with a kind prefix before they reach the report. |
| `title` | string | One line, states the defect. "Primary CTA label fails contrast at 3.1:1", not "Contrast issue". |
| `severity` | enum | `critical` / `serious` / `moderate` / `minor` / `info`. Rubric below. |
| `dimension` | enum | `accessibility` / `interaction_states` / `robustness` / `content_copy` / `visual_system` / `platform_fit`. **This is what places the finding in the report**: `accessibility` → Part 2, `robustness` → Part 4, everything else → Part 3. The id prefix is a label; the dimension is the address. Keep them consistent (`EDGE-` ↔ `robustness`, `A11Y-` ↔ `accessibility`, `DS-` ↔ `visual_system`); the lint warns when they disagree. Under a narrowed audit scope the dimension also decides whether the finding is scored, so `score.py` refuses to run when one is missing or unknown rather than coercing it to `accessibility` as it does at full scope. |
| `criterion` | string | The exact rule: "WCAG 2.2 SC 1.4.3 (AA)", "iOS HIG target size 44pt", "Nielsen #1 Visibility of system status". |
| `status` | enum | ACR vocabulary: `Supports` / `Partially Supports` / `Does Not Support` / `Not Applicable` / `Not Evaluated`. |
| `evidence` | object | `{image, region, measured, required, alt, caption}`, at least one of an image or a measured number. `image` is a path **relative to the directory that contains `findings.json`** (or absolute, or a `data:` URI); the builder embeds it and downscales anything over 1200px wide. A missing file is a build WARNING and a visible note in the report, check the build output. Add `frame: {x, y, w, h}` (with `normalized: true` for Argent `describe` frames in [0,1], or `normalized: false` for pixel frames from Figma metadata) and the builder draws a coral outline with the finding id and measured value on the screenshot and crops around it, in HTML and PDF alike. `dim: true` fades everything outside the region. For a Figma audit `evidence_frames.py` fills `image`, `frame` and `normalized: false` from `location.node_id`, so put the node the marker should outline first in that field. |
| `location` | object | `{screen, node, node_id, file, line, component}`, whatever applies. |
| `user_impact` | string | Who is affected and what happens to them. Not the rule restated. |
| `fix` | string | Concrete and in the project's own vocabulary: the token to swap, the prop to add, the value to change. |
| `effort` | enum | `S` (<1h) / `M` (<1d) / `L` (>1d or needs a design decision). |
| `retest` | string | The exact step that proves it is fixed. |
| `confidence` | enum | `measured` (computed from an extracted value) / `inferred` (pattern or name based) / `observed` (seen in a screenshot or at runtime). |
| `requires` | string | Optional. `runtime_pixel_probe`, `screen_reader_pass`, `keyboard_pass`, marks a finding that cannot be closed at this phase. |
| `owner` | string | Optional. `design` / `engineering` / `content` / `product`. |

## Severity rubric

Severity is a function of **impact × reach × persistence**. State which factor
drove the rating whenever the result is not obvious.

| Severity | Test | Examples |
|---|---|---|
| `critical` | Blocks a user from completing a primary task, or is a WCAG Level A failure on a primary path, or loses user data | Submit button unreachable by keyboard; form errors announced to nobody; text at 1.8:1; destructive action with no confirmation |
| `serious` | Primary task completable but materially harder, or a WCAG AA failure, or fails for a whole input modality on a secondary path | Body text at 3.4:1; 32pt tap targets in a list; icon-only controls with no accessible name; no error state designed |
| `moderate` | Noticeable friction, a workaround exists, or an AA failure on a rarely-used path | Line height 1.3 on body copy; inconsistent labels for one action; missing empty state; reading order inverted |
| `minor` | Cosmetic or hygiene, no user-visible failure | Hardcoded hex where a token exists; four radii on one screen; off-scale 13px gap |
| `info` | Not a defect: a Not Evaluated item, a note, or something needing a product decision | Contrast over a photo (indeterminate); no dark mode defined yet as a product choice |

Do not inflate. A report where everything is serious is a report nobody acts
on. Do not deflate either: a Level A failure on a primary path is critical even
if the fix is one line.

## Deduplication

- One root cause, one finding, with every affected node listed inside it. Ten
  instances of the same token misuse is one finding with ten locations, not ten
  findings, otherwise the score punishes repetition instead of severity.
- A single node failing two different criteria is two findings.
- Findings that recur across screens get one entry with a `screens` list and a
  note that the fix is systemic. Systemic findings outrank local ones at equal
  severity.

## Writing the fix

Wrong: "Improve the contrast of the button text."
Right: "Swap `text/on-brand` (#8A8A8E) for `text/on-brand-strong` (#3A3A3C) -
lifts 3.1:1 to 7.2:1 on `surface/brand`. Same swap applies to the 6 other
instances listed below."

The fix names the current value, the proposed value, the resulting number, and
the blast radius.
