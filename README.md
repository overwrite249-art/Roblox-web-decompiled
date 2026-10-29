# Roblox WebClient.wasm: full decompiler + compiler

Scripts for Roblox build **`version-75f1039cb4964863-RobloxWebClient`** that:

- **decompile the whole module**, meaning all 167,913 functions plus the imports, globals, table, exports and all 2,994 data segments
- **recompile** it to a byte-identical `WebClient.wasm`
- optionally pull out **every FastFlag** (14,379 of them), with its default value and the code that reads it

Nothing here is pre-generated. You run the scripts yourself, and every result can be reproduced.

Stock file: `https://setup.rbxcdn.com/webclient/version-75f1039cb4964863-RobloxWebClient/WebClient.wasm` (100,515,451 bytes, sha256 `d72c52618f5c153c9b17a97e644914d43918c7122d754d96f79e8323acc6a15d`).

## Repository layout

```
Roblox-web-decompiled/
├── README.md
├── stock/                  Roblox's stock files go here (downloaded automatically, not committed)
│   └── README.md           source URLs + sha256 of WebClient.wasm / WebClient.js
├── scripts/                the entry points: run these
│   ├── setup_tools.sh      downloads wasm-tools 1.262.0, binaryen 133, wabt 1.0.36 into tools/
│   ├── fetch_stock.sh      downloads stock/WebClient.wasm + WebClient.js from the Roblox CDN, checks sha256
│   ├── decompile.sh        full decompile -> build/WebClient.wat + build/WebClient.dcmp
│   ├── compile.sh          WAT -> wasm, validates it, compares it with stock
│   └── flags.sh            optional FastFlag analysis -> build/out/
├── decompiler/             the decompiler itself
│   ├── full_batch.py       decompiles all 167,913 functions + module header, verifies, merges
│   ├── reduce.py           builds the small per-batch modules (stubbed bodies + name section)
│   ├── wat_func.py         extracts / replaces one function in the 1.5 GB WAT
│   └── sections.py         prints the section layout
└── fflags/                 FastFlag analysis pipeline (run by scripts/flags.sh)
    ├── datamap.py  memmap.py  scanreg.py  inventory.py
    ├── luau2.py  gates.py  ctors.js  build_out.py
```

Generated, and git-ignored: `tools/` (toolchains) and `build/` (all outputs).

**The stock files aren't committed.** `WebClient.wasm` and `WebClient.js` are Roblox's proprietary code, and this repo is public, so the scripts download them from Roblox's CDN and check their hashes. The result is exactly the same as committing them.

## Quick start

```bash
git clone https://github.com/overwrite249-art/Roblox-web-decompiled.git && cd Roblox-web-decompiled
bash scripts/decompile.sh   # tools + stock file download automatically. ~2 min, ~2.5 GB disk
bash scripts/compile.sh     # ~1 min, needs ~8 GB RAM (or swap, see Pitfalls)
bash scripts/flags.sh       # optional FastFlag analysis, ~4 min, +0.35 GB
```

**Requirements:** Linux or macOS (on Windows, use WSL), bash, curl, tar, Python ≥ 3.8, and Node ≥ 22 (only for `scripts/flags.sh`). The scripts work from any directory.

## Outputs

| Output | Size | Contents |
|---|---|---|
| `build/WebClient.wat` | 1.53 GB | Exact text form of the **entire** module. This is the editable form. Recompiling it without changes gives a byte-identical file (verified: same sha256). |
| `build/WebClient.dcmp` | ~280 MB | Pseudo-C of the **entire** module: a header (274 imports, 15 globals, table, exports, 2,994 data segments with their bytes) followed by all 167,913 functions in index order. `scripts/decompile.sh` checks that every function appears exactly once. |
| `build/dec_full/` | | The same pseudo-C, split up: `header.txt` + `b000.txt … b022.txt` |
| `build/WebClient.recompiled.wasm` | 100 MB | Output of `scripts/compile.sh` |
| `build/out/` | ~330 MB | From `scripts/flags.sh`: `flags.csv`, one file per flag at `flags/<Prefix>/<Name>.c`, and `functions/bNNN.c` (the full decompile annotated with flag names and string literals) |

Measured on a 2-vCPU / 4 GB VM, from a fresh clone: `scripts/decompile.sh` ~105 s (including the 96 MB CDN download and a 9 s disassembly), `scripts/compile.sh` ~50 s (with swap), `scripts/flags.sh` ~255 s.

