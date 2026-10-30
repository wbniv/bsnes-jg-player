#!/usr/bin/env bash
set -euo pipefail

# deploy-bundle.sh — emit a self-contained, single-program bundle for hosting or
# embedding elsewhere (e.g. indri.studio's /apps/llvm-mos-65816/ inline embed).
#
# The bundle is just static files with RELATIVE asset paths, so it works under
# any base path. An embedding page points the loader at it with
#   window.BJG_BASE = "/apps/llvm-mos-65816/play/";
#   window.BJG_DEFAULT_ROM = "mandel-display";
# and includes <script src="…/play/app.js">. A direct visit to the bundle's
# index.html runs the same demo standalone.

usage() {
  cat <<'EOF'
Usage: ./deploy-bundle.sh [OUT_DIR]

Emits a single-program emulator bundle (default ROM: mandel-display) into
OUT_DIR (DEFAULT: ./dist-bundle). Builds the core first if it's missing.

Env overrides:
  BUNDLE_ROM   demo ROM id to ship (DEFAULT: mandel-display)
EOF
}
[ "${1:-}" = "-h" ] || [ "${1:-}" = "--help" ] && { usage; exit 0; }

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OUT="${1:-$ROOT/dist-bundle}"
ROM="${BUNDLE_ROM:-mandel-display}"
log() { echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] $*"; }

[ -f "$ROOT/web/roms/$ROM.sfc" ] || { echo "ERROR: no web/roms/$ROM.sfc" >&2; exit 1; }

# Build the core if it hasn't been built yet.
if [ ! -f "$ROOT/web/cores/bsnes_jg.wasm" ] || [ ! -f "$ROOT/web/cores/bsnes_jg.js" ]; then
  log "core not built — running build.sh"
  "$ROOT/build.sh"
fi

log "assembling bundle for '$ROM' → $OUT"
rm -rf "$OUT"
mkdir -p "$OUT/cores" "$OUT/roms"
cp "$ROOT/web/cores/bsnes_jg.js" "$ROOT/web/cores/bsnes_jg.wasm" "$OUT/cores/"
cp "$ROOT/web/cores/PROVENANCE.json" "$OUT/cores/" 2>/dev/null || true
cp "$ROOT/web/roms/$ROM.sfc" "$OUT/roms/"
cp "$ROOT/web/app.js" "$OUT/app.js"

# Coarse loading-preview image (painted on the canvas while the core downloads). Ship it
# only if this ROM has one (regenerate with ./make-preview.sh); absence just shows black.
if [ -f "$ROOT/web/preview/$ROM.png" ]; then
  mkdir -p "$OUT/preview"
  cp "$ROOT/web/preview/$ROM.png" "$OUT/preview/"
fi

# Single-ROM manifest (carries the fidelity self-check metadata for this ROM).
python3 - "$ROOT/web/roms/manifest.json" "$ROM" "$OUT/roms/manifest.json" <<'PY'
import json, sys
src, rom, dst = sys.argv[1], sys.argv[2], sys.argv[3]
m = json.load(open(src))
roms = [r for r in m.get("roms", []) if r.get("id") == rom]
json.dump({"_comment": m.get("_comment", ""), "roms": roms},
          open(dst, "w"), indent=2)
PY

# Per-asset content hashes for cache-busting. The page injects them as window.BJG_BUST and
# app.js appends "?v=<sha>" to every fetch (incl. the wasm via locateFile), so the assets can be
# served immutable yet a re-sync (same filename, new bytes -> new sha) busts the cache.
bust_hash() { sha256sum "$1" 2>/dev/null | cut -c1-12; }
BUST="{"
for a in app.js cores/bsnes_jg.js cores/bsnes_jg.wasm cores/PROVENANCE.json roms/manifest.json "roms/$ROM.sfc" "preview/$ROM.png"; do
  [ -f "$OUT/$a" ] || continue
  BUST="$BUST\"$a\":\"$(bust_hash "$OUT/$a")\","
done
BUST="${BUST%,}}"
APPV="$(bust_hash "$OUT/app.js")"

# Minimal standalone page (used when the bundle URL is visited directly).
cat > "$OUT/index.html" <<HTML
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>$ROM — bsnes-jg-player</title>
<style>
  html,body{margin:0;background:#0c0e13;color:#e7e9ee;
    font:14px/1.5 ui-sans-serif,system-ui,sans-serif;}
  main{max-width:760px;margin:0 auto;padding:16px;}
  #game{width:100%;aspect-ratio:8/7;background:#000;border-radius:8px;overflow:hidden;display:flex;}
  #screen{width:100%;height:100%;object-fit:contain;image-rendering:pixelated;}
  .row{display:flex;gap:10px;align-items:center;flex-wrap:wrap;margin-top:10px;font-size:12px;}
  button{background:#1b1f2a;color:#e7e9ee;border:1px solid #262a36;border-radius:6px;
    padding:6px 12px;font-size:13px;cursor:pointer;}
  button:hover{border-color:#7cc4ff;color:#7cc4ff;}
  .badge{font-family:ui-monospace,monospace;}
  .badge.pass{color:#0c1116;background:#54d98c;font-weight:600;padding:2px 8px;border-radius:5px;}
  .badge.fail{color:#0c1116;background:#ff6b6b;font-weight:600;padding:2px 8px;border-radius:5px;}
  .badge.running{color:#ffd166;}
  #banner{margin-top:12px;font-size:12px;color:#9aa0ad;}
  code{font-family:ui-monospace,monospace;color:#7cc4ff;}
</style>
</head>
<body>
<main>
  <div id="game"><canvas id="screen" width="256" height="224"></canvas></div>
  <div class="row">
    <span id="status">loading core…</span>
    <span id="checkresult" class="badge"></span>
    <button id="verify" disabled style="margin-left:auto">Verify fidelity</button>
  </div>
  <div id="banner"></div>
</main>
<script>window.BJG_DEFAULT_ROM = "$ROM"; window.BJG_BUST = $BUST;</script>
<script src="app.js?v=$APPV"></script>
</body>
</html>
HTML

log "done:"
( cd "$OUT" && find . -type f | sort | sed 's/^/  /' )
