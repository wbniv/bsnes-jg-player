#!/usr/bin/env bash
set -euo pipefail
# apk-facts.sh APK... -- per APK: sha256, package/version (aapt2), signer certificate SHA-256 (apksigner),
# launchable activity, MandelbrotBenchmarkActivity present, and the sha256 of its WASM engine assets.
if [[ "${1:-}" == -h || "${1:-}" == --help || $# -eq 0 ]]; then echo "usage: apk-facts.sh APK..."; exit 0; fi
B=/home/will/android-sdk-local/build-tools/34.0.0
for a in "$@"; do
  echo "== $a"
  echo "apk sha256:  $(sha256sum "$a" | cut -d' ' -f1)  ($(stat -c %s "$a") bytes)"
  "$B/aapt2" dump badging "$a" 2>/dev/null | grep -E "^package:" | sed 's/ platformBuild.*//'
  "$B/aapt2" dump xmltree --file AndroidManifest.xml "$a" 2>/dev/null | grep -c 'MandelbrotBenchmarkActivity' | sed 's/^/MandelbrotBenchmarkActivity mentions in manifest: /'
  "$B/apksigner" verify --print-certs "$a" 2>/dev/null | grep -E "certificate (DN|SHA-256)"
  "$B/apksigner" verify -v "$a" 2>/dev/null | grep -E "^Verified using v[0-9] scheme.*true" | tr '\n' ' '; echo
  for f in assets/cores/bsnes_jg.wasm assets/cores/bsnes_jg.js assets/cores/PROVENANCE.json assets/app.js; do
    echo "$f: $(unzip -p "$a" "$f" | sha256sum | cut -d' ' -f1)"
  done
done
