#!/usr/bin/env bash
# Downloads the stock Roblox files for build version-75f1039cb4964863 into stock/
# and checks their sha256. Skips files that are already present and correct.
set -euo pipefail
cd "$(dirname "$0")/.."   # repo root
BASE=https://setup.rbxcdn.com/webclient/version-75f1039cb4964863-RobloxWebClient
sha() { if command -v sha256sum >/dev/null; then sha256sum "$1" | cut -d' ' -f1; else shasum -a 256 "$1" | cut -d' ' -f1; fi; }
mkdir -p stock
fetch() {  # fetch <file> <sha256>
  local f=$1 want=$2
  if [ -f "stock/$f" ] && [ "$(sha "stock/$f")" = "$want" ]; then echo "stock/$f OK"; return; fi
  echo "downloading $BASE/$f"
  curl -fL --retry 3 -o "stock/$f.part" "$BASE/$f"
  local got; got=$(sha "stock/$f.part")
  if [ "$got" != "$want" ]; then
    echo "WARNING: stock/$f sha256 is $got, expected $want (Roblox may have replaced the build). Kept it anyway."
  fi
  mv "stock/$f.part" "stock/$f"; echo "stock/$f ready"
}
fetch WebClient.wasm d72c52618f5c153c9b17a97e644914d43918c7122d754d96f79e8323acc6a15d
fetch WebClient.js   81e38a0d9ff71728bb2c04ff578bd71ba720c0a72ff94b78e55f8356042d1228
