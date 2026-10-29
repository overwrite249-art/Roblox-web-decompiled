#!/usr/bin/env python3
"""
full_batch.py - decompile EVERY function in WebClient.wasm to pseudo-C.

Splits all 167,913 defined functions into ~4 MB batches. For each batch it
builds a reduced module (only those function bodies kept), runs
  wasm-opt (strip the new exnref exception handling, clean up) -> wasm-decompile
and writes the chosen functions to dec_full/bNNN.txt.

Normally run via scripts/decompile.sh (cwd = build/). ~90 s on 2 cores, 0 failures expected.
Self-contained: derives function sizes from the binary, no pre-made JSON.

Env:
  WASM            stock module            (default WebClient.wasm)
  WASM_OPT        binaryen wasm-opt       (default <repo>/tools/binaryen/bin/wasm-opt)
  WASM_DECOMPILE  wabt wasm-decompile     (default <repo>/tools/wabt/bin/wasm-decompile)
  DEC_OUT         output dir              (default dec_full)
  WORKERS         parallel batches        (default 2)
"""
import json, subprocess, os, re, sys, time
from concurrent.futures import ThreadPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import reduce as R

WASM = os.environ.get('WASM', 'WebClient.wasm')
ROOT = os.path.dirname(HERE)
WOPT = os.environ.get('WASM_OPT', os.path.join(ROOT, 'tools/binaryen/bin/wasm-opt'))
WDEC = os.environ.get('WASM_DECOMPILE', os.path.join(ROOT, 'tools/wabt/bin/wasm-decompile'))
OUT  = os.environ.get('DEC_OUT', 'dec_full'); os.makedirs(OUT, exist_ok=True)
WORKERS = int(os.environ.get('WORKERS', '2'))

B = open(WASM, 'rb').read()
NIMP, _, NDEF, _ = R.parse_header(B)

def code_sizes(b):
    """function index -> body byte length, read from the code section."""
    def uleb(i):
        r = s = 0
        while True:
            x = b[i]; i += 1; r |= (x & 0x7f) << s; s += 7
            if x < 0x80: return r, i
    i = 8
    while i < len(b):
        sid = b[i]; sz, j = uleb(i + 1)
        if sid == 10:
            n, k = uleb(j); sizes = {}
            for f in range(n):
                fs, k2 = uleb(k); sizes[f + NIMP] = fs; k = k2 + fs
            return sizes
        i = j + sz
    raise RuntimeError('no code section')

sizes = code_sizes(B)
allf = sorted(sizes); batches = []; cur = []; acc = 0
for f in allf:
    if sizes[f] > 2_000_000:                 # huge funcs (e.g. the ctors) get their own batch
        if cur: batches.append(cur); cur = []; acc = 0
        batches.append([f]); continue
    cur.append(f); acc += sizes[f]
    if acc > 4_000_000: batches.append(cur); cur = []; acc = 0
if cur: batches.append(cur)

names0 = R.base_names(B)
FEAT = ("--enable-exception-handling --enable-reference-types --enable-bulk-memory "
        "--enable-threads --enable-simd --enable-nontrapping-float-to-int --enable-sign-ext "
        "--enable-mutable-globals --enable-multivalue --enable-tail-call").split()

def run(tag, fl):
    keep = set(fl)
    w = f'{OUT}/_{tag}.wasm'; n = f'{OUT}/_{tag}.noeh.wasm'; d = f'{OUT}/_{tag}.dcmp'
    R.build(keep, w, names0, B)
    r = subprocess.run([WOPT, *FEAT, '--no-validation', '-g', '--strip-eh', '--dce',
                        '--vacuum', '--reorder-locals', w, '-o', n],
                       capture_output=True, text=True)
    ok = r.returncode == 0
    if ok:
        r = subprocess.run([WDEC, '--enable-all', n, '-o', d], capture_output=True, text=True)
        ok = r.returncode == 0
    res = None
    if ok:
        want = {names0[k] for k in keep}; res = []; on = False
        for line in open(d):
            if line.startswith(('function ', 'export function ')):
                m = re.match(r'(?:export )?function (\w+)', line); on = bool(m and m.group(1) in want)
            if on: res.append(line)
            if on and line.startswith('}'): on = False
    for x in (w, n, d):
        if os.path.exists(x): os.remove(x)
    return res, (None if ok else r.stderr[:200])

