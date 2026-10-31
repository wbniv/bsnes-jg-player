#!/usr/bin/env python3
"""pairsumm.py PAIR.json [REF] -- per-build ratio to REF (default 'baseline'): per-repeat medians and pooled chunk quartiles (first 2 chunks dropped as warmup)."""
import json, sys, statistics as st
d = json.load(open(sys.argv[1])); ref = sys.argv[2] if len(sys.argv) > 2 else "baseline"
bs = d["builds"]; ri = bs.index(ref)
for i, b in enumerate(bs):
    if i == ri: continue
    reps, pooled = [], []
    for r in d["runs"]:
        x = [a / c for a, c in zip(r["chunks"][i][2:], r["chunks"][ri][2:])]
        reps.append(st.median(x)); pooled += x
    q = st.quantiles(pooled, n=4)
    ms = [st.mean(r["chunks"][i][2:]) for r in d["runs"]]; mr = [st.mean(r["chunks"][ri][2:]) for r in d["runs"]]
    print(f"{b} / {ref}: per-repeat median ratios {[round(v, 3) for v in reps]} -> median {st.median(reps):.3f}; pooled chunks n={len(pooled)} median {st.median(pooled):.3f} IQR {q[0]:.3f}-{q[2]:.3f}; ms/frame {b} median {st.median(ms):.2f} [{min(ms):.2f}-{max(ms):.2f}] {ref} median {st.median(mr):.2f} [{min(mr):.2f}-{max(mr):.2f}]")
