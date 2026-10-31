| Date | Change |
|------|--------|
| [2026-10-30](https://github.com/wbniv/bsnes-jg-player/commit/e314486) | Prepare Native releases and configurable ROM demo |
| [2026-06-25](https://github.com/wbniv/bsnes-jg-player/commit/66bc05d) | Wire accurate mode: the gate's bsnes-jg 2.1.0 core, in the browser |
| [2026-06-25](https://github.com/wbniv/bsnes-jg-player/commit/0c1dc94) | scaffold bsnes-jg-wasm: the gate's cycle-accurate SNES core, in the browser |

<!--history-meta v1
e314486	author	Will Norris
e314486	added	0
e314486	deleted	1
e314486	files	1
66bc05d	author	Will Norris
66bc05d	added	124
66bc05d	deleted	28
66bc05d	files	1
66bc05d	body	Compile the EXACT core the llvm-mos-65816 differential gate trusts —\njgemu/bsnes 2.1.0, pinned by version and sha256 — to WebAssembly, and\ndrive it with a custom Jolly-Good-API frontend instead of EmulatorJS.\nThe page now reproduces the gate's headless fidelity assert live in a\nbrowser tab.\n\nResolved two findings from the first build:\n- The pin is jgemu/bsnes 2.1.0 (gitlab), NOT a libretro commit; the gate\n  builds that tarball via dev/jgxcheck.cpp through the Bsnes:: C++ API.\n  build.sh fetches + sha256-verifies it, so "same core" is literally true.\n- Stock libco v20 has no wasm path (falls through to sjlj.c, which needs\n  POSIX sigaltstack/SIGUSR1). Added web/src/libco_emscripten.c — a libco\n  backend on emscripten_fiber_*; the link uses -sASYNCIFY. libsamplerate\n  is vendored in the tarball, so USE_VENDORED_SAMPLERATE=1 self-contains it.\n\n- web/src/main.cpp: minimal wasm frontend mirroring dev/jgxcheck.cpp;\n  exports a C ABI (load/run/video/wram/input) to JS.\n- web/app.js + index.html: canvas loader, ROM picker + drag-drop, keyboard\n  pad, live PROVENANCE banner, and a Verify-fidelity self-check.\n- build.sh rewritten: emsdk → fetch+verify 2.1.0 → patch libco → emmake\n  make static core → em++ link with Asyncify + embedded game database.\n\nVerified end-to-end in headless Chrome (emscripten 6.0.1): demo boots and\nrenders a Mandelbrot (512x240), and the in-browser self-check reads WRAM\n$0580 == 0x9103 == the gate's jgxcheck value after 1000 frames. Raw\nthroughput ~82 fps on a laptop. Evidence + PASS/FAIL recorded in the plan.\n\nCo-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>\nClaude-Session: https://claude.ai/code/session_012z1vSadjiUqKEsQ6dU4u3P
0c1dc94	author	Will Norris
0c1dc94	added	82
0c1dc94	deleted	0
0c1dc94	files	1
0c1dc94	body	A WebAssembly build of bsnes-jg (the cycle-accurate core that is the second leg\nof the llvm-mos-65816 differential gate) + a loader page that runs the +mos-a16\nhomebrew demos. The pitch: a browser demo backed by THE SAME core the gate trusts\nis byte-for-byte what was verified — not a snes9x lookalike (snes9x is not\ncycle-accurate and is non-commercial/GPL-incompatible; bsnes-jg is cycle-accurate\nAND GPLv3).\n\nReproducible from repo + network:\n  build.sh        bootstrap emsdk -> clone+pin libretro/bsnes-jg -> build WASM core -> web/cores/\n  web/index.html  EmulatorJS loader (ROM picker + drag-drop; showcase mode works today)\n  serve.py        static server (plain single-thread; --isolated adds COOP/COEP for threaded builds)\n  sync-roms.sh / Taskfile.yml / LICENSE (GPLv3) / NOTICE\n  web/roms/       snapshot of mandel-{zoom,mode7,display,interactive}.sfc\n\nShowcase mode (stock CDN core) serves now (verified: page + ROM 200); accurate\nmode (the built bsnes-jg core, CRC-matched to the gate's jgxcheck) is the headline\nremaining work — see docs/plans/2026-06-25-bsnes-jg-wasm.md + TODO.md.\n\nCo-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>
-->
