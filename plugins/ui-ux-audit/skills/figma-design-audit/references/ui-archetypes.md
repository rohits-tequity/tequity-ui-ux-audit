# UI archetypes, what to check per screen type and user story

The generic checklist catches generic defects. The expensive defects are the
ones specific to what the screen is *for*. Before classifying, identify the
archetype from the user story (`user_story.ui_type`) and load that section. A
screen can be two archetypes at once (a payment form on a checkout).

The user story also sets the **primary path**. A finding on the primary path
is what turns `serious` into `critical` under the rubric, so establish the
path first, then rate.

## How to use the user story

Required fields, ask for what is missing:

- `persona`, including constraints that change the audit: font scale in use,
  one-handed, low bandwidth, screen reader, first-time vs returning.
- `goal`, one sentence, the user's words.
- `primary_path`, the ordered screens or steps to success.
- `success`, what the user sees when done.
- `ui_type`, from the list below.

The persona's constraints become mandatory matrix cells: a "font scale 130%"
persona makes *Largest font scale* a required state, not an optional one.

## Archetypes

### Authentication (sign-in, sign-up, OTP, biometrics)
- 3.3.8 Accessible Authentication: paste allowed into OTP and password fields;
  password-manager autofill works; no transcription puzzles without an
  alternative. This is the most-failed 2.2 criterion.
- 1.3.5: `autocomplete` / `textContentType` on every field.
- Error copy never says which of username or password was wrong (security) but
  does say what to do next (3.3.3).
- Show-password toggle present and labelled.
- Rate-limit and lockout states designed, with recovery path.
- Biometric fallback to PIN or password designed.
- Social-login buttons meet target size and have accessible names that include
  the provider.

