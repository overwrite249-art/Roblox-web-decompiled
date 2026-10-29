#!/usr/bin/env python3
"""sections.py - print the section layout of WebClient.wasm (ids per the wasm spec)."""
import os
def leb(b, i):
    r = s = 0
    while True:
        x = b[i]; i += 1; r |= (x & 0x7f) << s; s += 7
        if x < 0x80: return r, i
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
b = open(os.environ.get('WASM', os.path.join(ROOT, 'stock', 'WebClient.wasm')), 'rb').read()
names = {0:'custom',1:'type',2:'import',3:'function',4:'table',5:'memory',6:'global',7:'export',
         8:'start',9:'elem',10:'code',11:'data',12:'datacount',13:'tag'}
i = 8
while i < len(b):
    sid = b[i]; i += 1; sz, i = leb(b, i); extra = ''
    if sid == 0:
        nl, j = leb(b, i); extra = b[j:j+nl].decode(errors='replace')
    elif sid in (1, 2, 3, 6, 7, 9, 10, 11, 12, 13):
        cnt, _ = leb(b, i); extra = f'count={cnt:,}'
    elif sid == 8:
        st, _ = leb(b, i); extra = f'start func={st}'
    print(f'{names.get(sid, sid):10} size={sz:>12,} {extra}')
    i += sz
