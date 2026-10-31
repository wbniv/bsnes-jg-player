# Native iOS player integration

**Status:** Bootstrap implementation in progress (2026-10-31). The user reports **37 free Codemagic minutes remaining** and authorized starting iOS work. `ios/` now contains a CMake-generated Xcode app, a narrow single-instance native adapter, compiled ARM64 libco switch, Metal rendering, touch controls, lifecycle scheduling, and a simulator ROM self-check. `codemagic.yaml` limits each manual M2 run to 15 minutes, leaving room for one corrective run within the reported budget. No simulator success is claimed until a run receipt is recorded.

### Bootstrap scope adjustment

Prioritize Apple compilation and the configured 500-frame Raycaster fidelity check before the broad Android directory rename. Android remains at `android-tv/` for this bootstrap. The first shell is UIKit/Objective-C++ to exercise the native bridge directly; SwiftUI composition, audio output, GameController, physical iPhone signing/testing, and the full orientation/lifecycle test matrix remain open. The UI explicitly labels audio as unimplemented. The adapter deliberately overlaps the small Android callback boundary until Apple execution is proven; it does not claim a reusable multi-instance API.

The Apple ARM64 libco backend uses the upstream context layout and instruction sequence in a compiled `.S` file. It does not execute a data buffer or change page protections. Only ARM64 iOS/simulator builds are supported initially. The stock backend remains in the Linux smoke build.

Local adapter verification: `python3 ios/prepare.py`, then `cmake -S ios -B /tmp/bjg-ios-host-build -DCMAKE_BUILD_TYPE=Release`, `cmake --build /tmp/bjg-ios-host-build -j 4`, and `/tmp/bjg-ios-host-build/core-smoke ios/generated/demo.sfc ios/generated/bsnes-2.1.0/Database`.

Apple build commands and artifact paths are in `codemagic.yaml`; `ios/simulator-check.py` boots an available iPhone (preferring iPhone 16), requires a JSON self-check PASS, and captures the app. The `.xcresult` currently records the **build**, not an XCTest suite. Retained proof includes the ROM self-check JSON, simulator identity, build log, simulator `.app` ZIP, and screenshot. Simulator artifacts cannot be installed on a physical iPhone.

## Goal

Add an iPhone-first, native iOS example host for the same compact Raycaster Maze ROM used by the standalone Android Native player. Reuse the vendored bsnes-jg C++ core and keep the browser integration on WebAssembly. This demonstrates a third host integration without turning the full torture-test suite into an iOS app or making the browser package depend on Apple frameworks.

The first deliverable is a development-signed app that runs on an iOS Simulator and one physical iPhone, with native rendering, touch input, lifecycle pause/resume, and a reproducible ROM fidelity check. iPad layout should adapt from the same app target. App Store distribution and a full ROM library are not part of this first milestone.

## Repository layout decision

Use sibling platform directories:

```text
android/             # existing Android/Google TV example project (rename from android-tv/)
ios/                 # new SwiftUI iOS example app and Xcode project
native/              # shared platform-neutral C/C++ host adapter, if extraction proves useful
web/                 # WebAssembly player and ROM examples
vendor/bsnes-jg/     # pinned emulator core
```

`android-tv/` is no longer an accurate directory name: this project builds both Pixel phone and Google TV apps. Rename it to `android/` as a separate, mechanical preparatory change before creating the iOS project. Update all repository path references, build scripts, Gradle paths, Taskfile namespace, documentation, CI, and coordinator examples in that change. Prefer `task android:build` and `task android:release-build`; preserve old task aliases briefly if they help existing scripts. Do not combine the path move with emulator or UI behavior changes.

## Existing implementation and reuse boundary

- `vendor/bsnes-jg/` is the pinned C++ core. Android's CMake build already compiles these same core sources.
- `android-tv/app/src/main/cpp/jni.cpp` owns the Android integration today. It depends on `AAssetManager`, `JNIEnv`, and Android logging; those parts cannot be compiled for iOS unchanged.
- `NativeEngine.java` and `MainActivity.java` show the current Native Android frame, controller, ROM, and lifecycle contract. They are example-host code, not the iOS API.
- `demo-rom.json` names the selected standalone demo, supplies its SHA-256 and self-check, and should remain the single source of truth for the iOS sample ROM.
- The current Android host discards audio. The iOS player should provide real output through `AVAudioEngine` (or a reviewed low-latency Audio Unit path), rather than silently copying that limitation.

