#!/usr/bin/env python3
"""pair.py BUILDS REPEATS FRAMES -- run pair.html REPEATS times (fresh page each), print paired ratios vs the first build."""
import json, sys, glob, statistics as st
from playwright.sync_api import sync_playwright
builds, reps, frames = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
exe = glob.glob("/home/will/.cache/ms-playwright/chromium_headless_shell-*/chrome-*/chrome-headless-shell")[0]
out = {"builds": builds.split(","), "runs": []}
with sync_playwright() as p:
    br = p.chromium.launch(executable_path=exe); out["chromium"] = br.version
    for i in range(reps):
        ctx = br.new_context(); pg = ctx.new_page()
        pg.goto(f"http://127.0.0.1:8177/pair.html?b={builds}&frames={frames}&chunk=100")
        r = pg.evaluate("go()"); ctx.close(); out["runs"].append(r)
        base = r["chunks"][0]
        msg = [f"{b}: mean {st.mean(c[2:]):.2f} ms, median ratio {st.median([x / y for x, y in zip(c[2:], base[2:])]):.4f}" for b, c in zip(r["builds"], r["chunks"])]
        print(i, r["gates"], " | ".join(msg), file=sys.stderr, flush=True)
    br.close()
json.dump(out, sys.stdout, indent=1)
