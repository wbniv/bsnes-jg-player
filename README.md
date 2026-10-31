# bsnes-jg-player

**Reusable integrations for a cycle-accurate SNES core — including the browser WebAssembly player.**

The product is the reusable player integration: the pinned bsnes-jg core, browser WebAssembly frontend, package sync CLI, framework-agnostic embed, and Astro component. The Android APKs and iOS app are example Native host integrations; they are not the product API.

A WebAssembly build of [**bsnes-jg 2.1.0**](https://gitlab.com/jgemu/bsnes) (the Jolly Good fork of
bsnes), plus a minimal page that runs `.sfc` homebrew. Its reason to exist: bsnes-jg is the
**second leg of the differential gate** in the [`llvm-mos-65816`](https://github.com/wbniv/llvm-mos-65816)
project (a from-source LLVM fork adding native 16-bit-accumulator codegen — `+mos-a16` — for the
WDC 65816). That gate asserts *host == default@MAME == +mos-a16@MAME == +mos-a16@bsnes-jg*. By
shipping **the same core** — the exact `2.1.0` tarball the gate pins, by version *and* sha256 — a
browser demo of the `+mos-a16` ROMs is byte-for-byte the output the gate already verified, not a
snes9x lookalike. The page proves it: a **Verify fidelity** button reproduces the gate's headless
WRAM assert (`mandel-display` → `0x9103`) live in the tab.

> **Why bsnes-jg and not snes9x?** snes9x is the turnkey browser default, but it is *not*
> cycle-accurate and its license is **non-commercial / GPL-incompatible**. bsnes-jg is
> **cycle-accurate AND GPLv3** — the accuracy-matched *and* license-clean choice.

---

## The npm package — `@wbniv/bsnes-jg-player`

See [Integrate the bsnes-jg player](docs/how-to/integrate-the-player.md) for the browser WebAssembly flow, Astro and static-site samples, the C++ frontend contract, and the Android Native example bridge. The [iOS example](ios/README.md) adds SwiftUI, Metal, native audio and GameController support; [simulator validation and inline screenshots](docs/plans/2026-10-30-native-ios-player.md) are recorded, while physical iPhone signing/testing remain pending.

This repo doubles as an npm package so any site can vendor the player without touching Emscripten:

```sh
npm i @wbniv/bsnes-jg-player          # or: npm i git+https://github.com/wbniv/bsnes-jg-player.git
npx bsnes-jg-player sync public/play  # vendor app.js + cores/* (+ ENGINE_VERSION stamp)
npx bsnes-jg-player sync public/play --demo   # also seed the 32 KiB Raycaster Maze demo ROM
```

The npm payload includes this one small sample ROM, not the 152-ROM suite. The full suite is available as the APK download on [Indri](https://indri.studio/apps/bsnes-jg-player/).

`demo-rom.json` is the one place that selects the sample for npm, the standalone Android player and the iOS example: slug, title, APK filename stem, integrity hash, and optional WRAM self-check. Add the ROM and preview under `web/roms/` and `web/preview/`, update that config, and run `bash scripts/stage-dist.sh` to refresh the npm payload.

`sync` never touches `roms/` or `preview/` (your site's content) unless `--demo`. In CI, run
`npx bsnes-jg-player sync --check public/play` — it exits 1 if the vendored engine drifts from the
installed package version (byte-for-byte sha256), which replaces any "keep the copies identical by
hand" discipline. `dist/` (the published payload) is **committed**: CI rebuilds the core from source
and diffs it against `dist/engine/cores/`, so publishes never wait on an emsdk build and a git-URL
install works.

**Astro sites** get a component and an optional build-time warning light:

```astro
---
import SnesPlayer from '@wbniv/bsnes-jg-player/SnesPlayer.astro';
---
<SnesPlayer slug="my-rom" title="My ROM" keys="Arrows: pan · Z: fire." />
```

```js
// astro.config.mjs — warns (or mode:'error' fails) when public/play predates the package
import bsnesPlayer from '@wbniv/bsnes-jg-player/integration';
export default defineConfig({ integrations: [bsnesPlayer()] });
```

**Any other stack**: copy the documented block from [`embed/snippet.html`](embed/snippet.html) +
[`embed/player.css`](embed/player.css).

### Boot contract (what `app.js` reads)

| Surface | Meaning |
|---|---|
| `window.BJG_BASE` | URL base of the play dir, with trailing slash (default `''` = relative) |
| `window.BJG_DEFAULT_ROM` | ROM id to boot (a `?rom=` query param wins) |
| `window.BJG_BUST` | optional `{relpath: shortsha}` map → `?v=` immutable-cache busting |
| `#screen` | the 256×224 canvas (required) |
| `#status` `#checkresult` `#verify` `#banner` `#fullscreen` `#game` | status line · fidelity badge · self-check button · errors/provenance · fullscreen button · drag-drop wrapper (all optional) |
| manifest `selfcheck` | `{off,len,want,frames,label}` — powers **Verify fidelity** (run N frames, assert WRAM) |
| manifest `selfcheck.mode: "live-record"` | `{off,record,ready,oracle,titles,frames,poll,label}` — polls the **running** machine (no power-cycle) until `record.state == ready`, then asserts `ok == 1 && z == oracle[work]`. For ROMs whose on-screen state is the thing being checked |
| `#checkresult` classes | the player adds exactly one of `running` `pass` `fail` `warn` and **keeps whatever base class your markup gave the element** — style `.rp-badge.pass` etc. `warn` is indeterminate (frame budget spent, no verdict published), never a failure |
| manifest `touchNav` | `{left:[x,y,w,h], right:[x,y,w,h]}` — canvas taps press pad Left/Right (for ROMs drawing their own chevrons) |

Keyboard map (fixed): arrows = D-pad, `Z`/`X` = B/A, `A`/`S` = Y/X, `Q`/`W` = L/R, `Enter` = Start,
`Shift` = Select.

## What's here

```
build.sh            # reproducible: bootstrap emsdk → fetch+sha256-verify jgemu/bsnes 2.1.0 → build → web/cores/
serve.py            # local static server (single-thread by default; --isolated adds COOP/COEP if ever needed)
sync-roms.sh        # refresh the bundled demo ROMs from a sibling llvm-mos-65816 checkout
Taskfile.yml        # task build / serve / sync-roms / clean
web/
  index.html        # the loader page (canvas + ROM picker + drag-drop + Verify fidelity)
  app.js            # drives the core: render framebuffer, keyboard→pad, the fidelity self-check
  src/main.cpp      # minimal Jolly-Good-API wasm frontend (mirrors the gate's dev/jgxcheck.cpp)
  src/libco_emscripten.c  # libco backend on Emscripten fibers (stock libco has no wasm path)
  roms/*.sfc        # local demo sources; the npm payload stages only Raycaster Maze
  roms/manifest.json# per-ROM metadata and optional self-checks
  cores/            # build.sh drops bsnes_jg.{wasm,js} + PROVENANCE.json here (gitignored — reproducible)
package.json        # @wbniv/bsnes-jg-player (see above)
demo-rom.json       # selected one-ROM npm / standalone Android example
bin/sync.mjs        # the sync CLI (vendor / --check drift gate / version)
dist/               # COMMITTED npm payload: engine (app.js + cores) + 32 KiB Raycaster demo — staged by scripts/stage-dist.sh
astro/              # SnesPlayer.astro component + optional integration (ENGINE_VERSION warning light)
embed/              # framework-agnostic snippet.html + player.css
docs/plans/         # the build plan / contract (+ verification evidence)
LICENSE  NOTICE     # GPLv3 (the core) + attribution
```

## Quick start

```sh
task build          # bootstrap emsdk + build the bsnes-jg wasm core into web/cores/  (slow first run)
task serve          # serve web/ on http://localhost:8000
```

Open [http://localhost:8000](http://localhost:8000), pick a demo (or drop your own `.sfc`), and hit
**Verify fidelity** to watch the in-browser self-check land the gate's `0x9103`. (If you haven't run
`build.sh`, the page says so instead of erroring.)

`emsdk` is bootstrapped automatically if `emcc` isn't on `PATH`. First run is slow (downloads the
Emscripten toolchain + builds the core); after that it's cached.

Keys: arrows = d-pad, `Z`/`X` = B/A, `A`/`S` = Y/X, `Enter` Start, `Shift` Select, `Q`/`W` = L/R.

## How "same core" is made literal

- **The pin.** `build.sh` fetches the **`gitlab.com/jgemu/bsnes` 2.1.0** tarball and checks its
  sha256 against the value pinned in `llvm-mos-65816/dev/xcheck.sh` — the exact bytes the gate
  builds. (Not `libretro/bsnes-jg`; that's a different repo. See the plan's Decisions §4.)
- **The frontend.** `web/src/main.cpp` drives the same `Bsnes::` C++ API the gate's headless harness
  (`dev/jgxcheck.cpp`) uses — `load`/`power`/`run`, `getMemoryRaw(MainRAM)` — so the page can read
  WRAM and assert the gate's value. No libretro, no EmulatorJS.
- **The wasm wrinkle.** bsnes-jg threads cooperatively via libco, which has no WebAssembly code path;
  `web/src/libco_emscripten.c` reimplements it on Emscripten fibers (the build links `-sASYNCIFY`).
- **The proof.** The **Verify fidelity** button powers on `mandel-display`, runs 1000 frames, reads
  WRAM `$0580`, and shows `0x9103 == gate`. That's the gate's own assert, in a browser tab.

## License

The bsnes-jg core is **GPLv3** (`LICENSE` is its verbatim `COPYING`). Anything that links or ships
the built core inherits GPLv3 — so this repo, and any deploy of `web/cores/*.wasm`, publishes its
source. The build scripts and loader here are GPLv3 to match. See `NOTICE` for attribution. The
bundled `.sfc` files are homebrew built by the `llvm-mos-65816` toolchain from its own example
sources.

## Not a CI test leg

This runs the *same* cores the `llvm-mos-65816` gate already runs natively (MAME + bsnes-jg), only
slower and harder to drive headless. It adds **no** correctness coverage and is deliberately **not**
wired into that project's differential gate. It exists to *show*, not to *verify*.
