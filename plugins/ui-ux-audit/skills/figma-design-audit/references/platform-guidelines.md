# Platform thresholds

Grade against the **stricter** of WCAG and the platform guideline, and report
both numbers so the reader can see which rule bit.

## Target size

| Platform | Minimum | Notes |
|---|---|---|
| WCAG 2.2 SC 2.5.8 | 24×24 CSS px | Or <24px with ≥24px centre-to-centre spacing; inline text links exempt |
| iOS (HIG) | 44×44 pt | Applies to the tappable area, not the glyph. Hit-slop counts, so a 24pt icon with 10pt padding passes, the design must state the padding |
| Android (Material 3) | 48×48 dp | Recommends ≥8dp between adjacent targets |
| Web (pointer) | 44×44 px | Practical floor for touch-capable web |
| tvOS / Android TV | n/a | Focus-based: every focusable element needs a visible focus treatment with ≥3:1 contrast against both focused and unfocused neighbours |

The analyser emits two of these as separate findings: undersized target, and
insufficient spacing between adjacent targets. Proximity to a screen edge or a
system gesture area is a manual check, the metadata payload carries node frames
but not reliable screen bounds or platform inset values, so read it off the
screenshot rather than expecting a script finding.

## Type

| Platform | Body minimum | Notes |
|---|---|---|
| iOS | 17pt body, 11pt absolute floor | Must support Dynamic Type; check largest accessibility size (AX5, ≈310%) |
| Android | 14–16sp body | Must respect `fontScale` up to 200% (Android 14+ allows non-linear scaling) |
| Web | 16px body | Never set a fixed px size that blocks user zoom |

Line height ≥1.5× for body copy (WCAG 1.4.12), ≥1.2× for display. Line length
45–75 characters for sustained reading; flag >90.

## Layout and safe areas

- iOS: respect safe-area insets; nothing interactive within the home-indicator
  region or the Dynamic Island bounds.
- Android: account for the system gesture insets on the left/right edges and the
  navigation bar; edge-to-edge is the default from Android 15.
- Web: define behaviour at 320px CSS width and at 400% zoom (WCAG 1.4.10).
- Check a landscape and a large-tablet frame exist, or that the lock is justified.

## Motion

- Respect `prefers-reduced-motion` / Reduce Motion / Remove Animations. Every
  transition over ~200ms of movement needs a reduced variant.
- Transition durations: 200–300ms standard; >500ms feels broken on mobile.
- No parallax or auto-playing motion without a stop control.

## Platform idiom

Flag a design that fights the platform, as a usability finding rather than a
WCAG one: back-navigation that ignores the Android hardware/gesture back,
iOS-style pickers on Android, non-native pull-to-refresh, bottom sheets without
a drag handle, swipe actions with no visible affordance, and destructive actions
placed where the platform puts confirmatory ones.

## React Native specifics

- `accessible`, `accessibilityRole`, `accessibilityLabel`, `accessibilityState`,
  `accessibilityHint` must be spec'd per interactive component; the design hands
  these over in the component spec, not the developer's guesswork.
- `hitSlop` is how RN reaches the platform target minimum without changing
  visual size, the design should name the value.
- `allowFontScaling` must not be set false on body text; if a layout cannot
  survive scaling, the layout is the defect.
- Old vs New Architecture makes no accessibility difference, but Fabric changes
  measurement timing, note it as an implementation risk only.
