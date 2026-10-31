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

// Native (Java) engine: MainActivity.onDrawFrame is not unit-testable here, so pin its catch-up cap in the
// source and check a JS model of the same arithmetic. Covers the cap constant and the model's behaviour,
// not the Java execution itself. Unlike the JS scheduler above (which recovers a stall in full), the native
// path drops missed time beyond MAX_CATCHUP_STEPS.
const java = await readFile(new URL("../app/src/main/java/org/bsnesjg/tv/MainActivity.java", import.meta.url), "utf8");
const capMatch = java.match(/static final int MAX_CATCHUP_STEPS\s*=\s*(\d+);/);
assert.ok(capMatch, "MainActivity must declare MAX_CATCHUP_STEPS");
const maxCatchup = Number(capMatch[1]);
assert.equal(maxCatchup, 4, "native catch-up cap is one callback of work (4 steps)");
assert.ok(java.includes("credit=Math.min(credit,MAX_CATCHUP_STEPS);"), "onDrawFrame must clamp credit after the update");
assert.ok(java.includes("Math.min(MAX_CATCHUP_STEPS,(int)credit)"), "per-callback steps must use the same cap");

function nativeModel() { // mirrors the credit arithmetic in MainActivity.onDrawFrame
  let credit = 0, last = null;
  return function (nowMs) {
    if (last === null) last = nowMs;
    credit += Math.min(0.25, (nowMs - last) / 1000) * rate;
    last = nowMs;
    credit = Math.min(credit, maxCatchup);
    const steps = Math.min(maxCatchup, Math.floor(credit));
    credit -= steps;
    return { steps, credit };
  };
}

// Slow core (~64 ms/frame): callbacks arrive every steps*64 ms; credit must stay bounded, not grow forever.
{
  const step = nativeModel();
  let t = 0, peak = 0, frames = 0;
  for (let i = 0; i < 2000; i++) {
    const r = step(t);
    peak = Math.max(peak, r.credit);
    frames += r.steps;
    t += Math.max(16.7, r.steps * 64);
  }
  assert.ok(peak <= maxCatchup, `slow device credit must stay bounded (peak ${peak})`);
  assert.ok(frames / (t / 1000) < 20, "a slow core must not run faster than its own speed");
}

// A 10 s stall followed by healthy 60 Hz callbacks must not fast-forward.
{
  const step = nativeModel();
  step(0);
  const stall = step(10_000);
  assert.ok(stall.steps <= maxCatchup, "the stalled callback is limited to the per-callback cap");
  let t = 10_000, resumed = 0, worst = 0;
  for (let i = 0; i < 60; i++) {
    t += 1000 / 60;
    const r = step(t);
    resumed += r.steps;
    worst = Math.max(worst, r.steps);
  }
  assert.ok(worst <= 2, `after a stall steps per callback return to normal (worst ${worst})`);
  assert.ok(Math.abs(resumed - 60.0988) < 4, `no stored catch-up burst after a stall (ran ${resumed} in 1 s)`);
}

console.log("TV frame scheduler checks passed: 50/59.94/60/120 Hz and bounded stall recovery, native catch-up cap");