def do(bi):
    out = f'{OUT}/b{bi:03d}.txt'
    if os.path.exists(out): return f'{bi} cached'
    t = time.time(); fl = batches[bi]; res, err = run(f'b{bi}', fl); failed = []
    if res is None:                                   # retry by splitting into 8
        res = []; step = max(1, len(fl) // 8)
        for j in range(0, len(fl), step):
            sub = fl[j:j+step]; r2, e2 = run(f'b{bi}_{j}', sub)
            if r2 is None: failed += sub
            else: res += r2
    open(out + '.tmp', 'w').writelines(res); os.rename(out + '.tmp', out)
    if failed: open(f'{OUT}/failed_b{bi:03d}.json', 'w').write(json.dumps(failed))
    nok = sum(1 for l in res if l.startswith(('function', 'export function')))
    return f'batch {bi}: {len(fl)} funcs, {nok} ok, failed {len(failed)}, {time.time()-t:.0f}s'

def header():
    """Module-level part of the file: imports, globals, table, exports and all
    data segments WITH their real bytes (function bodies are stubbed and skipped)."""
    out = f'{OUT}/header.txt'
    if os.path.exists(out): return 'header cached'
    w = f'{OUT}/_hdr.wasm'; n = f'{OUT}/_hdr.noeh.wasm'; d = f'{OUT}/_hdr.dcmp'
    R.build(set(), w, names0, B, keep_data=True)
    r = subprocess.run([WOPT, *FEAT, '--no-validation', '-g', '--strip-eh', w, '-o', n],
                       capture_output=True, text=True)
    if r.returncode: raise SystemExit('header wasm-opt failed: ' + r.stderr[:300])
    r = subprocess.run([WDEC, '--enable-all', n, '-o', d], capture_output=True, text=True)
    if r.returncode: raise SystemExit('header wasm-decompile failed: ' + r.stderr[:300])
    res = []; on = False
    for line in open(d):
        if line.startswith(('function ', 'export function ')): on = True
        if not on: res.append(line)
        elif line.startswith('}'): on = False
    open(out + '.tmp', 'w').writelines(res); os.rename(out + '.tmp', out)
    for x in (w, n, d): os.remove(x)
    return f'header: {sum(1 for l in res if l.startswith("import "))} imports, ' \
           f'{sum(1 for l in res if l.startswith("global "))} globals, ' \
           f'{sum(1 for l in res if l.startswith("data "))} data segments'

def verify_and_merge(merged='WebClient.dcmp'):
    """Check every defined function was decompiled exactly once, then write one
    merged file: header + all functions in index order."""
    seen = {}; inv = {v: k for k, v in names0.items()}
    files = [f'{OUT}/b{i:03d}.txt' for i in range(len(batches))]
    for fn in files:
        for line in open(fn):
            if line.startswith(('function ', 'export function ')):
                m = re.match(r'(?:export )?function (\w+)', line)
                k = inv.get(m.group(1)) if m else None
                if k is not None: seen[k] = seen.get(k, 0) + 1
    want = range(NIMP, NIMP + NDEF)
    missing = [k for k in want if k not in seen]; dup = [k for k, c in seen.items() if c > 1]
    print(f'verify: {len(seen)}/{NDEF} functions decompiled, missing {len(missing)}, duplicated {len(dup)}',
          flush=True)
    if missing: print('  missing (first 20):', missing[:20])
    with open(merged + '.tmp', 'w') as o:
        o.write(f'// {os.path.basename(WASM)} - full decompilation (wasm-decompile pseudo-code)\n'
                f'// {NIMP} imported functions, {NDEF} defined functions. Read-only view:\n'
                f'// edit build/WebClient.wat and run scripts/compile.sh to rebuild the binary.\n\n')
        for fn in [f'{OUT}/header.txt'] + files:
            with open(fn) as i:
                while True:
                    c = i.read(1 << 24)
                    if not c: break
                    o.write(c)
    os.rename(merged + '.tmp', merged)
    print(f'merged -> {merged} ({os.path.getsize(merged)/1e6:.0f} MB)', flush=True)
    return not missing and not dup

if __name__ == '__main__':
    print(f'module: {NIMP} imported + {NDEF} defined functions; {len(batches)} batches', flush=True)
    print(header(), flush=True)
    with ThreadPoolExecutor(WORKERS) as ex:
        for m in ex.map(do, range(len(batches))): print(m, flush=True)
    ok = verify_and_merge(os.environ.get('MERGED', 'WebClient.dcmp'))
    print('ALL DONE' if ok else 'DONE WITH MISSING FUNCTIONS', flush=True)
    sys.exit(0 if ok else 1)
