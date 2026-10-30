#!/usr/bin/env bash
# stage-dist.sh — copy the canonical player + built core into dist/ (the committed
# npm payload). web/ stays the single source; dist/ is generated-and-committed so
# `npm publish` and `npm i git+…` never depend on an emsdk build.
#
# dist/engine/  app.js + cores/{bsnes_jg.js,bsnes_jg.wasm,PROVENANCE.json}
# dist/demo/    the single ROM selected by demo-rom.json + its manifest and preview
set -euo pipefail

usage() { echo "usage: stage-dist.sh [-h|--help]  — stage web/ artifacts into dist/"; }
case "${1:-}" in -h|--help) usage; exit 0;; esac

cd "$(dirname "$0")/.."

for f in web/app.js web/cores/bsnes_jg.js web/cores/bsnes_jg.wasm web/cores/PROVENANCE.json; do
  [[ -f "$f" ]] || { echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) missing $f — run ./build.sh first" >&2; exit 1; }
done

DEMO_ROM_CONFIG=demo-rom.json
demo_slug="$(node -p 'JSON.parse(require("fs").readFileSync(process.argv[1], "utf8")).slug' "$DEMO_ROM_CONFIG")"
demo_sha256="$(node -p 'JSON.parse(require("fs").readFileSync(process.argv[1], "utf8")).sha256' "$DEMO_ROM_CONFIG")"
actual_demo_sha256="$(sha256sum "web/roms/$demo_slug.sfc" | cut -d ' ' -f 1)"
[[ "$actual_demo_sha256" == "$demo_sha256" ]] || {
  echo "stage-dist: web/roms/$demo_slug.sfc hash mismatch: $actual_demo_sha256" >&2
  exit 1
}

# dist/demo is a generated, allow-listed package payload. Clear it before staging so
# A former ROM choice does not remain in the next npm artifact.
rm -rf dist/demo

mkdir -p dist/engine/cores dist/demo/roms dist/demo/preview
cp web/app.js dist/engine/app.js
cp web/cores/bsnes_jg.js web/cores/bsnes_jg.wasm web/cores/PROVENANCE.json dist/engine/cores/

cp "web/roms/$demo_slug.sfc" dist/demo/roms/
cp "web/preview/$demo_slug.png" dist/demo/preview/

# The package manifest is built from the selected ROM config. The web harness manifest can
# describe additional site-owned ROMs, so copying it wholesale would create missing-asset rows.
python3 - "$DEMO_ROM_CONFIG" dist/demo/roms/manifest.json <<'PY'
import json, sys
config = json.load(open(sys.argv[1], encoding="utf-8"))
entry = {"id": config["slug"], "title": config["title"]}
if config.get("selfcheck"):
    check = config["selfcheck"]
    entry["selfcheck"] = {
        "off": check["offset"],
        "len": 2,
        "want": check["want"],
        "frames": check["frames"],
        "label": f"{config['title']} WRAM fidelity check",
    }
with open(sys.argv[2], "w", encoding="utf-8") as output:
    json.dump({"roms": [entry]}, output, indent=2, ensure_ascii=False)
    output.write("\n")
PY

echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) staged dist/ from web/:"
( cd dist && find . -type f -printf '  %-40p %10s bytes\n' | sort )
