# Install and first run

## Install

```
/plugin marketplace add rohits-tequity/tequity-ui-ux-audit
/plugin install ui-ux-audit@tequity-tools
```

`/plugin marketplace update` pulls later versions.

## First run

Give Claude the thing you want audited. It runs the intake first, which detects
what you handed it and asks only what it cannot infer, as multiple choice with a
free-text option on every question:

```
audit https://www.figma.com/design/<key>/<file>?node-id=1-2
```

Expect to be asked: the platform, the user story, themes and devices, the audit
scope, the WCAG target, whether there is a design system, the output formats and
who is going to read it. The answers land in `.audit/config.json` in your
project and are binding from then on, so a second audit asks nothing.

## What you get

An artifact you can share, plus whichever of HTML, A4 PDF and the executive cut
you asked for. Seven sections: overview with the verdict panel, screens
reviewed, accessibility against your WCAG target, design quality, missing
screens and states, the fix plan with owners and a retest plan, and an appendix
with the standards, the full conformance table, the scoring model and the
candidates that were checked and cleared.

## Before you rely on it

- A conformance claim needs a full WCAG-EM evaluation with assistive-technology
  testing by a qualified evaluator. This is an audit, not a certification.
- The design phase cannot settle behaviour. Keyboard, focus, real reflow, motion
  and contrast over imagery come back Not Evaluated until the runtime phase runs.
- Screen-reader speech is not checked. The runtime phase reads the accessibility
  tree; what VoiceOver and TalkBack actually say needs a manual pass.
- Figma reads are rate limited by seat. The plugin tells you your seat and the
  published cap before spending any.

## Troubleshooting

**`Executable not found in $PATH` in the plugin Errors tab.** The `argent` CLI is
missing. `npm i -g @swmansion/argent`, then `argent doctor`. It only affects the runtime
phase.

**The Figma phase stops and asks for a different link.** A Figma URL without
`node-id` does not identify a frame. In Figma, select the frame and copy the link
to selection.

**No PDF, only HTML.** `pip install playwright` and make a Chromium available.
The print stylesheet is already tuned for A4, so printing the HTML from a
browser gives the same result.

**The report says a finding is `inferred`.** It came from a layer name rather
than a measured value. Those are flagged on purpose and are the ones to confirm
first.
