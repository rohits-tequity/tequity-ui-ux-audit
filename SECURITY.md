# Security

## Reporting

Email security@tequity.tech with what you found and how to reproduce it. Please
do not open a public issue for anything exploitable. You will get an
acknowledgement within five working days.

## What this plugin does on your machine

Worth knowing before you install it, because a plugin runs with your agent's
permissions.

**It reads.** Figma payloads through the Figma MCP server, files in the repo or
path you point it at, this project's own Claude session transcript (only the
image payloads the Figma MCP returned, and only from the transcript folder that
matches your working directory, see
`skills/figma-design-audit/scripts/save_screenshot.py`), and the accessibility
tree of a running app through Argent.

**It writes** into the working directory you run it in: `.audit/config.json`
holding the brief, an `audit/` folder with cached payloads, measurements,
screenshots and the rendered report. Nothing outside it.

**It runs** Python scripts bundled here, and `argent` from your PATH for the
runtime phase. No network calls of its own: the MCP servers and your agent make
those.

**It sends nothing anywhere.** Reports are written to disk. Publishing one as an
artifact is an action your agent takes at your request, not something the
plugin does.

## Design decisions that are security decisions

**A report is a page that gets shared, so everything that feeds it is untrusted
input.** That means three files, not one. Fields from `findings.json` are
HTML-escaped; an `image` is embedded only as a base64 png, jpeg, gif or webp,
and only from inside the findings file's own directory; a link is emitted only
for `http`, `https`, `mailto` or a fragment. Numbers from `scorecard.json` are
coerced before they reach a style attribute. A brief (`.audit/config.json`)
lives in the project being audited, so its values are re-validated against the
same allowed sets the command line enforces, a custom palette has to be passed
explicitly on the command line rather than named by the brief, and a palette is
rebuilt from the declarations that parse rather than pasted into the page. CI
builds a report from a hostile findings file and a hostile brief on every push,
and fails if a script tag, a non-image data URI, a `javascript:` URL or an event
handler attribute reaches the output.

These checks are regression tests for known sinks, not a certificate that the
renderer is safe against everything.

**Figma metadata is XML, and ElementTree expands entities.** A metadata file
that declares a `DOCTYPE` or an `ENTITY` is refused before parsing, so the
billion-laughs pattern has nowhere to land. Figma metadata never needs one.

**No credentials, ever.** The plugin holds no tokens and asks for none. Figma
access is whatever your Figma MCP server already has; GitHub access is whatever
your own git setup has. There is nothing here to leak.

**Content the plugin reads is data, not instructions.** A Figma layer name, a
code comment, a web page or a PR description can contain text aimed at your
agent. The skills say to treat all of it as material to audit and never as a
direction to follow, and to surface anything that looks like an instruction as a
finding rather than acting on it.

## Known limits

- `argent` comes from your PATH. The plugin declares the MCP server but cannot
  verify the binary. Install it from a source you trust, and note there is no
  way to pin a binary dependency in a plugin manifest. The legitimate package is
  `@swmansion/argent` on the public npm registry, maintained by Software Mansion.
  There is an unrelated, dormant package called plain `argent`; it is not this
  tool. Verify what you have with `npm ls -g @swmansion/argent`, `which -a argent`
  and `argent --version`, and prefer a project-local install over a global one.
- PDF output shells out to a headless Chromium through Playwright, which renders
  a local file. If you do not want that, skip `--pdf` and print the HTML from
  your own browser instead.
- `save_screenshot.py` reads your Claude session transcript from your home
  directory. It extracts only image payloads the Figma MCP returned, only from
  this project's transcript folder, and writes them under the output directory
  you named. If that is not acceptable in your environment, pass screenshots in
  yourself and skip that script.
- The runtime phase can capture network logs and console output from a running
  build. If that build is signed into a real account, those carry tokens and
  personal data. The skill says to review and redact anything captured before it
  becomes evidence, but nothing enforces it: that judgement is yours.

## Supply chain

Two runtime dependencies, both optional and both widely used: Pillow for image
work, Playwright for PDF. Neither is vendored. CI pins Pillow, runs on
`pull_request` rather than `pull_request_target` so a fork's code never sees
repository secrets, and grants the workflow `contents: read` only.
