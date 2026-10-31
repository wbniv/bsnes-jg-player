# Use the shared Chromecast coordinator

Use the shared coordinator for every Chromecast test in this repository. The
coordinator service owns a complete device session from admission through
cleanup. This prevents two projects from controlling the same device at once
and keeps installs, input, captures and evidence attached to an auditable job.

## Available project tasks

The project imports a focused task surface from
[`Taskfile.chromecast.yml`](../../Taskfile.chromecast.yml). It calls the CLI in
the sibling `../chromecast-coordinator/` checkout; it does not duplicate the
coordinator implementation.

| Task | Purpose |
| --- | --- |
| `task chromecast:devices` | List enrolled devices and readiness. |
| `task chromecast:queue` | Check active work, queued jobs and reservations. |
| `task chromecast:app:register` | Register a frozen APK and its declared activity; no device session. |
| `task chromecast:submit` | Submit an install, launch or other supported workflow. |
| `task chromecast:check` | Run a coordinator-supported check. |
| `task chromecast:profile` | Capture a performance profile. |
| `task chromecast:record` | Start an interactive recording session. |
| `task chromecast:capture` | Capture the current screen. |
| `task chromecast:keep-awake` | Hold an unlocked device awake during bounded preparation between tests. |
| `task chromecast:readd` | Request a coordinator-managed reconnect. |
| `task chromecast:watch` | Follow a job or batch. |
| `task chromecast:evidence` | Download verified evidence for a job or batch. |
| `task chromecast:message` | Send a supported message to an owned job. |
| `task chromecast:cancel` | Cancel a job owned by this session. |

See the [coordinator CLI guide](../../../chromecast-coordinator/docs/chromecast-cli-guide.md)
for argument definitions, workflow choices and admission behavior. The
coordinator's own Taskfile is the source of truth for CLI mapping and options.

For the fixed Mandelbrot comparison, register each Phase 2 APK with
`ACTIVITY=org.bsnesjg.tv.MandelbrotBenchmarkActivity`. The ordinary
`MainActivity` opens the selector and must not be profiled as emulation.
Use `REPLACE=true` when updating an existing registration, and pass the exact
`APK` to every profile/check so the coordinator verifies the installed bytes.
Check `startup-latency-run-1.json` and the ROM-loaded metrics in downloaded
evidence before accepting a run. Registration is shared state: restore the
normal activity after the benchmark jobs finish.

## Standard session

Check device readiness and shared queue state before every device session,
including captures:

```sh
task chromecast:devices
task chromecast:queue
```

Choose an available device, then submit the full operation as one coordinator
job. For example, install and verify the registered native app:

```sh
task chromecast:submit DEVICE=chromecast-test-01 APP=bsnes-jg-tv WORKFLOW=install APK="$PWD/android/app/build/outputs/apk/native/release/app-native-release.apk"
```

The app registration, APK path, and workflow must match the current build and
coordinator catalog. Follow the job ID printed by submit:

```sh
task chromecast:watch JOB=J-…
```

Download verified proof to the project's evidence directory:

```sh
task chromecast:evidence JOB=J-… OUT=docs/proof/<test-name>
```

Use `task chromecast:check` for a supported check or
`task chromecast:capture DEVICE=chromecast-test-01` for a current-screen
capture. Watch any returned job and fetch its evidence. The coordinator guide
covers options such as `ASYNC=true`, profiling fields, recording recipes and
output locations.

For a slow fixed-frame validation, use the coordinator's bounded checkpoint
workflow (available with coordinator 0.1.18):

```sh
task chromecast:check DEVICE=chromecast-test-01 APP=bsnes-jg-tv-phase2-native APK="<absolute frozen APK path>" DURATION=600 CHECKPOINT=frame TARGET=5800 ASYNC=true
```

Register the frozen layout benchmark activity before submitting this check.
The coordinator captures when the registered frame checkpoint reaches 5800,
or retains partial evidence if the duration expires. Follow the returned job
with `watch`, retrieve its proof with `evidence`, and restore the app's normal
activity after completion. A completed checkpoint still needs the project's
canonical pixel comparison; session success alone does not establish correctness.

## Ownership and availability rules

For phone test sequences, keep preparation gaps covered. While a test is running,
queue `task chromecast:keep-awake DEVICE=phone-pixel-8-pro DURATION=600 ASYNC=true`
to follow it if further preparation is needed. Watch that job. Once the next test
is ready, submit it to the same device queue and cancel only your keep-awake job;
wait for its cleanup and watch the next test. The test's own session handles wake
pulses while it runs. Cancel any unused keep-awake job at the end of the sequence
and retrieve its evidence. Do not leave the phone idle while building, analyzing,
or changing the app registration between tests.

Keep-awake occupies the device, respects reservations, and cannot unlock an
already locked phone. Its 600-second maximum is a bound, not an indefinite lease;
finish preparation or arrange the next owned job before it expires. Do not change
the phone's persistent lock settings to work around a missed hand-off.

- A job is the complete device session. Keep its launch, input, capture and
  cleanup inside the coordinator workflow; do not split ownership across raw
  ADB or local control scripts.
- Honor existing personal reservations and queued work. Do not create or
  release Will's reservation from an agent session.
- Closing a watcher does not cancel its job. Cancel only a job this session
  created, using its exact printed ID.
- For reconnection, use `task chromecast:readd DEVICE=…`; do not probe or
  reconnect with direct ADB.
- If the task entry point, coordinator CLI or service is unavailable, stop
  device work and report the outage. There is no direct-device fallback.
- Use `task chromecast:evidence` for coordinator evidence. Follow project
  policy for whether the resulting files belong in committed proof or private
  diagnostics.

## Extending this project's task surface

Keep the consumer commands in `Taskfile.chromecast.yml`, separate from the
main project Taskfile. Preserve the coordinator's shared `WF_CC_*` environment
mapping so variables and CLI arguments reach the service. Each task should
dispatch to `python3 ../chromecast-coordinator/scripts/chromecast.py task <operation>` from
`../chromecast-coordinator/`. Do not copy coordinator implementation code or
add raw ADB commands. Document new task names here and verify discovery with
`task --list` before using them.
