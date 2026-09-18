# Intake question bank

Every question is multiple choice with a recommended option first, and the
AskUserQuestion tool always adds a free-text "Other" so the user can type
something else. Ask only the questions `detect_inputs.py` lists under
`questions_to_ask`; never re-ask something already in `.audit/config.json`.
Group up to four questions per call. Unattended session: pick the recommended
option, say so at the top of the work, and carry on.

## what_to_audit
Header: Audit target. Question: What should this audit cover?
- Figma design (Recommended if a Figma link is present): pre-code, measured from the file
- UI source code: a PR, diff, repo or component files
- Running app or page: simulator, emulator, device or Chromium via Argent
- Everything available: design, code and runtime in one report
Follow-up when the answer needs an input that was not given: ask for the link, path or device in plain text.

## figma_node_link
Header: Figma link. Question: The Figma link has no node-id, so nothing can be extracted. How do you want to proceed?
- Paste a node link (Recommended): in Figma, select the frame, right-click, Copy link to selection
- Audit the whole page: costs one extra read to list pages, then one link per frame
- Skip the design phase for now

## phase_order
Header: Order. Question: Several phases apply. In what order?
- Design first, then code, then runtime (Recommended): findings carry forward with stable ids
- Runtime first: the build exists and the design is stale
- Only one phase now: choose which in the next question

## platform
Header: Platform. Question: Which platform sets the thresholds?
- React Native, iOS and Android (Recommended when the repo or design says RN): graded against the stricter of the two
- iOS only: 44pt targets, 17pt body, Dynamic Type
- Android only: 48dp targets, 14sp body, fontScale
- Web: 24px targets, 16px body, 320px reflow, keyboard and focus

## user_story
Ask as up to four short questions in one call. These decide what is `critical`.
1. Header: UI type. Question: What kind of screen is this? (four options; the rest via Other)
   - Checkout / payment / transfer (Recommended when money moves) · Form: profile, KYC, address, settings-as-form · Auth: sign-in, sign-up, OTP · List, feed or search results
   If none fits, the user types one of: Detail / read view, Dashboard / data, Onboarding, Settings, Chat, Media player, Map, TV. Map the typed text to the archetype in `figma-design-audit/references/ui-archetypes.md`.
2. Header: Persona. Question: Who is the primary user and what constraint matters most?
   - Returning user, no special constraint (Recommended default) · Uses a larger font scale or one hand · Screen-reader or switch user · Low bandwidth or offline-prone
3. Header: Goal. Free text prompt: In one sentence, what is the user trying to do on this screen? (Other box)
4. Header: Primary path. Free text prompt: List the steps to success, separated by arrows. (Other box)
If the user skips 3 or 4, run the generic checks and state in the report that no user story was supplied.

## themes
Header: Themes. Question: Which colour themes should be audited? Each theme is a separate Figma extraction (3 reads).
- Light and dark (Recommended): contrast recomputed per theme
- Light only
- Dark only
- Light, dark and high contrast

## devices
Header: Devices. Question: Which device classes should the layout be judged on?
- Smallest supported phone plus a standard phone (Recommended): iPhone SE 375 and iPhone 15 / Pixel 8
- Add a large phone: Pro Max 430
- Add tablet or split view
- Desktop widths (web): 1280 and 320

## scope
Header: Grade what. Question: Which dimensions should the score and grade cover?
- Everything (Recommended): accessibility, interaction and states, robustness and edge cases, content and copy, design system, platform fit
- WCAG conformance only: accessibility alone, for a conformance statement or a client deliverable
- Conformance plus platform rules: accessibility, platform fit and robustness; leaves copy and design-system opinions out
- Design system only: token, style and copy consistency, no conformance grading

Record the chosen dimension list, not the option text, so nothing has to stay in sync:

| Option | `scope.dimensions` |
|---|---|
| Everything | omit the key, or all six |
| WCAG conformance only | `["accessibility"]` |
| Conformance plus platform rules | `["accessibility", "platform_fit", "robustness"]` |
| Design system only | `["visual_system", "content_copy"]` |

Scope narrows what is **scored**, never what is looked at. Anything found outside
the scope still reaches the report, in its own unscored section, because a client
who paid for a conformance audit still needs to know their primary button is 26pt.
Say that in one line when confirming the brief, so nobody expects the other
dimensions to have been checked and passed. Under a narrowed scope the weights are
re-normalised over the chosen dimensions, the grade label reads "on accessibility"
rather than bare, and the release line says it is not a product-wide decision.

