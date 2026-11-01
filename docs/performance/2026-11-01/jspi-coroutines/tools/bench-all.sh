#!/usr/bin/env bash
set -euo pipefail
# bench-all.sh [BUILDS] [REPEATS] [FRAMES] -- the timing protocol of the 2026-10-31 trim plan, run on BUILDS
# (default baseline,jspi) against the server on 127.0.0.1:8177: paired lockstep (pair.py), then separate cold
# pages (drive.py time), then the libco switch microbenchmark (pingpong.py). Results go next to this tools dir.
if [[ "${1:-}" == -h || "${1:-}" == --help ]]; then echo "usage: bench-all.sh [BUILDS] [REPEATS] [FRAMES]"; exit 0; fi
ulimit -c 0
H="$(cd "$(dirname "$0")" && pwd)"; O="$(dirname "$H")"; T="$H/../../../2026-10-31/asyncify-trim/tools"
B="${1:-baseline,jspi}"; N="${2:-5}"; F="${3:-1500}"
ts() { date -u +%Y-%m-%dT%H:%M:%SZ; }
echo "[$(ts)] start; $(uptime)"; echo "governor $(cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor)"
python3 "$T/pair.py" "$B" "$N" "$F" > "$O/pair.json"
python3 "$T/pairsumm.py" "$O/pair.json" baseline
echo "[$(ts)] pair done; $(uptime)"
python3 "$T/drive.py" time "$B" "$N" "$F" > "$O/bench.json"
python3 "$T/summ.py" "$O/bench.json"
echo "[$(ts)] cold pages done; $(uptime)"
python3 "$H/pingpong.py" 200000 "$N" > "$O/pingpong.json"
cat "$O/pingpong.json"; echo
echo "[$(ts)] end; $(uptime)"
