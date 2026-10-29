#!/usr/bin/env python3
"""memmap.py - map every (passive) data segment to its linear-memory address.
This build (pthreads) has no active segments: the start function copies each one
with `memory.init` (i32.const DEST; i32.const 0; i32.const LEN; memory.init SEG).
Reads the start function index from the binary and scans only that function's WAT.
in: WebClient.wasm, WebClient.wat, segs.json  ->  out: memmap.json"""
import json, re
segs = json.load(open('segs.json'))  # [addr(None), file_off, len]
b = open('WebClient.wasm', 'rb').read()
def uleb(i):
    r = s = 0
    while True:
        x = b[i]; i += 1; r |= (x & 0x7f) << s; s += 7
        if x < 0x80: return r, i
i = 8; START = None
while i < len(b):
    sid = b[i]; sz, j = uleb(i + 1)
    if sid == 8: START = uleb(j)[0]
    i = j + sz
print('start function:', START)
hdr = '  (func (;%d;)' % START; lines = []; on = False
with open('WebClient.wat') as f:
    for l in f:
        if l.startswith(hdr): on = True
        elif on and l.startswith('  (func'): break
        if on: lines.append(l.strip())
dest = {}
for k in range(len(lines) - 3):
    m = re.match(r'memory\.init (\d+)$', lines[k+3])
    if m and lines[k].startswith('i32.const') and lines[k+1] == 'i32.const 0' and lines[k+2].startswith('i32.const'):
        dest[int(m.group(1))] = int(lines[k].split()[1])
print('segments mapped:', len(dest), 'of', len(segs))
mm = [(dest[i], segs[i][1], segs[i][2]) for i in dest]  # (memaddr, fileoff, len)
json.dump(sorted(mm), open('memmap.json', 'w'))
def f2m(off):
    for a, fs, l in mm:
        if fs <= off < fs + l: return a + off - fs
for name in ["TaskSchedulerTargetFps", "DebugDisplayFPS", "LuauSolverV2"]:
    off = b.find(b"\0" + name.encode() + b"\0") + 1
    print(name, 'mem=', f2m(off))
