# Changelog

## ui-ux-audit 0.8.0 - 2026-09-23

### A verdict instead of a grade

- Every report now opens with two answers, kept apart: **can we go ahead**
  (GO, GO WITH FIXES, NO-GO, NOT DECIDED, with the next step named for the
  phase) and **where WCAG stands**, per version (2.0, 2.1, 2.2) and per level up
  to the target, with AA shown as "AA (includes A)". Statuses are Fails,
  Incomplete, No known failures, No failures found and Not targeted; never
  "Met", "conformant" or "compliant".
- The grade letter is gone from the panel. A big "A" read as WCAG Level A. The
  score stays, below the verdict, as a quality score with a word (Excellent,
  Good, Fair, Weak, Poor) and a sentence saying it does not decide anything.
- Gate rules, first match wins: any critical or serious finding, or a criterion
  at the target that does not support, is NO-GO at any coverage; nothing
  blocking but a design-checkable criterion not yet judged is NOT DECIDED; any
  moderate finding or partial criterion is GO WITH FIXES; only minor and info
  left is GO. Minor findings never block.
- **Design done.** A design-stage GO with no known WCAG failures says so and
  lists what only the build can settle. That is the signal to stop iterating.
- Every finding card says whether it blocks the go-ahead. Overview and
  hand-over lines lead with the verdict.

### WCAG results that match what the design shows

- Every criterion a finding cites is read, not only the first. A new `wcag`
  field states each one's effect: `fails`, `risk` or `context`. Old files are
  read clause by clause, and "2.5.8 is met at 24px" is context, not a failure.
- Minor and info findings never change a criterion's status. `score.py`
  refuses a minor finding that claims a WCAG failure.
- A platform-guideline miss (44pt, 48dp) is a platform-fit finding that can
  block the go-ahead but never fails WCAG. The guidance used to grade WCAG
  against the stricter platform number.
- Findings outside the agreed scope no longer change WCAG statuses, and an info
  finding no longer hides an explicit Supports.
- Each criterion is tagged D, D/R or R for what the design phase can settle
  (28 of 55 at 2.2 AA are D). The figma skill now walks every D criterion on a
  declared sample; a D criterion left unjudged keeps the verdict NOT DECIDED.
- A fixed finding no longer makes its criterion pass on its own: the criterion
  has to be re-checked across the sample first.
- A design-checkable criterion the design genuinely cannot settle on the sample
  (text over a photo: 1.4.3, 1.4.6 or 1.4.11 only) can be recorded under
  `evaluated.indeterminate` with a reason; it moves to the build checks instead
  of holding the verdict at NOT DECIDED.
- Legacy criterion text is read with negation in mind ("does not satisfy",
  "only meets"), a trailing "once built" covers every criterion in its clause,
  a platform-fit finding never infers a WCAG failure, and a target written as
  "WCAG 2.2 A/AA" means AA.

### Audit memory

- Re-audit the same file and the plugin builds on the last round, from
  `.audit/memory/` (`audit_memory.py`: init, load, assign-ids, merge,
  record-round, migrate, check).
- Open findings are re-checked first. One the round does not reach comes back
  as Not re-checked at its last severity and still counts. Every pass is
  measured again each round; nothing that passed is carried.
- Ids stay stable across rounds even when node ids change: an exact match on
  criteria and component names (order, node ids and dimension ignored) keeps
  the id, near matches come back as proposals for the agent to confirm, a fixed
  finding that returns reopens its id as Regressed, and ids are never reused.
  On the real R1 to R2 data: 6 of 10 matched exactly, 4 proposed, none wrong.
- A second, unrelated flow in an audited file gets its own history
  (`init --flow`). `merge` can run twice safely, and stops when a new finding
  looks like an open one under a new id. `record-round` refuses a round that
  was not merged or is dated before the last one. A lost index is rebuilt from
  the target files on disk.
- Cards carry New this round, Still open, Improved, Worsened, Regressed or Not
  re-checked. A progress table re-judges every earlier round under the current
  model, and a fixed-since-last-round table shows before and after.
- The re-audit mode is asked every round: check fixes then a full pass
  (recommended, and the only mode that can declare design done), check fixes
  only, or fresh.
- Local only: the first run writes a `.gitignore` of `*` into `.audit/` and
  `audit/`. Nothing goes to personal Claude memory. Memory files are validated
  on read, corrupt ones are moved aside, and free text reaches the agent only
  as data.
- Rounds from before memory are imported with `migrate`, including fixes
  recorded in the older `cleared` shape.

### Fixes

- `.audit/previous-scorecard.json` was a manual step and was skipped in
  practice; `record-round` writes it, and the builder has `--save-baseline`.
  The documented baseline path no longer disagrees between files.
- `cleared` entries in the `{candidate, why}` shape rendered as blank rows.
- A baseline from an older scoring model is labelled not comparable, with the
  movement in open findings shown instead.
- The verifier returns re-check verdicts (FIXED needs a measurement taken this
  round) and corrects WCAG effects when it downgrades a finding. The
  consistency checker checks the gate invariants.
- CI runs 54 verdict tests and 55 memory tests, and the injection test covers
  the verdict block.

## ui-ux-audit 0.7.6 - 2026-09-22

- Install and repository references now point at the published repo,
  `rohits-tequity/tequity-ui-ux-audit`. The README install command, the team
  settings snippet, `docs/install.md` and the plugin manifest's `homepage` and
  `repository` all agreed on a placeholder owner before this; they would have
  sent anyone following the README to a repo that does not exist.

## ui-ux-audit 0.7.5 - 2026-09-22

- Publishing is confirmed the first time. An artifact is a URL carrying
  screenshots of the client's designs or app, so the first publish of a project
  asks; a re-audit republishes to the recorded URL without asking, because the
  delta is the point; an unattended run never publishes. The brief now carries
  `artifact_url` so the plugin can tell the two cases apart.
- Fixed a contradiction introduced in 0.7.4: the publish step still said to
  export a PDF for anything leaving Claude, while the rule above it said a PDF
  is only produced on request. The README and the intake said the old thing too.

## ui-ux-audit 0.7.4 - 2026-09-22

- The artifact is the deliverable. A PDF is a second render of the same data
  that costs a headless Chromium pass and usually goes unread, so it is no
  longer produced unless the brief lists it or the person asks. The intake's
  output question now defaults to the artifact link alone, and the builder says
  plainly when it skips a PDF and how to get one.
- The report skill now says to close the reply with the link. A reader who has
  just read the summary should not have to scroll back up to find the report.

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
