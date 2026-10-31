#!/usr/bin/env bash
set -euo pipefail
umask 077

repo="$(cd "$(dirname "$0")/../.." && pwd)"
parameter_name='/indri-studio/bsnes-jg/android/release/signing-payload'
aws_profile="${BSNES_AWS_PROFILE:-${INDRI_AWS_PROFILE:-wf-terraform}}"
aws_region="${BSNES_AWS_REGION:-${INDRI_AWS_REGION:-us-west-2}}"
cache_dir="$repo/.private/android-release"
cleanup_paths=()
cleanup() {
  if ((${#cleanup_paths[@]})); then
    rm -rf -- "${cleanup_paths[@]}"
  fi
}
trap cleanup EXIT

require_aws_access() {
  aws sts get-caller-identity --profile "$aws_profile" --region "$aws_region" \
    --query Account --output text >/dev/null
}

pull() {
  require_aws_access
  mkdir -p "$cache_dir"
  chmod 700 "$cache_dir"
  local payload_tmp
  payload_tmp="$(mktemp "$cache_dir/payload.XXXXXX")"
  cleanup_paths+=("$payload_tmp")
  chmod 600 "$payload_tmp"
  aws ssm get-parameter --profile "$aws_profile" --region "$aws_region" \
    --name "$parameter_name" --with-decryption \
    --query Parameter.Value --output text > "$payload_tmp"
  python3 - "$payload_tmp" "$cache_dir" <<'PY'
import base64
import json
import os
import pathlib
import sys

payload = json.loads(pathlib.Path(sys.argv[1]).read_text())
directory = pathlib.Path(sys.argv[2])
files = {
    "release.p12": base64.b64decode(payload["keystoreBase64"], validate=True),
    "store-password": payload["storePassword"].encode(),
    "key-alias": payload["keyAlias"].encode(),
}
for name, data in files.items():
    path = directory / name
    path.write_bytes(data)
    os.chmod(path, 0o600)
PY
  echo "Release signing cache refreshed in ignored .private/android-release/"
}

inspect() {
  require_aws_access
  aws ssm describe-parameters --profile "$aws_profile" --region "$aws_region" \
    --query "Parameters[?contains(Name, 'bsnes') || contains(Name, 'biohack') || contains(Name, 'indri')].Name" \
    --output text
}

bootstrap() {
  require_aws_access
  local existing_names
  existing_names="$(inspect)"
  if grep -Eiq 'android|apk|release|signing|keystore' <<< "$existing_names"; then
    echo 'Found a possibly related SSM parameter. Inspect parameter names first; refusing to create another signing identity.' >&2
    exit 1
  fi
  if aws ssm get-parameter --profile "$aws_profile" --region "$aws_region" \
      --name "$parameter_name" >/dev/null 2>&1; then
    echo "Refusing to replace existing release signing material in SSM." >&2
    exit 1
  fi
  local temp_dir payload_json alias
  temp_dir="$(mktemp -d)"
  cleanup_paths+=("$temp_dir")
  chmod 700 "$temp_dir"
  openssl rand -hex 32 > "$temp_dir/store-password"
  chmod 600 "$temp_dir/store-password"
  alias='bsnes-jg-public-release'
  keytool -genkeypair -noprompt -storetype PKCS12 \
    -keystore "$temp_dir/release.p12" \
    -storepass:file "$temp_dir/store-password" \
    -keypass:file "$temp_dir/store-password" \
    -alias "$alias" -keyalg RSA -keysize 4096 -validity 10000 \
    -dname 'CN=bsnes-jg Android Release, O=Biohack' >/dev/null
  chmod 600 "$temp_dir/release.p12"
  base64 -w0 "$temp_dir/release.p12" > "$temp_dir/keystore.b64"
  chmod 600 "$temp_dir/keystore.b64"
  payload_json="$temp_dir/parameter.json"
  python3 - "$temp_dir" "$payload_json" "$alias" <<'PY'
import json
import pathlib
import sys

directory = pathlib.Path(sys.argv[1])
payload = {
    "keystoreBase64": (directory / "keystore.b64").read_text(),
    "storePassword": (directory / "store-password").read_text().strip(),
    "keyAlias": sys.argv[3],
}
request = {
    "Name": "/indri-studio/bsnes-jg/android/release/signing-payload",
    "Description": "Encrypted Android public release signing material for bsnes-jg",
    "Type": "SecureString",
    "Tier": "Advanced",
    "Value": json.dumps(payload, separators=(",", ":")),
    "Overwrite": False,
}
pathlib.Path(sys.argv[2]).write_text(json.dumps(request))
PY
  chmod 600 "$payload_json"
  aws ssm put-parameter --profile "$aws_profile" --region "$aws_region" \
    --cli-input-json "file://$payload_json" \
    --query Version --output text >/dev/null
  pull
  echo "Durable release signing material is stored in AWS SSM SecureString."
}

build() {
  [[ -s "$cache_dir/release.p12" && -s "$cache_dir/store-password" && -s "$cache_dir/key-alias" ]] || {
    echo 'Run task android:release-secrets-pull before building.' >&2
    exit 1
  }
  export BJG_RELEASE_KEYSTORE="$cache_dir/release.p12"
  export BJG_RELEASE_KEYSTORE_PASSWORD="$(<"$cache_dir/store-password")"
  export BJG_RELEASE_KEY_ALIAS="$(<"$cache_dir/key-alias")"
  export BJG_RELEASE_KEY_PASSWORD="$BJG_RELEASE_KEYSTORE_PASSWORD"
  export BJG_PUBLIC_RELEASE=1
  exec "$repo/android/build-in-container.sh"
}

case "${1:-}" in
  bootstrap) bootstrap ;;
  inspect) inspect ;;
  pull) pull ;;
  build) build ;;
  *) echo "Usage: $0 {inspect|bootstrap|pull|build}" >&2; exit 2 ;;
esac
