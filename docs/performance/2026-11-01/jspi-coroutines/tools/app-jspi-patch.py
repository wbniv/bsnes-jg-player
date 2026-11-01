#!/usr/bin/env python3
"""app-jspi-patch.py IN_APP_JS OUT_APP_JS -- make a scratch copy of web/app.js drive a core whose _bjg_run returns
a Promise (JSPI). Every core call goes through runCore(), which records the in-flight frame; the rAF loop skips a
tick while one is in flight, verify() awaits each frame and waits for an in-flight frame before re-loading the ROM.
Still works unchanged with the synchronous Asyncify core (runCore returns undefined). The benchmark() TV hook is
left synchronous: it is not exercised here."""
import sys
if len(sys.argv) != 3 or sys.argv[1] in ("-h", "--help"): print(__doc__); sys.exit(0 if sys.argv[1:2] in (["-h"], ["--help"]) else 2)
s = open(sys.argv[1]).read()
def sub(old, new, count=1):
    global s
    n = s.count(old)
    if n != count: sys.exit(f"patch anchor found {n}x, want {count}: {old[:70]!r}")
    s = s.replace(old, new)
sub("  function frame(timestamp) {\n    if (!running) return;\n",
    "  // JSPI cores return a Promise from _bjg_run; never start a frame while another is in flight.\n"
    "  function runCore() {\n"
    "    var pr = Module._bjg_run();\n"
    "    if (pr && pr.then) { window.__bjgInflight = pr; pr.then(function () { if (window.__bjgInflight === pr) window.__bjgInflight = null; }); }\n"
    "    return pr;\n"
    "  }\n\n"
    "  function frame(timestamp) {\n    if (!running) return;\n"
    "    if (window.__bjgInflight) { rafId = requestAnimationFrame(frame); return; }\n")
sub("      var coreStart = performance.now();\n      Module._bjg_run();\n",
    "      var coreStart = performance.now();\n      runCore();\n")
sub("    (function chunk() {\n      for (var i = 0; i < poll; i++) Module._bjg_run();\n",
    "    (async function chunk() {\n      for (var i = 0; i < poll; i++) await runCore();\n")
sub("      .then(function (buf) {\n        if (verification !== task || task.cancelled) return;\n        if (!loadRomBytes(",
    "      .then(function (buf) { return Promise.resolve(window.__bjgInflight).then(function () { return buf; }); })\n"
    "      .then(function (buf) {\n        if (verification !== task || task.cancelled) return;\n        if (!loadRomBytes(")
sub("        function chunk() {\n          if (verification !== task || task.cancelled) {",
    "        async function chunk() {\n          if (verification !== task || task.cancelled) {")
sub("          do {\n            Module._bjg_run();\n            done++;",
    "          do {\n            await runCore();\n            done++;")
open(sys.argv[2], "w").write(s)
print("patched", sys.argv[2])
