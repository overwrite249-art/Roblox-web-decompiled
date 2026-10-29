#!/usr/bin/env python3
"""scanreg.py - rebuild the initial memory image (mem.img) from memmap.json and find every
call whose first argument is an identifier string (flag registrations) -> reg_hits.json"""
import re,json,collections
mm=json.load(open('memmap.json'));wasm=open('WebClient.wasm','rb').read()
size=max(a+l for a,f,l in mm);img=bytearray(size)
for a,f,l in mm: img[a:a+l]=wasm[f:f+l]
open('mem.img','wb').write(img)
ident=re.compile(rb'^[A-Za-z_][A-Za-z0-9_]{2,}$')
def s(addr):
    if not(0<addr<size):return None
    e=img.find(0,addr)
    if e<0 or e-addr>200:return None
    t=bytes(img[addr:e]);return t.decode() if ident.match(t) else None
pat=re.compile(rb'(?:[ \t]*i32\.const (-?\d+)\n)(?:[ \t]*i32\.const (-?\d+)\n)(?:[ \t]*i32\.const (-?\d+)\n)?(?:[ \t]*i32\.const (-?\d+)\n)?[ \t]*call (\d+)\n')
hist=collections.Counter();samples=collections.defaultdict(list);hits=[]
with open('WebClient.wat','rb') as f:
    tail=b''
    while True:
        chunk=f.read(1<<26)
        if not chunk:break
        buf=tail+chunk;cut=buf.rfind(b'\n',0,len(buf)-4096) if len(chunk)==1<<26 else len(buf)
        for m in pat.finditer(buf,0,cut):
            args=[int(x) for x in m.groups()[:4] if x is not None];fn=int(m.group(5))
            nm=s(args[0])
            if nm:
                hist[(fn,len(args))]+=1;hits.append((nm,args,fn))
                if len(samples[(fn,len(args))])<4:samples[(fn,len(args))].append((nm,args[1:]))
        tail=buf[cut:]
json.dump(hits,open('reg_hits.json','w'))
for (fn,na),c in hist.most_common(25): print(f"call {fn:>7} nargs={na} count={c:>6}  e.g. {samples[(fn,na)][:3]}")
