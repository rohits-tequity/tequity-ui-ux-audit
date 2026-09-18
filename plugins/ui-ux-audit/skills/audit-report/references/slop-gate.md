# Anti-slop gate

Run every check before publishing. A failed check is fixed or the finding is
deleted, never softened into vagueness.

## Evidence

- [ ] Every finding has a measured number **or** a marked image region. No
      exceptions, including for findings that feel obvious.
- [ ] Every measured number prints its threshold beside it.
- [ ] No finding uses "may", "could", "potentially" about something that was
      measured. Reserve hedging for genuinely inferred items, and label those
      `inferred` with the basis stated.
- [ ] No claim of conformance for anything marked Not Evaluated.
- [ ] Every screenshot in the report is one that was actually captured this run.
      No illustrative or reconstructed images.
- [ ] Node ids / file paths / line numbers present so each finding is locatable.

## Substance

- [ ] Every fix names the current value, the proposed value and the resulting
      number. "Improve contrast" fails.
- [ ] No duplicate findings for one root cause; instances are listed inside one
      finding.
- [ ] Systemic findings are identified as systemic, with their instance count.
- [ ] The overview's bullets each carry a consequence, not a topic.
- [ ] Severity distribution is defensible: if everything is serious, re-rate.
- [ ] The Limitations section is present and specific, not "some items require
      further testing".
- [ ] The retest step for each finding is executable by someone else.

## Language

- [ ] No filler openers: "In today's digital landscape", "It is important to
      note that", "This report aims to".
- [ ] No inflated symbolism: nothing "underscores", "highlights the importance
      of", "serves as a testament to".
- [ ] No rule-of-three padding: "clear, consistent and coherent".
- [ ] No vague attribution: "industry best practice suggests" without naming the
      guideline and its clause.
- [ ] No em-dash pile-ups, no sentence starting "Moreover" or "Furthermore".
- [ ] No praise that no finding supports.
- [ ] Sentences under ~25 words in the overview and fixes.
- [ ] Then run the `anthropic-skills:humanizer` skill over the prose sections
      and apply what it returns.

## Numbers

- [ ] Score came from `score.py`, not from judgement.
- [ ] Coverage is reported separately from score.
- [ ] The scoring model is published in the appendix.
- [ ] Finding ids are stable and match the ids in the findings JSON.
- [ ] Every count in the overview matches the findings table. Recount, do not
      trust the draft.

## Self-audit

- [ ] The report page itself passes its own contrast checks in light and dark.
- [ ] The report is readable at 320px and at 200% zoom.
- [ ] Colour is never the only carrier of severity, chips and bars show text.
- [ ] Every table has a header row; no data table is used for layout.

The last check: would you send this to the client who paid for it, and defend
every number in a meeting? If not, the problem is in the list above.