### Onboarding / walkthrough
- Skip is visible on every step and is the same size as Next.
- Progress indication (2.2.1 does not apply, but Nielsen #1 does).
- Auto-advancing slides need pause (2.2.2).
- Permission primers explain *why* before the OS prompt; denial state designed.
- Illustration text is real text, not images of text (1.4.5).

### Forms (profile, address, KYC, settings-as-form)
- Persistent labels, not placeholders (3.3.2).
- Required-field convention stated once, not just an asterisk.
- Validation timing: on blur or submit, not on every keystroke.
- Inline error next to the field, in text, with a fix (3.3.1, 3.3.3).
- Keyboard type per field spec'd; return-key action spec'd.
- Field order matches the source document the user copies from.
- Redundant Entry (3.3.7): nothing asked twice across steps.
- Long-form: save-and-resume, session-expiry preservation.
- Address and name fields tolerate long and non-Latin input.

### Checkout / payment / transfer
- Review step shows every value being confirmed (Nielsen #6).
- Error Prevention (3.3.4): confirmation or undo on the irreversible action.
- Primary CTA is the only primary on the screen; disabled-until-valid with a
  reason, or enabled with clear errors, not silently disabled.
- Double-submission guard designed (in-flight state on the CTA).
- Amount formatting: locale, currency symbol, thousands separators, zero,
  maximum, negative (refund) handled.
- Failure states: declined, timeout, network, duplicate, each with a next step.
- Receipt / confirmation persists; reference number is selectable/copyable.
- Timer on OTP or session shown and extendable (2.2.1).
- Saved-card / biller pickers are lists with roles, not colour-coded tiles.

### List / feed / search results
- Empty first-run vs empty-after-filter are distinct states.
- Loading-more is distinct from initial loading and does not reset scroll.
- Row tap target is the whole row; nested actions do not overlap it.
- Item count or "results for" announced (4.1.3).
- Pull-to-refresh has an alternative (2.5.1); swipe actions have a visible
  alternative (2.5.7).
- Long titles: truncation rule and where the full value lives.
- Sort and filter controls announce their state.
- Skeletons match final layout to avoid shift.

### Detail / read view (article, product, transaction detail)
- Heading hierarchy real, not visual (1.3.1).
- Line length 45–75 characters; body ≥ platform minimum; line height ≥ 1.5.
- Images carry alt; decorative ones hidden.
- Sticky action bar does not obscure content or focus (2.4.11).
- Share / copy / save actions labelled, not icon-only.
- Reflow at 320px and 200%: no two-axis scroll (1.4.10).

### Dashboard / data / charts
- Every chart has a text alternative: table, summary, or both (1.1.1).
- Series distinguished by more than colour: pattern, shape, direct labels (1.4.1).
- Colour palette validated for the common colour-vision deficiencies.
- Numbers formatted with units and locale; no bare percentages without base.
- Stat tiles carry the comparison they imply (vs last period).
- Interactive tooltips are keyboard-reachable and dismissible (1.4.13).
- Live-updating values do not steal focus or announce constantly (4.1.3, 2.2.2).
- Load `dataviz` for the chart-specific rules.

### Settings / preferences
- Toggle state exposed as text and role (4.1.2); on/off not colour-only.
- Destructive settings (delete account, sign out everywhere) confirmed (3.3.4).
- Grouping and headings real (1.3.1).
- Changes saved-on-toggle vs on-Save made explicit (Nielsen #1).
- Search within settings for long lists (Nielsen #7).

### Chat / messaging / support
- New-message announcement without hijacking focus (4.1.3).
- Message bubbles: sender identity in text, not only alignment/colour (1.4.1).
- Timestamps and status (sent/delivered/read) as text.
- Composer: send button ≥ target minimum, attach button labelled, keyboard
  covers nothing essential.
- Long messages wrap; links distinguishable by more than colour.
- Typing and connection status designed.

### Media / player
- Captions, transcript, audio description slots (1.2.x).
- Controls meet target size; scrubber has a non-drag alternative (2.5.7).
- Auto-play has a pause and starts muted (1.4.2, 2.2.2).
- Full-screen and rotation handled; controls remain reachable.
- Playback speed and skip controls labelled with the value.

### Maps / location
- Every map has a list alternative (1.1.1, 2.1.1).
- Markers distinguished by shape or label, not colour only.
- Pinch-zoom has button alternatives (2.5.1); drag-to-pan has an alternative (2.5.7).
- Location-permission denied state designed.

### TV / large-screen (tvOS, Android TV, Fire TV)
- Every focusable element has a visible focus treatment ≥ 3:1 against both its
  own unfocused state and neighbours (1.4.11).
- Focus order follows the D-pad expectation: horizontal rails, vertical stacks.
- Text ≥ 24pt at 10-foot distance; safe-area margins ≥ 5%.
- No hover-only affordances (there is no pointer).

### Web-specific (any archetype on web)
- Skip link, landmarks, page title (2.4.1, 2.4.2).
- Focus visible on every interactive element; no `outline:none` without
  replacement (2.4.7).
- Reflow at 320px and 400% zoom (1.4.10).
- Load `modern-web-guidance` before judging CSS or DOM patterns.

## Anti-pattern by archetype (quick triage)

| Archetype | Most common failure seen in audits |
|---|---|
| Auth | OTP field blocks paste; error says "invalid credentials" with no next step |
| Onboarding | Skip hidden or tiny; auto-advance with no pause |
| Forms | Placeholder as label; validation on keystroke |
| Checkout | Two primary CTAs; no in-flight state; no decline state |
| List | One empty state for two situations; swipe with no alternative |
| Detail | Sticky bar covers last paragraph; visual headings only |
| Dashboard | Colour-only series; charts with no text alternative |
| Settings | Toggle state by colour only; destructive with no confirm |
| Chat | Sender by colour; new-message steals focus |
| Media | Auto-play with sound; drag-only scrubber |
| Maps | No list alternative; pinch-only zoom |
| TV | Invisible focus; hover-only affordances carried from web |
