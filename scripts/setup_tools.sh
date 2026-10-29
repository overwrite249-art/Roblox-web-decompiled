#!/usr/bin/env bash
# Downloads the three toolchains (tested versions) into <repo>/tools
#   tools/wasm-tools  bytecodealliance wasm-tools v1.262.0  (disassembler + compiler: wasm <-> wat)
#   tools/binaryen    binaryen version_133                  (wasm-opt: strips exnref EH before decompiling)
#   tools/wabt        wabt 1.0.36                           (wasm-decompile: wasm -> pseudo-C)
set -euo pipefail
cd "$(dirname "$0")/.."   # repo root
mkdir -p tools
OS=$(uname -s); ARCH=$(uname -m)
WABT_VER=1.0.36
case "$OS-$ARCH" in
  Linux-x86_64)          WT=x86_64-linux;  BN=x86_64-linux;  WB=wabt-1.0.36-ubuntu-20.04.tar.gz ;;
  Linux-aarch64)         WT=aarch64-linux; BN=aarch64-linux; WABT_VER=1.0.41; WB=wabt-1.0.41-linux-arm64.tar.gz ;;
  Darwin-x86_64)         WT=x86_64-macos;  BN=x86_64-macos;  WB=wabt-1.0.36-macos-12.tar.gz ;;
  Darwin-arm64)          WT=aarch64-macos; BN=arm64-macos;   WB=wabt-1.0.36-macos-14.tar.gz ;;
  *) echo "Unsupported platform $OS-$ARCH. On Windows run this inside WSL (Ubuntu)."; exit 1 ;;
esac
get() {  # get <url> <dest-dir-name>
  local url=$1 name=$2 tmp
  if [ -d "tools/$name" ]; then echo "tools/$name already present"; return; fi
  echo "downloading $url"
  tmp=$(mktemp -d)
  curl -fL --retry 3 -o "$tmp/a.tgz" "$url"
  tar xzf "$tmp/a.tgz" -C "$tmp"
  rm "$tmp/a.tgz"
  mv "$tmp"/* "tools/$name"
  rm -rf "$tmp"
}
get "https://github.com/bytecodealliance/wasm-tools/releases/download/v1.262.0/wasm-tools-1.262.0-$WT.tar.gz" wasm-tools
get "https://github.com/WebAssembly/binaryen/releases/download/version_133/binaryen-version_133-$BN.tar.gz" binaryen
get "https://github.com/WebAssembly/wabt/releases/download/$WABT_VER/$WB" wabt
tools/wasm-tools/wasm-tools --version
tools/binaryen/bin/wasm-opt --version
tools/wabt/bin/wasm-decompile --version
echo "tools ready"
