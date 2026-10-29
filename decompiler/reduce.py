#!/usr/bin/env python3
"""
reduce.py - build a "reduced" copy of WebClient.wasm in which every function
body except a chosen `keep` set is replaced by a 1-instruction stub, the data
segment payloads are emptied, and a `name` custom section is added.

The reduced module is tiny and is what we hand to wasm-opt + wasm-decompile so
the decompiler only has to work on a handful of real function bodies at a time.
Parses imports/exports straight from the wasm binary, so it does NOT need the
(1.5 GB) .wat for naming.

Env:
  WASM   path to the stock module (default: WebClient.wasm in the cwd; scripts run from build/)
"""
import sys, os, json

WASM = os.environ.get('WASM', 'WebClient.wasm')

def uleb(b, i):
    r = s = 0
    while True:
        x = b[i]; i += 1; r |= (x & 0x7f) << s; s += 7
        if x < 0x80: return r, i

def enc(n):
    o = bytearray()
    while True:
        x = n & 0x7f; n >>= 7
        if n: o.append(x | 0x80)
        else: o.append(x); return bytes(o)

def vecstr(s):
    b = s.encode(); return enc(len(b)) + b

def _name(b, i):
    n, i = uleb(b, i); return b[i:i+n].decode('utf-8', 'replace'), i + n

def _skip_limits(b, i):
    fl = b[i]; i += 1
    _, i = uleb(b, i)                 # min
    if fl & 0x01: _, i = uleb(b, i)   # max (also set when shared, fl=0x03)
    return i

def parse_header(b):
    """Return (nimp_func, import_func_names, ndef, export_names{idx:name})."""
    i = 8; imp_names = []; nimp = 0; ndef = 0; exports = {}
    while i < len(b):
        sid = b[i]; sz, j = uleb(b, i + 1); end = j + sz
        if sid == 2:                                  # import section
            n, k = uleb(b, j)
            for _ in range(n):
                _, k = _name(b, k)                    # module
                nm, k = _name(b, k)                   # name
                kind = b[k]; k += 1
                if kind == 0x00:                      # func import
                    _, k = uleb(b, k)                 # typeidx
                    imp_names.append(nm); nimp += 1
                elif kind == 0x01:                    # table
                    k += 1; k = _skip_limits(b, k)
                elif kind == 0x02:                    # memory
                    k = _skip_limits(b, k)
                elif kind == 0x03:                    # global
                    k += 2
                elif kind == 0x04:                    # tag (exceptions)
                    k += 1; _, k = uleb(b, k)
                else:
                    raise ValueError('bad import kind %d' % kind)
        elif sid == 3:                                # function section
            ndef, _ = uleb(b, j)
        elif sid == 7:                                # export section
            n, k = uleb(b, j)
            for _ in range(n):
                nm, k = _name(b, k); kind = b[k]; k += 1; idx, k = uleb(b, k)
                if kind == 0x00: exports[idx] = nm
        i = end
    return nimp, imp_names, ndef, exports

def base_names(b=None):
    if b is None: b = open(WASM, 'rb').read()
    nimp, imp_names, ndef, exports = parse_header(b)
    names = {}
    for idx, nm in enumerate(imp_names):
        names[idx] = 'imp_' + ''.join(c if c.isalnum() else '_' for c in nm)
    for idx in range(nimp, nimp + ndef):
        names[idx] = 'f%d' % idx
    for idx, nm in exports.items():
        safe = ''.join(c if c.isalnum() else '_' for c in nm).strip('_')
        names[idx] = 'f%d_%s' % (idx, safe)
    return names

def build(keep, out, names, b=None, keep_data=False):
    """keep: set of function indices whose bodies are kept (others -> stub).
    keep_data: keep real data-segment bytes (used for the module-header pass)."""
    if b is None: b = open(WASM, 'rb').read()
    nimp = parse_header(b)[0]
    i = 8; parts = [b[:8]]
    while i < len(b):
        sid = b[i]; sz, j = uleb(b, i + 1); body = b[j:j+sz]
        if sid == 10:                                 # code section
            n, k = uleb(body, 0); nb = bytearray(enc(n))
            for f in range(n):
                fs, k2 = uleb(body, k)
                nb += body[k:k2+fs] if (f + nimp) in keep else b'\x03\x00\x00\x0b'
                k = k2 + fs
            body = bytes(nb)
        elif sid == 11 and not keep_data:             # data section -> empty passive
            n, k = uleb(body, 0); body = enc(n) + b'\x01\x00' * n
        elif sid == 0:                                # drop custom sections
            i = j + sz; continue
        parts.append(bytes([sid]) + enc(len(body)) + body); i = j + sz
    fn = sorted(names.items())
    sub = enc(len(fn)) + b''.join(enc(k) + vecstr(v) for k, v in fn)
    nm = vecstr('name') + bytes([1]) + enc(len(sub)) + sub
    parts.append(b'\x00' + enc(len(nm)) + nm)
    open(out, 'wb').write(b''.join(parts))

if __name__ == '__main__':
    # usage: reduce.py OUT.wasm idx1,idx2,...
    b = open(WASM, 'rb').read()
    keep = set(int(x) for x in sys.argv[2].split(',')) if len(sys.argv) > 2 else set()
    names = base_names(b)
    build(keep, sys.argv[1], names, b)
    json.dump(names, open('basenames.json', 'w'))
    print('nimp/ndef:', parse_header(b)[0], parse_header(b)[2], 'kept:', len(keep))
