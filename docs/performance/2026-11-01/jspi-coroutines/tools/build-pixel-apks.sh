#!/usr/bin/env bash
set -euo pipefail
# build-pixel-apks.sh TREE OUT [STEP...] -- build the JSPI Pixel measurement APKs in a scratch copy TREE of this
# repository (vendor/, android/app/build caches, .private symlink and ../biohack.net, ../llvm-mos-65816 links
# prepared; the experimental engine files in TREE/.experimental/jspi-core) and copy the wasm-flavor APKs to OUT.
# Steps (default: all, in this order):
#   default-orig  main's build.gradle.kts, no -P: the control for "default build unchanged"
#   default-new   this branch's build.gradle.kts, no -P: must equal default-orig and pass every pinned check
#   jspi-debugkey experimental engine, package org.bsnesjg.tv.phase2, signed with ~/.android/debug.keystore
#   jspi-release  experimental engine, package org.bsnesjg.tv.phase2.jspi, signed with the durable release key
if [[ "${1:-}" == -h || "${1:-}" == --help || $# -lt 2 ]]; then sed -n 3,11p "$0" | sed 's/^# \{0,1\}//'; exit 0; fi
ulimit -c 0
H="$(cd "$(dirname "$0")" && pwd)"; R="$(cd "$H/../../../../.." && pwd)"
TREE="$(cd "$1" && pwd)"; OUT="$2"; shift 2
STEPS=("${@:-default-orig default-new jspi-debugkey jspi-release}"); [[ $# -eq 0 ]] && STEPS=(default-orig default-new jspi-debugkey jspi-release)
mkdir -p "$OUT"
E="$TREE/.experimental/jspi-core"
sha() { sha256sum "$1" | cut -d' ' -f1; }
EXP="-PexperimentalWasmDir=.experimental/jspi-core -PexperimentalWasmGlueSha=$(sha "$E/bsnes_jg.js") -PexperimentalWasmSha=$(sha "$E/bsnes_jg.wasm") -PexperimentalWasmAppSha=$(sha "$E/app.js") -PexperimentalWasmProvenanceSha=$(sha "$E/PROVENANCE.json")"
VER=(ORG_GRADLE_PROJECT_releaseVersionName=0.1.10 ORG_GRADLE_PROJECT_releaseVersionCode=11)
ts() { date -u +%Y-%m-%dT%H:%M:%SZ; }
wasm_apk="$TREE/android/app/build/outputs/apk/wasm/release/app-wasm-release.apk"
for step in "${STEPS[@]}"; do
  echo "[$(ts)] === $step; / free $(df -h --output=avail / | tail -1)"
  if [[ $step == default-orig ]]; then git -C "$R" show main:android/app/build.gradle.kts > "$TREE/android/app/build.gradle.kts"
  else cp "$R/android/app/build.gradle.kts" "$TREE/android/app/build.gradle.kts"; fi
  rm -f "$wasm_apk"
  case $step in
    default-orig|default-new) env "${VER[@]}" "$TREE/android/build-in-container.sh" ;;
    jspi-debugkey) env "${VER[@]}" BJG_GRADLE_EXTRA="$EXP" "$TREE/android/build-in-container.sh" ;;
    jspi-release) env "${VER[@]}" BJG_GRADLE_EXTRA="$EXP -PwasmIdSuffixExtra=.jspi :app:verifyReleaseArtifact" \
                    "$TREE/android/tools/release-signing-secrets.sh" build ;;
    *) echo "unknown step $step" >&2; exit 2 ;;
  esac
  cp "$wasm_apk" "$OUT/$step.apk"
  echo "[$(ts)] $step -> $OUT/$step.apk $(sha "$OUT/$step.apk")"
done
cp "$R/android/app/build.gradle.kts" "$TREE/android/app/build.gradle.kts"
echo "[$(ts)] done; / free $(df -h --output=avail / | tail -1)"
