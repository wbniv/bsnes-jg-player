# Pixel 8 Pro pacing: web/WASM player vs native player (2026-10-31)

**Result: the web/WASM player cannot claim 60 FPS on a phone; the native player holds it on this phone.** Neither result says anything about a low-end phone: no low-end phone is enrolled with the coordinator, and a Pixel 8 Pro is an upper bound for phones.

Device: `phone-pixel-8-pro` (Pixel 8 Pro, Android 17, arm64-v8a), 60.0988 Hz pacing, ROM `mandel-display`. Figures are medians of `playback_window` records with 3 warm-up windows dropped, from six existing coordinator jobs run between 08:23 and 08:59 device time. No fresh job was run for this report.

| Engine | Job | Workflow | Windows | Median core time | Median emulation speed | Frame-5800 gate |
|---|---|---|---:|---:|---:|---|
| WASM (Asyncify, WebView), APK `043323ff` | J‑e9aa930505cd | check | 80 | 23.18 ms | 46.16 FPS | no WASM record |
| WASM | J‑f6a11b900d90 | profile | 160 | 23.66 ms | 45.22 FPS | no WASM record |
| WASM | J‑68b3f9bdcde1 | record (screen capture on) | 151 | 27.69 ms | 40.52 FPS | no WASM record |
| Native, APK `fb4b8a78` | J‑3a13ec5ce46a | check, landscape | 66 | 10.71 ms | 59.98 FPS | pass |
| Native, APK `a64650ac` | J‑ccf4f03cf386 | check, portrait | 71 | 10.81 ms | 59.96 FPS | pass |
| Native, APK `a64650ac` | J‑ae4268b0701b | check, layout | 57 | 10.73 ms | 59.97 FPS | pass |

Median of the run medians: WASM 23.66 ms and 45.22 FPS (142% of the 16.6 ms frame budget); native 10.73 ms and 59.97 FPS (64% of the budget). On this phone native core time is 0.453 of WASM's, so native is 2.2× faster. `summary.json` and `core-ms.svg` in this directory compare J‑3a13ec5ce46a with J‑f6a11b900d90.

Raw evidence is under `docs/diagnostics/android-repeat-2026-10-31/` (`pixel-wasm`, `pixel-wasm-gate`, `pixel-wasm-long`, `pixel-native-fixed-signed`, `pixel-portrait`, `pixel-landscape-final`).

## What this does and does not show

- **WASM misses 60 FPS even on a 2023 flagship.** About 45 FPS median, with 5th-percentile windows near 27 FPS. Laptop raw WASM is 12.3 ms per frame, so the Pixel takes about 1.9× as long.
- **The WASM engine here is the web player's `bsnes_jg.wasm` inside an Android WebView.** Phone Chrome itself was not measured; the coordinator cannot drive a browser.
- **Native holds 60 FPS with the frame-5800 gate passing**, which supports a claim about this phone only.
- **Native ran APKs `fb4b8a78` and `a64650ac`, not the release baseline `8811ca04`** used for the Cast1 comparison.
- **The zoom and Mode 7 demos no longer exist.** Commit `85de645` dropped `mandel-zoom`, `mandel-mode7` and `mandel-interactive`; `mandel-display` is now the Mode‑7 tester, so it is the Mode‑7 demo itself and not a stand-in.
- **The core-time medians are not the Cast1 comparison.** Cast1 native is 64 ms on the same core; the Pixel is 10.7 ms.

## Consequence

The Polish item to trim Asyncify cost now has its trigger: mobile web pacing is below 60 FPS on the best phone available. A real low-end phone has not been measured.
