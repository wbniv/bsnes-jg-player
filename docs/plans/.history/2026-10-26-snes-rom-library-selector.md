| Date | Change |
|------|--------|
| [2026-11-01](https://github.com/wbniv/bsnes-jg-player/commit/bc2f74c) | Record 24 of 24 library UI cases passing |
| [2026-11-01](https://github.com/wbniv/bsnes-jg-player/commit/611c792) | Record the library UI test result and file its findings |
| [2026-11-01](https://github.com/wbniv/bsnes-jg-player/commit/7cf30f4) | Record the verify run for the library selector and search plans |
| [2026-10-31](https://github.com/wbniv/bsnes-jg-player/commit/d6498ac) | Validate Cast1 checkpoint and Pixel layouts with inline proof |
| [2026-10-31](https://github.com/wbniv/bsnes-jg-player/commit/1e7b34a) | Reconcile documentation status with iOS and Android validation evidence |
| [2026-10-31](https://github.com/wbniv/bsnes-jg-player/commit/83c5456) | Rename Android host directory and retain task compatibility aliases |
| [2026-10-29](https://github.com/wbniv/bsnes-jg-player/commit/8cf3f67) | Correct SNES display aspect guidance in mockups |
| [2026-10-29](https://github.com/wbniv/bsnes-jg-player/commit/e8c438f) | Improve TV library, APK sharing, and device workflows |
| [2026-10-28](https://github.com/wbniv/bsnes-jg-player/commit/33177cd) | Implement share and responsive ROM launcher menus |
| [2026-10-28](https://github.com/wbniv/bsnes-jg-player/commit/a755147) | feat: unify responsive SNES layout across platforms |

<!--history-meta v1
bc2f74c	author	Will Norris
bc2f74c	added	3
bc2f74c	deleted	9
bc2f74c	files	1
bc2f74c	body	Step 1 of the selector and search plans now passes. The two verify items stay\nopen because their device steps have not run.\n\nCo-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>\nClaude-Session: https://claude.ai/code/session_01YEenqN5v3cNEkbzjiw3yKs
611c792	author	Will Norris
611c792	added	10
611c792	deleted	4
611c792	files	1
611c792	body	The test now exists (4ed94f8): 24 cases, 18 pass, 6 fail. The failures are real\ngaps between library.js/library.css and the selector and search plans, filed as\nranked TODO items. The two verify items stay open.\n\nCo-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>\nClaude-Session: https://claude.ai/code/session_01YEenqN5v3cNEkbzjiw3yKs
7cf30f4	author	Will Norris
7cf30f4	added	31
7cf30f4	deleted	0
7cf30f4	files	1
7cf30f4	body	Step 2 of the selector plan passes (152 records, ROMs and cards). Step 1 of\nboth plans fails: android/test/library-ui.test.mjs has never existed. The\ndevice steps are marked not run. Both items stay [verify]; the missing test\nis a new TODO item.\n\nCo-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>\nClaude-Session: https://claude.ai/code/session_01YEenqN5v3cNEkbzjiw3yKs
d6498ac	author	Will Norris
d6498ac	added	4
d6498ac	deleted	2
d6498ac	files	1
1e7b34a	author	Will Norris
1e7b34a	added	2
1e7b34a	deleted	2
1e7b34a	files	1
83c5456	author	Will Norris
83c5456	added	12
83c5456	deleted	12
83c5456	files	1
8cf3f67	author	Will Norris
8cf3f67	added	1
8cf3f67	deleted	1
8cf3f67	files	1
e8c438f	author	Will Norris
e8c438f	added	3
e8c438f	deleted	1
e8c438f	files	1
33177cd	author	Will Norris
33177cd	added	13
33177cd	deleted	1
33177cd	files	1
a755147	author	Will Norris
a755147	added	483
a755147	deleted	0
a755147	files	1
-->
