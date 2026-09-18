# UX heuristics, state coverage and edge cases

## Severity scale (Nielsen, used for UX findings)

| Score | Meaning | Maps to report severity |
|---|---|---|
| 4 | Usability catastrophe, must fix before release | Critical |
| 3 | Major problem, high priority | Serious |
| 2 | Minor problem, low priority | Moderate |
| 1 | Cosmetic, fix if time allows | Minor |
| 0 | Not a usability problem | Dropped |

The table is the starting point. The final rating is a function of three things,
and the report says which one drove it: **impact** (how badly the user is
blocked), **frequency** (how many users hit it, how often), **persistence** (can
the user learn around it, or does it bite every time).

Frequency moves a rating by at most one step, and only within the usability
dimension, it never moves a WCAG failure. So a cosmetic issue on the primary
CTA can rise from Minor to Moderate, and a Major problem in a setting almost
nobody opens can fall from Serious to Moderate. Frequency cannot turn a Minor
into a Serious, or a Level A failure into anything but Critical on a primary
path. State the adjustment and its reason in the finding.

## The ten heuristics, as design-file questions

1. **Visibility of system status**, does every async action have a loading,
   success and failure state in the file? Is progress shown in multi-step flows?
2. **Match with the real world**, labels in the user's vocabulary, not the
   database's. Flag internal jargon, enum names, and codes leaking into UI.
3. **User control and freedom**, cancel, undo, back, dismiss, and a way out of
   every modal. Destructive actions reversible or confirmed.
4. **Consistency and standards**, same action, same label, same icon, same
   position. Check across all screens in the audit set, not just one.
5. **Error prevention**, constrain input, disable impossible actions, format as
   the user types, warn before the irreversible.
6. **Recognition over recall**, don't make the user remember a value from a
   previous screen; show it. Flag any confirmation screen that hides what is
   being confirmed.
7. **Flexibility and efficiency**, shortcuts, defaults, remembered choices,
   bulk actions for power users without penalising novices.
8. **Aesthetic and minimalist design**, one primary action per view. Count
   competing primary buttons; more than one is a finding.
9. **Help users recognise, diagnose and recover from errors**, plain-language
   errors, next to the field, saying what to do.
10. **Help and documentation**, reachable, searchable, contextual. Consistent
    position (also WCAG 3.2.6).

## State coverage matrix

Every screen gets this grid. Use these row names verbatim in `state_matrix`, they are the canonical list in `audit-report/scripts/wcag22.py` and the report renders them in this order. Mark each cell **Present / Missing / N/A**, and
count Missing cells, a screen designed only in its happy state is the single
most common cause of ugly production UI.

| State | What to look for |
|---|---|
| Empty (first run) | Explains what goes here and how to add it, not just "No data" |
| Empty (filtered to nothing) | Distinct from first-run; offers to clear the filter |
| Loading: initial | Skeleton or spinner, layout does not jump when content lands |
| Loading: more / pagination | Distinct from initial; does not replace existing content |
| Partial / stale | Some sections loaded, some failed; cached-data indication |
| Error: network | Retry affordance, plain-language cause |
| Error: server | Distinguished from network; no raw codes in UI |
| Error: validation | Per-field, in text, with a fix suggestion |
| Error: permission denied | Explains what to do, links to settings |
| Offline | Explicit, and says what still works |
| Success / confirmation | Persistent enough to read; not a 1.5s toast for a critical action |
| Disabled | Reason given, ≥3:1 contrast if still perceivable-and-meaningful |
| Read-only | Visually distinct from disabled and from editable |
| Long content | Longest realistic string, not "Lorem ipsum" |
| Truncation | Where it truncates, and whether the full value is reachable |
| Zero / negative / very large numbers | 0, −1, 1,000,000, and currency edge cases |
| Localisation (long strings) | German (~35% longer), Arabic/Hebrew (RTL), CJK (line breaking, no spaces) |
| RTL mirroring | Layout, icons with direction, progress, back arrows |
| Largest font scale | iOS AX5, Android 200% |
| Dark mode | Every token resolved in the dark variable mode; contrast recomputed |
| High contrast | OS setting variant |
| Reduced motion | Static alternative for every transition |
| Rotation / split view | Landscape, iPad split, foldables |
| Small screen (320px) | 320px / iPhone SE height |
| Keyboard open | Does the focused input stay visible; does the CTA get covered |
| Slow network (3G) | Perceived performance, timeout copy |
| Interrupted | Backgrounded mid-flow, call received, app killed and relaunched |
| Session expired | Mid-form; is the user's input preserved |
| Rapid / double tap | Duplicate submission guard |
| Deep link entry | Screen entered directly with no back stack |

## Forms, the recurring offenders

- Placeholder used as the label (disappears on focus, fails 3.3.2, low contrast).
- Validation fired on every keystroke before the field is complete.
- Error summary at the top with no link to the field.
- Required marked only with a red asterisk and no key.
- Field order that does not match the physical document the user is copying from.
- No paste into OTP / card / password fields (fails 3.3.8).
- Submit button that neither disables nor shows progress → double submission.
- Keyboard type not specified per field (numeric, email, phone).
- Label and its field separated so a zoomed user cannot see both.

## Information hierarchy and cognitive load

- One primary action per view; secondary actions visually subordinate.
- Scan path follows the task order, not the data model.
- Group related fields; no more than ~7 items in an ungrouped list of choices.
- Reading grade ≈ 8 for consumer UI; flag sentences over ~25 words in UI copy.
- Numbers formatted for the locale, units always stated, no bare IDs.
- Don't make colour, position or size carry information that is not also in text.

## Visual craft, measurable, so measure it

- Spacing values off the design scale (e.g. a 13px gap in a 4px system).
- Hardcoded hex values where a token exists.
- Near-duplicate text styles (two 15px/500 styles with different line heights).
- Optical alignment failures: icons not centred to cap-height, mixed corner radii.
- Elevation/shadow inconsistency across the same component family.
- Contrast that passes in light mode and fails in dark, or the reverse.
