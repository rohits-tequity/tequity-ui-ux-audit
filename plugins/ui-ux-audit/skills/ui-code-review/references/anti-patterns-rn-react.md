# UI anti-pattern library

Each entry: what to search for, why it fails, the fix. Grep first, then read the
surrounding code before reporting, a wrapper component may already handle it.

Severity column is a starting point; adjust for reach and position on the primary
path.

## Accessibility: React Native

| Pattern to search | Why it fails | Fix | Sev |
|---|---|---|---|
| `Touchable\|Pressable` with no `accessibilityRole` | Announced as a plain view; assistive tech cannot tell it is actionable | Add `accessibilityRole="button"` (or `link`, `tab`, `switch`) | serious |
| Icon-only `Pressable` with no `accessibilityLabel` | Announced as nothing, or as the glyph's font codepoint | Add `accessibilityLabel`; SC 4.1.2 | serious |
| `accessibilityLabel` that does not contain the visible text | Voice Control users say the visible word and nothing happens | Label must contain the visible label; SC 2.5.3 | serious |
| Custom toggle/checkbox with no `accessibilityState` | State changes are silent | `accessibilityState={{checked, disabled, selected, expanded}}` | serious |
| `allowFontScaling={false}` on body text | Blocks the user's own font size; SC 1.4.4 | Remove it and fix the layout that needed it | serious |
| Fixed `height` on a container wrapping `<Text>` | Clips at larger font scales | `minHeight` plus flex, or let content drive height | serious |
| `numberOfLines` on the only copy of a value with no way to see the full text | Information becomes unreachable | Expandable, tooltip, or detail screen | moderate |
| `<Image>` with no `accessibilityLabel` and no `accessibilityElementsHidden` | Either unannounced content or noise for screen readers | Label it, or mark it decorative | serious |
| `accessible={true}` on a container with several interactive children | Collapses them into one target | Group only non-interactive content | serious |
| `importantForAccessibility` / `accessibilityElementsHidden` on a visible interactive subtree | Makes working controls invisible to assistive tech | Scope it to decoration only | critical |
| Modal/sheet with no focus management and no `accessibilityViewIsModal` | Focus stays behind the overlay; SC 2.4.3 | Set it on iOS, manage focus on Android | serious |
| Toast/inline validation with no `accessibilityLiveRegion` / `AccessibilityInfo.announceForAccessibility` | Status changes never announced; SC 4.1.3 | Add a live region | serious |
| `activeOpacity` as the only press feedback | No feedback for non-sighted or low-vision users | Add a state change, haptic or label | minor |

## Accessibility: React / web

| Pattern | Why it fails | Fix | Sev |
|---|---|---|---|
| `<div onClick>` / `<span onClick>` | Not focusable, not keyboard-operable, no role; SC 2.1.1 | Use `<button>`; if impossible, add `role`, `tabIndex={0}` and key handlers | critical |
| `outline: none` / `outline: 0` with no replacement | Removes the focus indicator; SC 2.4.7 | `:focus-visible` style with ≥3:1 contrast | serious |
| `tabIndex` greater than 0 | Breaks the natural tab order | Reorder the DOM instead | serious |
| `aria-label` on a non-interactive, non-landmark element | Silently ignored | Remove, or give the element a role | minor |
| `alt=""` on meaningful images, or missing `alt` | SC 1.1.1 | Real alt text; empty only for decoration | serious |
| Placeholder used instead of `<label>` | Disappears on input, fails SC 3.3.2, usually fails contrast too | Persistent visible label bound with `htmlFor` | serious |
| Error rendered as a red border or colour change only | SC 1.4.1 and 3.3.1 | Error text next to the field, plus an icon | serious |
| Heading levels skipped, or `<h1>` used for styling | SC 1.3.1 | Correct level, style with CSS | moderate |
| `user-scalable=no` / `maximum-scale=1` in the viewport meta | Blocks zoom; SC 1.4.4 | Remove | serious |
| `aria-hidden="true"` on a focusable element | A focus stop that announces nothing | Also remove it from the tab order, or unhide it | serious |
| Custom control with no keyboard handler (Esc, arrows, Enter/Space) | Fails the WAI-ARIA pattern for its role | Implement the APG pattern for that widget | serious |
| `dialog` without focus trap and return-focus | SC 2.4.3, 2.1.2 | Trap focus, restore on close | serious |

## Target size and hit area

