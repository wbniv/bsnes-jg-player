#!/usr/bin/env bash
set -euo pipefail
# sizes.sh [BUILD...] -- raw and gzip -9 size and sha256 of each $OUT/builds/BUILD/bsnes_jg.wasm (default OUT /tmp/jspi-coro)
if [[ "${1:-}" == -h || "${1:-}" == --help ]]; then echo "usage: [OUT=dir] sizes.sh [BUILD...]"; exit 0; fi
S="${OUT:-/tmp/jspi-coro}"
printf '%-14s %10s %12s %10s  %s\n' build raw_bytes gzip9_bytes glue_js wasm_sha256
for b in "${@:-baseline jspi}"; do
  w="$S/builds/$b/bsnes_jg.wasm"
  printf '%-14s %10s %12s %10s  %s\n' "$b" "$(stat -c %s "$w")" "$(gzip -9c "$w" | wc -c)" "$(stat -c %s "$S/builds/$b/bsnes_jg.js")" "$(sha256sum "$w" | cut -d' ' -f1)"
done
