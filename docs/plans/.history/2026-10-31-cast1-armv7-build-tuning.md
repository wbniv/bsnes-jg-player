| Date | Change |
|------|--------|
| [2026-11-01](https://github.com/wbniv/bsnes-jg-player/commit/3794783) | Record Cast2 frame-5800 gate and layout from existing evidence |
| [2026-11-01](https://github.com/wbniv/bsnes-jg-player/commit/f807031) | Record the Cast2 measurement: 44.04 ms median, 22.41 FPS |
| [2026-10-31](https://github.com/wbniv/bsnes-jg-player/commit/9d17a92) | Record the Cast1 device check of the catch-up credit cap |
| [2026-10-31](https://github.com/wbniv/bsnes-jg-player/commit/9132eae) | Cap native catch-up credit so a slow core or stall is dropped, not banked |
| [2026-10-31](https://github.com/wbniv/bsnes-jg-player/commit/cd6a3fc) | Record Cast1 build-flag bisect: no compiler flag helps, none kept |

<!--history-meta v1
3794783	author	Will Norris
3794783	added	81
3794783	deleted	0
3794783	files	1
3794783	body	Cast2 job J-0020fd86a0c0 logged the in-app frame-5800 framebuffer\n(0 of 57,344 differing) and WRAM 0x204F checks as pass, 96/96 zero\nglGetError readings, and a 1440x1080 4:3 game rectangle. The display\nchanges after frame ~5400, so the end-of-run screenshot cannot prove\nzero differing displayed pixels; that needs a frozen checkpoint run.\n\nCo-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>\nClaude-Session: https://claude.ai/code/session_01YEenqN5v3cNEkbzjiw3yKs
f807031	author	Will Norris
f807031	added	17
f807031	deleted	1
f807031	files	1
f807031	body	Cast2 refused four installs (a stale org.bsnesjg.tv.native.phase2 signed with\nanother key survived a factory reset), so the measurement uses a release-signed\nbuild with the package id suffix .cast2. -PnativeIdSuffixExtra is optional and\nchanges nothing when unset. No frame-5800 capture: the new package registers\nno checkpoint with the coordinator.\n\nCo-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>\nClaude-Session: https://claude.ai/code/session_01YEenqN5v3cNEkbzjiw3yKs
9d17a92	author	Will Norris
9d17a92	added	1
9d17a92	deleted	1
9d17a92	files	1
9d17a92	body	Release APK from 9132eae on Chromecast HD: frame 5809 at 377 s, WRAM\ngate passes, median core time 64.24 ms (0.999x the baseline), and\nemulation_backlog_frames stays 0.0 in all 366 windows against the\nbaseline's 3,739.74 rising to 16,219.70.\n\nCo-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>\nClaude-Session: https://claude.ai/code/session_01YEenqN5v3cNEkbzjiw3yKs
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
