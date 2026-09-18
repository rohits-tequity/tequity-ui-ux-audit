# Figma extraction, payload shapes and parsing

## Budget first

`mcp__Figma__whoami` is exempt from rate limits. Call it once, read the plan and
seat, and state the published cap for that seat before spending reads, it
returns no remaining count, so never quote a balance. Starter plan, or a View or
Collab seat on any plan, ≈ 20 reads per month; Dev or Full seat ≈ 200–600 per
day depending on the plan. Reads that count include
`get_metadata`, `get_design_context`, `get_variable_defs`, `get_screenshot`,
`search_design_system` and `get_libraries`.

Cache every raw response to disk immediately. Re-running the analyser must never
cost a Figma call.

## 1. `get_metadata` → geometry

Args: `fileKey`, `nodeId` (omit `nodeId` to list the file's pages).
Returns XML: node id, layer type, name, position and size. This is the cheapest
structural read and carries everything the geometry checks need.

Parse into one record per node: `id`, `name`, `type`, `x`, `y`, `w`, `h`, parent.

Derive:
- **Interactivity guess**, a node is treated as interactive when its name or
  type matches `button|btn|cta|link|tab|chip|toggle|switch|checkbox|radio|input|
  field|icon-button|iconbtn|fab|close|menu|card` (case-insensitive), or it is an
  `INSTANCE` of a component whose name matches. Record the guess and its basis;
  never present a guessed target-size failure as certain. Ask the user to confirm
  ambiguous ones.
- **Target size**: `w` × `h` against the platform minimum.
- **Target spacing**, centre-to-centre distance to the nearest other
  interactive node.
- **Overlap**, fixed overlays (headers, bottom bars, FABs, sheets) intersecting
  interactive nodes → SC 2.4.11 risk.
- **Reading order**, layer order vs. nodes sorted by `(y, x)`; report the
  inversions, not just a count.
- **Text growth slack (SC 1.4.4)**, a TEXT node whose parent frame is within
  ~15% of the text's own height has no room to absorb a larger font scale. This
  is inference from geometry, so it carries `requires:
  runtime_font_scale_pass`; the implementation audit settles it.

## 2. `get_design_context` → colour, type, tokens

Load Figma's `figma-design-to-code` guidance first, the tool's own description
requires it.

Args: `fileKey`, `nodeId`. Returns reference code (JSX/CSS-like), a screenshot,
asset download URLs, and token/variable names where the design uses them.

Save the code payload verbatim. Extract with the analyser:
- Colour literals: `#rgb`, `#rrggbb`, `#rrggbbaa`, `rgb()`, `rgba()`, and the
  common named colours (`white`, `black`, `red`, `green`, `blue`, `gray`).
  Exotic named CSS colours are not matched, if a payload uses them, say so
  rather than assuming the sweep was complete.
- A colour literal that appears **without** a nearby variable/token reference is
  a hardcoded-value finding for the design-system score.
- `font-size`, `line-height`, `font-weight`, `letter-spacing` and their token
  names. Compute the line-height ÷ font-size ratio.
- Foreground/background pairing: the analyser pairs each text colour with a
  background declared in the **same rule**, or, failing that, the most recent
  background declared earlier in the payload (`bg_source: inherited`, and the
  finding is downgraded to `confidence: inferred`). Where no background at all
  resolves, the backdrop is an image, gradient, video or blur, the result is
  **indeterminate**, emitted as a `contrast_indeterminate` info finding with
  `requires: runtime_pixel_probe`. Never assume white. An inherited pairing can
  still be wrong (text over a hero image inherits the page background), so
  review every `inherited` result against the screenshot before reporting it.
- `opacity` below 1 on text: multiply into the effective foreground before
  computing contrast, and flag it, because designers routinely lose contrast
  this way.

Keep the screenshot: the report uses crops of it as finding evidence.

## 3. `get_variable_defs` → token map

Args: `fileKey`, `nodeId`. Returns a name → value map, e.g.
`{"icon/default/secondary": "#949494"}`.

Use it to:
- Resolve token names to values for contrast maths.
- Build the allowed **colour** set, so a literal in the design context that
  matches no token is reported as drift. Spacing and radius drift are judged
  against an inferred base unit and a distinct-value count rather than against
  the token set, if the system publishes spacing and radius tokens, check those
  by eye and say you did.
- Detect **mode coverage**: the analyser reports which modes are discoverable in
  the token names and flags a single-mode token set. It does **not** recompute
  every contrast pair per mode, the design-context payload carries one
  resolution. To audit dark mode properly, extract the dark-mode screen as its
  own run and compare the two reports.
- Detect exact duplicates: two or more tokens resolving to the identical colour
  value. Perceptual near-duplicates (ΔE-close pairs, or text styles differing
  only in line height) are a manual read of the variable list, not a script
  output.

## Optional, only if token conformance is in scope

`mcp__Figma__search_design_system` and `mcp__Figma__get_libraries` answer
"does a component for this already exist in the library". Useful for flagging
one-off components that should have been library instances, but each costs
budget. Ask before spending it.

## Things Figma cannot tell you

Say so in the report rather than inferring:

- Whether a control is actually focusable or in the tab order.
- The accessible name that will ship (unless annotated in the file).
- Real rendered contrast over photography, video or translucency.
- Whether the implementation honours font scaling or reduced motion.
- Animation timing and easing as built.
- Anything data-dependent: real string lengths, real list sizes, real latency.