Before introducing `native/`, compare the current Android JNI adapter with `web/src/main.cpp` and the proposed Native Android upstream extraction. Prefer one small platform-neutral C ABI over a second independent implementation of core callbacks. Keep Android asset access/JNI and iOS bundle access/Objective-C++ in thin platform wrappers. If a shared context API requires broad changes to the global core, defer that refactor and first document the single-instance constraint instead of expanding scope.

Proposed host boundary:

```c
typedef struct bjg_host bjg_host;
bjg_host *bjg_create(const struct bjg_callbacks *callbacks);
int       bjg_load_rom(bjg_host *, const uint8_t *rom, size_t size);
void      bjg_run_frame(bjg_host *);
void      bjg_set_buttons(bjg_host *, uint16_t mask);
void      bjg_reset(bjg_host *);
int       bjg_video_info(bjg_host *, struct bjg_video_info *out);
int       bjg_copy_rgba(bjg_host *, uint8_t *dst, size_t capacity);
void      bjg_destroy(bjg_host *);
```

This is a design sketch, not a committed API. Choose concrete types after checking core callback lifetimes and buffer ownership. Keep errors explicit; do not expose private bsnes-jg structs across the ABI. Document thread ownership and whether the underlying core permits more than one active instance.

## App design

- **SwiftUI host:** app lifecycle, status/error states, accessible buttons, safe areas, orientation adaptation, and settings/help shell.
- **Objective-C++ bridge:** a small `.mm` wrapper calls the C ABI and converts Swift-friendly data types; it contains no screen layout or ROM selection policy.
- **Video:** use `MTKView` and a Metal texture updated from the latest core frame. Avoid a SwiftUI `Image` allocation per emulated frame. Preserve the full SNES picture and its traditional 4:3 display presentation; do not size it as the erroneous 8:7 sample grid.
- **Timing:** drive presentation with `CADisplayLink`, but step the emulator against monotonic elapsed time at the core's SNES frame rate (60.0988 Hz), not one core frame per display callback. Bound catch-up work and reset elapsed-time credit on pause/resume. Test 60 Hz and 120 Hz displays/simulators.
- **Audio:** send core PCM through a bounded, nonblocking ring buffer to an audio render callback. Do not allocate, lock, or call SwiftUI from the real-time audio callback. Verify sample rate/channel format and teardown ordering.
- **Input:** provide a large, optional touch D-pad and A/B/Start/Select controls; also support `GameController.framework` controllers with the same button mapping. Touch controls should respect safe areas and never cover the active SNES picture.
- **Lifecycle:** pause frame scheduling and audio when inactive/backgrounded; resume only after the view is active and buffers are valid. Teardown must stop callbacks before destroying core state.
- **Demo ROM:** bundle only the 32 KiB `raycaster.sfc` chosen through `demo-rom.json`; verify its configured SHA-256 at build/staging time. Keep slug/title/hash configurable so another small ROM can replace it without UI rewrites.
- **Distribution:** start with simulator artifacts and locally installable development-signed builds. TestFlight/App Store signing, provisioning, privacy declarations, and public listing are a later explicit release gate; store credentials only in Codemagic secure integrations, never in Git or chat.

## Codemagic build plan and expiring minutes

No `codemagic.yaml` or Xcode project exists in the repo at this plan's writing. The user has authorized Codemagic use and reports 219 build minutes expiring at **00:00 UTC, 2026-10-31**. Do not spend that budget on speculative parallel pipelines.

1. Immediately confirm this GitHub repository is connected to the intended Codemagic app/team and that the remaining minutes are visible there. Confirm the account's macOS/Xcode machine availability and workflow trigger method.
2. Add a minimal `codemagic.yaml` with one `ios-simulator` workflow. Pin a supported Xcode version explicitly. It should run the project build and unit tests for a named iPhone Simulator destination, without signing, then retain the `.xcresult` and build log as artifacts.
3. Push the skeleton as soon as it opens in Xcode; start the first Codemagic run before the minute expiry. Treat the first run as a toolchain/project validation, not as proof that gameplay works.
4. Keep a reserve for one corrective build. Avoid repetitive clean builds; use Codemagic's dependency/build caches after the first successful run.
5. If account/repository integration or macOS runner setup cannot be completed before expiry, record the exact blocker and use local Apple hardware later. Do not claim that minutes were used or that CI passed without a successful run receipt.

