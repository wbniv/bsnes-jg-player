#!/usr/bin/env python3
"""apkdiff.py A.apk B.apk -- compare two APKs entry by entry (name, CRC-32, size), ignoring the v1 signature
files under META-INF/. Prints each differing entry and SAME or DIFF; exits 1 on any difference."""
import sys, zipfile
if len(sys.argv) != 3 or sys.argv[1] in ("-h", "--help"): print(__doc__); sys.exit(0)
def entries(p):
    with zipfile.ZipFile(p) as z:
        return {i.filename: (i.CRC, i.file_size) for i in z.infolist()
                if not (i.filename.startswith("META-INF/") and i.filename.rsplit(".", 1)[-1] in ("SF", "RSA", "MF", "EC", "DSA"))}
a, b = entries(sys.argv[1]), entries(sys.argv[2])
diff = sorted(n for n in a.keys() | b.keys() if a.get(n) != b.get(n))
for n in diff: print("differs:", n, a.get(n), b.get(n))
print(f"{len(a)} vs {len(b)} entries; {'SAME' if not diff else 'DIFF'}")
sys.exit(1 if diff else 0)
