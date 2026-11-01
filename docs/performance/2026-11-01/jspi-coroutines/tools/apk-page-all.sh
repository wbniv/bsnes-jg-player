#!/usr/bin/env bash
set -euo pipefail
# apk-page-all.sh OUTDIR APK... -- apk-page-check.py on each APK in Playwright's headless Chromium and in
# Google Chrome, one after another; JSON per run into OUTDIR.
if [[ "${1:-}" == -h || "${1:-}" == --help || $# -lt 2 ]]; then echo "usage: apk-page-all.sh OUTDIR APK..."; exit 0; fi
ulimit -c 0
H="$(cd "$(dirname "$0")" && pwd)"; O="$1"; shift; mkdir -p "$O"
for apk in "$@"; do
  for exe in default /usr/bin/google-chrome; do
    tag="$(basename "$apk" .apk)-$( [[ $exe == default ]] && echo headless || echo chrome )"
    echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] $tag"
    python3 "$H/apk-page-check.py" "$apk" "$exe" 20 1800 > "$O/$tag.json" || echo "rc=$? for $tag"
    python3 -c "import json,sys; d=json.load(open(sys.argv[1])); print(' ', d['browser'], 'ready', d['reference_ready'], 'engine', d['engine_info'] and d['engine_info']['jspi'], 'windows', d['playback_windows'], 'core', d['median_core_mean_ms'], 'errors', d['pageerrors'])" "$O/$tag.json"
  done
done
