#!/usr/bin/env python3
"""summ.py BENCH.json -- per-build median/min/max of steady ms per frame across repeats."""
import json, sys, statistics as st
d = json.load(open(sys.argv[1])); by = {}
for r in d["runs"]:
    if "steadyMsPerFrame" in r: by.setdefault(r["build"], []).append(r)
base = None
for b, rs in by.items():
    s = [r["steadyMsPerFrame"] for r in rs]; m = [r["medianFrameMs"] for r in rs]
    med = st.median(s); base = base or med
    print(f"{b:9} n={len(s)} steady mean ms/frame: median {med:.3f} min {min(s):.3f} max {max(s):.3f} | per-frame median: median {st.median(m):.3f} | vs first {100*(med/base-1):+.1f}% | gate {set(r['gate'] for r in rs)}")