| Pattern | Why it fails | Fix | Sev |
|---|---|---|---|
| Icon button sized to the glyph (e.g. `width: 20`) with no padding or `hitSlop` | Under 44pt / 48dp / 24px | `hitSlop`, or padding on the pressable | serious |
| Adjacent small pressables with no gap | SC 2.5.8 spacing exception fails too | ≥24px centre-to-centre, or enlarge | serious |
| Close button in a corner inside the safe-area inset | Physically hard to hit | Respect safe-area insets | moderate |
| Whole-row press plus a nested action with overlapping bounds | Mis-taps, ambiguous target | Separate the bounds, or drop one | moderate |

## Motion and animation

| Pattern | Why it fails | Fix | Sev |
|---|---|---|---|
| Animation with no `prefers-reduced-motion` / `AccessibilityInfo.isReduceMotionEnabled` branch | Triggers vestibular symptoms; SC 2.3.3 | Static or minimal-motion variant | moderate |
| Auto-playing carousel with no pause | SC 2.2.2 | Pause/stop control | serious |
| Transition over ~500ms on a routine interaction | Feels broken | 200–300ms | minor |
| Animating `width`/`height`/`top`/`left` on web | Layout thrash, dropped frames | Transform and opacity only | moderate |
| `useNativeDriver: false` on a transform animation | Runs on the JS thread and stutters | `useNativeDriver: true`, or Reanimated worklets | moderate |

## State completeness

| Pattern | Why it fails | Fix | Sev |
|---|---|---|---|
| Data fetch with no error branch in render | Blank screen on failure | Error state with retry | serious |
| `isLoading` with no skeleton, or a skeleton whose shape differs from the content | Layout jump | Match the loaded layout | moderate |
| `data.length === 0` with no empty state, or one that only says "No data" | Dead end for a new user | Explain and offer the next action | moderate |
| Submit handler with no in-flight guard | Double submission | Disable plus progress, and idempotency server-side | serious |
| `catch {}` swallowing an error | Silent failure; the user sees nothing | Surface it, log it | serious |
| Raw error object, status code or stack rendered in the UI | Unusable and leaks internals | Mapped, plain-language message | moderate |
| No offline branch where a network call is central | Confusing failure | Offline state, cached view | moderate |

## Performance

| Pattern | Why it fails | Fix | Sev |
|---|---|---|---|
| `.map()` over a long list instead of `FlatList` / `FlashList` / virtualization | Mounts everything; slow first render and memory growth | Virtualize | serious |
| Inline arrow or object prop on a list item (`renderItem={() => ...}`, `style={{...}}`) | New identity every render breaks memoisation | `useCallback`, hoist styles | moderate |
| `FlatList` with no `keyExtractor`, or index as key | Remount churn and lost state | Stable ids | moderate |
| Context holding a frequently-changing value consumed widely | Re-renders the whole subtree | Split the context, or a selector store | serious |
| Heavy work in render, or `JSON.parse`/`.sort()` per render | Blocks the JS thread | `useMemo`, or move it off render | moderate |
| Full-resolution remote images into a small thumbnail | Bandwidth and decode cost | Server-side resize, correct `resizeMode`, caching | moderate |
| Web: no `width`/`height` or `aspect-ratio` on images | Layout shift (CLS) | Reserve the space | moderate |
| Web: render-blocking font with no `font-display` | Invisible text on first paint | `font-display: swap`, preload | moderate |
| `useEffect` with a missing or over-wide dependency array driving a fetch | Fetch loops and flicker | Fix the deps; use a query library | serious |
| Animation state in React state rather than a shared value | A re-render per frame | Reanimated shared values, or CSS | moderate |

## Design-system conformance

| Pattern | Why it fails | Fix | Sev |
|---|---|---|---|
| Hex, rgb or named colour literal in a component | Bypasses theming; breaks dark mode | Theme token | minor |
| Off-scale spacing number (`padding: 13`) | Visual drift | Nearest scale step | minor |
| Local reimplementation of a component the library already has | Divergent behaviour and a11y regressions | Import the library component | moderate |
| `Dimensions.get('window')` for layout instead of flex or `useWindowDimensions` | Wrong after rotation, split view and foldables | Responsive layout | moderate |
| Platform-forked UI where the library already abstracts it | Two code paths to keep accessible | Use the abstraction | minor |
| Font size or family set directly rather than via a text style | Type-scale drift, breaks scaling | Typography token | minor |

## Notes on using this list

- These are pattern prompts, not verdicts. Every finding needs a file, a line
  and a read of the surrounding context.
- When something on this list is genuinely correct in context, say nothing. A
  reviewer that reports known-good code stops being read.
- When a concern cannot be settled from source, actual rendered size, actual
  frame drops, actual announcement, route it to the implementation audit with
  `requires` set rather than asserting it.
