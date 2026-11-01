| Date | Change |
|------|--------|
| [2026-10-31](https://github.com/wbniv/bsnes-jg-player/commit/5239e95) | Record the Asyncify trim experiment: no meaningful gain |

<!--history-meta v1
5239e95	author	Will Norris
5239e95	added	178
5239e95	deleted	0
5239e95	files	1
5239e95	body	Relinked the existing core archive with ASYNCIFY_ADVISE, IGNORE_INDIRECT,\nADD, and REMOVE lists into tmpfs. Captured the swap-reachable stack set\nat runtime, and benched every build in a paired lockstep Chromium bench.\n\nA REMOVE list of load-time library code cuts the wasm by 7% raw and 2.8%\ngzip. Frame time drops by at most 1-3%, inside the noise. Emulation is\nunchanged: the checkpoints are identical and Firefox ?verify=1 passes\n0x204F at frame 5800. A namespace ADD list traps on the first rewind.\nNothing is landed. web/cores, dist, and the pinned shas are untouched.\n\nCo-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>\nClaude-Session: https://claude.ai/code/session_01YEenqN5v3cNEkbzjiw3yKs
-->
