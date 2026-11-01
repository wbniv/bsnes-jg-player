#!/usr/bin/env bash
set -euo pipefail
# Regression test: sync-roms.sh must not overwrite a committed ROM with different bytes
# unless --force is given. Runs against a throwaway git repo; touches nothing in this one.

if [ "${1:-}" = "-h" ] || [ "${1:-}" = "--help" ]; then
  echo "Usage: scripts/sync-roms-guard.test.sh"; exit 0
fi

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
T="$(mktemp -d)"; trap 'rm -rf "$T"' EXIT
mkdir -p "$T/repo/web/roms" "$T/build"
cp "$HERE/sync-roms.sh" "$T/repo/"
printf 'committed' > "$T/repo/web/roms/mandel-display.sfc"
printf 'lzss-same' > "$T/repo/web/roms/lzss-gallery.sfc"
git -C "$T/repo" init -q
git -C "$T/repo" add -A
git -C "$T/repo" -c user.name=t -c user.email=t@t commit -qm init
printf 'rebuilt' > "$T/build/mandel-display.sfc"
printf 'lzss-same' > "$T/build/lzss-gallery.sfc"

fail() { echo "FAIL: $*" >&2; exit 1; }

if "$T/repo/sync-roms.sh" "$T/build" >/dev/null 2>&1; then fail "synced over a differing committed ROM"; fi
[ "$(cat "$T/repo/web/roms/mandel-display.sfc")" = committed ] || fail "committed ROM was modified"
echo "PASS: refuses a differing committed ROM, leaves it untouched"

"$T/repo/sync-roms.sh" --force "$T/build" >/dev/null 2>&1 || fail "--force run failed"
[ "$(cat "$T/repo/web/roms/mandel-display.sfc")" = rebuilt ] || fail "--force did not overwrite"
echo "PASS: --force overwrites"

"$T/repo/sync-roms.sh" "$T/build" >/dev/null 2>&1 || fail "identical bytes should sync without --force"
echo "PASS: identical bytes sync without --force"
