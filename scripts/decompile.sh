#!/usr/bin/env bash
# Fully decompiles stock/WebClient.wasm (the whole module, not just flags) into build/:
#   build/WebClient.wat   exact text disassembly of the entire file (~1.5 GB).
#                         This is the editable form: scripts/compile.sh turns it back
#                         into a byte-identical WebClient.wasm.
#   build/WebClient.dcmp  pseudo-C of the entire file (~280 MB): module header (imports,
#                         globals, table, exports, all 2,994 data segments) + all 167,913
#                         functions. Split copies: build/dec_full/ (header.txt, b000..b022.txt).
# Usage: bash scripts/decompile.sh             (both outputs)
#        SKIP_WAT=1 bash scripts/decompile.sh  (pseudo-C only)
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"; cd "$ROOT"
T="$ROOT/tools"
[ -x "$T/wasm-tools/wasm-tools" ] && [ -x "$T/binaryen/bin/wasm-opt" ] && [ -x "$T/wabt/bin/wasm-decompile" ] || bash scripts/setup_tools.sh
bash scripts/fetch_stock.sh
mkdir -p build && cd build
ln -sf ../stock/WebClient.wasm WebClient.wasm
if [ -z "${SKIP_WAT:-}" ]; then
  echo "== 1/2 disassembling whole module -> build/WebClient.wat"
  "$T/wasm-tools/wasm-tools" print WebClient.wasm -o WebClient.wat
  ls -l WebClient.wat
fi
echo "== 2/2 decompiling whole module -> build/WebClient.dcmp (+ build/dec_full/)"
WASM=WebClient.wasm WASM_OPT="$T/binaryen/bin/wasm-opt" WASM_DECOMPILE="$T/wabt/bin/wasm-decompile" \
  python3 "$ROOT/decompiler/full_batch.py"
echo "done. outputs are in build/"
