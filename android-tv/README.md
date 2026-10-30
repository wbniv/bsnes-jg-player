# LLVM 65816 Torture Test Suite on SNES

The reusable player integration is the project product, including the browser WebAssembly player. The Android APKs are example host integrations, not the product SDK. Android WASM is retained for controlled engine comparison, but offers no Android integration advantage: it is less efficient than the Native adapter and too slow on Chromecast. Use the browser WebAssembly integration for web pages and the Native JNI/C++ adapter for Android hosts. Both Android Phase 2 variants use the same D-pad-friendly selector, 152-ROM catalog, card screenshots, pause menu, and control/lifecycle contract. Catalog, screenshots, and ROM bytes are bundled for offline examples. The existing Phase 1 APK remains a separate package.

The standalone Native player example launches Raycaster Maze, a self-running 32 KiB demo ROM. The full 152-ROM suite is distributed separately as the Native suite APK.

In the ROM-library app, Back pauses gameplay and returns to the ROM selector with its previous view, filters, search, and selection intact. The primary action reads **Resume** when the selected ROM is the one currently loaded; selecting another ROM changes it to **Play**. Back from the selector exits the app. The pause overlay no longer has a duplicate “Choose another ROM” action. Leaving the app pauses emulation and cancels verification; returning to the app leaves the pause menu visible.

## Build in a container

Builds always run in the pinned JDK 17 container with the rootless Docker daemon and no network inside the build container:

```sh
./android-tv/build-in-container.sh
```

The script uses Android SDK 34 at `/home/will/android-sdk-local` and the shared Gradle cache. Override `ANDROID_HOME` or `GRADLE_USER_HOME` when needed. It mounts the sibling `../biohack.net/` catalog and `../llvm-mos-65816/` build directory read-only, validates the staged ROM library against source ROM and card hashes, then builds and checks both library variants. Set `REFRESH_PUBLISHED_LIBRARY=1` to recapture all catalog card art. The APKs are `app/build/outputs/apk/wasm/release/bsnes-jg-wasm.apk` and `app/build/outputs/apk/native/release/llvm-65816-torture-test-suite-snes.apk`.

Both Release APKs are non-debuggable, shell-profileable, and signed with the local debug key for controlled coordinator installation. Do not distribute these test-signed APKs. They have distinct application IDs (`org.bsnesjg.tv.phase2` and `org.bsnesjg.tv.native.phase2`) and share the suite icon/product identity. The WASM build checks the frozen core hashes and canonical `web/app.js`; the native build checks its C++ library and adapter assets. Both APK gates check the exact same ROM/catalog contents. The container syntax-checks both engine adapters, the player, and remote-control JavaScript.

Public Native APKs use the durable PKCS12 release keystore. Load its path, store password, alias, and key password into `BJG_RELEASE_KEYSTORE`, `BJG_RELEASE_KEYSTORE_PASSWORD`, `BJG_RELEASE_KEY_ALIAS`, and `BJG_RELEASE_KEY_PASSWORD`, then run `task android-tv:release-build`. The task fails closed if the keystore or any value is missing. Keep the keystore and its recovery backup out of the repository; never pass passwords as Gradle arguments or print them in logs.

The TV scheduler targets 60.0988 SNES frames per second from monotonic RAF timestamps, independently of output refresh. It retains backlog when work is late and runs at most four core steps per callback; pause/resume resets its clock. The browser player retains its existing refresh-driven behavior. Container tests cover 50, 59.94, 60, and 120 Hz, bounded catch-up, and pause reset.

The runtime writes structured `BJG_TV_METRIC` JSON records to Android's log under the same tag. Each `playback_window` summarizes 60 emulated frames: core-step duration, canvas conversion/submission time, and WebView RAF intervals. These are app-side timings; they do not measure compositor presentation or displayed-frame cadence. Core/ROM startup, lifecycle, fidelity, and emulation backlog emit separate records.

After exporting a coordinator logcat capture that contains this tag, generate the run files with:

```sh
node android-tv/tools/metrics-report.mjs /path/to/coordinator-logcat.txt /path/to/run-report
```

It writes the parsed JSONL events, rolling-window CSV, a Markdown summary table, and an SVG time-series plot. The summary explicitly labels window-level quantiles and keeps RAF spacing separate from compositor presentation.

The build fails if the frozen ROM/map hashes, core glue/wasm hashes, pinned core provenance, or ROM self-check offset change. To refresh the ROM, copy a reviewed `.sfc` and matching `.map` into `fixture/`, rerun the native `jgxcheck` gate against those exact files, capture a new reference frame, and update the hashes/manifest/build assertions together.

## Device verification

Use only the Chromecast coordinator for device work. The current coordinator names are `chromecast-test-01` and `chromecast-test-02`; its inventory currently reports Android 14 and Android 12, respectively. Check their availability immediately before a run.

Chromecast review covers install/launcher, offline library startup, D-pad focus and paging, on-screen keyboard search and Backspace, category filters, Mode 7 badges, ROM launch, remote pause/resume/restart/verify/cancel/exit, background/resume, and playback profiling. Preserve coordinator jobs and evidence with the report. The coordinator must register `org.bsnesjg.tv` and `org.bsnesjg.tv/.MainActivity` before it will admit the APK.

Add this reviewed descriptor to the coordinator's Android application registration before job submission:

```json
"bsnes-jg-tv": {
  "package": "org.bsnesjg.tv",
  "activity": "org.bsnesjg.tv/.MainActivity",
  "native": false,
  "scenes": []
}
```

Then submit install and verification jobs by the `bsnes-jg-tv` app alias. Do not reuse a registered app's package ID: coordinator validation requires the APK package to match its registered application.

## Container contents

- `app/src/main/`: Android launcher Activity, WebView, remote overlay, and resource art.
- `fixture/`: frozen fidelity-check ROM, matching map, reference image, and self-check metadata.
- Gradle stages `web/app.js`, the committed `dist/engine/cores` files, and the generated biohack.net ROM library into the APK. The core is not rebuilt as part of this Android application build.

## App icons

`../docs/plans/assets/mandel-display-app-icon.png` is the approved square master. Regenerate the density-specific Google TV launcher icons and 16:9 banners, plus the browser/mobile favicon and home-screen sizes, with `python3 android-tv/tools/generate-app-icons.py`. Android TV resources are wired through `@mipmap/ic_launcher` and `@mipmap/tv_banner`; web icons are linked from `web/index.html` and declared in `web/site.webmanifest`. This repository has no separate native phone APK; phone home-screen artwork is provided by the browser player.
