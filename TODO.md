# TODO — bsnes-jg-player

Plan / contract: [docs/plans/2026-06-25-bsnes-jg-wasm.md](docs/plans/2026-06-25-bsnes-jg-wasm.md).

## Open

### Accurate mode — remaining

- [T2] **Low-end phone measurement.** Pixel 8 Pro: native 10.7 ms (60 FPS), WASM 23.7 ms (45 FPS); enrol a low-end phone with the coordinator and rerun the paired job.

### Polish

- [T4] **Land the JSPI core beside the Asyncify core, if Will agrees.** Pixel 8 Pro measured 2026‑11‑01 ([plan](docs/plans/2026-11-01-jspi-pixel-apk.md), [laptop plan](docs/plans/2026-11-01-jspi-coroutines.md)): median core 14.20 ms (cold phone) to 16.58 ms (warm, light throttling) against Asyncify's 23.66 ms and 45.22 FPS (warm); like-for-like speedup 1.43× to 1.50×, 1.67× cold, frame 5800 `0x204F` passes, no core errors. One earlier run (v1 APK) drew a single frame and logged nothing more; it did not recur on v2, whose only change is diagnostic logging, so the cause is unknown. JSPI is not universal (Safari and iOS 27, Firefox 153), so it ships beside the Asyncify core, chosen at load with `typeof WebAssembly.Suspending === "function"`. Three repeat runs of the v2 APK (2026‑11‑01) all ran clean, with medians 14.20, 15.81 and 16.58 ms; a fourth died from a coordinator `worker-crash` before the app started. The stall has not recurred, but three runs is a small sample. Landing means two cores, an async `_bjg_run`, new pinned shas and the Android/TV paths, and needs Will's decision before any change to `web/cores`, `dist` or the pinned shas. **Decision (Will, 2026‑11‑01): wait for a low-end phone measurement ([T2] item above), then land with the Asyncify core as the fallback.** Plugged runs 9 and 10 were throttled; unplugged run 11 was 16.63 ms (1.42x).

### npm package — [plan](docs/plans/2026-07-27-npm-player-package.md)


### live-record mode — [spec](../llvm-mos-65816/docs/plans/2026-07-28-gallery-per-image-selfcheck.md)


### Google TV ROM library — [plan](docs/plans/2026-10-26-snes-rom-library-selector.md)



### Release automation — [plan](docs/plans/2026-10-31-repeatable-release-tooling.md)


### Later (separate)

- [T3] **Physical iOS validation:** SwiftUI, native audio and GameController support are implemented. Six iPhone/iPad simulator UI tests, ROM/offline-audio checks and unsigned iPhone SDK compilation pass. Remaining: Apple signing identities and access to an iPhone, then install, audible audio/route/interruption checks, hardware-controller checks and sustained device pacing. [Plan and inline proof](docs/plans/2026-10-30-native-ios-player.md).

- [T3] **Showroom** — a demo-reel page consuming this core (curated `+mos-a16` productions). Its own
  effort; this repo just provides the `.wasm`.

## Watch

_Nothing being watched._

## Parked

- [T1] **First publish (manual prereq)**: create the npm account owning `@wbniv`, mint a granular
  automation token for this package, add repo secret `NPM_TOKEN`, then `git tag v1.0.0 && git push --tags`.
  Parked 2026‑11‑01 (Will: "we're not ready for release"). Re-check the tier on unpark.
- [T1] **Consumer release verification:** player `1.1.0` and live-record are committed and pushed on `npm-package` and merged into `main`. The old “unpushed branch” blocker is resolved. Recheck each consumer's installed revision, sync result and live-record deployment before closing the cross-repository release; this repository's push does not prove either site is current.
  Parked 2026‑11‑01 (Will: "we're not ready for release"). Re-check the tier on unpark.

- [T3] Tooling and full local candidate preparation PASS (0.1.10/code 11); 20 failure/gate tests, signed APK inspection, signing recovery, browser fidelity and local consumer-page checks pass. Remaining: scoped R2 credentials (existing admin token HTTP 403), live publication/retention tests, consumer deployments and real QR/recipient transfer proof. Cast1 player install is signature-incompatible; Pixel test was cancelled before grant due to another session reservation. No public release was made.
  Parked 2026‑11‑01 (Will: "we're not ready for release"). All remaining steps are release steps (R2 credentials, live publication, consumer deployments, QR transfer proof). Re-check the tier on unpark.