## Editing and recompiling

```bash
python3 decompiler/wat_func.py extract 394 > f394.wat   # function index N = fN in build/WebClient.dcmp
# ...edit f394.wat...
python3 decompiler/wat_func.py replace 394 f394.wat     # splices it back into build/WebClient.wat
bash scripts/compile.sh                                 # -> build/WebClient.recompiled.wasm (validated)
```

- **The pseudo-C (`.dcmp`) is read-only.** Nothing compiles `wasm-decompile` output. It's for reading only; make your edits in the WAT.
- Changing a body is easy. If you change a function's type, or add functions, globals or data, keep the indices consistent. Function `N` is `(func (;N;)` in the WAT and `fN` in the pseudo-C.
- If you put back the original function, the build is byte-identical again (tested).

## How the decompile works

You can't run `wasm-decompile` on the whole file directly, for two reasons. First, wabt 1.0.36 can't parse the new exception-handling encoding (exnref, `try_table`/`throw_ref`) and fails with `expected valid result type (got -0x17)`. Second, the module is too large to decompile in one go. So `decompiler/full_batch.py` does this:

1. Splits the 167,913 functions into 23 batches of ~4 MB of code each. `__wasm_call_ctors` (f273, 3.6 MB, all static initialisation) gets a batch to itself.
2. For each batch, `decompiler/reduce.py` writes a copy of the module in which every other function body is a 3-byte stub (`unreachable`). Data payloads are emptied and a name section is added (`fN`, `imp_<name>`, `fN_<export>`). Every index and call target stays the same as in the real file.
3. Runs `wasm-opt <explicit feature flags> --no-validation -g --strip-eh --dce --vacuum --reorder-locals` to remove the exnref exception handling so wabt can read the module.
4. Runs `wasm-decompile --enable-all` and keeps only that batch's functions.
5. A header pass (all bodies stubbed, real data kept) produces the imports, globals, table, exports and data segments.
6. Checks that every function is present exactly once, then merges everything into `build/WebClient.dcmp`.

The WAT comes straight from `wasm-tools print`, and `scripts/compile.sh` is `wasm-tools parse` followed by `wasm-tools validate` and a sha256 comparison.

## Module facts

```
type       count=892          export     count=49 (46 functions)
import     count=274          start      func 275 (copies all data segments into memory)
             273 functions + env.memory (shared, 4096..65536 pages)
function   count=167,913      elem       1 segment (indirect function table, 174,301 entries)
table      174,301 funcref    code       91,667,267 bytes
tag        2 (C++ exceptions) data       8,191,782 bytes in 2,994 PASSIVE segments
global     15                 custom     build_id only (no name section: functions are unnamed)
```

The build is Emscripten with pthreads, the new exnref exception-handling encoding and SIMD. Notable exports: `__wasm_call_ctors`=f273, `main_loop_iteration`=f412, `__main_argc_argv`=f489, `malloc`=f163490, `_emscripten_thread_init`=f164581, `_emscripten_tls_init`=f163106.

## Reading the pseudo-code

- `fNNN(...)` is function index NNN. The binary has no symbols. `imp_*` are JS imports and `fNNN_name` are exported functions.
- `x[n]:int` is a 32-bit load at `x + n*4` (the index is scaled by the type size). `@1` is an alignment hint.
- `call_indirect(obj, (obj[0]:int)[k]:int)` is a virtual method call through vtable slot k.
- `g_a` is the C stack pointer (global 0).
- In `build/out/functions` (annotated): `FFlag::Name` means the flag's value is read there. `&FFlag::Name` means its address is passed (to a getter, registry or listener). `/*"text"*/` marks a string literal, or a constant that decodes to ASCII (an inlined string compare).

## FastFlags (`scripts/flags.sh`, code in `fflags/`)

Flag names are stored in the binary **without** their prefix (`FFlag`, `DFInt`, …). The prefix comes from which registration function is called and its "kind" argument.

| Prefix | Flags | With direct code reads |
|---|---|---|
| FFlag | 3,814 (incl. 48 Luau) | 2,936 |
| DFFlag | 2,875 | 2,315 |
| SFFlag | 45 | 12 |
| FInt | 1,346 | 835 |
| DFInt | 4,693 | 2,781 |
| FString | 417 | 417 |
| DFString | 309 | 309 |
| SFString | 2 | 2 |
| FLog | 421 | 327 |
| DFLog | 457 | 342 |
| **Total** | **14,379** | **10,276** |

How the pipeline works:

