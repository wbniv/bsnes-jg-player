#!/usr/bin/env python3
"""swapset.py CHECK.json OUT.txt -- union of wasm function names on the stack at any fiber swap."""
import json, re, sys, collections
d = json.load(open(sys.argv[1]))
fr = re.compile(r"^\s*at (?:bsnes_jg\.wasm\.)?(.*) \((?:http\S*|wasm://wasm/\S*?):wasm-function\[(\d+)\]")
names, stacks, swaps = collections.Counter(), 0, 0
for r in d["runs"]:
    for st, n in (r.get("swaps") or []):
        stacks += 1; swaps += n
        for line in st.split("\n"):
            m = fr.match(line)
            if m: names[m.group(1)] += n
open(sys.argv[2], "w").write("\n".join(sorted(names)) + "\n")
print(f"distinct stacks {stacks}, swaps {swaps}, distinct functions {len(names)}")
