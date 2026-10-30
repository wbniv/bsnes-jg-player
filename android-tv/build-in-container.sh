#!/usr/bin/env bash
set -euo pipefail

here="$(cd "$(dirname "$0")" && pwd)"
repo="$(cd "$here/.." && pwd)"
sibling_root="$(cd "$repo/.." && pwd)"
gradle_cache="${GRADLE_USER_HOME:-$HOME/.gradle}"
android_sdk="${ANDROID_HOME:-}"
if [[ ! -f "$android_sdk/platforms/android-34/android.jar" ]]; then
  android_sdk="/home/will/android-sdk-local"
fi
image='bsnes-jg-tv-jdk:local'
public_release="${BJG_PUBLIC_RELEASE:-0}"
release_keystore="${BJG_RELEASE_KEYSTORE:-}"
if [[ "$public_release" == "1" ]]; then
  if [[ -z "$release_keystore" || ! -f "$release_keystore" ]]; then
    echo 'BJG_PUBLIC_RELEASE=1 requires BJG_RELEASE_KEYSTORE to name an existing PKCS12 keystore.' >&2
    exit 1
  fi
  for name in BJG_RELEASE_KEYSTORE_PASSWORD BJG_RELEASE_KEY_ALIAS BJG_RELEASE_KEY_PASSWORD; do
    if [[ -z "${!name:-}" ]]; then
      echo "BJG_PUBLIC_RELEASE=1 requires $name in the environment." >&2
      exit 1
    fi
  done