## Work sequence

1. **Platform naming cleanup:** rename `android-tv/` to `android/` in an isolated commit; update Taskfile task names, documentation, scripts, CI, and path references. Build the Android examples once to prove the move is mechanical.
2. **Codemagic bootstrap:** verify access and create the smallest simulator-only workflow early, as described above.
3. **Core portability audit:** identify Android-only dependencies, core global-state assumptions, audio/video/input callback ownership, and the minimum ROM database assets required by Raycaster Maze.
4. **Shared adapter decision:** extract only the stable frame/input/video/audio/ROM callback boundary if Android and iOS can both use it without forcing a broad core rewrite. Otherwise keep a narrow Objective-C++ adapter and document any deliberate overlap with JNI.
5. **iOS app shell:** add SwiftUI target, bundle the selected demo ROM with a generated hash manifest, and render a static frame before adding real-time scheduling.
6. **Playback:** implement core lifecycle, scheduler, Metal presentation, PCM audio, touch controls, and GameController mapping in small reviewable steps.
7. **Fidelity and UI proof:** run the configured `demo-rom.json` self-check on the simulator and physical iPhone; capture portrait, landscape, pause/resume, and controller evidence. Confirm iPad adapts without clipping or stretching.
8. **Documentation and release decision:** document build/run steps and known limits. Decide whether the shared native adapter should be proposed upstream alongside the Android integration; do not submit or publish without review.

```mermaid
flowchart TD
  A[Rename android-tv to android; update paths] --> B[Confirm Codemagic connection and expiring budget]
  B --> C[Push minimal Xcode project and simulator workflow]
  C --> D[Build shared core boundary or narrow Obj-C++ adapter]
  D --> E[SwiftUI shell and bundled Raycaster ROM]
  E --> F[Metal video, accurate timing, touch and controller input]
  F --> G[PCM audio and background lifecycle]
  G --> H[Simulator self-check and CI artifact]
  H --> I[Physical iPhone and iPad layout proof]
  I --> J[Review upstream and distribution options]
```

## Acceptance criteria

- Android build commands and APK variants still work after the directory rename; repository search finds no stale executable path references to `android-tv/` (historical plans may retain their original context with a short note).
- Codemagic builds the simulator target and runs the automated tests from the pushed commit; logs and `.xcresult` are retained.
- The iOS app loads only the configured small ROM, passes its self-check, and renders continuously without blocking the UI or audio render thread.
- Video uses the correct 4:3 full-picture presentation with no crop/stretch; timing remains stable on 60 Hz and 120 Hz refresh.
- Touch controls and a connected GameController operate the same SNES button mapping; accessibility labels and visible focus/pressed states are present.
- Backgrounding pauses emulation/audio; foregrounding resumes without duplicate scheduler/audio callbacks or a stuck core.
- Portrait and landscape iPhone screenshots plus iPad layout evidence show no clipped controls, unreadable text, or hidden game picture.
- ROM/core provenance and license notices are included. No signing key or profile is committed.
- No App Store/TestFlight release is claimed until signing, distribution, and release checks are deliberately completed.

## Risks and deferred decisions

- The Android frontend relies on bsnes-jg global state. A reusable multi-instance C API may take more work than a thin iOS bridge; constrain the first app to one emulator instance.
- Metal texture upload and audio-ring behavior need measurement on physical hardware; simulator success alone is not performance proof.
- Codemagic's current Xcode image, workflow availability, account link, and minute counter must be checked in the account; no repo config proves those settings.
- Public iOS distribution requires Apple Developer signing/provisioning and account setup. Those credentials are outside the repo and are not part of simulator CI.
- Upstream ownership for the cross-platform native adapter is unresolved. Keep the web package and browser WASM product in this fork; coordinate the Android/iOS adapter proposal with the core maintainer before submission.
- tvOS, full 152-ROM catalog, save states, import-any-ROM UX, cloud saves, and App Store submission are outside this first iOS example.
