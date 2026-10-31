#!/usr/bin/env python3
"""drive.py MODE BUILD[,BUILD...] [REPEATS] -- MODE is 'check' (hash checkpoints) or 'time' (interleaved timing)."""
import json, sys, glob, time
from playwright.sync_api import sync_playwright
mode, builds = sys.argv[1], sys.argv[2].split(",")
reps = int(sys.argv[3]) if len(sys.argv) > 3 else 5
FR = int(sys.argv[4]) if len(sys.argv) > 4 else 5800
exe = glob.glob("/home/will/.cache/ms-playwright/chromium_headless_shell-*/chrome-*/chrome-headless-shell")[0]
CHECKS = [("mandel-display", 5800, 500, "none", {}), ("lzss-gallery", 3000, 250, "gallery", {}),
          ("raycaster", 3000, 250, "ray", {}), ("mandel-display", 1200, 300, "none", {"resetAt": 600})]
out = {"mode": mode, "chromium": exe, "started": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "runs": []}
with sync_playwright() as p:
    br = p.chromium.launch(executable_path=exe)
    out["version"] = br.version
    def page(b):
        ctx = br.new_context(); pg = ctx.new_page()
        pg.on("pageerror", lambda e: out["runs"].append({"build": b, "pageerror": str(e)}))
        pg.goto(f"http://127.0.0.1:8177/bench.html?b={b}")
        pg.wait_for_function("window.ready === true", timeout=120000)
        return ctx, pg
    if mode == "check":
        for b in builds:
            ctx, pg = page(b)   # cold start per build
            r = {"build": b, "instMs": pg.evaluate("instMs"), "roms": []}
            for rom, n, ev, inp, o in CHECKS:  # same page: also exercises re-load of a second ROM
                try:
                    r["roms"].append(pg.evaluate("([a,b,c,d,e]) => run(a,b,c,d,e)", [rom, n, ev, inp, o]))
                except Exception as e:
                    r["roms"].append({"rom": rom, "gate": "ERROR", "error": str(e).split("\n")[0], "cps": [[0, {"wram": "-", "video": "-"}]]}); break
            r["swaps"] = pg.evaluate("globalThis.__swaps ? Array.from(globalThis.__swaps.entries()) : null")
            out["runs"].append(r); ctx.close()
            print(b, [(x["rom"], x["gate"], x["cps"][-1][1]["wram"], x["cps"][-1][1]["video"]) for x in r["roms"]], file=sys.stderr)
    else:
        for i in range(reps):
            for b in (builds if i % 2 == 0 else builds[::-1]):
                ctx, pg = page(b)
                x = pg.evaluate("run('mandel-display', %d, 0, 'none', {times: true})" % FR)
                x.pop("cps"); x.update(build=b, rep=i, instMs=pg.evaluate("instMs"))
                out["runs"].append(x); ctx.close()
                print(b, i, round(x["msPerFrame"], 3), round(x["medianFrameMs"], 3), x["gate"], file=sys.stderr)
    br.close()
json.dump(out, sys.stdout, indent=1)