fi
version_name="$(sed -n 's/^[[:space:]]*versionName = "\([^"]*\)".*/\1/p' "$here/app/build.gradle.kts" | head -n 1)"
if [[ -z "$version_name" ]]; then
  echo 'Could not read Android versionName from app/build.gradle.kts.' >&2
  exit 1
fi
player_apk_slug="$(node -p 'JSON.parse(require("fs").readFileSync(process.argv[1], "utf8")).apkSlug' "$repo/demo-rom.json")"
player_rom_title="$(node -p 'JSON.parse(require("fs").readFileSync(process.argv[1], "utf8")).title' "$repo/demo-rom.json")"

if [[ "${REFRESH_PUBLISHED_LIBRARY:-0}" == "1" || ! -f "$here/app/build/generated/publishedLibrary/library.json" ]]; then
  python3 "$here/tools/sync-published-library.py" --output "$here/app/build/generated/publishedLibrary" --check
else
  python3 "$here/tools/sync-published-library.py" --output "$here/app/build/generated/publishedLibrary" --validate-only
fi

if [[ ! -f "$android_sdk/platforms/android-34/android.jar" ]]; then
  echo "Android 34 SDK missing at $android_sdk; set ANDROID_HOME to its installed path." >&2
  exit 1
fi

if ! docker info --format '{{json .SecurityOptions}}' | rg -q 'name=rootless'; then
  echo 'Select the rootless Docker endpoint before building.' >&2
  exit 1
fi

docker build -f "$here/Dockerfile.jdk" -t "$image" "$here"
container_args=(--rm --network none --cap-drop ALL --security-opt no-new-privileges \
  --user 0:0 -e GRADLE_USER_HOME=/gradle-cache -e ANDROID_HOME=/android-sdk \
  -e ORG_GRADLE_PROJECT_publicDownloadUrl="${ORG_GRADLE_PROJECT_publicDownloadUrl:-}" \
  -e BJG_PUBLIC_RELEASE="$public_release" \
  --mount "type=bind,src=$repo,dst=/workspace" \
  --mount "type=bind,src=$gradle_cache,dst=/gradle-cache" \
  --mount "type=bind,src=$android_sdk,dst=/android-sdk,readonly" \
  --mount "type=bind,src=$sibling_root/biohack.net,dst=/biohack.net,readonly" \
  --mount "type=bind,src=$sibling_root/llvm-mos-65816,dst=/llvm-mos-65816,readonly" \
  --mount type=bind,src=/home/will/.android/debug.keystore,dst=/root/.android/debug.keystore,readonly)
if [[ "$public_release" == "1" ]]; then
  container_args+=(
    -e BJG_RELEASE_KEYSTORE=/root/.android/bsnes-jg-release.keystore
    -e BJG_RELEASE_KEYSTORE_PASSWORD
    -e BJG_RELEASE_KEY_ALIAS
    -e BJG_RELEASE_KEY_PASSWORD
    --mount "type=bind,src=$release_keystore,dst=/root/.android/bsnes-jg-release.keystore,readonly"
  )
fi
container_args+=(--workdir /workspace/android-tv "$image")
if [[ "$public_release" == "1" ]]; then
  gradle_signing=''
  gradle_tasks=':app:verifyPublicReleaseSigning :app:verifyNativeReleaseArtifact :app:verifyNativeplayerReleaseArtifact'
else
  gradle_signing='-PcontrolledDebugSigning=true'
  gradle_tasks=':app:verifyDebugArtifact :app:verifyReleaseArtifact :app:verifyWasmplayerDebugArtifact :app:verifyWasmplayerReleaseArtifact :app:verifyNativeDebugArtifact :app:verifyNativeReleaseArtifact :app:verifyNativeplayerReleaseArtifact'
fi
build_commands="python3 tools/apply-core-patches.py ../vendor/bsnes-jg && python3 tools/generate-suite-icon.py && python3 tools/generate-app-icons.py && node --check ../web/app.js && node --check app/src/main/assets/tv.js && node --check app/src/main/assets/tv-player.js && node --check app/src/main/assets/performance-overlay.js && node --check app/src/main/assets/library.js && node --check app/src/main/assets/tv-scheduler.js && node --check app/src/wasm/assets/engine-adapter.js && node --check app/src/native/assets/engine-adapter.js && node --check tools/metrics-report.mjs && node --check tools/compare-report.mjs && node tools/compare-report.mjs && node test/frame-scheduler.test.mjs && node test/metrics-report.test.mjs && node ../bin/sync.mjs sync /tmp/bsnes-jg-tv-package-smoke --demo && node ../bin/sync.mjs sync --check /tmp/bsnes-jg-tv-package-smoke && exec ./gradlew $gradle_signing $gradle_tasks --offline --no-daemon"
docker run "${container_args[@]}" sh -c "$build_commands"

if [[ "$public_release" == "1" ]]; then
  cp "$here/app/build/outputs/apk/native/release/app-native-release.apk" "$here/app/build/outputs/apk/native/release/bsnes-jg_llvm-65816-torture-test-suite-on-snes-v${version_name}.apk"
  cp "$here/app/build/outputs/apk/nativeplayer/release/app-nativeplayer-release.apk" "$here/app/build/outputs/apk/nativeplayer/release/bsnes-jg_${player_apk_slug}-v${version_name}.apk"
  echo "Native SNES library APK: $here/app/build/outputs/apk/native/release/bsnes-jg_llvm-65816-torture-test-suite-on-snes-v${version_name}.apk"
  echo "Native ${player_rom_title} player APK: $here/app/build/outputs/apk/nativeplayer/release/bsnes-jg_${player_apk_slug}-v${version_name}.apk"
else
  cp "$here/app/build/outputs/apk/wasmplayer/release/app-wasmplayer-release.apk" "$here/app/build/outputs/apk/wasmplayer/release/bsnes-jg-wasm-player.apk"
  cp "$here/app/build/outputs/apk/wasm/release/app-wasm-release.apk" "$here/app/build/outputs/apk/wasm/release/bsnes-jg-wasm.apk"
  cp "$here/app/build/outputs/apk/native/release/app-native-release.apk" "$here/app/build/outputs/apk/native/release/bsnes-jg_llvm-65816-torture-test-suite-on-snes-v${version_name}.apk"
  cp "$here/app/build/outputs/apk/nativeplayer/release/app-nativeplayer-release.apk" "$here/app/build/outputs/apk/nativeplayer/release/bsnes-jg_${player_apk_slug}-v${version_name}.apk"
  echo "WASM ${player_rom_title} player APK: $here/app/build/outputs/apk/wasmplayer/release/bsnes-jg-wasm-player.apk"
  echo "WASM library APK: $here/app/build/outputs/apk/wasm/release/bsnes-jg-wasm.apk"
  echo "Native SNES library APK: $here/app/build/outputs/apk/native/release/bsnes-jg_llvm-65816-torture-test-suite-on-snes-v${version_name}.apk"
  echo "Native ${player_rom_title} player APK: $here/app/build/outputs/apk/nativeplayer/release/bsnes-jg_${player_apk_slug}-v${version_name}.apk"
fi
