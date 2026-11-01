#!/usr/bin/env python3
"""probe.py [smoke BUILD FRAMES] -- report JSPI support in Playwright's headless Chromium and the installed
Google Chrome (jspi-probe.html on 127.0.0.1:8177); with 'smoke', also boot BUILD in each and run FRAMES frames."""
import glob, json, sys
from playwright.sync_api import sync_playwright
if sys.argv[1:2] in (["-h"], ["--help"]): print(__doc__); sys.exit(0)
smoke = sys.argv[1:2] == ["smoke"]
exes = {"headless-shell": glob.glob("/home/will/.cache/ms-playwright/chromium_headless_shell-*/chrome-*/chrome-headless-shell")[0],
        "google-chrome": "/usr/bin/google-chrome"}
with sync_playwright() as p:
    for name, exe in exes.items():
        br = p.chromium.launch(executable_path=exe, headless=True)
        pg = br.new_page(); errs = []
        pg.on("pageerror", lambda e: errs.append(str(e)))
        pg.goto("http://127.0.0.1:8177/jspi-probe.html"); pg.wait_for_function("window.ready === true")
        r = {"browser": name, "version": br.version, "probe": pg.inner_text("#checkresult")}
        if smoke:
            b, n = sys.argv[2], int(sys.argv[3])
            pg.goto(f"http://127.0.0.1:8177/bench.html?b={b}"); pg.wait_for_function("window.ready === true", timeout=120000)
            x = pg.evaluate(f"run('mandel-display', {n}, 0, 'none', {{times: true}})")
            r["smoke"] = {k: x.get(k) for k in ("frames", "gate", "msPerFrame", "medianFrameMs")}
            r["switches"] = pg.evaluate("typeof M !== 'undefined' && M.CoJspiSwitches ? M.CoJspiSwitches() : null")
        r["pageerrors"] = errs
        print(json.dumps(r)); br.close()
