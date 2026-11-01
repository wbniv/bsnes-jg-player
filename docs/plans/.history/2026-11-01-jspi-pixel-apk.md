| Date | Change |
|------|--------|
| [2026-11-01](https://github.com/wbniv/bsnes-jg-player/commit/58d77ee) | Record the JSPI Pixel result: 14.20 ms median, 60.64 FPS |
| [2026-11-01](https://github.com/wbniv/bsnes-jg-player/commit/7d1a828) | Add device diagnostics to the JSPI APK after the Pixel stall |
| [2026-11-01](https://github.com/wbniv/bsnes-jg-player/commit/6d8798f) | Record the JSPI Pixel APK builds and the signing-key finding |
| [2026-11-01](https://github.com/wbniv/bsnes-jg-player/commit/a094821) | Add an opt-in experimental WASM engine to the wasm flavor for a JSPI Pixel run |

<!--history-meta v1
58d77ee	author	Will Norris
58d77ee	added	14
58d77ee	deleted	0
58d77ee	files	1
58d77ee	body	The JSPI WASM core on the Pixel 8 Pro is 1.666x faster than Asyncify, with the\nframe-5800 gate passing. One earlier run stalled after its first frame and has\nno known cause; the TODO item asks for repeat runs before landing.\n\nCo-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>\nClaude-Session: https://claude.ai/code/session_01YEenqN5v3cNEkbzjiw3yKs
7d1a828	author	Will Norris
7d1a828	added	21
7d1a828	deleted	0
7d1a828	files	1
7d1a828	body	Pixel job J-6839cadfce9b stopped after engine_info with no console error and\na meminfo timeout on the app pid; the host does not reproduce it. The JSPI\nglue now logs switch progress and coroutine errors from inside the microtask\nchain, and app.js logs core errors (and keeps the loop going) plus a 60 s\nheartbeat, so one device run tells a busy loop, a lost resume and a trap apart.\n\nCo-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>\nClaude-Session: https://claude.ai/code/session_01YEenqN5v3cNEkbzjiw3yKs
6d8798f	author	Will Norris
6d8798f	added	21
6d8798f	deleted	1
6d8798f	files	1
6d8798f	body	The Pixel's installed org.bsnesjg.tv.phase2 (043323ff) is debug-signed, so\nthe release-signed JSPI APK carries the .jspi suffix and needs its own\nregistration. The default wasm build is byte-identical to main's.\n\nCo-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>\nClaude-Session: https://claude.ai/code/session_01YEenqN5v3cNEkbzjiw3yKs
a094821	author	Will Norris
a094821	added	86
a094821	deleted	0
a094821	files	1
a094821	body	-PexperimentalWasmDir stages bsnes_jg.{js,wasm}, PROVENANCE.json and app.js\nfrom a directory instead of dist/ and web/app.js, for the wasm flavor only.\nAll four files must match shas passed with -PexperimentalWasm*Sha, checked\nbefore staging and again inside the APK. -PwasmIdSuffixExtra optionally\ngives the package its own id. With no property set the wasm release APK is\nbyte-identical to one built from main's build.gradle.kts (5ee1f6c8...).\n\napp-jspi-patch.py now awaits the core in the TV frame loop and benchmark\nhook and logs an engine_info record; build-pixel-apks.sh, apk-page-check.py\nand apkdiff.py build and check the APKs off-device.\n\nCo-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>\nClaude-Session: https://claude.ai/code/session_01YEenqN5v3cNEkbzjiw3yKs
-->
