| Date | Change |
|------|--------|
| [2026-10-31](https://github.com/wbniv/bsnes-jg-player/commit/1dc1706) | Measure Pixel 8 Pro pacing: WASM misses 60 FPS, native holds it |

<!--history-meta v1
1dc1706	author	Will Norris
1dc1706	added	154
1dc1706	deleted	0
1dc1706	files	1
1dc1706	body	Plan docs/plans/2026-10-31-pixel-phone-perf.md for the "Perf on a phone"\nitem. tuning-report.py gains --baseline-engine/--tuned-engine (WASM\nplayback_window records carry no engine field) and legend labels; Cast1\noutput is unchanged (64.14 / 64.42 ms, 0.996x).\n\nInterim result from the 2026-10-31 morning Pixel jobs on mandel-display\n(the Mode 7 demo; zoom/mode7 ROMs were dropped in 85de645): WASM median\n23.66 ms/frame, 45.22 FPS; native 10.73 ms, 59.97 FPS, frame-5800 pass.\nFresh WASM repeats were not run: re-registering bsnes-jg-tv-phase2-wasm\nto the benchmark activity was refused by the permission system. The\nnative release baseline cannot be registered under a new app id\n(package already registered).\n\nCo-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>\nClaude-Session: https://claude.ai/code/session_01YEenqN5v3cNEkbzjiw3yKs
-->
