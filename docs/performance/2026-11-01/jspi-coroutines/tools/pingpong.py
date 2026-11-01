#!/usr/bin/env python3
"""pingpong.py [N] [REPEATS] -- time pp_run(N) (2N libco switches) for pp-asyncify and pp-jspi, interleaved,
in Playwright's headless Chromium; prints ns per switch for each repeat and the medians."""
import glob, json, statistics as st, sys
from playwright.sync_api import sync_playwright
if sys.argv[1:2] in (["-h"], ["--help"]): print(__doc__); sys.exit(0)
N = int(sys.argv[1]) if len(sys.argv) > 1 else 200000
REPS = int(sys.argv[2]) if len(sys.argv) > 2 else 5
exe = glob.glob("/home/will/.cache/ms-playwright/chromium_headless_shell-*/chrome-*/chrome-headless-shell")[0]
JS = """async ([b, n]) => {
  await new Promise((ok, no) => { const s = document.createElement('script'); s.src = 'builds/' + b + '/bsnes_jg.js'; s.onload = ok; s.onerror = no; document.head.appendChild(s); });
  const M = await BsnesJg({ locateFile: f => 'builds/' + b + '/' + f });
  { const w = M._pp_run(1000); if (w && w.then) await w; }   // warm up
  const t = performance.now(); const r = M._pp_run(n); if (r && r.then) await r; const ms = performance.now() - t;
  return ms * 1e6 / (2 * n);
}"""
res = {"pp-asyncify": [], "pp-jspi": []}
with sync_playwright() as p:
    br = p.chromium.launch(executable_path=exe)
    for i in range(REPS):
        for b in (list(res) if i % 2 == 0 else list(res)[::-1]):
            pg = br.new_page(); pg.goto("http://127.0.0.1:8177/jspi-probe.html")
            res[b].append(pg.evaluate(JS, [b, N])); pg.close()
        print(i, {b: round(v[-1], 1) for b, v in res.items()}, file=sys.stderr, flush=True)
    ver = br.version; br.close()
print(json.dumps({"chromium": ver, "switchesPerRun": 2 * N, "nsPerSwitch": res,
                  "median": {b: round(st.median(v), 1) for b, v in res.items()}}))
