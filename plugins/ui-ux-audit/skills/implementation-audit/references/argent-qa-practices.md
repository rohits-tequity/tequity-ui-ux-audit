# Argent RN App Audit: NEW QA Practices (Not in existing references)

## Element Discovery Priority & Fallbacks
- **Tree priority**: `describe` → `debugger-component-tree` → `native-describe-screen` → `screenshot`
- **describe** auto-detects system dialogs, returns button coordinates; fallback to screenshot only if unreliable
- **React Native**: Use `debugger-component-tree` (component names, testIDs, tap coords); requires Metro + `adb reverse tcp:8081` on Android
- **Chromium**: Read references/chromium.md for tabs/cookies/storage differences
- **Physical iPhones**: Reject Metro tools; flow tree is `describe` tree (no UIView hierarchy)

## Metro Configuration & Workflow Discovery
- **Mandatory first**: Read `package.json` scripts for custom start/build; defer to them over defaults
- **Save workflows to memory** to avoid re-discovery
- **debugger-status**: `connected` or `no_app_connected` = Metro up; `metro_not_running` = unreachable
- **debugger-reload-metro** for JS-only changes (no rebuild); distinct from `restart-app` (native/pod)
- **lsof -i :PORT** before starting Metro to catch conflicts

## Screenshot & Visual Diff Discipline
- **Baseline capture**: `screenshot { scale: 1.0, includeImageInContext: false }` for baseline/current PNG only
- **screenshot-diff parameters**: Exactly one baseline input (baselinePath XOR captureBaseline) + exactly one current (currentPath XOR captureCurrent)
- **Baselines per device**: Different model/orientation/resolution need separate baseline
- **Physical iPhone diffs** supported (full resolution, device-wide); rotation parameter ignored
- **Seed determinism** (freeze clock, fix data, disable animation) or diff is noise

## Screen Readiness & Waiting
- **await-screen-idle**: Live diagnosis only; block until non-empty tree stops changing
- **Flows use `await: { idle: true }`** which also compares pixels (six possible warnings)
- **await-ui-element false pass**: Note says selector never matched; treat as failed, fix selector
- **Never poll screenshot/describe in loop**: Use `await-ui-element` (blocks server-side on tree)

## Coordinates & Interaction Mechanics
- **Normalized 0.0–1.0** coordinates for all gesture tools
- **Point-space measurement** for 44pt/48dp: convert via screen dims or use `native-describe-screen`
- **Coordinate fallback gate**: Resolve raw-point warnings immediately; keep coordinates only for genuinely unlabeled targets
- **gesture-swipe momentum**: Default true (fling); `momentum: false` requires durationMs ≥ 150ms
- **gesture-scroll** (Chromium only): Wheel-based; positive deltaY = down
- **Long-press context menus** use `gesture-custom` with 800ms hold
- **run-sequence** when later steps do NOT depend on prior results (allows gesture-*, button, keyboard, paste, rotate, shake, tv-remote, await-ui-element)
- **Secrets placeholder** `{{secret:NAME}}` in keyboard/paste (server-resolved, never in context)

## Tool Deferred Loading
- **Gesture tools deferred** (gesture-tap, gesture-swipe, gesture-pinch, gesture-rotate, gesture-custom): Batch ToolSearch load before calling
- **Unified tool dispatch via udid shape**: UUID → iOS sim; chromium-cdp-<port> → Chromium; other → Android serial

## Permissions Decision Tree
- **In-app toggle** → tap it. **System dialog on screen** → answer it (describe exposes). **settings-permissions** only for pre-launch or re-enable after denial
- **Pre-launch deny suppresses prompt iOS only** (TCC denial); Android deny clears grant but still shows dialog
- **Changing permission can terminate app**: Pre-set before `launch-app`; if running, `restart-app` after
- **grant location iOS** needs app pre-installed (pre-install grant records nothing)

## Performance Profiling Phases
- **Measure first** with target metric + threshold; fix top offender; re-measure honestly
- **Quick scan**: `react-profiler-renders` (live render count table)
- **Deep measure**: start → interact → stop → analyze cycle
- **Inspect**: `react-profiler-component-source` + `react-profiler-fiber-tree`
- **React Compiler awareness**: If `reactCompilerEnabled: true`, do NOT propose useCallback/useMemo/React.memo unless confirmed bail-out (check for absent useMemoCache in fiber-tree)
- **One fix per cycle** (architectural); mechanical batch fixes ok, re-profile once after batch
- **Record flow before first run** if measurement involves device interaction
- **Phase sequence**: Lint (deterministic) → Semantic (judgment) → Baseline profile → Regression verify
- **Sub-agent dispatch**: Lint/semantic per-file/item ok; profiling + E2E stays main agent only

## QA Flow Contract & Proof Discipline
- **Test contract table first** (before touching app): app/platform/start, actions, outcomes, stable evidence
- **Definition of done (6 items)**: (1) First non-echo/script is `launch:`. (2) Walkthrough recorded all actions + live checks (three polish insertions unrecorded). (3) Every requirement = hard await:/assert:/snapshot:. (4) Every screen change = destination identity + idle readiness. (5) Stable-selector rules; coordinates only unlabeled. (6) Unchanged YAML passes twice, same runner, same fresh services.
- **Three unrecorded insertions**: planned `snapshot:`, navigation `await: { idle: true }`, Chromium `launch:`
- **Stable selectors** fixed by code, survive data/time/locale (prefer strict id > text/a11y; no dynamic values)
- **Proof cycle**: Fresh services with `stop-all-simulator-servers --devices [<device>]` (scoped, never bare); streak = two consecutive passes

## Visual Evidence Classification
- **Visual** (layout, spacing, color, typography, image, clipping): Use `screenshot-diff`
- **Structural** (navigation, element existence, a11y, selection, hierarchy): Use `describe`, `debugger-component-tree`, `native-describe-screen`
- **Runtime/logs/network**: Use `view-network-logs`, `debugger-log-registry`, `debugger-evaluate`
- **Collection absence**: Viewport absence ≠ global; use fixed position, count, empty state, collection-wide evidence

## Critical "Do Not" Rules
- Do NOT derive tap targets from screenshot pixels (use tree first)
- Do NOT navigate by tapping home-screen icons (use `launch-app` / `open-url`)
- Do NOT poll screenshot/describe in loop (use `await-ui-element`)
- Do NOT use DevMenu by default (use argent tools)
- Do NOT record `await-screen-idle` in flows (flows use `await: { idle: true }`)
- Do NOT combine capture flags on same side
- Do NOT put acceptance evidence inside `when:` (use only for optional setup)

**9 high-impact NEW areas for implementation-audit skill**
1. Metro config discovery + debugger-reload-metro (vs restart-app)
2. Element tree priority + conditional fallbacks
3. QA flow contract table + 6-item definition of done
4. Profiling phases + React Compiler bailout check
5. Proof cycle with scoped fresh services + streak
6. Visual evidence classification (visual/structural/runtime/mixed)
7. screenshot-diff parameters + baseline per device
8. Stable selectors + coordinate fallback gate
9. Gesture mechanics + deferred tool loading
