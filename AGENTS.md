# Shared Chromecast device work

Use `task chromecast:*` from this repository for all Chromecast testing. The
project task namespace forwards to the shared service in `../chromecast-coordinator/`;
that coordinator owns each complete device session, including install, launch,
input, capture, profiling and cleanup.

Before submitting work, inspect `task chromecast:devices` and
`task chromecast:queue`. Submit only through the matching task, follow its job
with `task chromecast:watch`, and retrieve proof with `task chromecast:evidence`.
Cancel only jobs submitted by the current session. A watcher exiting does not
cancel its job. Use `task chromecast:readd` for reconnects. If the coordinator
or service is unavailable, stop device work until it is available again.

Never use raw Chromecast ADB, direct device-control scripts, or another
project's copied harness as a fallback. Do not bypass coordinator ownership by
connecting directly to a device. Follow the repository how-to at
[`docs/how-to/use-the-chromecast-coordinator.md`](docs/how-to/use-the-chromecast-coordinator.md)
for the complete workflow and task examples.
