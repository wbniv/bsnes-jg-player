#!/usr/bin/env python3
"""app-jspi-patch.py IN_APP_JS OUT_APP_JS -- derive the experimental app.js that drives a JSPI core, whose
_bjg_run returns a Promise. web/app.js itself is never changed; the output is staged only by an opt-in build.

Every core call goes through runCore(), which records the in-flight frame. Each call site that runs frames
awaits it: the rAF frame() loop (the path the Android MandelbrotBenchmarkActivity measures), verify(),
verifyLiveRecord() and the TV benchmark() hook. A JSPI frame resumes its coroutines only through promise
reactions (microtasks), so an awaited frame still completes inside the same rAF task, before the browser can
run any other callback: the frame loop's scheduling, step cap and core timing bracket are unchanged, and the
timed interval contains only the core call plus the switches JSPI itself requires. The rAF loop also skips
a tick if a frame is somehow still in flight, and verify() waits for one before re-loading the ROM.
In TV mode it logs one extra BJG_TV_METRIC record, engine_info, after each ROM load: whether
WebAssembly.Suspending exists and the WebView's user agent, so a device run records its JSPI support.
With a synchronous (Asyncify) core runCore() returns undefined and every await is skipped."""
import sys
if sys.argv[1:2] in (["-h"], ["--help"]): print(__doc__); sys.exit(0)
if len(sys.argv) != 3: print(__doc__); sys.exit(2)
s = open(sys.argv[1]).read()
def sub(old, new, count=1):
    global s
    n = s.count(old)
    if n != count: sys.exit(f"patch anchor found {n}x, want {count}: {old[:70]!r}")
    s = s.replace(old, new)
# rAF loop: async, awaited steps, in-flight guard
sub("  function frame(timestamp) {\n    if (!running) return;\n",
    "  // JSPI cores return a Promise from _bjg_run; never start a frame while another is in flight.\n"
    "  function runCore() {\n"
    "    var pr = Module._bjg_run();\n"
    "    if (pr && pr.then) { var clear = function () { if (window.__bjgInflight === pr) window.__bjgInflight = null; }; window.__bjgInflight = pr; pr.then(clear, clear); }\n"
    "    return pr;\n"
    "  }\n\n"
    "  async function frame(timestamp) {\n    if (!running) return;\n"
    "    if (window.__bjgInflight) { rafId = requestAnimationFrame(frame); return; }\n")
sub("      var coreStart = performance.now();\n      Module._bjg_run();\n",
    "      var coreStart = performance.now();\n"
    "      try { var pending = runCore(); if (pending) await pending; }\n"
    "      catch (e) { tvMetric(\"core_error\", { message: String(e && e.stack || e).slice(0, 1500) }); break; }\n")
# live-record self-check (gallery)
sub("    (function chunk() {\n      for (var i = 0; i < poll; i++) Module._bjg_run();\n",
    "    (async function chunk() {\n      for (var i = 0; i < poll; i++) { var pending = runCore(); if (pending) await pending; }\n")
# power-on self-check (?verify=1, mandel-display)
sub("      .then(function (buf) {\n        if (verification !== task || task.cancelled) return;\n        if (!loadRomBytes(",
    "      .then(function (buf) { return Promise.resolve(window.__bjgInflight).then(function () { return buf; }); })\n"
    "      .then(function (buf) {\n        if (verification !== task || task.cancelled) return;\n        if (!loadRomBytes(")
sub("        function chunk() {\n          if (verification !== task || task.cancelled) {",
    "        async function chunk() {\n          if (verification !== task || task.cancelled) {")
sub("          do {\n            Module._bjg_run();\n            done++;",
    "          do {\n            var pending = runCore(); if (pending) await pending;\n            done++;")
# TV benchmark() hook (F9)
sub("          function chunk() {\n            var until = Math.min(totalFrames, done + 60);",
    "          async function chunk() {\n            var until = Math.min(totalFrames, done + 60);")
sub("var t = performance.now(); Module._bjg_run(); coreNs +=",
    "var t = performance.now(); var pending = runCore(); if (pending) await pending; coreNs +=")
# record JSPI support with every ROM load (TV mode only; tvMetric is a no-op elsewhere)
sub('      tvMetric("rom_loaded", { rom: current || DEFAULT_ROM, bytes: bytes.length });\n',
    '      tvMetric("rom_loaded", { rom: current || DEFAULT_ROM, bytes: bytes.length });\n'
    '      tvMetric("engine_info", { core: "jspi", jspi: typeof WebAssembly.Suspending === "function", ua: navigator.userAgent });\n'
    '      if (!window.__bjgBeat) { var beats = 0; window.__bjgBeat = setInterval(function () {\n'
    '        tvMetric("jspi_heartbeat", { frames: tvMetrics.frames, rom_frames: tvMetrics.romFrames, running: running, inflight: !!window.__bjgInflight });\n'
    '        if (++beats >= 30) clearInterval(window.__bjgBeat); }, 2000); }\n')
if "Module._bjg_run()" in s.replace("var pr = Module._bjg_run();", ""):
    sys.exit("an unpatched _bjg_run call site remains")
open(sys.argv[2], "w").write(s)
print("patched", sys.argv[2])
