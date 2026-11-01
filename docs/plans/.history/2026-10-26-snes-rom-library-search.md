| Date | Change |
|------|--------|
| [2026-11-01](https://github.com/wbniv/bsnes-jg-player/commit/611c792) | Record the library UI test result and file its findings |
| [2026-11-01](https://github.com/wbniv/bsnes-jg-player/commit/7cf30f4) | Record the verify run for the library selector and search plans |
| [2026-10-31](https://github.com/wbniv/bsnes-jg-player/commit/83c5456) | Rename Android host directory and retain task compatibility aliases |
| [2026-10-29](https://github.com/wbniv/bsnes-jg-player/commit/a071ee1) | Record SNES launcher and profiling work |

<!--history-meta v1
611c792	author	Will Norris
611c792	added	10
611c792	deleted	4
611c792	files	1
611c792	body	The test now exists (4ed94f8): 24 cases, 18 pass, 6 fail. The failures are real\ngaps between library.js/library.css and the selector and search plans, filed as\nranked TODO items. The two verify items stay open.\n\nCo-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>\nClaude-Session: https://claude.ai/code/session_01YEenqN5v3cNEkbzjiw3yKs
7cf30f4	author	Will Norris
7cf30f4	added	13
7cf30f4	deleted	0
7cf30f4	files	1
7cf30f4	body	Step 2 of the selector plan passes (152 records, ROMs and cards). Step 1 of\nboth plans fails: android/test/library-ui.test.mjs has never existed. The\ndevice steps are marked not run. Both items stay [verify]; the missing test\nis a new TODO item.\n\nCo-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>\nClaude-Session: https://claude.ai/code/session_01YEenqN5v3cNEkbzjiw3yKs
83c5456	author	Will Norris
83c5456	added	4
83c5456	deleted	4
83c5456	files	1
a071ee1	author	Will Norris
a071ee1	added	97
a071ee1	deleted	0
a071ee1	files	1
-->
