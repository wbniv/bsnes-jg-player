#!/usr/bin/env python3
"""seedcmp.py CHECK.json BASE_BUILD VARIANT_BUILD [BASE_BUILD2] -- strict comparison for builds linked with seed.o
(constant clock(), so power-on RAM is deterministic): WRAM *and* framebuffer hashes must be equal at every
checkpoint, and the gate values equal. With BASE_BUILD2 it first checks the baseline against a second
baseline run, to show the seed made WRAM deterministic at all."""
import json, sys
if len(sys.argv) < 4 or sys.argv[1] in ("-h", "--help"): print(__doc__); sys.exit(0)
runs = [r for r in json.load(open(sys.argv[1]))["runs"] if "roms" in r]
def get(b, k=0): return [r for r in runs if r["build"] == b][k]
def compare(a, b, label):
    ok = True
    for x, y in zip(a["roms"], b["roms"]):
        w = [c[1]["wram"] for c in x["cps"]] == [c[1]["wram"] for c in y["cps"]]
        v = [c[1]["video"] for c in x["cps"]] == [c[1]["video"] for c in y["cps"]]
        g = x["gate"] == y["gate"]; ok &= w and v and g and len(x["cps"]) == len(y["cps"])
        print(f'{label:24} {x["rom"]:15} frames={x["frames"]:5} checkpoints={len(x["cps"]):3} wram_match={w} video_match={v} gate base={x["gate"]} var={y["gate"]} {"OK" if w and v and g else "DIFF " + y.get("error", "")}')
    ok &= len(a["roms"]) == len(b["roms"])
    print(f'{label}: {"ALL MATCH" if ok else "MISMATCH"}'); return ok
ok = True
if len(sys.argv) > 4: ok &= compare(get(sys.argv[2]), get(sys.argv[4], 1 if sys.argv[4] == sys.argv[2] else 0), f"{sys.argv[2]} vs {sys.argv[4]}")
ok &= compare(get(sys.argv[2]), get(sys.argv[3]), f"{sys.argv[2]} vs {sys.argv[3]}")
sys.exit(0 if ok else 1)
