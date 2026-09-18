# Audit matrix, themes × devices × font scale

A screen is not one thing. It is the product of its theme, the device it renders
on, and the user's font scale. Audit the cells the user story makes mandatory,
sample the rest, and say which cells were not covered.

## Dimensions

| Axis | Values | Default sample |
|---|---|---|
| Theme | light, dark, high-contrast (OS increased contrast) | light + dark always; high-contrast when the persona or platform requires |
| Device class | small phone (iPhone SE 375×667 / 320px web), standard phone (iPhone 15 393×852, Pixel 8 412×915), large phone (Pro Max 430×932), tablet (iPad 820×1180, split view 507px), desktop 1280+, TV 1920×1080 at 10ft | the two phone classes the analytics say users have, plus the smallest supported |
| Font scale | 100%, 130% (common accessibility setting), largest (iOS AX5 ≈ 310%, Android 200%) | 100% + largest always; 130% when the persona uses it |
| Orientation | portrait, landscape | portrait always; landscape unless locked with justification |
| Locale | default, longest (German), RTL (Arabic/Hebrew), CJK | default + longest always; RTL when the product ships to RTL markets |
| Motion | normal, reduced | both, reduced is a one-flag check |
| Input | touch, keyboard, switch/voice, screen reader, D-pad | touch + screen-reader tree always; keyboard on web/desktop; D-pad on TV |

## What changes per axis

**Theme**, every contrast pair recomputes. Tokens that resolve in one mode
only, hardcoded fills, and elevation/shadow visibility in dark are the recurring
failures. Design stage: extract the dark-mode variant of the screen as a second
run (the design-context payload carries one resolution). Runtime: toggle OS
appearance, re-capture, re-probe.

**Device class**, layout, target size in points, safe areas, and reflow. Small
phone finds truncation and stacked-CTA problems; tablet finds stretched
single-column layouts and split-view breakage; large phone finds one-handed
reach problems (primary CTA above thumb zone).

**Font scale**, text growth slack, clipping, control height, and whether the
CTA is pushed off-screen behind the keyboard. The single most under-tested axis
in mobile audits; it is where `allowFontScaling={false}` hides.

**Locale**, string length (German ≈ +35%), RTL mirroring of icons with
direction, number and date formats, line-breaking in CJK.

## Recording context on findings

Every finding carries `context: {theme, device, font_scale, locale}` when the
defect is specific to a cell, or `"all"` when it is not. The report renders a
findings-by-theme-and-device table from this automatically. A finding that
appears in every cell is systemic; one that appears in one cell is a layout
edge case, both are useful, but they have different fixes.

## Budgeting

Design stage on a rate-limited Figma seat: each theme is a separate extraction
run (3 reads). Two themes × N screens × 3 reads is the cost, say it before
starting. Device classes and font scale at design stage are read off the frames
the designer made; if only one frame exists, the other cells are **Not
Evaluated**, which is a finding on the design process, not a gap in the audit.

Runtime: one device per agent, cells walked sequentially. Font scale and theme
changes are OS settings toggles; device class means a different simulator.
Record which cells ran in the report's Environment and Limitations.

## Minimum honest matrix

If budget allows only one pass, run it on: **light theme, the smallest
supported phone, 100% font scale, default locale**, and list every other cell
under Limitations. A report that says "light only, SE only" is trustworthy; one
that implies coverage it did not do is not.
