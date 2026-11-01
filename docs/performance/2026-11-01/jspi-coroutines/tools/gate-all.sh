#!/usr/bin/env bash
set -euo pipefail
# gate-all.sh -- fidelity gates against the server on 127.0.0.1:8177 (root /tmp/jspi-coro):
#   1. drive.py check on the fixed-seed builds (baseline-seed twice, jspi-seed once), strict WRAM+video compare;
#   2. ?verify=1 in headless Chromium (Playwright shell) and Google Chrome on web-jspi and web-base.
# Firefox ?verify=1 is run separately with scripts/firefox-verify.py (it needs a Marionette Firefox).
if [[ "${1:-}" == -h || "${1:-}" == --help ]]; then echo "usage: gate-all.sh"; exit 0; fi
ulimit -c 0
H="$(cd "$(dirname "$0")" && pwd)"; O="$(dirname "$H")"; T="$H/../../../2026-10-31/asyncify-trim/tools"
ts() { date -u +%Y-%m-%dT%H:%M:%SZ; }
echo "[$(ts)] seeded check"
python3 "$T/drive.py" check baseline-seed,jspi-seed,baseline-seed > "$O/check-seed.json"
rc=0; python3 "$H/seedcmp.py" "$O/check-seed.json" baseline-seed jspi-seed baseline-seed || rc=$?
echo "seedcmp rc=$rc"
for site in web-jspi web-base; do
  for exe in default /usr/bin/google-chrome; do
    echo "[$(ts)] verify $site $exe"
    if [[ $exe == default ]]; then python3 "$H/chromium-verify.py" "http://127.0.0.1:8177/$site/?verify=1"
    else python3 "$H/chromium-verify.py" "http://127.0.0.1:8177/$site/?verify=1" "$exe"; fi
  done
done
echo "[$(ts)] end"
