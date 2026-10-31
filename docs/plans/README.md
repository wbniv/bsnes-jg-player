# Plans — bsnes-jg-player

*Index of the plans in this directory — one row per `*.md`, oldest → newest by the commit that first
introduced it, with a one-sentence summary, the commit(s) that touched it, and a category. Summaries are
**auto-generated** (Sonnet) — refine as needed; the shared `check-plan-index.sh` drift hook flags missing
rows on commit.*

**Categories:** `Feature` · `Fix` · `Investigation` · `Tooling` · `Docs` · `Infra` · `Platform`.

| Plan | Summary | Commit(s) | Category |
|---|---|---|---|
| [Plan — `bsnes-jg-wasm`: ship the gate's cycle-accurate core to the browser](2026-06-25-bsnes-jg-wasm.md) | Compile bsnes-jg 2.1.0 to WebAssembly and wire a minimal loader page for SNES homebrew ROMs. | `0c1dc94`, `66bc05d` | Platform |
| [Fast first paint for the SNES Mandelbrot display](2026-06-26-fast-first-paint-for-the-snes-mandelbrot-display.md) | Add progressive coarse-to-fine render passes and a baked canvas preview to cut mandel-display first-paint below 0.1 s. | `b5bacec`, `2092512` | Feature |
| [bsnes-jg player → reusable npm package + biohack.net migration](2026-07-27-npm-player-package.md) | Merge the three drifted app.js copies, ship the player as the @wbniv/bsnes-jg-player npm package (sync CLI + Astro component + embed), and migrate biohack.net to one dynamic route over a content collection. | [`85462bc`](https://github.com/wbniv/bsnes-jg-wasm/commit/85462bc) | Platform |
| [bsnes-jg on Chromecast with Google TV](2026-10-26-chromecast-google-tv.md) | Build one-ROM WASM and native C++ TV apps in two phases, then compare both on cast1/cast2 with detailed tables, charts, and raw profiling data. | Implemented; Pixel/Cast1 native correctness PASS; see 31 October evidence | Platform |
| [SNES ROM quick-launch library for Google TV](2026-10-26-snes-rom-library-selector.md) | An offline Google TV library for the 152 published SNES ROMs, shared by the WASM and native Phase 2 apps. It has a single-column D-pad list with previews using the site's card images, single-select filters, favorites saved on the device, and I'm Feeling Lucky. Search is deferred to its own plan. | User-validated 2026-10-31; substitute Cast1/Pixel layout coverage passed | Feature |
| [Published SNES ROM library: complete inventory](2026-10-26-snes-rom-library-rom-inventory.md) | List all 152 published SNES ROMs with screenshots, filenames, categories, sizes, and their matching biohack.net preview paths. | [`a071ee1`](https://github.com/wbniv/bsnes-jg-wasm/commit/a071ee1) | Docs |
| [Search for the Google TV ROM library](2026-10-26-snes-rom-library-search.md) | Word-prefix search for the TV library: the best result is tagged TOP MATCH and the keyboard's action key jumps to it. The open question is TOP MATCH versus ghost text. The code exists and remains on; the historical disable-search instruction is under clarification. | Deferred | Feature |
| [Two SNES app icons: Mandelbrot and the full ROM suite](2026-10-26-snes-app-icons.md) | Give the Mandelbrot-only player and 152-ROM LLVM 65816 suite distinct artwork tied together by a realistic North American SNES controller badge. | Assets generated; app-identity artwork wiring remains | Feature |
| [Google TV performance overlay for SNES apps](2026-10-26-google-tv-performance-overlay.md) | Add a consistent remote-toggleable overlay for emulation FPS, app-side draw submissions, frame time, and scheduler backlog across WASM and Native players and libraries. | In progress; Cast1 Native/WASM profiles captured, Pixel and remote-toggle checks pending | Feature |
| [Resolution-adaptive SNES display and side panels](2026-10-27-responsive-snes-display.md) | Maximize the aspect-correct SNES image while adapting metadata/performance gutters between split landscape, single-rail landscape, and portrait phone/tablet layouts. | Proposed; mockups and geometry defined | Feature |
| [Native SNES renderer texture mapping](2026-10-28-native-snes-renderer-texture-mapping.md) | Corrected framebuffer mapping and color channels; Pixel portrait/landscape and Pixel/Cast1 native reference checks pass. | `491f57a`; hardware validation PASS | Fix |
| [Reliable Cast1 reinstall and launcher artwork refresh](2026-10-28-cast1-reinstall-and-launcher-artwork.md) | Add coordinator-owned, user-aware package reactivation and verified launcher refresh so Cast1 reinstalls do not repeatedly fail on packages retained for Android user 10. | Proposed; Cast1 multi-user package state confirmed | Platform |
| [Google TV launcher views: Quick Launch and Cartridge Flow](2026-10-28-google-tv-launcher-views.md) | Preserve Quick Launch and add Cartridge Flow and ROM Treemap as three shared-state launcher views in one D-pad chooser. | User-validated 2026-10-31; substitute Cast1/Pixel layout coverage passed | Feature |
| [Google TV ROM Treemap launcher view](2026-10-28-google-tv-rom-treemap-view.md) | Add a category-grouped treemap whose ROM tile areas follow exact byte sizes, with geometric D-pad focus and a detail rail. | User-validated 2026-10-31; substitute Cast1/Pixel layout coverage passed | Feature |
| [Treemap category palette investigation](2026-10-29-treemap-palette-investigation.md) | Compare categorical color palettes for the ROM treemap, document how to map palettes to N categories, and add a persistent palette dropdown with desktop and phone mockups. | User-validated 2026-10-31; substitute Cast1/Pixel layout coverage passed | Investigation |
| [Share the SNES app across phone, tablet, Chromecast, and web](2026-10-28-cross-platform-app-sharing.md) | Share the installed Android APK through Android Sharesheet or a short-lived LAN QR, with a public-download fallback and web URL sharing. | [`33177cd`](https://github.com/wbniv/bsnes-jg-wasm/commit/33177cd) | Platform |
| [Public Android APK downloads on Cloudflare R2](2026-10-28-r2-apk-public-downloads.md) | Native APK release 0.1.9 is published with 0.1.8 retained; automation, scoped credentials, source listing and device QR fallback proof remain open. | Published; follow-up work remains | Infra |
| [Propose a reusable Native Android frontend upstream](2026-10-29-native-android-upstream.md) | Keep the browser player in this fork and prepare a focused upstream proposal for the core-facing Native Android adapter, leaving the launcher and ROM catalog downstream. | Proposal draft; not submitted | Platform |
| [Native iOS player integration](2026-10-30-native-ios-player.md) | Native iOS example implemented with SwiftUI, Metal, audio and GameController; six iPhone/iPad simulator tests and unsigned device SDK build pass. | Simulator PASS; physical signing/testing blocked | Platform |
| [Rename the project to `bsnes-jg-player`](2026-10-31-bsnes-jg-player-rename.md) | Align the GitHub repository, local checkout, and public product URL around the reusable player, while retaining redirects and the established APK delivery path. | In progress | Platform |
| [Repeatable releases, signing, retention and sharing proof](2026-10-31-repeatable-release-tooling.md) | Prepare and verify signed release candidates, publish with resumable current/previous retention, scope credentials and validate device QR/sharing flows with inline evidence. | Implemented locally; credentials/publication and device proof pending | Infra |
| [Pixel phone performance: can the player claim mobile?](2026-10-31-pixel-phone-perf.md) | Measure emulation pacing of the WASM and native Android engines on the Pixel 8 Pro with the `playback_window` metric and record whether mobile can be claimed. | Interim: WASM 45 FPS, native 60 FPS; fresh WASM and native-baseline runs blocked on coordinator registration | Investigation |
| [Asyncify trim: does an instrumentation list make the WASM core faster or smaller?](2026-10-31-asyncify-trim.md) | Relink the core with `ASYNCIFY_ADVISE`/`ADD`/`REMOVE` lists, profile the swap-reachable stack set, and bench every build paired in headless Chromium with checkpoint and Firefox fidelity gates. | Done: no meaningful gain (−7% raw wasm, ≤3% frame time); nothing landed | Investigation |

---

## How this index was derived

- **Order** = each plan's *creation* commit (oldest commit that touched the file), by committer date.
- **Commit(s)** = the full `git log --follow` set per plan, oldest → newest.
- **Summaries / categories** auto-generated from each plan's TL;DR (Sonnet, medium effort) — refine as needed.
- **Generated** 2026-06-26 for 2 plan(s); updated 2026-07-27 for 3 plan(s); asyncify-trim row added by hand 2026-10-31.
