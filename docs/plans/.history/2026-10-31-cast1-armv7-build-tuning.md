| Date | Change |
|------|--------|
| [2026-10-31](https://github.com/wbniv/bsnes-jg-player/commit/cd6a3fc) | Record Cast1 build-flag bisect: no compiler flag helps, none kept |

<!--history-meta v1
cd6a3fc	author	Will Norris
cd6a3fc	added	199
cd6a3fc	deleted	0
cd6a3fc	files	1
cd6a3fc	body	Release-signed A/B on Chromecast HD, one frame-5800 job per build:\nbaseline 64.1 ms, ARMv8 flags only 64.4 ms (0.996x), -O3 + thin LTO\n100.1 ms (0.641x), both 106.1 ms (0.604x). The tuned builds miss the\ncheckpoint; the ARMv8 build passes the WRAM gate. Adds the comparison\nreport script and chart, the plan result and verification output, the\nCast1 support position, and the raw coordinator evidence for all four\njobs plus the refused debug-signed install.\n\nCo-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>\nClaude-Session: https://claude.ai/code/session_01YEenqN5v3cNEkbzjiw3yKs
-->
