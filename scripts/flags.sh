#!/usr/bin/env bash
# Optional FastFlag analysis on top of the full decompile (runs inside build/).
# Needs: build/WebClient.wat + build/dec_full/ (run scripts/decompile.sh first), Python 3, Node >= 22.
# Output: build/out/flags/<Prefix>/<Name>.c (every flag + its read sites), build/out/flags.csv,
#         build/out/functions/bNNN.c (whole decompile annotated with flag names + strings)
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"; F="$ROOT/fflags"
cd "$ROOT/build" 2>/dev/null && [ -f WebClient.wat ] && [ -f dec_full/header.txt ] || { echo "run first: bash scripts/decompile.sh"; exit 1; }
python3 "$F/datamap.py"                        # data segments           -> segs.json
python3 "$F/memmap.py"                         # segment -> memory addr  -> memmap.json
python3 "$F/scanreg.py"                        # memory image + registrations -> mem.img, reg_hits.json
python3 "$F/inventory.py"                      # engine flags            -> inv_engine.json
python3 "$F/luau2.py"                          # Luau FValue flags       -> inv_luau.json
python3 "$F/gates.py"                          # all flag read sites     -> gate_hits.json
node --experimental-wasm-exnref "$F/ctors.js"  # run static ctors        -> runtime_values.json
python3 "$F/build_out.py"                      # -> build/out/
echo "flags done: see build/out/flags.csv and build/out/flags/"
