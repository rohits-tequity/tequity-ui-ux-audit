# Executive overview and rating panel

## The rating panel

Everything on the panel is read straight from `scorecard.json`. Nothing on it is
retyped or rounded by hand.

Layout, top to bottom:

1. **Overall grade**, the letter, the score out of 100, and the band label
   ("C: Needs work"). Grade is the headline; the number is the detail.
2. **Release recommendation**, one of "Releasable", "Release after clearing the
   listed fixes", "Do not release". This is the sentence the reader came for.
3. **Severity counts**, five chips: critical, serious, moderate, minor, info.
   Critical is visually loudest. A zero count still shows, as a zero.
4. **Dimension bars**, six horizontal bars, each labelled with its score and
   its weight, sorted worst first so the eye lands on the problem. Weight is
   shown because a 70 on a 30%-weight dimension matters more than a 70 on an 8%
   one.
5. **Coverage**: "34 of 50 applicable criteria evaluated (68%)" and "11 of 28
   states designed (39%)". Coverage sits next to the score, never inside it.
6. **Confidence**, the phase label and its caveat, e.g. "Provisional, design
   stage only".

Colour rules: use the band colour for the grade, severity colours for the chips,
and a single neutral hue for the bars with the band colour only at the fill.
Never rely on colour alone, every chip and bar carries its number as text, and
the grade carries its word label. The report must survive being printed in
greyscale and must pass its own contrast checks. Load `dataviz` before drawing
the bars, `artifact-design` before writing the page.

## The executive overview

Five to eight bullets. Each one is a fact plus its consequence. The test: could
a PM who reads only these bullets decide what happens next?

Write:

- Lead with the release decision and what drives it.
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
