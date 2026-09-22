# Changelog

## ui-ux-audit 0.7.3 - 2026-09-22

Two fixes found by running a real re-audit, both in the screenshot pipeline.

- `save_screenshot.py` searched only the transcript folder matching the current
  directory. An audit normally runs in a subdirectory of where the session
  started, so it found nothing. It now walks up from the working directory and
  takes the first ancestor with a transcript. An unrelated project is never an
  ancestor, so the confinement added in 0.7.1 still holds.
- `get_design_context` returns a preview render of the node alongside the code,
  which is a screenshot the audit has already paid for. It is now recovered like
  any other, so a colour and type extraction doubles as full-resolution evidence
  and costs no extra read against the seat budget.

## ui-ux-audit 0.7.2 - 2026-09-21

- The Figma MCP wraps its metadata XML in prose, a "Currently selected nodes:"
  preamble and an "IMPORTANT:" note after the closing tag, so a verbatim saved
  response would not parse. The three readers now slice the XML out of the
  saved response, which is what the skill tells you to keep. The entity check
  still runs over the whole file, not just the slice.

## ui-ux-audit 0.7.1 - 2026-09-18

Security pass before the first public release, run with the OWASP-mapped
security-audit skill by toshipon. Five blocking issues, all fixed and all now
covered by a CI regression test.

- The brief (`.audit/config.json`) lives in the project being audited, so it is
  untrusted input, and two of its values were trusted. `output.pdf_theme`
  reached `page.evaluate()` as JavaScript source, and `output.theme` could name
  any file whose `:root` block was spliced raw into the report's `<style>`. Both
  were proven to execute. Values from a brief are now validated against the same
  allowed sets the command line enforces, a custom palette must be passed
  explicitly on the command line, a palette is rebuilt from the declarations
  that parse, and the theme value is passed to Chromium as an argument rather
  than interpolated.
- `save_screenshot.py` built an output path from a `nodeId` recorded in the
  session transcript, which a crafted value could use to write an
  attacker-chosen file anywhere. Node ids are now validated, and writes are
  confined to the output directory. The same script searched every project's
  transcript, so another engagement's screenshots could land in this one's
  evidence; it is now limited to this project.
- The README and the install guide told users to `npm i -g argent`. That is an
  unrelated dormant package, not the tool, while the plugin auto-executes a PATH
  binary of that name as an MCP server. Corrected to `@swmansion/argent`
  everywhere, with the provenance and verification steps in SECURITY.md.
- CI scanned the tree with `glob("**/*")`, which never matches a dotted path, so
  `.mcp.json` and both plugin manifests were invisible to the secret and hygiene
  checks. The scan walks the tree properly now, and a new check pins the MCP
  server declaration, since that command runs on every user's machine.
- `evidence.image` accepted an absolute or climbing path, and without Pillow the
  bytes were embedded unverified, so any readable local file could be base64ed
  into a published page. Evidence is now confined to the findings file's own
  directory and is never embedded unverified.

Also: the untrusted-content rule is now in all nine skills and agents rather
than four, and CI enforces its presence. `audit-verifier` is told explicitly
that a claim of exemption in the audited code is not evidence. `reinstall-app`
and runtime log capture carry warnings about data loss and about tokens in
evidence. An unattended run no longer publishes an artifact by default. Numbers
from a scorecard are coerced before they reach a style attribute. The XML entity
guard scans a 4MB window instead of 64KB, so a padded prolog cannot slip a
DOCTYPE past it. CODEOWNERS, Dependabot, a job timeout, a concurrency group,
`persist-credentials: false`, and credential file shapes in `.gitignore`.

## ui-ux-audit 0.7.0 - 2026-09-18

First public release.

- Brand palette extracted into a swappable theme file, with a `neutral` preset
  and `theme_check.py` to validate a replacement against the contrast figures
  the report states about itself
- Example findings use a fictional product
- MIT licence, marketplace manifest, CI that validates the manifests, compiles
  the scripts, renders the bundled example and checks both themes

## 0.6.x - 2026-09-17

- Audit scope: the intake asks which dimensions to grade, the scorer
  re-normalises the weights over them and reports anything found outside the
  scope without scoring it, and the report drops the sections nobody
  commissioned while renumbering itself
- Print parity with the artifact: one rem type and spacing scale, no print rule
  re-grids a component, the prism edge survives as a printable strip, and the
  builder warns if either invariant is broken
- Page geometry: 20mm side margins, a 170mm column, the footer inside the
  printable area, and no item broken across pages
- Cream cards on white paper with real borders, in both PDF themes
- Screenshots taken through the Figma MCP and marked at the finding, with no
  manual export step
- Executive PDF cut: the verdict and the fix plan only
