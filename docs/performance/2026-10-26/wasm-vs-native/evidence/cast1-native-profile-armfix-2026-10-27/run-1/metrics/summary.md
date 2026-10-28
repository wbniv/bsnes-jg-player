# Phase 1 WebView metrics — logcat.txt

Parsed 252 structured events and 250 rolling playback windows.
Intervals are app-side observations. RAF intervals are callback spacing, not compositor presentation.
Window quantiles summarize window-level values; they are not per-frame distributions.

| Measure | Windows | Min | Median | p95 | p99 | Max |
|---|---:|---:|---:|---:|---:|---:|
| Core mean per 60-frame window (ms) | 250 | 60.978 | 63.781 | 65.337 | 66.157 | 66.563 |
| Core p95 per 60-frame window (ms) | 250 | 64.758 | 70.716 | 83.994 | 94.168 | 95.373 |
| Canvas submission mean per callback (ms) | 250 | 1.343 | 1.429 | 1.530 | 1.620 | 6.496 |
| Canvas submission p95 per callback (ms) | 250 | 1.358 | 1.538 | 1.763 | 2.061 | 26.228 |
| WebView RAF interval p95 (ms) | 250 | 254.779 | 263.221 | 277.768 | 287.360 | 288.605 |
| Peak emulation backlog (frames) | 250 | 40.640 | 5528.610 | 10511.770 | 10952.760 | 11040.960 |

## Event counts

| Event | Count |
|---|---:|
| core_ready | 1 |
| playback_window | 250 |
| rom_loaded | 1 |
