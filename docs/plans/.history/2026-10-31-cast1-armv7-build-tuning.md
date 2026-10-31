| Date | Change |
|------|--------|
| [2026-10-31](https://github.com/wbniv/bsnes-jg-player/commit/9132eae) | Cap native catch-up credit so a slow core or stall is dropped, not banked |
| [2026-10-31](https://github.com/wbniv/bsnes-jg-player/commit/cd6a3fc) | Record Cast1 build-flag bisect: no compiler flag helps, none kept |

<!--history-meta v1
9132eae	author	Will Norris
9132eae	added	1
9132eae	deleted	1
9132eae	files	1
9132eae	body	MainActivity.NativeRenderer added up to 0.25 s of credit per callback and\nnever capped the total. On Cast1 (core ~64 ms/frame, ~15 FPS) the\nemulation_backlog_frames metric, which is the running credit value at the\nend of each one-second window, grew monotonically from 3 739.74 to\n16 219.70 frames over the 284-window baseline run (about 44 frames/s); the\ntuned and variant runs showed the same. After any stall the player would\nhave replayed the debt at 4 steps per callback.\n\nClamp credit to MAX_CATCHUP_STEPS (4, one callback of work, the existing\nper-callback step limit) right after peak_backlog_frames is sampled, so the\nmetrics keep their meaning and the frame-5800 gate (frame-count based) is\nunchanged. The WASM tv-scheduler.js is untouched: it has no credit cap and\nrecovers a stall in full, which its test still pins.\n\nRegression guard in android/test/frame-scheduler.test.mjs: asserts the Java\nsource declares MAX_CATCHUP_STEPS = 4 and the clamp, and runs a JS model of\nthe arithmetic (bounded on a slow core, no burst after a 10 s stall).\nCovered: constant, clamp presence, model behaviour. Not covered: the Java\nexecuting, and any device run. Only the credit arithmetic pattern was\ncompiled with javac in the project JDK image; the full android:build was\nnot run.\n\nAlso corrects the Out of scope bullet in the Cast1 tuning plan and moves\nthe TODO item to Done.\n\nCo-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>\nClaude-Session: https://claude.ai/code/session_01YEenqN5v3cNEkbzjiw3yKs
cd6a3fc	author	Will Norris
cd6a3fc	added	199
cd6a3fc	deleted	0
cd6a3fc	files	1
cd6a3fc	body	Release-signed A/B on Chromecast HD, one frame-5800 job per build:\nbaseline 64.1 ms, ARMv8 flags only 64.4 ms (0.996x), -O3 + thin LTO\n100.1 ms (0.641x), both 106.1 ms (0.604x). The tuned builds miss the\ncheckpoint; the ARMv8 build passes the WRAM gate. Adds the comparison\nreport script and chart, the plan result and verification output, the\nCast1 support position, and the raw coordinator evidence for all four\njobs plus the refused debug-signed install.\n\nCo-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>\nClaude-Session: https://claude.ai/code/session_01YEenqN5v3cNEkbzjiw3yKs
-->
