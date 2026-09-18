# Runtime audit workflow

## Per-state evidence loop

For every (screen, state) pair, capture the same set so findings are comparable
and the report's coverage matrix can be filled honestly.

1. `await-screen-idle`, do not measure a screen mid-render.
2. `describe`, accessibility / DOM tree. Save verbatim.
3. `native-describe-screen` (iOS sim), point-space frames and traits.
4. `debugger-component-tree` (React Native), component names and testIDs.
5. `screenshot --scale 1.0 --includeImageInContext false` → `shots/<screen>__<state>.png`.
6. `debugger-log-registry` and `view-network-logs`, errors that never surface.
7. Note anything visually wrong that the trees cannot express, from a
   downscaled screenshot you actually look at.

Name every artefact `<screen>__<state>` so the report can pair design and
runtime evidence automatically.

## Forcing the states

| State | How |
|---|---|
| Empty | Fresh install (`reinstall-app`) or an account with no data |
| Loading | Throttle the network, or capture immediately after navigation |
| Error 5xx / network | Point the app at a dead host, or airplane-mode the emulator; `adb shell svc data disable` on Android |
| Offline | Disable connectivity, then re-enable and check recovery |
| Permission denied | `settings-permissions` to deny, then relaunch |
| Long text / localisation | Seed long strings; switch device language, including an RTL locale |
| Largest font scale | iOS Accessibility → Larger Text (AX5); Android Display → Font size max |
| Dark mode | Toggle the OS appearance, re-capture every screen |
| Reduced motion | iOS Reduce Motion; Android Remove animations |
| Rotation | `rotate` to Landscape and back |
| Keyboard open | `gesture-tap` an input, then `describe`, is the focused field still visible, is the CTA covered |
| Rapid double tap | `run-sequence` with two taps a few ms apart on a submit control |
| Deep link entry | `open-url` straight to the screen with no back stack |
| Interrupted | `button` home, then `launch-app` again mid-flow; then `restart-app` to test state loss |
| Session expired | Invalidate the token server-side, then act in the app |

## Focus and keyboard

- Chromium / web: `keyboard` with Tab, then `describe` after each press.
  Build the actual focus order, compare it to the visual order, and check every
  stop has a visible indicator. SC 2.4.7 asks only that it be visible; measure
  the indicator's contrast under SC 1.4.11 (≥3:1) with `pixel_probe.py` using
  `non_text: true`, do not eyeball it.
- Look for: focus lost after a modal closes, focus not moved into an opened
  modal, a trap with no escape, focus landing on a hidden element, and focus
  obscured by a sticky bar (SC 2.4.11).
- TV targets: `tv-remote` to move focus, `describe` shows `[focused]`.
- Native mobile: VoiceOver / TalkBack **announcements are not readable through
  Argent**. Report the tree-level facts (name, role, state, order) and mark the
  announcement checks as Not Evaluated, requiring a manual pass. Do not claim
  screen-reader conformance.

## Visual regression

`screenshot-diff` with `--baselinePath` plus `--captureCurrent` is the standard
loop. Rules that keep it useful:

- Baselines per device model and orientation; different aspect ratios fail as a
  dimension mismatch, not as a diff.
- Full resolution on both sides.
- Freeze the clock, seed fixed data, and disable animation before capturing, or
  the diff is noise.
- It is the right tool for clipping, overflow, spacing, colour and typography
  regressions. It is the wrong tool for state, navigation and accessibility
  checks, the tool's own guidance says so.

## Performance as a usability finding

Use `react-profiler-start` / `-stop` / `-analyze` and
`native-profiler-start` / `-stop` / `-analyze`, then
`profiler-combined-report` to correlate. Report as usability defects, with
numbers: interaction latency over ~100 ms for direct manipulation, over ~1 s for
navigation, any main-thread hang over 250 ms, dropped frames during a scroll,
and list re-render storms from unstable props. Tie each to the component
`react-profiler-component-source` names, so the fix has an address.

## Repeatability

Wrap the walk in a flow: `flow-start-recording`, then `flow-add-step` per tool
call, then `flow-finish-recording`. The YAML lands in
`.argent/flows/<name>.yaml` and replays with `flow-execute`. Commit it. The
retest plan in the report should name the flow, not describe the clicks.
