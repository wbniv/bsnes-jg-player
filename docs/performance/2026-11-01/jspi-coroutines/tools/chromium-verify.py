#!/usr/bin/env python3
"""chromium-verify.py URL [EXE] -- the Chromium counterpart of scripts/firefox-verify.py: load the player URL
(normally ...?verify=1) in headless Chromium via Playwright and wait up to 15 min for the #checkresult badge to
settle on a verdict. EXE defaults to Playwright's chrome-headless-shell; pass /usr/bin/google-chrome for Chrome."""
import glob, json, sys, time
from playwright.sync_api import sync_playwright
if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help"): print(__doc__); sys.exit(0)
url = sys.argv[1]
exe = sys.argv[2] if len(sys.argv) > 2 else glob.glob("/home/will/.cache/ms-playwright/chromium_headless_shell-*/chrome-*/chrome-headless-shell")[0]
JS = """() => { const b = document.getElementById('checkresult');
  return {badge: b ? b.textContent : null, cls: b ? b.className : null, ua: navigator.userAgent,
          coi: window.crossOriginIsolated, jspi: typeof WebAssembly.Suspending, title: document.title}; }"""
with sync_playwright() as p:
    br = p.chromium.launch(executable_path=exe, headless=True)
    pg = br.new_page(); errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)))
    t0 = time.time(); pg.goto(url); last = None
    while time.time() - t0 < 900:
        last = pg.evaluate(JS)
        b = last["badge"] or ""
        if "FIDELITY" in b or "✗" in b or "MISMATCH" in b or "FAIL" in b.upper(): break
        time.sleep(1)
    last.update(browser=br.version, seconds=round(time.time() - t0, 1), pageerrors=errs)
    print(json.dumps(last, ensure_ascii=False, indent=1)); br.close()
