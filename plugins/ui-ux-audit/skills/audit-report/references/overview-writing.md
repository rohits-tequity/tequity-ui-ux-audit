# Executive overview and rating panel

## The rating panel

Everything on the panel is read straight from `scorecard.json`. Nothing on it is
retyped or rounded by hand.

Layout, top to bottom:

1. **Go-ahead**, one of GO, GO WITH FIXES, NO-GO, NOT DECIDED, with the one
   sentence that names the next step ("Do not go ahead to build yet: 2 serious
   findings open"). This is the sentence the reader came for. It comes from the
   verdict gate in `score.py`, never from the score.
2. **WCAG line and grid**, the target ("WCAG 2.2 Level AA (includes A): fails on
   2.5.8, 4.1.2") and one row per version, one column per level up to the
   target: Fails / Incomplete / No known failures / Not targeted. Never "Met",
   "conformant" or "compliant".
3. **Quality score** out of 100 with its word ("Fair"). No letter: a big "A"
   reads as WCAG Level A. The score is detail, not the decision.
4. **Severity counts**, five chips: critical, serious, moderate, minor, info.
   Critical is visually loudest. A zero count still shows, as a zero.
5. **Dimension bars**, six horizontal bars, each labelled with its score and
   its weight, sorted worst first so the eye lands on the problem. Weight is
   shown because a 70 on a 30%-weight dimension matters more than a 70 on an 8%
   one.
6. **Coverage**: "34 of 50 applicable criteria evaluated (68%)" and "11 of 28
   states designed (39%)". Coverage sits next to the score, never inside it.
7. **Confidence**, the phase label and its caveat, e.g. "Provisional, design
   stage only".

Colour rules: the gate word carries its meaning in text, colour only reinforces it; severity colours for the chips,
and a single neutral hue for the bars with the band colour only at the fill.
Never rely on colour alone, every chip and bar carries its number as text, and
the grade carries its word label. The report must survive being printed in
greyscale and must pass its own contrast checks. Load `dataviz` before drawing
the bars, `artifact-design` before writing the page.

## The executive overview

Five to eight bullets. Each one is a fact plus its consequence. The test: could
a PM who reads only these bullets decide what happens next?

Write:

- Lead with the go-ahead exactly as the gate states it (GO, GO WITH FIXES,
  NO-GO, NOT DECIDED) and what drives it. Then the WCAG line for the target.
  On a re-audit, the next bullet is the movement: what was fixed, what is still
  open, what is new this round, so progress is visible even when the gate has
  not moved.
- When the gate is GO at design stage, say so plainly: the design is done, the
  remaining minor findings are polish, and the next step is the build and the
  implementation audit. Do not invite another design iteration.
- Then the one or two systemic causes, the token, the component, the missing
  state that explains the largest cluster of findings. Systemic beats a list of
  symptoms.
- Then the cheapest high-value fix, with its count: "Six of the eleven contrast
  failures clear with one token swap."
- Then the biggest gap in coverage, stated as a risk, not as an apology.
- Then the honest limitation: what this phase could not test.

Do not write:

- Topic bullets. "Accessibility: several issues were found" says nothing.
- Counts with no consequence. "12 findings" is not an insight.
- Praise padding. "The design shows a strong visual foundation" earns its place
  only if something downstream depends on it.
- Hedged language on measured facts. A 3.1:1 ratio is a failure, not a
  "potential concern".
- Recommendations the report does not then support with a finding.

## Tone

Plain, specific, short sentences. Numbers with their thresholds. No adjectives
doing work that a measurement should do. Name components and tokens by their
real names. The reader is a colleague who has to fix this, not an audience being
sold a service.
