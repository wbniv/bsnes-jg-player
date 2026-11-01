#!/usr/bin/env python3
"""cmp.py BASE.json VARIANT.json [BASE_BUILD VARIANT_BUILD] -- compare per-checkpoint video hashes and gates (WRAM is clock()-seeded, so not compared whole)."""
import json, sys
def load(p, b=None):
    for r in json.load(open(p))["runs"]:
        if "roms" in r and (b is None or r["build"] == b): return r
bb, vb = (sys.argv[3], sys.argv[4]) if len(sys.argv) > 4 else (None, None)  # pick builds out of one check file
base, var = load(sys.argv[1], bb), load(sys.argv[2], vb)
ok = True
for a, b in zip(base["roms"], var["roms"]):
    va = [c[1]["video"] for c in a["cps"]]; vb = [c[1]["video"] for c in b["cps"]]
    same = va == vb and a["gate"] == b["gate"]
    ok &= same
    print(f'{var["build"]:8} {a["rom"]:15} frames={a["frames"]:5} checkpoints={len(va):3} video_match={va == vb} gate base={a["gate"]} var={b["gate"]} {"OK" if same else "DIFF " + b.get("error", "")}')
print("ALL MATCH" if ok and len(base["roms"]) == len(var["roms"]) else "MISMATCH")
