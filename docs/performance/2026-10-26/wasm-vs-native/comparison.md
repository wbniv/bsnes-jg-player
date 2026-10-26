# bsnes-jg Android: WASM vs native comparison

**Status: preliminary; Cast1 paired measurements remain pending.** This report records the first usable Mandelbrot render profiles from Pixel as supporting data and documents why they are not a controlled head-to-head result. Pixel is Android 17 and was optional; Cast1 (Android 14, ARMv7) remains the target for the first comparable set.

The workload is the single bundled `mandel-display` ROM (SHA-256 `6c13c9042ca68be06f42650862ad7e116cc782e3a433ceaf9f760f090b430353`). The shared 152-ROM selector/catalog is present in both app variants but is not part of this workload. Core version is bsnes-jg 2.1.0; release builds use NDK 26.2.11394342 and CMake 3.22.1.

## Executive results

| Finding | Result | Interpretation |
| --- | ---: | --- |
| Pixel WASM SurfaceFlinger | 3 runs; median 5.93 presented frames/s | Severe missed-refresh behavior at 60Hz; all sampled intervals missed at least one 60Hz refresh. |
| Pixel native SurfaceFlinger | 1 run; 119.17 presented frames/s | Near the Pixel's 120Hz refresh, but only one run and two sampling holes. |
| Pixel comparison | 60Hz WASM vs 120Hz native | Not a valid speedup comparison; different refresh modes and run counts. |
| Cast1 WASM | Mandelbrot visible; sampler insufficient | 7 distinct timestamps across 14.46s, so no FPS estimate. |
| Cast1 native | Direct benchmark launch returned to Home | No playback samples. |
| Correctness gate | Not captured | Visual output is evidence of rendering only; frame-5800 WRAM and framebuffer checks remain outstanding. |
| Current Cast1 access | Recovery-required | Coordinator's diagnostic says administrator attention is required for connection check. No device session was attempted outside the coordinator. |

![Pixel exploratory presented frame rates](charts/pixel-exploratory-fps.svg)

## Measurement provenance

| Device | Engine | Job | Installed APK SHA-256 | Runs | Status/evidence |
| --- | --- | --- | --- | ---: | --- |
| Pixel 8 Pro, Android 17, arm64-v8a | WASM | `J‑7a4b7a0072ca` | `b2bfe5ed6eab03da8e3847ee2c65a5ff1d890c73ca972a22f0a7ca738d8556fa` | 3 | Completed; `evidence/pixel-wasm/`; installed hash verified. |
| Pixel 8 Pro, Android 17, arm64-v8a | Native | `J‑dab401a8e077` | `22b5561185bccd46ea517b0916873d17e3ddfe88a6cd527f7807bf8b8bf9643e` | 1 | Completed; `evidence/pixel-native/`; two SurfaceFlinger sampling holes. |
| Cast1 Chromecast HD, Android 14, armeabi-v7a | WASM | `J‑b47d61f35ce8` | `b2bfe5ed6eab03da8e3847ee2c65a5ff1d890c73ca972a22f0a7ca738d8556fa` | 1 attempt | Mandelbrot screenshot captured; sampler had too few timestamps. |
| Cast1 Chromecast HD, Android 14, armeabi-v7a | Native | `J‑c374ebe393bb` | `22b5561185bccd46ea517b0916873d17e3ddfe88a6cd527f7807bf8b8bf9643e` | 1 attempt | Benchmark activity left foreground; no timing samples. |

The Pixel APK hashes above precede the current telemetry build. Current APKs were rebuilt in the container after native metric instrumentation was added. Their hashes and sizes are listed below; they have not yet been profiled on Cast1. Thus the Pixel results are tied to the APK hashes in the evidence table, not the current artifacts.

## Pixel SurfaceFlinger results

Each WASM run sampled approximately 12 seconds of playback. Pixel WASM was at 60Hz; Pixel native was at 120Hz. `frames` below means sampled presentation intervals, not emulated SNES frames.

| Engine | Run | Refresh | Present intervals | FPS | p50 interval | p95 interval | p99 interval | Worst interval | Missed refreshes | Sampling holes |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| WASM | 1 | 60Hz | 163 | 9.96 | 100.00ms | 116.75ms | 133.33ms | 133.39ms | 100.00% | 0 |
| WASM | 2 | 60Hz | 126 | 5.39 | 175.01ms | 225.06ms | 225.14ms | 941.88ms | 100.00% | 0 |
| WASM | 3 | 60Hz | 133 | 5.93 | 174.87ms | 191.70ms | 191.75ms | 750.26ms | 100.00% | 0 |
| Native | 1 | 120Hz | 1,458 | 119.17 | 8.34ms | 8.39ms | 8.45ms | 58.34ms | 0.14% | 2 (41.6ms, 58.3ms) |

| Engine | Run count | Median FPS | Range | Median run p95 interval | Median run worst interval |
| --- | ---: | ---: | ---: | ---: | ---: |
| WASM | 3 | 5.93 | 5.39–9.96 | 191.70ms | 750.26ms |
| Native | 1 | 119.17 | n=1 | 8.39ms | 58.34ms |

