#!/usr/bin/env bash
set -euo pipefail

# sync-roms.sh — refresh the bundled demo ROMs from a sibling llvm-mos-65816 checkout.
# The ROMs are homebrew built by that project's +mos-a16 toolchain; we snapshot a few
# graphical demos here so the page runs out of the box.

usage() {
  cat <<EOF
Usage: ./sync-roms.sh [-h] [SRC_BUILD_DIR]

Copies the demo .sfc ROMs into web/roms/.

  SRC_BUILD_DIR   path to llvm-mos-65816/build (DEFAULT: ../llvm-mos-65816/build)
EOF
}
[ "${1:-}" = "-h" ] || [ "${1:-}" = "--help" ] && { usage; exit 0; }

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SRC="${1:-$ROOT/../llvm-mos-65816/build}"
ROMS=(mandel-display lzss-gallery)
# lzss-gallery's manifest entry (mode "live-record") asserts a `gallery_shown` WRAM record. That
# record is defined in llvm-mos-65816 main's examples/snes/lzss-gallery.c (the
# `feature/verify-fidelity-button` branch has merged), so a build from main carries it. A missing
# build only WARNs below and leaves the committed web/roms ROM untouched.

[ -d "$SRC" ] || { echo "ERROR: source build dir not found: $SRC" >&2; exit 1; }

mkdir -p "$ROOT/web/roms"
for r in "${ROMS[@]}"; do
  if [ -f "$SRC/$r.sfc" ]; then
    cp -v "$SRC/$r.sfc" "$ROOT/web/roms/$r.sfc"
  else
    echo "WARN: $SRC/$r.sfc missing — skipped" >&2
  fi
done
echo "done."
