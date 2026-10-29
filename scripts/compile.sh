#!/usr/bin/env bash
# Compiles a WAT back into a wasm binary, validates it and compares it to the stock file.
# Usage: bash scripts/compile.sh [in.wat] [out.wasm]
#   defaults: build/WebClient.wat -> build/WebClient.recompiled.wasm
# Unmodified build/WebClient.wat recompiles to a byte-identical copy of stock/WebClient.wasm.
# Needs ~8 GB RAM (or swap) for the full 1.5 GB WAT.
set -euo pipefail
abs() { case "$1" in /*) echo "$1" ;; *) echo "$PWD/$1" ;; esac; }
IN=$(abs "${1:-}"); OUT=$(abs "${2:-}")
ROOT="$(cd "$(dirname "$0")/.." && pwd)"; cd "$ROOT"
[ -n "${1:-}" ] || IN="$ROOT/build/WebClient.wat"
[ -n "${2:-}" ] || OUT="$ROOT/build/WebClient.recompiled.wasm"
sha() { if command -v sha256sum >/dev/null; then sha256sum "$1" | cut -d' ' -f1; else shasum -a 256 "$1" | cut -d' ' -f1; fi; }
WT="$ROOT/tools/wasm-tools/wasm-tools"
[ -x "$WT" ] || bash scripts/setup_tools.sh
[ -f "$IN" ] || { echo "$IN not found - run: bash scripts/decompile.sh"; exit 1; }
echo "== compiling $IN -> $OUT"
"$WT" parse "$IN" -o "$OUT"
echo "== validating"
"$WT" validate "$OUT" && echo "valid wasm"
ls -l "$OUT"
if [ -f stock/WebClient.wasm ]; then
  if [ "$(sha "$OUT")" = "$(sha stock/WebClient.wasm)" ]; then echo "RESULT: byte-identical to the stock WebClient.wasm"
  else echo "RESULT: differs from stock WebClient.wasm (expected if you edited the WAT)"; fi
fi
