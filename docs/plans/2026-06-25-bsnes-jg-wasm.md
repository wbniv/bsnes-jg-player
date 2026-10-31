# Plan — `bsnes-jg-wasm`: ship the gate's cycle-accurate core to the browser

**Status:** ACCURATE MODE WIRED + VERIFIED (2026-06-25). The exact gate core (jgemu/bsnes 2.1.0,
sha256-pinned) is compiled to WebAssembly and driven by a minimal custom Jolly-Good-API frontend;
the page boots the demos, renders, and the in-browser fidelity self-check reproduces the gate's
headless WRAM assert (`mandel-display` → `0x9103`). All five verification steps below pass.

**Origin:** the [llvm-mos-65816 investigation](https://github.com/wbniv/llvm-mos-65816/blob/main/docs/investigations/snes-emulator-in-browser.md)
(`docs/investigations/snes-emulator-in-browser.md` in that repo) — verdict: yes, feasible; bsnes-jg
is a libretro core → compiles to WASM. Named `bsnes-jg-wasm` (user, 2026-06-25): the honest artifact
name. Repo location resolved to a **standalone repo** (user, 2026-06-25) — cleanly separate from the
LLVM tree's Apache-2.0-w/-LLVM-exception licensing and with its own GPLv3 publish story.

## Context

The `+mos-a16` toolchain produces 32 KiB LoROM `.sfc` homebrew (Mandelbrot zoom / Mode-7 / DMA
demos). We want them runnable **in a browser, no install**, in **the same cycle-accurate `bsnes-jg`
core the differential gate trusts** (the gate's second leg, `build/jgxcheck` → `vendor/bsnes-jg`),
so the page's pitch is "byte-for-byte what the gate verified," not a snes9x lookalike.

snes9x (the turnkey browser default) is high-compat but **not** cycle-accurate and **non-commercial /
GPL-incompatible**. bsnes-jg is **cycle-accurate AND GPLv3** — accuracy-matched and license-clean.

## Goal / deliverable

A self-contained **WASM build of bsnes-jg** (`bsnes_jg_libretro.{wasm,js}`) + a **minimal loader
page** that boots our `.sfc` ROMs and renders them, on a plain static host. Reusable: the same
`.wasm` later backs a "showroom" demo-reel page (out of scope here).

## Source of truth

- **Core:** [`libretro/bsnes-jg`](https://github.com/libretro/bsnes-jg) — libretro wrapper around the
  Jolly Good fork ([gitlab.com/jgemu/bsnes](https://gitlab.com/jgemu/bsnes), GPLv3). **Pin the clone
  to the commit matching the llvm-mos-65816 `vendor/bsnes-jg` revision** so "same core" is literally
  true (`build.sh` records the built SHA → `web/cores/PROVENANCE.json`).
- **Build:** Emscripten SDK + libretro's emscripten path
  ([RetroArch `pkg/emscripten`](https://github.com/libretro/RetroArch/tree/master/pkg/emscripten),
  [EmulatorJS: building raw cores](https://emulatorjs.org/docs4devs/buildingraw/)).
- **Loader:** EmulatorJS ([emulatorjs.org](https://emulatorjs.org)).

## Decisions (resolved)

1. **Repo:** standalone `~/SRC/bsnes-jg-wasm` ✅ (user, 2026-06-25).
2. **Audio:** bsnes-jg embeds the SPC700 IPL (no BIOS — same reason the gate's jg leg needs none);
   demos are sound-free → audio resampled then discarded (silent).
3. **Threads:** default **single-threaded** (full speed for SNES, no COOP/COEP, any static host).
   `serve.py --isolated` is ready if a threaded build is ever wanted.
4. **The pin is jgemu/bsnes `2.1.0`, not a libretro commit** ✅ (resolved on first build, 2026-06-25).
   The gate's second leg (`dev/jgxcheck.cpp`) builds the **`gitlab.com/jgemu/bsnes` 2.1.0 tarball**,
   pinned by version *and* sha256 (`a8e0fd…0c42`) in `llvm-mos-65816/dev/xcheck.sh`. `libretro/bsnes-jg`
   is a *different* repo that re-vendors the core; "pin libretro/bsnes-jg to the vendor revision" was
   not literally satisfiable. `build.sh` now fetches + sha256-verifies that exact tarball, so "same
   core" is byte-for-byte true.
5. **Wiring: a custom Jolly-Good-API frontend, not EmulatorJS/libretro** ✅ (user choice, 2026-06-25).
   `web/src/main.cpp` drives the same `Bsnes::` C++ API the gate harness uses (`load`/`power`/`run`,
   `getMemoryRaw(MainRAM)`), compiled to wasm and presented on a `<canvas>` by `web/app.js`. This
   dissolves the "EmulatorJS custom-core packaging" unknown entirely **and** lets the page reproduce
   the gate's exact WRAM assert in-browser (the strongest possible "same core, same pixels" claim).
6. **libco needed an Emscripten backend** (build-time finding). Stock libco v20 (bundled in bsnes-jg)
   has no wasm path — its dispatcher falls through to `sjlj.c`, which bootstraps coroutine stacks via
   POSIX `sigaltstack`/`SIGUSR1` (absent under Emscripten). `web/src/libco_emscripten.c` implements
   libco on `emscripten_fiber_*`; the final link uses `-sASYNCIFY`. The SNES core needs cooperative
   threads (CPU/SMP/coprocessor), so this is load-bearing.
7. **libsamplerate is self-contained.** The 2.1.0 tarball *ships* `deps/libsamplerate`, so
   `USE_VENDORED_SAMPLERATE=1` compiles the resampler into the archive — no external `-lsamplerate`,
   same source the gate ships. (Audio is discarded anyway; this only affects link-completeness.)

## Status

- ✅ `build.sh` — bootstraps emsdk, fetches+sha256-verifies jgemu/bsnes 2.1.0, patches libco for
  wasm, builds the static core, links `web/src/main.cpp` → `web/cores/bsnes_jg.{js,wasm}` + provenance.
- ✅ `web/src/main.cpp` — minimal Jolly-Good-API wasm frontend (mirrors `dev/jgxcheck.cpp`).
- ✅ `web/src/libco_emscripten.c` — Emscripten-fiber libco backend (the wasm threading fix).
- ✅ `web/index.html` + `web/app.js` — canvas loader, ROM picker + drag-drop, keyboard pad,
  **in-browser fidelity self-check**, live PROVENANCE banner. (EmulatorJS removed.)
- ✅ `serve.py` (plain / `--isolated`), `sync-roms.sh`, `Taskfile.yml`, `LICENSE` (GPLv3), `NOTICE`.
- ✅ `web/roms/` — snapshot of mandel-{zoom,mode7,display,interactive}.sfc + `manifest.json` (self-check meta).
- ✅ **Accurate mode** — the page runs the locally built `bsnes-jg` core; CRC match proven in-browser
  (verification 1–3 below). The old showcase/CDN path is retired.

## Verification

> Run each step; paste raw output below it in a code block; PASS/FAIL; write back here.
> (Evidence recorded 2026-06-25 on a Dell Inspiron 14 7445 2-in-1, emscripten 6.0.1, headless Chrome.)

1. **Build + pin.** `./build.sh` (pinned to jgemu/bsnes `2.1.0`, the gate's revision) produces
   `web/cores/bsnes_jg.{wasm,js}` from a clean fetch, and `PROVENANCE.json` records the version+sha256.

   ```
   [2026-06-25T14:33:51Z] core archive: …/vendor/bsnes-jg/objs/libbsnes.a
   [2026-06-25T14:33:51Z] linking web/cores/bsnes_jg.js (+ .wasm) with Asyncify
   [2026-06-25T14:34:26Z] done — web/cores/bsnes_jg.{js,wasm} + PROVENANCE.json
   -rw-rw-r-- … 495      PROVENANCE.json
   -rw-rw-r-- … 72749    bsnes_jg.js
   -rwxrwxr-x … 3903214  bsnes_jg.wasm

   # PROVENANCE.json
   { "core": "bsnes-jg (jgemu/bsnes)", "version": "2.1.0",
     "sha256": "a8e0fd36711406198afe1110ddc6960c9d795f4ab73d0badd8878396ac3d0c42",
     "emscripten": "…6.0.1…", … }
   # `…echo "$SHA  tarball" | sha256sum -c -` printed: bsnes-2.1.0.tar.gz: OK
   ```
   **PASS** — note the artifact is `bsnes_jg.{js,wasm}` (custom frontend), not `*_libretro.*`; the
   pin is the jgemu/bsnes 2.1.0 *tarball* (sha256-verified), which is the literal gate core.

2. **Boots a demo.** The page (headless Chrome, plain `serve.py`) boots and renders a recognizable
   Mandelbrot. Canvas is 512×240, 85% of pixels lit (not black):

   ```
   status: running mandel-zoom.sfc · 512×240
   canvas: {"w":512,"h":240,"litFraction":0.849}
   ```
   <img src="screenshots/mandel-display-browser.png" width="700">

   **PASS** — the classic Mandelbrot cardioid+bulb, rendered by the wasm core after the self-check's
   1000 frames.

3. **Fidelity (the headline).** The in-browser self-check reproduces the gate's headless assert
   exactly: power on `mandel-display.sfc`, run 1000 frames, read 2 little-endian WRAM bytes at
   `$0580` (the `corpus_result` VMA from the ROM's map), require `== 0x9103`. (The "framebuffer CRC"
   wording in the original step was imprecise — `0x9103` is the ROM's on-console image hash in WRAM,
   which is exactly what `jgxcheck`'s `getMemoryRaw(MainRAM)` reads; we reproduce that read, not a
   pixel CRC.)

   ```
   # native gate, for reference:
   $ jgxcheck mandel-display.sfc Database 0x580 2 0x9103 1000
   SMOKE: PASS off=0x580 len=2 got=0x9103 (ran 1000 frames, bsnes-jg)

   # in-browser (this build), the Verify-fidelity button:
   self-check: ✓ FIDELITY 0x9103 == gate (corpus_result @ WRAM $0580, 1000 frames) [badge pass]
   VERIFY: PASS   (no console errors)
   ```
   **PASS** — byte-for-byte the gate's value, computed live in a browser tab by the same core.

4. **Static-host friendly.** Works with **no COOP/COEP** — `serve.py` runs in plain (single-thread)
   mode, the page uses no `SharedArrayBuffer`/threads (Asyncify fibers are single-threaded), and the
   end-to-end run above passes in current Chromium with no cross-origin-isolation headers.

   ```
   serve: LISTENING on :8000   [plain (single-thread)]   index HTTP 200
   ```
   **PASS (Chromium).** Firefox not automated here; the claim (no special headers, standard
   wasm+Asyncify, no SAB) is structural — re-confirm with a manual Firefox load before deploy.

   **Firefox spot-check (2026-10-31).** Headless Firefox 156.0.1 on Linux x86_64, driven over Marionette by
   `scripts/firefox-verify.py`, loaded the plain `serve.py` page (no COOP/COEP) with `?verify=1`:

   ```
   $ python3 serve.py -p 8123 &
   $ firefox --headless --no-remote --marionette --profile <tmp> &
   $ python3 -I scripts/firefox-verify.py "http://127.0.0.1:8123/?verify=1" out.png
   "badge": "✓ FIDELITY 0x204F == gate (gate jgxcheck CRC (corpus_result @ WRAM $0200), 5800 frames)",
   "cls": "badge pass",
   "ua": "Mozilla/5.0 (X11; Linux x86_64; rv:156.0) Gecko/20100101 Firefox/156.0",
   "coi": false,
   "sab": "undefined",
   ```

   <img src="plans/screenshots/firefox-verify-2026-10-31.png" width="700">

   **PASS (Firefox).** The self-check ran all 5800 frames and passed, the page is not cross-origin isolated
   and has no `SharedArrayBuffer`, so the no-special-headers claim holds. Not covered: console errors were
   not captured, and the run was headless (software rendering, so not a pacing measurement). Run twice
   (the first attempt's wait expired at frame 2016, the rerun finished).

5. **License hygiene.** GPLv3 source ships with the build (this repo); `LICENSE` is bsnes-jg's
   verbatim `COPYING`; `NOTICE` updated for the custom frontend + vendored deps; **no snes9x and no
   EmulatorJS** anywhere in the accurate path (`grep` of `web/` finds neither in the shipped page).
   **PASS.**

**Perf (TODO "60 fps" check).** Raw core throughput, headless Chrome on the laptop above:

   ```
   mandel-zoom     81.3 fps  (12.3 ms/frame)
   mandel-mode7    80.8 fps  (12.4 ms/frame)
   mandel-display  82.8 fps  (12.1 ms/frame)
   ```
   **PASS on desktop/laptop** (>60 fps with headroom; this is `_bjg_run()` only — the RAF loop adds a
   ~sub-ms `putImageData`). Phone/mobile **not yet measured** — still open.

## Risks / open items

- ~~**"Same core" must be literally true** — the pin is what makes the claim real.~~ **RESOLVED:**
  sha256-pinned to jgemu/bsnes 2.1.0, the gate's exact tarball; the in-browser self-check reads back
  the gate's `0x9103`.
- ~~**Custom-core wiring** — EmulatorJS packages cores in its own format…~~ **RESOLVED / sidestepped:**
  we ship a custom Jolly-Good-API frontend (`web/src/main.cpp`) and never touch EmulatorJS/libretro,
  so there is no custom-core packaging problem. New build-time risk surfaced + fixed: libco had no
  wasm path (added an Emscripten-fiber backend + Asyncify; see Decisions §6).
- **GPLv3** — fine; build source ships (this repo). Kept out of the LLVM tree via the standalone repo.
- **Perf** — ✅ ~82 fps raw on a laptop (step "Perf" above). **Open:** phone/mobile not yet measured;
  Asyncify adds size/overhead, so a low-end phone is the real test.
- **Firefox** — Chromium verified end-to-end; Firefox load not automated. Spot-check before deploy.
- **Reproducibility caveat** — `EMSDK_VERSION` defaults to `latest` (built here with 6.0.1, recorded
  in `PROVENANCE.json`). Pin it if a frozen toolchain is wanted; the *core* is already sha-pinned.
- **Scope guard** — NOT a CI differential leg for llvm-mos-65816 (same cores it runs natively → no
  new coverage). For show only.
