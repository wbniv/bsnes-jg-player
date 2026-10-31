import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import vm from "node:vm";

const source = await readFile(new URL("../app/src/main/assets/tv-scheduler.js", import.meta.url), "utf8");
const context = {};
vm.runInNewContext(source, context);
const create = context.BJGFrameScheduler.create;
const rate = 60.0988;

for (const displayHz of [50, 59.94, 60, 120]) {
  const clock = create(rate, 4);
  const callbacks = Math.round(displayHz * 600);
  const period = 1000 / displayHz;
  let frames = 0;
  let maxSteps = 0;
  for (let i = 0; i <= callbacks; i++) {
    const result = clock.advance(i * period);
    frames += result.steps;
    maxSteps = Math.max(maxSteps, result.steps);
    assert.ok(result.steps <= 4, "per-callback work must stay bounded");
    assert.ok(result.pending >= 0 && result.pending < 4, "fractional/backlog credit must be retained");
  }
  const elapsedSeconds = callbacks / displayHz;
  assert.ok(Math.abs(frames - elapsedSeconds * rate) < 1.1,
    `${displayHz} Hz display must preserve the ${rate} Hz SNES clock (got ${frames})`);
  if (displayHz === 50) assert.ok(maxSteps <= 2, "50 Hz output should use one or two SNES frames per callback");
  if (displayHz === 120) assert.ok(maxSteps <= 1, "120 Hz output should not run multiple frames each callback");
}

const stalled = create(rate, 4);
let caughtUp = stalled.advance(0).steps;
caughtUp += stalled.advance(1000).steps;
for (let i = 0; i < 20; i++) caughtUp += stalled.advance(1000).steps;
assert.equal(caughtUp, 61, "a one-second scheduling stall should be recovered without dropping SNES frames");
assert.ok(stalled.pending() < 1, "scheduler should drain the accumulated stall backlog");
stalled.reset();
assert.equal(stalled.pending(), 0, "pause/resume reset must clear stale scheduling credit");

console.log("TV frame scheduler checks passed: 50/59.94/60/120 Hz and bounded stall recovery");
