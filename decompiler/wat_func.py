#!/usr/bin/env python3
"""
wat_func.py - pull one function out of the 1.5 GB WebClient.wat, or put an edited
copy back, so you can patch the module without opening the whole WAT.

  python3 decompiler/wat_func.py extract 394 > f394.wat     # function index 394
  python3 decompiler/wat_func.py replace 394 f394.wat       # splice it back in
  bash scripts/compile.sh                                   # -> build/WebClient.recompiled.wasm

Function indices are the same N as in WebClient.dcmp (fN / fN_exportname).
Optional last arg: path to the WAT (default build/WebClient.wat in the repo).
"""
import mmap, os, sys
DEFAULT_WAT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'build', 'WebClient.wat')

def locate(mm, idx):
    key = b'\n  (func (;%d;)' % idx
    s = mm.find(key)
    if s < 0: raise SystemExit(f'function {idx} not found (imports 0..272 have no body)')
    s += 1                                   # start of the "  (func" line
    e = mm.find(b'\n  )\n', s)               # top-level close paren of this func
    if e < 0: raise SystemExit('unterminated function')
    return s, e + len(b'\n  )\n')

def main():
    if len(sys.argv) < 3 or sys.argv[1] not in ('extract', 'replace'):
        print(__doc__); sys.exit(1)
    cmd, idx = sys.argv[1], int(sys.argv[2])
    if cmd == 'extract':
        wat = sys.argv[3] if len(sys.argv) > 3 else DEFAULT_WAT
        with open(wat, 'rb') as f, mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ) as mm:
            s, e = locate(mm, idx); sys.stdout.buffer.write(mm[s:e])
    else:
        new = open(sys.argv[3], 'rb').read()
        wat = sys.argv[4] if len(sys.argv) > 4 else DEFAULT_WAT
        if not new.lstrip().startswith(b'(func (;%d;)' % idx):
            raise SystemExit(f'replacement must start with "(func (;{idx};)"')
        if not new.endswith(b'\n'): new += b'\n'
        tmp = wat + '.tmp'
        with open(wat, 'rb') as f, mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ) as mm, open(tmp, 'wb') as o:
            s, e = locate(mm, idx)
            o.write(mm[:s]); o.write(new); o.write(mm[e:])
        os.replace(tmp, wat)
        print(f'replaced func {idx} in {wat}; now run: bash scripts/compile.sh')

if __name__ == '__main__':
    main()
