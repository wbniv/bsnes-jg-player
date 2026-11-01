// Engine-adapter contract the library UI relies on: library.js shows "▶ Resume" and
// resumes instead of restarting when api.hasRom() && api.currentRom() === slug.
// Loads the REAL adapter sources in a Node vm with the Android bridge stubbed.
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";
import vm from "node:vm";

const asset = (path) => readFile(new URL(`../app/src/${path}`, import.meta.url), "utf8");

function nativeHarness(source) {
  const classes = new Set();
  const calls = [];
  const loadable = new Set(["mandel-display", "hello-world"]);
  const context = {
    console,
    Map,
    Promise,
    document: {
      documentElement: { classList: { add: (c) => classes.add(c), remove: (c) => classes.delete(c) } },
      querySelectorAll: () => [],
      getElementById: () => null,
    },
  };
  context.window = context;
  context.BjgAndroid = {
    // Mirrors MainActivity.Bridge: playRom resolves asynchronously through __bjgNativeResolve.
    playRom(slug, id) { calls.push(["playRom", slug]); setImmediate(() => context.__bjgNativeResolve(id, loadable.has(slug))); },
    pauseGame() { calls.push(["pauseGame"]); },
    resumeGame() { calls.push(["resumeGame"]); },
    showLibrary() { calls.push(["showLibrary"]); },
    restartGame(id) { setImmediate(() => context.__bjgNativeResolve(id, true)); },
    verifyGame(id) { setImmediate(() => context.__bjgNativeResolve(id, false)); },
    cancelVerify() {},
  };
  vm.runInNewContext(source, context);
  return { api: context.BJGTV, calls, classes };
}

test("native adapter currentRom() tracks the loaded ROM", async () => {
  const { api, calls, classes } = nativeHarness(await asset("native/assets/engine-adapter.js"));
  assert.equal(typeof api.currentRom, "function", "native adapter must expose currentRom()");
  assert.equal(api.currentRom(), "", "nothing loaded before any play");
  assert.equal(api.hasRom(), false);

  assert.equal(await api.play("mandel-display"), true);
  assert.equal(api.currentRom(), "mandel-display", "slug after a successful play");
  assert.equal(api.hasRom(), true);

  api.pause();
  assert.equal(api.currentRom(), "mandel-display", "still loaded while paused");
  api.showLibrary();
  assert.equal(api.currentRom(), "mandel-display", "still loaded while paused behind the library");
  api.resume();
  assert.equal(api.currentRom(), "mandel-display");
  api.background();
  assert.equal(api.currentRom(), "mandel-display", "backgrounding pauses, it does not unload");

  assert.equal(await api.play("missing-rom"), false);
  assert.equal(api.currentRom(), "", "a failed load clears the loaded ROM");
  assert.equal(api.hasRom(), false);
  assert.equal(classes.has("game-active"), false);

  assert.equal(await api.play("hello-world"), true);
  assert.equal(api.currentRom(), "hello-world", "a later successful play is reported");
  assert.deepEqual(calls.filter((c) => c[0] === "playRom").map((c) => c[1]), ["mandel-display", "missing-rom", "hello-world"]);
});

test("wasm adapter delegates to web/app.js, whose BJGTV defines currentRom()", async () => {
  const appended = [];
  const context = {
    document: {
      querySelectorAll: () => [],
      getElementById: () => null,
      createElement: () => ({}),
      body: { appendChild: (node) => appended.push(node) },
    },
  };
  context.window = context;
  vm.runInNewContext(await asset("wasm/assets/engine-adapter.js"), context);
  assert.equal(context.BJG_ENGINE, "wasm");
  assert.equal(appended.length, 1);
  assert.equal(appended[0].src, "app.js", "the WASM APK's BJGTV comes from web/app.js");
  const app = await readFile(new URL("../../web/app.js", import.meta.url), "utf8");
  assert.match(app, /window\.BJGTV = \{[\s\S]*?currentRom: function \(\) \{ return current; \}/,
    "web/app.js BJGTV must keep exposing currentRom()");
});