1. `datamap.py` + `memmap.py`: all data segments are passive (pthreads build), so their memory addresses come from the `memory.init` calls in the start function f275.
2. `scanreg.py`: rebuilds the initial memory image (`mem.img`) and finds every call whose first argument is an identifier string. Those are the registrars:
   - `f156909(name, var, kind)` for bools (kind 1=FFlag, 2=DFFlag)
   - `f156916` for SFFlag (kind 4)
   - `f156927` for FLog/DFLog
   - `f156932` for FString/DFString/SFString (libc++ string: long form `{ptr,size,cap|0x80000000}`, short form inline with the length at byte +11)
   - `f156934(var, kind)` for FInt/DFInt, where var → `{i32 default; const char* name; u32 len}`
   - Bool variables are 12-byte structs `{u8 value; name ptr; len}`.
3. `inventory.py`: writes the engine flags to `inv_engine.json` (14,308).
4. `luau2.py`: recovers the Luau `FValue<bool>`/`FValue<int>` linked lists (heads at @19628440 and @19628492) into `inv_luau.json` (71).
5. `gates.py`: finds every load, store or address-of for each flag address (50,272 sites).
6. `ctors.js`: instantiates the module in Node with stub imports and runs `__wasm_call_ctors`, then reads every default from memory, including strings. Cross-check: all 13,651 non-string defaults matched the static data exactly.
7. `build_out.py`: annotates the full decompile and writes `build/out/flags/<Prefix>/<Name>.c` (metadata plus ±10 lines around each read, marked `// <<<`) and `build/out/flags.csv`.

Example: `DFIntWebPointerLockRetryDelayMs` = 500 is used in f394 (pointer-lock retry: `now + 500 ms`).

## Build-specific constants (for running on a newer build)

These are found automatically: the number of imported functions (273), the start function (275) and the export names.

These are hard-coded for this build:

- **Registrar indices** 156909/156916/156927/156932/156934 (`fflags/inventory.py`, `fflags/gates.py`). Rerun `fflags/scanreg.py` and it prints a histogram of `call N` sites whose first argument is an identifier string. The top entries are the new registrars.
- **Luau list heads** 19628440/19628492 (`fflags/luau2.py`). In the ctor WAT for a Luau flag, look for the `i32.const HEAD; i32.load` / `i32.store` pair that links each FValue node into the list.
- **f273** (`__wasm_call_ctors`) in `fflags/build_out.py`, which is used to separate static-init reads from real reads.
- **`fflags/ctors.js`**: uses `_emscripten_thread_init(tb,1,1,1,1<<20,0)` + `_emscripten_tls_init()` and memory limits of 4096/65536 pages.

## Pitfalls (already solved here)

- binaryen's `-all` produces an encoding that wabt can't read (`malformed import kind 127`). Pass explicit feature flags instead (see `decompiler/full_batch.py`).
- exnref needs `--no-validation`. `--strip-eh` leaves exnref locals behind, which `--dce --vacuum --reorder-locals` cleans up.
- wabt ≥ 1.0.37 can parse exnref, but it prints try blocks as an opaque `TryTable();` and drops the try body, so 1.0.36 + strip-eh gives better output. 1.0.39 needs glibc 2.38, and 1.0.42 removed `wasm-decompile`.
- `wasm-tools parse` on the 1.5 GB WAT needs ~7–8 GB RAM. With less, it gets OOM-killed (exit 137). Add swap: `sudo fallocate -l 8G /swapfile && sudo chmod 600 /swapfile && sudo mkswap /swapfile && sudo swapon /swapfile`.
- Node can't hold the WAT as a single string, so `fflags/ctors.js` reads only its first 3 MB (types and imports).

## Limitations

- The binary has no symbol names, so this is reconstructed low-level code, not Roblox's C++ source. Control flow and data are exact; the identifiers aren't.
- The pseudo-C has exception handling (`try_table` catch/cleanup paths) stripped so the decompiler can run. The WAT keeps everything.
- 4,103 flags have no direct reads. They are looked up by name at runtime (FastFlag registry or Lua), only touched during static init, or compiled in but unused.
- Defaults are the values compiled into this build. Live values come from Roblox's ClientSettings and can be different.

## Legal

`WebClient.wasm` and `WebClient.js` are proprietary code owned by Roblox Corporation. That's why this repository doesn't contain them: `scripts/fetch_stock.sh` downloads them from Roblox's own CDN. Don't commit them to a public repository.
