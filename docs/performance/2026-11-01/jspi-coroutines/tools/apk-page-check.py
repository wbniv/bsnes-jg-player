#!/usr/bin/env python3
"""apk-page-check.py APK [EXE] [SECONDS] [MAX_SECONDS] -- host stand-in for the Pixel benchmark run, without a device.

Extracts the APK's assets/ and serves them at /assets/ (the WebView's appassets.androidplatform.net layout),
stubs the BjgAndroid bridge as MainActivity does for a benchmark launch (app version from the APK, overlay on,
empty prefs), and opens /assets/index.html?rom=mandel-display, which is the URL MandelbrotBenchmarkActivity
loads, in headless Chromium (Playwright's chrome-headless-shell, or EXE). It collects the page's BJG_TV_METRIC
console records, the records the WebView forwards to logcat, until reference_ready (frame 5800) has been seen
and SECONDS have passed, or MAX_SECONDS (default 900). Prints engine_info, reference_ready, the playback_window count and the
median core_mean_ms after 3 warm-up windows."""
import functools, glob, http.server, json, statistics as st, sys, tempfile, threading, time, zipfile
from playwright.sync_api import sync_playwright
if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help"): print(__doc__); sys.exit(0)
apk = sys.argv[1]
exe = sys.argv[2] if len(sys.argv) > 2 and sys.argv[2] != "default" else glob.glob("/home/will/.cache/ms-playwright/chromium_headless_shell-*/chrome-*/chrome-headless-shell")[0]
hold = float(sys.argv[3]) if len(sys.argv) > 3 else 30
limit = float(sys.argv[4]) if len(sys.argv) > 4 else 900
root = tempfile.mkdtemp(prefix="apk-page-", dir="/tmp/jspi-apk")
with zipfile.ZipFile(apk) as z:
    z.extractall(root, [n for n in z.namelist() if n.startswith("assets/")])
class H(http.server.SimpleHTTPRequestHandler):
    extensions_map = {**http.server.SimpleHTTPRequestHandler.extensions_map, ".wasm": "application/wasm", ".js": "application/javascript"}
    def log_message(self, *a): pass
srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(H, directory=root))
threading.Thread(target=srv.serve_forever, daemon=True).start()
url = f"http://127.0.0.1:{srv.server_address[1]}/assets/index.html?rom=mandel-display"
STUB = """window.BjgAndroid = { getAppVersion: () => "host-check", getPlayerRomSlug: () => "mandel-display",
  getPlayerRomTitle: () => "Mandelbrot", hasPlayerRomSelfCheck: () => true, setGameRect: () => {},
  getPerformanceOverlayEnabled: () => true, setPerformanceOverlayEnabled: () => true, getPrefs: () => "{}",
  setPrefs: () => true, exitApp: () => {}, shareApk: () => {} };"""
recs, errs = [], []
with sync_playwright() as p:
    br = p.chromium.launch(executable_path=exe, headless=True)
    pg = br.new_page(viewport={"width": 1280, "height": 720})
    pg.add_init_script(STUB)
    pg.on("console", lambda m: recs.append(json.loads(m.text[14:])) if m.text.startswith("BJG_TV_METRIC ") else None)
    pg.on("pageerror", lambda e: errs.append(str(e)))
    t0 = time.time(); pg.goto(url); ready_at = None
    while time.time() - t0 < limit:
        pg.wait_for_timeout(1000)
        if ready_at is None and any(r.get("event") == "reference_ready" for r in recs): ready_at = time.time()
        if ready_at and time.time() - ready_at >= hold: break
    ver = br.version; br.close()
srv.shutdown()
win = [r for r in recs if r.get("event") == "playback_window"]
core = [r["core_mean_ms"] for r in win[3:] if "core_mean_ms" in r]
out = {"apk": apk, "browser": ver, "seconds": round(time.time() - t0, 1),
       "engine_info": next((r for r in recs if r.get("event") == "engine_info"), None),
       "reference_ready": next((r for r in recs if r.get("event") == "reference_ready"), None),
       "playback_windows": len(win), "median_core_mean_ms": round(st.median(core), 3) if core else None,
       "median_emu_fps": round(st.median([r["emu_fps"] for r in win[3:]]), 2) if len(win) > 3 else None,
       "events": sorted({r.get("event") for r in recs}), "pageerrors": errs}
print(json.dumps(out, indent=1))
