# TODO — bsnes-jg-wasm

Plan / contract: [docs/plans/2026-06-25-bsnes-jg-wasm.md](docs/plans/2026-06-25-bsnes-jg-wasm.md).

## Open

### Accurate mode — remaining

- [T3] **Perf on a phone.** Laptop is ~82 fps raw (>60 with headroom); Asyncify adds overhead, so
  measure a real low-end phone for the zoom/Mode-7 demos before claiming mobile.
- [T2] **Firefox spot-check.** End-to-end is verified in Chromium; load the page once in current
  Firefox (single-thread, no COOP/COEP) to confirm before deploy. (Plan step 4.)

### Polish

- [T3] Optional: trim Asyncify cost (size/speed) with an `ASYNCIFY_ONLY`/`ADD` list once the core's
  swap-reachable call set is profiled — only if mobile perf needs it.
- [T2] Wire self-checks for the other demos (zoom/mode7/interactive) — needs their scripted-input
  gates (see `dev/mandel-interactive.sh`), not just a boot-time WRAM read.

### npm package — [plan](docs/plans/2026-07-27-npm-player-package.md)

- [T1] **First publish (manual prereq)**: create the npm account owning `@wbniv`, mint a granular
  automation token for this package, add repo secret `NPM_TOKEN`, then `git tag v1.0.0 && git push --tags`.

### live-record mode — [spec](../llvm-mos-65816/docs/plans/2026-07-28-gallery-per-image-selfcheck.md)

- [T1] **Release + resync** — **PREPARED 2026-09-15, publication still user-gated.** `1.1.0` is
  committed on `npm-package` (**unpushed**) with `live-record` staged into `dist/`, the badge
  base-class fix, and `.rp-badge.warn` in `embed/player.css`; both sites are synced and committed
  locally (also unpushed). What remains needs the user's go-ahead and is outward-facing:
  `git push origin npm-package`, then on each site `pnpm update @wbniv/bsnes-jg-player` (the dep is
  `github:wbniv/bsnes-jg-wasm#npm-package`, so the branch push *is* the release — `npm publish` is
  only needed for registry consumers), then flip the gallery's selfcheck to `mode: "live-record"`
  and deploy. Until the branch is pushed, both sites' CI `sync --check` sees 1.1.0 on disk against
  1.0.0 in `node_modules` and fails — that is the gate working, not a defect.
- [T2] **Re-verify the retarget-once "stop" case** (2nd navigation mid-poll → fail badge) in a less
  resource-contended browser session — reproduced only the 1st retarget live (work 0→1, counter
  reset, correct title); the 2nd attempt kept losing its headless Chrome target to what looked like
  host memory pressure (multiple concurrent wasm/Chrome sessions on a shared box), not an app.js
  defect — the code path is the same branch already proven for the 1st retarget, gated only by a
  trivial `retargets > 1` counter.
- [T1] **Wire `lzss-gallery` into `sync-roms.sh`'s default ROMS list** once
  `feature/verify-fidelity-button` merges to `llvm-mos-65816` main — deliberately left out for now
  (see code comment) since a default sync from `main` today would overwrite the demo with a ROM
  that lacks the `gallery_shown` record.

### Google TV ROM library — [plan](docs/plans/2026-10-26-snes-rom-library-selector.md)

- [wip T3] **Implement the quick-launch library**: in progress in another session, and both Phase 2
  APKs build. Two decisions changed on 2026‑10‑26: use the site's `/play/preview/<slug>.png` card art
  instead of frame‑600 capture, and switch search off (it is deferred, see Parked). Device checks
  are still open.

### Later (separate)

- [T3] **Showroom** — a demo-reel page consuming this core (curated `+mos-a16` productions). Its own
  effort; this repo just provides the `.wasm`.

## Watch

_Nothing being watched._

## Parked

- [T2] **Search for the TV library**: see the [plan](docs/plans/2026-10-26-snes-rom-library-search.md).
  Deferred by Will on 2026‑10‑26. The code exists in `library.js` and is switched off. Un-park when
  the catalog nears 1,000 ROMs. T2 because it means switching on and testing one module; choosing
  ghost text would make it T3.

## Done

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