Ask this immediately before the conformance target: the two answers together are
what the report is graded on. Do not ask it for a report-only re-render, the scope
is already in the brief.

## conformance_target
Header: Standard. Question: Which WCAG version and level should the report grade against?
- WCAG 2.2 AA (Recommended): current W3C Recommendation; the report also reads as 2.0 and 2.1
- WCAG 2.1 AA: matches EN 301 549 / EAA, ADA Title II, GIGW 3.0 wording
- WCAG 2.2 AAA: adds the 31 AAA criteria
- WCAG 2.0 AA: legacy contracts and Section 508 wording

## design_system
Header: Tokens. Question: Is there a token set or component library to check conformance against?
- Yes, in the same Figma file (Recommended if variables exist): one extra read for variables
- Yes, a separate library file: paste its link
- Yes, in code only: give the tokens path
- No design system

## device_reachable
Header: Device. Question: For the runtime phase, where is the app running?
- iOS simulator on this Mac with Argent installed (Recommended for RN/iOS)
- Android emulator or device with adb and Argent
- Web page in Chromium
- Not available now: skip runtime and mark those criteria Not Evaluated
Remind: Argent runs where the device is, not in the cloud session; if `list-devices` returns nothing, stop and say so.

## output
Header: Output. Question: How do you want the report delivered?
- Artifact link plus HTML file (Recommended): shareable, re-publishable to the same URL on re-audit
- Artifact, HTML and a PDF: PDF in the brand print theme (cream, ink, teal, orange, coral)
- PDF only, dark theme: the on-screen dark look, for screen reading, heavier to print
- HTML file only: no publishing
Follow-up when PDF is chosen: Header: PDF theme. Options: Brand print theme (Recommended for printing and client decks) · Dark (matches the artifact).

## pdf_theme
Header: PDF theme. Question: Which look should the PDF use?
- Brand print theme (Recommended): cream page, ink text, teal, orange and coral accents; prints well and reads in daylight
- Dark: the on-screen dark theme; heavier to print, good for on-screen reading

## theme (only when the user mentions their own brand)
Header: Brand. Question: Which palette should the report use?
- Tequity default (Recommended): the shipped palette, both modes contrast-checked
- Neutral (ink, slate and rust): brand-free, for a report going to a third party
- Our own brand: paste or point at the tokens; run `theme_check.py` before using it

Record as `output.theme` (a preset name or a path). A custom palette that fails
`theme_check.py` is not used silently: say which pair failed and offer the
nearest passing value.

## audience
Header: Readers. Question: Who will read this report? (multi-select)
- Product manager or founder (Recommended default)
- Designer
- Developer
- Client or compliance / legal
Each selection keeps its row in "How to read this report" and sets the depth of the overview; selecting client adds the regulatory row from `standards-map.md` to Standards applied.

## regime (only when audience includes client / compliance)
Header: Regulation. Question: Which regime should the standards block mention?
- None specific (Recommended unless known)
- EU: EN 301 549 / European Accessibility Act
- US: ADA Title II or Section 508
- India: RPwD Act / GIGW 3.0
Multi-select allowed; UK Public Sector Bodies Regulations, Canada AODA and others go in Other.

## re_audit (only when .audit/previous-scorecard.json exists)
Header: Re-audit. Question: A previous scorecard exists. How should this run relate to it?
- Compare and show the delta (Recommended): carries ids forward, leads the overview with movement
- Fresh audit, ignore the baseline
- Only re-test the previously open findings

## Edge cases the skill handles without asking
- Several Figma links: one screen per link; budget = links × themes × 3 reads. State the total before extracting; if it exceeds the seat's cap, ask which screens first.
- Figma link to a page (no node): list pages costs one read; then one link per frame is needed.
- Branch URL: `/design/<fileKey>/branch/<branchKey>/…`; the branch key is the fileKey.
- Path does not exist: say so; do not guess a sibling path.
- Mixed inputs (Figma + PR): both phases, design first, ids carried into the code phase.
- Runtime hinted but no device: mark runtime Not Evaluated and continue with what exists.
- No user story after asking: run generic checks, no archetype section, report says so.
- Output not chosen and unattended: artifact + HTML; PDF only if the user mentioned print or client.
