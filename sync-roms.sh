#!/usr/bin/env bash
set -euo pipefail

# sync-roms.sh — refresh the bundled demo ROMs from a sibling llvm-mos-65816 checkout.
# The ROMs are homebrew built by that project's +mos-a16 toolchain; we snapshot a few
# graphical demos here so the page runs out of the box.

usage() {
  cat <<EOF
Usage: ./sync-roms.sh [-h] [--force] [SRC_BUILD_DIR]

Copies the demo .sfc ROMs into web/roms/.

  SRC_BUILD_DIR   path to llvm-mos-65816/build (DEFAULT: ../llvm-mos-65816/build)
  --force         overwrite a committed ROM even when the source bytes differ

Without --force the script refuses, before copying anything, if a ROM that git
tracks in web/roms/ differs from the source build. The committed ROMs are the
ones the pinned fidelity checks were recorded against.
EOF
}
FORCE=0
ARGS=()
for a in "$@"; do
  case "$a" in
    -h|--help) usage; exit 0 ;;
    --force) FORCE=1 ;;
    *) ARGS+=("$a") ;;
  esac
done
set -- ${ARGS[@]+"${ARGS[@]}"}

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SRC="${1:-$ROOT/../llvm-mos-65816/build}"
ROMS=(mandel-display lzss-gallery)
# lzss-gallery's manifest entry (mode "live-record") asserts a `gallery_shown` WRAM record. That
# record is defined in llvm-mos-65816 main's examples/snes/lzss-gallery.c (the
# `feature/verify-fidelity-button` branch has merged), so a build from main carries it. A missing
# build only WARNs below and leaves the committed web/roms ROM untouched.

[ -d "$SRC" ] || { echo "ERROR: source build dir not found: $SRC" >&2; exit 1; }

if [ "$FORCE" -ne 1 ]; then
  clobber=()
  for r in "${ROMS[@]}"; do
    dst="$ROOT/web/roms/$r.sfc"
    if [ -f "$SRC/$r.sfc" ] && [ -f "$dst" ] \
       && git -C "$ROOT" ls-files --error-unmatch "web/roms/$r.sfc" >/dev/null 2>&1 \
       && ! cmp -s "$SRC/$r.sfc" "$dst"; then
      clobber+=("$r.sfc")
    fi
  done
  if [ "${#clobber[@]}" -gt 0 ]; then
    echo "ERROR: refusing to overwrite committed ROM(s) whose bytes differ from $SRC: ${clobber[*]}" >&2
    echo "       Re-run with --force if the new build is intended." >&2
    exit 1
  fi
fi

mkdir -p "$ROOT/web/roms"
for r in "${ROMS[@]}"; do
  if [ -f "$SRC/$r.sfc" ]; then
    cp -v "$SRC/$r.sfc" "$ROOT/web/roms/$r.sfc"
  else
    echo "WARN: $SRC/$r.sfc missing — skipped" >&2
  fi
done
echo "done."
