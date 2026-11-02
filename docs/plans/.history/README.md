| Date | Change |
|------|--------|
| [2026-11-01](https://github.com/wbniv/bsnes-jg-player/commit/6d8798f) | Record the JSPI Pixel APK builds and the signing-key finding |
| [2026-11-01](https://github.com/wbniv/bsnes-jg-player/commit/fda6cf9) | Sweep the plans for statements this session made stale |
| [2026-11-01](https://github.com/wbniv/bsnes-jg-player/commit/2f65e42) | Index the JSPI coroutines plan |
| [2026-10-31](https://github.com/wbniv/bsnes-jg-player/commit/efcea07) | Observe the retarget-once stop case live on the real ROM |
| [2026-10-31](https://github.com/wbniv/bsnes-jg-player/commit/1fe82f5) | Index the Asyncify trim plan |
| [2026-10-31](https://github.com/wbniv/bsnes-jg-player/commit/40e06ae) | Index the Pixel phone performance plan |
| [2026-10-31](https://github.com/wbniv/bsnes-jg-player/commit/95b76ad) | Implement verified release candidates and resumable APK publication |
| [2026-10-31](https://github.com/wbniv/bsnes-jg-player/commit/d6498ac) | Validate Cast1 checkpoint and Pixel layouts with inline proof |
| [2026-10-31](https://github.com/wbniv/bsnes-jg-player/commit/1e7b34a) | Reconcile documentation status with iOS and Android validation evidence |
| [2026-10-31](https://github.com/wbniv/bsnes-jg-player/commit/eb74075) | Rename project to bsnes-jg-player |
| [2026-10-30](https://github.com/wbniv/bsnes-jg-player/commit/e314486) | Prepare Native releases and configurable ROM demo |
| [2026-10-29](https://github.com/wbniv/bsnes-jg-player/commit/4b68d74) | Index the published ROM inventory plan |
| [2026-10-29](https://github.com/wbniv/bsnes-jg-player/commit/a071ee1) | Record SNES launcher and profiling work |
| [2026-07-27](https://github.com/wbniv/bsnes-jg-player/commit/39c02cb) | TODO/plan-index: triage deferrals, record A1 done, index the npm-package plan |
| [2026-06-26](https://github.com/wbniv/bsnes-jg-player/commit/9b85386) | docs: add plan index (docs/plans/README.md) |

<!--history-meta v1
6d8798f	author	Will Norris
6d8798f	added	2
6d8798f	deleted	1
6d8798f	files	1
6d8798f	body	The Pixel's installed org.bsnesjg.tv.phase2 (043323ff) is debug-signed, so\nthe release-signed JSPI APK carries the .jspi suffix and needs its own\nregistration. The default wasm build is byte-identical to main's.\n\nCo-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>\nClaude-Session: https://claude.ai/code/session_01YEenqN5v3cNEkbzjiw3yKs
fda6cf9	author	Will Norris
fda6cf9	added	2
fda6cf9	deleted	1
fda6cf9	files	1
fda6cf9	body	The renderer plan still said Cast2 had failed to reconnect; it now points at\nthe 2026-11-01 Cast2 run and says what is and is not proven. The Asyncify\ntrim, Pixel perf and Cast1 tuning plans get status lines, the Cast1 plan gets\nits missing index row, and the selector plan no longer calls the library UI\ntest new.\n\nCo-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>\nClaude-Session: https://claude.ai/code/session_01YEenqN5v3cNEkbzjiw3yKs
2f65e42	author	Will Norris
2f65e42	added	2
2f65e42	deleted	1
2f65e42	files	1
2f65e42	body	Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>\nClaude-Session: https://claude.ai/code/session_01YEenqN5v3cNEkbzjiw3yKs
efcea07	author	Will Norris
efcea07	added	1
efcea07	deleted	0
efcea07	files	1
efcea07	body	scripts/retarget-verify.py drives headless Firefox (Marionette, /tmp profile)\nagainst the real lzss-gallery ROM and the real web/app.js: two ArrowRight\nnavigations mid-check produce "following your navigation to ..." and then the\nfail badge "navigation kept restarting the check". Real ROM, not a stubbed\nModule. Plan, timeline and screenshot recorded; TODO item moved to Done.\n\nCo-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>\nClaude-Session: https://claude.ai/code/session_01YEenqN5v3cNEkbzjiw3yKs
1fe82f5	author	Will Norris
1fe82f5	added	2
1fe82f5	deleted	1
1fe82f5	files	1
1fe82f5	body	Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>\nClaude-Session: https://claude.ai/code/session_01YEenqN5v3cNEkbzjiw3yKs
40e06ae	author	Will Norris
40e06ae	added	1
40e06ae	deleted	0
40e06ae	files	1
40e06ae	body	Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>\nClaude-Session: https://claude.ai/code/session_01YEenqN5v3cNEkbzjiw3yKs
95b76ad	author	Will Norris
95b76ad	added	1
95b76ad	deleted	0
95b76ad	files	1
d6498ac	author	Will Norris
d6498ac	added	5
d6498ac	deleted	5
d6498ac	files	1
1e7b34a	author	Will Norris
1e7b34a	added	8
1e7b34a	deleted	8
1e7b34a	files	1
eb74075	author	Will Norris
eb74075	added	3
eb74075	deleted	1
eb74075	files	1
e314486	author	Will Norris
e314486	added	3
e314486	deleted	1
e314486	files	1
4b68d74	author	Will Norris
4b68d74	added	1
4b68d74	deleted	0
4b68d74	files	1
a071ee1	author	Will Norris
a071ee1	added	12
a071ee1	deleted	0
a071ee1	files	1
39c02cb	author	Will Norris
39c02cb	added	2
39c02cb	deleted	1
39c02cb	files	1
39c02cb	body	Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>\nClaude-Session: https://claude.ai/code/session_011DEG8ouwAWtqeWtcvZSysz
9b85386	author	Will Norris
9b85386	added	22
9b85386	deleted	0
9b85386	files	1
9b85386	body	One row per docs/plans/*.md — auto-generated summary + category plus the per-plan\ncommit history — kept current by the shared check-plan-index drift hook on commit.\nSummaries auto-generated (Sonnet, medium effort); refine as needed.\n\nCo-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>
-->
