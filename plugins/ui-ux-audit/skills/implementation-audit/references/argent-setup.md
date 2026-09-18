# Argent setup and constraints

Argent is an agentic toolkit from Software Mansion that exposes a running app to
an agent over MCP: simulator/emulator control, accessibility and DOM trees,
React and native debugging, profiling, screenshots and visual diffing, plus
recordable YAML flows. ~76 tools.

## Install

```bash
npx @swmansion/argent init      # writes MCP config + skills + rules into the workspace
```

`init --global` (default) puts `argent` on PATH; `init --local` commits a
devDependency so the whole team gets it on `npm install`. Restart the editor or
app afterwards so the MCP server is picked up.

MCP entry (what this plugin ships in `.mcp.json`):

```json
{ "mcpServers": { "argent": { "command": "argent", "args": ["mcp"] } } }
```

Useful CLI outside MCP: `argent tools` lists every tool,
`argent tools describe <name>` prints its flags, `argent run <tool>` invokes one,
`argent server status|stop|start --detach` manages the shared tool-server.

## Hard requirements

- Node ≥ 20.12.
- **iOS / tvOS: macOS with Xcode.** There is no way around this, no container,
  no Linux VM, no file bridge substitutes for it.
- Android: Android SDK platform-tools (`adb`) plus an emulator image, or a
  physical device over adb. On Linux: KVM, SwiftShader GPU, 8 GB+ AVDs.
- Chromium / Electron: launch the app with `--remote-debugging-port`.
- React component tree, `debugger-evaluate` and the React profiler need a
  **development build with Metro running**. Expo Go cannot do native profiling.
- Boot the device through `boot-device` rather than manually, or system dialogs
  may be invisible to `describe`.

## Where it can and cannot run

| Environment | Works? |
|---|---|
| Developer's own macOS with Xcode | Yes, the reference setup |
| Developer's Linux/Windows with Android SDK | Yes, Android and Chromium only |
| Cloud container / remote agent sandbox | **No**, no simulator, no emulator |
| Claude's local Linux VM over a folder bridge | **No**, that VM is not the Mac and has no Xcode |
| macOS CI runner | Yes, with Xcode and a booted simulator |

So a cloud-hosted session can run the Figma design audit end to end, but the
implementation audit must run where the device is. Say this before the user
expects otherwise.

## Coordinate spaces, the recurring mistake

- `describe` frames and all gesture coordinates are **normalised [0,1]**
  fractions of the screen, not pixels. Tap centre =
  `x + width/2`, `y + height/2`.
- To judge target size against 44pt / 48dp you need point-space, so either
  convert using the screen dimensions or use `native-describe-screen`, which
  returns raw point-space frames directly (iOS simulator only).
- `screenshot` defaults to **scale 0.25** for iOS/Android. Any pixel measurement
  needs `--scale 1.0`, and pass `--includeImageInContext false` when saving a
  baseline so the bytes do not flood context.
- `describe` carries no z-order, so an element listed at a point may be covered.
  Confirm with a screenshot before calling a tap failure a layout bug.

## Other notes

- Telemetry is on by default: `argent telemetry disable` to opt out. Say this to
  the user before a client project.
- Licence: Apache 2.0 source, with some proprietary per-platform binaries
  (`simulator-server`, `ax-service`, the iOS native-devtools dylibs) restricted
  to use within the project.
- Argent ships its own skills (`argent-test-ui-flow`, `argent-screenshot-diff`,
  `argent-ios-simulator-setup`, `argent-android-emulator-setup`,
  `argent-device-interact`, `argent-qa-flows`, `argent-create-flow`,
  `argent-react-native-profiler`, and more). Prefer them for device mechanics
  rather than reimplementing setup here, this plugin's job is the audit
  judgement and the report, not device plumbing.
- `native-describe-screen` returns statuses rather than failures:
  `restart_required` → restart the app; `service_stale` → restart the
  tool-server; `connect_pending` → wait and retry; `init_failed` → reboot the
  simulator. Do not loop on retries.