- [T2] **Search for the TV library**: see the [plan](docs/plans/2026-10-26-snes-rom-library-search.md).
  Deferred by Will on 2026‑10‑26. Search is currently visible. The old instruction to disable it is under clarification with Will; do not remove it solely because of that historical deferral. Un-park when
  the catalog nears 1,000 ROMs. T2 because it means switching on and testing one module; choosing
  ghost text would make it T3.

## Done

- ✅ 2026‑11‑01 — [device-coverage] Cast1, Pixel and Cast2 frame-5800 proofs pass (0 differing pixels, 4:3, GL 0); tablet never available. See [plan](docs/plans/2026-10-28-native-snes-renderer-texture-mapping.md).
- ✅ 2026‑11‑01 — [jspi-pixel-run] JSPI WASM on the Pixel 8 Pro: 14.20 ms median, 60.64 FPS vs 23.66 ms Asyncify; one unexplained stall. See [plan](docs/plans/2026-11-01-jspi-pixel-apk.md).
- ✅ 2026‑11‑01 — [lucky-dpad] D-pad route to I'm Feeling Lucky added and a chip-timer focus bug fixed; library UI test 31 of 31; no remote or device run. See [plan](docs/plans/2026-10-26-snes-rom-library-selector.md).
- ✅ 2026‑11‑01 — [native-currentrom] Native adapter exposes `currentRom()`, so Resume works from the library; new adapter test 2 of 2; not run on a device. See [plan](docs/plans/2026-10-26-snes-rom-library-selector.md).
- ✅ 2026‑11‑01 — [jspi-coroutines] JSPI libco backend measured: 0.551× frame time, bit-identical gates, needs an Asyncify fallback. See [plan](docs/plans/2026-11-01-jspi-coroutines.md).
- ✅ 2026‑11‑01 — [stale-library-copy] Deleted `android/app/src/library/assets/` (drifted, no consumer); its `res/` icons stay, the generator writes them. See [plan](docs/plans/2026-10-28-google-tv-launcher-views.md).
- ✅ 2026‑11‑01 — [library-text-rules] Empty-state text, "Search all N ROMs" count and 2-category chip rule match the plans; library UI test 24 of 24. See [plan](docs/plans/2026-10-26-snes-rom-library-selector.md).
- ✅ 2026‑11‑01 — [library-hidden-css] `.search[hidden],.filters[hidden]` now hide; library UI tests 3, 14, 24 pass (21 of 24). See [plan](docs/plans/2026-10-26-snes-rom-library-selector.md).
- ✅ 2026‑11‑01 — [library-ui-test] `android/test/library-ui.test.mjs` written: 24 cases, 18 pass, 6 fail on real code/plan gaps. See [plan](docs/plans/2026-10-26-snes-rom-library-selector.md).
- ✅ 2026‑11‑01 — [cast2-measurement] Cast2 median 44.04 ms, 22.41 FPS (Cast1 64.14 ms); no frame‑5800 capture, `.cast2` id. See [plan](docs/plans/2026-10-31-cast1-armv7-build-tuning.md#cast2-measurement-2026-11-01).
- ✅ 2026‑11‑01 — [sync-roms-gallery] `lzss-gallery` added to `sync-roms.sh` defaults; `main` defines `gallery_shown`, missing builds only warn.
- ✅ 2026‑10‑31 — [retarget-stop] Real ROM, headless Firefox: 1st navigation restarts the check, 2nd shows the fail badge. See [plan](docs/plans/2026-10-31-retarget-stop-check.md).
- ✅ 2026‑10‑31 — [asyncify-trim] No meaningful gain: REMOVE list cuts wasm 7% raw/2.8% gzip, ≤3% frame time; ONLY too fragile. See [plan](docs/plans/2026-10-31-asyncify-trim.md).
- ✅ 2026‑10‑31 — [firefox-check] Headless Firefox 156 passes the 5800-frame fidelity self-check, no COOP/COEP or SAB. See [plan](docs/plans/2026-06-25-bsnes-jg-wasm.md).
- ✅ 2026‑10‑31 — [stale-demos] Dropped the three dead picker buttons and ROM names; `npm test` now checks every button has a manifest entry.
- ✅ 2026‑10‑31 — [pixel-perf] Pixel 8 Pro: native 10.7 ms/60 FPS, WASM 23.7 ms/45 FPS; low-end phone unmeasured. See [plan](docs/plans/2026-10-31-pixel-phone-perf.md).
- ✅ 2026‑10‑31 — [catchup-credit] Native credit was unbounded (3.7k to 16.2k frames on Cast1); now capped at 4. See [plan](docs/plans/2026-10-31-cast1-armv7-build-tuning.md).
- ✅ 2026‑10‑31 — [cast1-build-tuning] Flag bisect on Cast1: ARMv8 neutral, `-O3`/LTO 0.64× slower, none kept. See [plan](docs/plans/2026-10-31-cast1-armv7-build-tuning.md).
- [x] 2026-10-31 — Android chooser, palette and pause menu confirmed working by Will. This is user acceptance, not a new automated device-run receipt.

- [x] 2026-10-31 — Native iOS simulator milestone: SwiftUI, audio graph, touch and controller mapping, lifecycle, iPhone/iPad portrait and landscape tests; unsigned device SDK build. Android directory rename and APK build checks also pass. Physical iPhone validation remains open above.

- [x] 2026-09-15 — [live-record] badge state is swapped with `classList`, so the host page's base
  class (`rp-badge` / `badge`) survives every transition and its CSS finally applies; `.rp-badge.warn`
  added to `embed/player.css`; `stage-dist.sh` filters the demo manifest to the ROMs it bundles.
  Headless Playwright: 4/4 states assert both classes and the computed pill colour.
- [x] 2026-07-31 — [live-record] `mode: "live-record"` implemented in `verify()` (no power-cycle,
  polls the running machine); browser-verified pass/mismatch/warn + 1st-of-2 retarget. See TODO Open.
- [x] 2026-07-27 — [npm-package] Phase C: indri adopts the package (kept own embed markup, deliberate); snes-rom-page skill v2 (no vendored engine).
- [x] 2026-07-27 — [npm-package] Phase B: biohack.net migrated + deployed (v1.0.307); prod selfcheck PASS. See [plan](docs/plans/2026-07-27-npm-player-package.md).
- [x] 2026-07-27 — [npm-package] CI green on GH ([run 30303535793](https://github.com/wbniv/bsnes-jg-wasm/actions/runs/30303535793)): functional gate (bitwise repro disproved cross-host; glue+CRC gate instead).
- [x] 2026-07-27 — [npm-package] A5: CI (repro+fidelity+sync gates) + publish.yml + Taskfile tasks; ?verify=1 headless hook. See [plan](docs/plans/2026-07-27-npm-player-package.md).
- [x] 2026-07-27 — [npm-package] A4: SnesPlayer.astro + integration + embed snippet/css + README boot contract. See [plan](docs/plans/2026-07-27-npm-player-package.md).
- [x] 2026-07-27 — [npm-package] A2–A3: package.json + committed dist/ + bin/sync.mjs (sync/--demo/--check). See [plan](docs/plans/2026-07-27-npm-player-package.md).
- [x] 2026-07-27 — [npm-package] A1: merged the 3 drifted app.js copies (kept adaptive yoff, manifest touchNav). See [plan](docs/plans/2026-07-27-npm-player-package.md).
- [x] **Mode 7 Mandelbrot, on-SNES + progressive** (2026-06-26): `mandel-display` rewritten to render
  in Mode 7 — 64×56 per-pixel bitmap computed on the 65816, revealed coarse→fine via **vblank DMA**
  (no force-blank flash), then a hardware affine **rotate+zoom**. CRC `0x204F` @ WRAM `$0400`/5200 fr.
  Also: build now defaults to the **a16 toolchain** so `mandel-mode7` builds (was skipped) — and it
  was made progressive too (128×128 far-WRAM compute, banded vblank reveal, CRC `0x75E8`).
- [x] **Fast first paint for `mandel-display`** (2026-06-26): progressive 4×4→8×7→16×14→32×28 ROM
  render + baked 4×4 loader preview; first visual <0.2 s, monotonic sharpen. CRC `0x9103` unchanged
  (self-check moved to WRAM `$0660` / 1400 frames). Deployed live (indri `v0.1.72`).
  [plan](docs/plans/2026-06-26-fast-first-paint-for-the-snes-mandelbrot-display.md)
- [x] **Deployed to indri.studio** (2026-06-25): the live emulator is embedded inline on
  [`/apps/llvm-mos-65816/`](https://indri.studio/apps/llvm-mos-65816/) running `mandel-display` + the
  `0x9103` self-check; `task bundle` → `dist-bundle/`, synced into indri's `public/`. Prod CSP block
  found+fixed (`'wasm-unsafe-eval'`); verified live (`v0.1.69`). [indri plan](../indri.studio/docs/plans/2026-06-25-llvm-mos-emulator-embed.md)
- [x] **Accurate mode wired + verified** (2026-06-25): built jgemu/bsnes 2.1.0 (sha256-pinned, the
  gate core) to wasm via a custom Jolly-Good-API frontend + Emscripten-fiber libco backend + Asyncify;
  canvas loader; in-browser self-check reads WRAM `0x9103` == gate. Verification 1–5 + perf PASS.
- [x] **[verify] Fidelity CRC match** (2026-06-25): in-browser `mandel-display` WRAM `$0580` ==
  `0x9103` == gate `jgxcheck`, headless Chrome — PASS. (Plan step 3.)
- [x] **Page flipped to accurate mode** (2026-06-25): EmulatorJS/CDN path removed; live PROVENANCE
  banner shows core version + sha256; `Verify fidelity` button added. (Plan polish.)
- [x] **build.sh build target resolved** (2026-06-25): `emmake make ENABLE_STATIC=1 DISABLE_MODULE=1
  USE_VENDORED_SAMPLERATE=1` → `libbsnes.a`, then `em++` links the frontend to `.js`+`.wasm`.
- [x] Scaffolded the repo (2026-06-25): reproducible `build.sh`, loader page, `serve.py`,
  `sync-roms.sh`, `Taskfile.yml`, GPLv3 `LICENSE`+`NOTICE`, bundled demo ROMs, the plan.


## Inbox — auto-captured plan deferrals

_Auto-added from plan "Out of scope"/"Deferred" sections at commit time. Triage each into M1/M2/etc. and delete it here — it will not come back._

<!-- BEGIN auto-captured-deferrals (managed by audit-plan-deferrals.sh — triage these into the curated sections above; the fingerprint ledger means a deleted item is NOT re-added) -->
- [verify] **2026-10-26-snes-rom-library-selector** — Verification section present but no PASS recorded — run + record the steps. _from [2026-10-26-snes-rom-library-selector.md](docs/plans/2026-10-26-snes-rom-library-selector.md)_  <!-- fp:b5cb5721dabd9fec -->
- [verify] **2026-10-27-responsive-snes-display** — Verification section present but no PASS recorded — run + record the steps. _from [2026-10-27-responsive-snes-display.md](docs/plans/2026-10-27-responsive-snes-display.md)_  <!-- fp:6adcfb5740bb82a1 -->
- [verify] **2026-10-28-google-tv-launcher-views** — Verification section present but no PASS recorded — run + record the steps. _from [2026-10-28-google-tv-launcher-views.md](docs/plans/2026-10-28-google-tv-launcher-views.md)_  <!-- fp:0ee29cdf2adf6368 -->
- [verify] **2026-10-28-google-tv-rom-treemap-view** — Verification section present but no PASS recorded — run + record the steps. _from [2026-10-28-google-tv-rom-treemap-view.md](docs/plans/2026-10-28-google-tv-rom-treemap-view.md)_  <!-- fp:c68fac9462dfeadf -->
- [ ] **(triage)** [ ] Add devices as they arrive, including the wider Android 7–14 inventory and the planned Android 16 purchase. Reuse both flavors and the same comparison protocol; their arrival is not a prerequisite for Phases 1 or 2. — _from [2026-10-26-chromecast-google-tv.md](docs/plans/2026-10-26-chromecast-google-tv.md)_  <!-- fp:c5e4c82c2f8ecff6 -->
- [ ] **(triage)** [x] Add the published ROM quick-launch library to the WASM app; keep `?rom=<slug>` direct boot usable for controlled testing. See the [selector implementation plan and published ROM list](2026-10-26-snes-rom-library-selector.md). Android document picker remains later work. — _from [2026-10-26-chromecast-google-tv.md](docs/plans/2026-10-26-chromecast-google-tv.md)_  <!-- fp:8fa6e5ef01ace90c -->
- [ ] **(triage)** [ ] Add full SNES gamepad mapping, additional controller ports, and disconnect/dead-zone tests with an interactive ROM that can demonstrate the mappings. The initial self-running ROM cannot validate them. — _from [2026-10-26-chromecast-google-tv.md](docs/plans/2026-10-26-chromecast-google-tv.md)_  <!-- fp:7885e979d673ccb9 -->
- [ ] **(triage)** [ ] Add audio playback and SRAM persistence when a ROM that uses them is in scope; then measure audio underruns and persistence across app restart. The initial `mandel-display` milestone should not wait on these unrelated features. — _from [2026-10-26-chromecast-google-tv.md](docs/plans/2026-10-26-chromecast-google-tv.md)_  <!-- fp:df92f88f6ea0b7b4 -->
- [ ] **(triage)** Changing the emulator frame scheduler or target SNES clock. — _from [2026-10-26-google-tv-performance-overlay.md](docs/plans/2026-10-26-google-tv-performance-overlay.md)_  <!-- fp:fbe7360986c55156 -->
- [ ] **(triage)** Collecting Android SurfaceFlinger presentation timestamps or claiming display refresh rate as app FPS. — _from [2026-10-26-google-tv-performance-overlay.md](docs/plans/2026-10-26-google-tv-performance-overlay.md)_  <!-- fp:4134ed190639f205 -->
- [ ] **(triage)** A desktop browser performance dashboard or mouse/keyboard-only controls. — _from [2026-10-26-google-tv-performance-overlay.md](docs/plans/2026-10-26-google-tv-performance-overlay.md)_  <!-- fp:04a1a690fe2285b1 -->
- [ ] **(triage)** Persisting historical sessions inside the apps; coordinator evidence remains the record for comparison runs. — _from [2026-10-26-google-tv-performance-overlay.md](docs/plans/2026-10-26-google-tv-performance-overlay.md)_  <!-- fp:b2b2d02005c6dc83 -->
- [verify] **2026-10-26-snes-rom-library-search** — Verification section present but no PASS recorded — run + record the steps. _from [2026-10-26-snes-rom-library-search.md](docs/plans/2026-10-26-snes-rom-library-search.md)_  <!-- fp:d21c98d625b27066 -->
- [ ] **(triage)** The Android frontend relies on bsnes-jg global state. A reusable multi-instance C API may take more work than a thin iOS bridge; constrain the first app to one emulator instance. — _from [2026-10-30-native-ios-player.md](docs/plans/2026-10-30-native-ios-player.md)_  <!-- fp:3755e5a5576d6456 -->
- [ ] **(triage)** Metal texture upload and audio-ring behavior need measurement on physical hardware; simulator success alone is not performance proof. — _from [2026-10-30-native-ios-player.md](docs/plans/2026-10-30-native-ios-player.md)_  <!-- fp:cdcdee449261179e -->
- [ ] **(triage)** Public iOS distribution requires Apple Developer signing/provisioning and account setup. Those credentials are outside the repo and are not part of simulator CI. — _from [2026-10-30-native-ios-player.md](docs/plans/2026-10-30-native-ios-player.md)_  <!-- fp:e0e28266e1471873 -->
- [ ] **(triage)** Upstream ownership for the cross-platform native adapter is unresolved. Keep the web package and browser WASM product in this fork; coordinate the Android/iOS adapter proposal with the core maintainer before submission. — _from [2026-10-30-native-ios-player.md](docs/plans/2026-10-30-native-ios-player.md)_  <!-- fp:3d782bc12400b500 -->
- [ ] **(triage)** tvOS, full 152-ROM catalog, save states, import-any-ROM UX, cloud saves, and App Store submission are outside this first iOS example. — _from [2026-10-30-native-ios-player.md](docs/plans/2026-10-30-native-ios-player.md)_  <!-- fp:8cf6d1326fee5a82 -->
- [ ] **(triage)** Codemagic account access and Xcode 16.4 execution are proven by the retained build. Shared usage and active jobs still need a fresh check before each future run. — _from [2026-10-30-native-ios-player.md](docs/plans/2026-10-30-native-ios-player.md)_  <!-- fp:8582e82c13e24fdc -->
- [T4] **PGO training build.** A `-fprofile-generate` variant of `libbjg.so`, a JNI `dumpProfile()` that writes `.profraw` after a fixed frame count, a coordinator step that pulls it from the app's files directory, and a `-fprofile-use` release build. Expected gain 10–30% on this interpreter-style code. Gate on the coordinator having a file-pull capability for a non-debuggable package. — _from [2026-10-31-cast1-armv7-build-tuning.md](docs/plans/2026-10-31-cast1-armv7-build-tuning.md)_  <!-- fp:86caa3550c052f99 -->
- [T1] **Startup cost.** `Bus::map` spends about 1.1 G instructions at load, roughly 1–2 s of Cast1's time to first frame. Inherent to the core's address-map design; record it in the selector plan's startup timing rather than optimising here. — _from [2026-10-31-cast1-armv7-build-tuning.md](docs/plans/2026-10-31-cast1-armv7-build-tuning.md)_  <!-- fp:8d745742a1eabb20 -->
- [verify] **2026-11-01-jspi-pixel-apk** — Verification section present but no PASS recorded — run + record the steps. _from [2026-11-01-jspi-pixel-apk.md](docs/plans/2026-11-01-jspi-pixel-apk.md)_  <!-- fp:33976c8f326912f0 -->
<!-- END auto-captured-deferrals -->
