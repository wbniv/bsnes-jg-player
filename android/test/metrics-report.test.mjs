import assert from "node:assert/strict";
import { parseMetrics, playbackCsv, summaryMarkdown, pacingSvg } from "../tools/metrics-report.mjs";

const log = [
  "10-26 10:00:00.000  123 I/BJG_TV_METRIC: {\"event\":\"core_ready\",\"t_ms\":100}",
  "10-26 10:00:01.000  123 I/BJG_TV_METRIC: {\"event\":\"playback_window\",\"t_ms\":1100,\"rom_run\":1,\"frames\":60,\"rom_frames\":60,\"sample_frames\":60,\"window_ms\":1000,\"target_hz\":60.0988,\"core_mean_ms\":2,\"core_p95_ms\":3,\"core_max_ms\":4,\"canvas_callbacks\":60,\"canvas_submit_mean_ms\":1,\"canvas_submit_p95_ms\":2,\"canvas_submit_max_ms\":3,\"raf_interval_p95_ms\":17,\"raf_interval_max_ms\":20,\"emulation_backlog_frames\":0,\"peak_backlog_frames\":0}",
  "unrelated Android log line",
  "10-26 10:00:02.000  123 I/BJG_TV_METRIC: {truncated"
].join("\n");

const events = parseMetrics(log);
assert.equal(events.length, 2, "only complete structured metric records should be parsed");
assert.match(playbackCsv(events), /core_mean_ms/);
assert.match(playbackCsv(events), /2,3,4/);
assert.match(summaryMarkdown(events, "sample.log"), /Window quantiles summarize window-level values/);
assert.match(summaryMarkdown(events, "sample.log"), /\| Core mean per 60-frame window/);
assert.match(pacingSvg(events, "fixture & test"), /fixture &amp; test/);
assert.match(pacingSvg([], "empty"), /No playback_window records/);

console.log("TV metrics parser/report checks passed");
