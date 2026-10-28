# Cast1 native suite label and artwork refresh

- APK package: `org.bsnesjg.tv.native.phase2`
- Current APK SHA-256: `66ec252f3ddd1a72df8d227b440c46d567f20db317bd4ba6d8888c139aca3e53`
- Manifest label: `LLVM 65816 Torture Test Suite on SNES`
- Successful install and launcher verification: `J‑4ee3f0fd75a1` on Cast1. The coordinator read back the exact APK hash, reset Google TV Home once under the explicit request authorization, and verified both the current manifest label and artwork. Cast1 returned ready and stayed at Home.
- [launcher-after-reset.png](launcher-after-reset.png) shows the refreshed app row; [verified-tile.png](verified-tile.png) is the controller-bearing tile. The [hierarchy capture](launcher-after-reset.xml) contains the exact label `LLVM 65816 Torture Test Suite on SNES`; the [result JSON](launcher-after-reset-result.json) records `status: verified` and the one `launcher-data-reset-and-home` operation.
- The Home data reset restored the app-row ordering/preferences to Google TV defaults. It did not uninstall apps or clear app data. Pixel remains recovery-required; no Pixel install was run.

## Investigation history

- Coordinator `0.1.16` added bounded HOME refresh and stale-tile identification. Cast1's Home database kept the old title/artwork through three restarts (`J‑f32df034ecef`), so the app remained `launcher-unverified`.
- After the user authorized one reset, coordinator `0.1.17` added `RESET_LAUNCHER_DATA=true` as an explicit per-job request. The flag is absent from routine installs; reset is journaled and restricted to the reviewed TV launchers.
- The current APK was re-registered by its exact hash before job `J‑4ee3f0fd75a1`. An earlier submit using a previously frozen APK was rejected before device contact; nothing changed on Cast1 in that attempt.
- Private complete coordinator evidence is under `docs/diagnostics/cast1-launcher-reset-J-4ee3f0fd75a1/` in the Chromecast coordinator repository.