![Per-run Pixel FPS](charts/pixel-run-fps.svg)

This difference is descriptive only. Refresh rates, run counts, and likely device display policy differ. It must not be reported as a native/WASM speedup ratio.

## WASM application-side telemetry

The Pixel WASM logs contain 15 `playback_window` events across three runs. Values below summarize those windows; they are independent of the SurfaceFlinger interval calculations and are not available for the native run because that older native APK did not emit matching structured telemetry.

| Metric across 15 windows | Minimum | Median | Maximum | Unit |
| --- | ---: | ---: | ---: | --- |
| Core step mean | 36.587 | 39.812 | 67.631 | ms |
| Core step p95 | 40.7 | 43.2 | 79.3 | ms |
| Core step maximum | 43.2 | 45.4 | 589.1 | ms |
| Canvas submit mean | 0.540 | 0.667 | 1.281 | ms |
| Canvas submit p95 | 0.7 | 0.8 | 11.8 | ms |
| RAF interval p95 | 155.6 | 173.6 | 759.8 | ms |
| Emulation backlog | 245.60 | 879.15 | 1,487.63 | frames |

![WASM internal timing and backlog](charts/wasm-internal-metrics.svg)

The core-step time is consistent with the observed low WASM presentation rate: core work takes substantially longer than a 16.67ms 60Hz frame budget, and the measured emulation backlog grows. Native app-side timing must be collected with the new telemetry build before a core-to-core comparison can be made.

## Current build artifacts

| Engine | Variant | Application ID | Current APK SHA-256 | APK bytes | ABIs |
| --- | --- | --- | --- | ---: | --- |
| WASM | WasmRelease | `org.bsnesjg.tv.phase2` | `247bc559214e86237c908a2a9f90f5d6883587e6573dbeec21afaa8fa7758bf9` | 14,801,590 | armeabi-v7a, arm64-v8a |
| Native | NativeRelease | `org.bsnesjg.tv.native.phase2` | `98c16b0b6d2d25b1bda89a254515d78d0c65a172d1ef725fe308e1b579f4cfb2` | 13,600,019 | armeabi-v7a, arm64-v8a |

Both variants use the shared selector. WASM runs the Emscripten core in Android WebView; native runs the C++ shared library through JNI. The container build completed successfully. The latest telemetry instrumentation emits core, canvas, RAF, backlog, ROM-load, and first-live-frame metrics for the native engine.

## Cast1 status and launch attempts

| Job | Engine | Outcome |
| --- | --- | --- |
| `J‑b47d61f35ce8` | WASM | Direct Mandelbrot launch rendered the expected Mandelbrot image; SurfaceFlinger sampling produced only 7 distinct timestamps in 14.46s, insufficient for FPS. |
| `J‑c374ebe393bb` | Native | Direct benchmark activity returned to Home; startup was not a successful playback measurement. |
| `J‑cea8e67c8b3b` | Home key | Coordinator-owned foreground cleanup job remained accepted while Cast1 showed recovery-required. |

Current Cast1 status: the shared Android transport is repaired and healthy, but Cast1 remains fenced because a cancelled APK install has an uncertain result. Coordinator cleanup requires a new boot ID. The job evidence was reviewed and recovery stopped before rebooting. Profiling remains paused until the device has rebooted and the coordinator clears the uncertain install state.

## Correctness, startup, and remaining coverage

| Gate/metric | Status | Notes |
| --- | --- | --- |
| Mandelbrot visual output | Observed on Pixel WASM/native and Cast1 WASM | Screenshots are included in the evidence directories. |
| Fixed-frame correctness | Not measured | No frame-5800 capture, expected WRAM `0x204F` comparison, or canonical framebuffer diff. |
| First-live-frame latency | Captured in per-job startup files | Pixel WASM runs include load/first-frame telemetry. These timings are tied to the prior APKs; this report does not use ActivityManager `am start` duration as first-frame time. |
| Native structured playback metrics | Pending new build profile | Current native APK now emits metrics; no run has captured them yet. |
| Cast1 paired profile | Blocked by coordinator recovery state | WASM sampling failure and native launch exit above are preserved as failed attempts, not measurements. |
| Memory / thermal | Partially captured on Pixel native only | Raw supporting evidence is in `evidence/pixel-native/`; conditions were not matched, so no cross-engine conclusion. |
| Audio, sleep/resume, remote controls, long-run stability | Not measured | Outside these initial short profiles. |

## Next measurement protocol

When Cast1 returns to coordinator-ready state, profile the current APK hashes above, register the deterministic `MandelbrotBenchmarkActivity` alias for the profile only, collect three runs per engine, and restore each alias to the normal launcher activity afterward. Capture screenshots, exact hashes, SurfaceFlinger intervals, app-side metrics, memory, thermal state, and the frame-5800 correctness gate. Keep display mode and run order matched. Pixel remains a useful optional second device.

No engine recommendation is supported yet. The Pixel samples identify a large exploratory performance gap, but they are not paired at the same refresh rate, use different replication counts, and lack the correctness gate.
