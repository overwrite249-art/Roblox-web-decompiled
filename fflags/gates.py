#!/usr/bin/env python3
"""gates.py - find every read/write site of every flag variable in the WAT
(i32.const ADDR followed by a load/store, or i32.const 0 + load offset=ADDR) -> gate_hits.json, fstarts.json.
BUILD-SPECIFIC: registrar calls 1569(09|16|27|32|34) are excluded."""
import json,re,bisect,collections
inv={}
for f in('inv_engine.json','inv_luau.json'):
    for k,v in json.load(open(f)).items(): inv[int(k)]=v
addr={}
for a,v in inv.items():
    addr[a]=(a,0)
    if v['type']=='String':
        for o in(4,8,11): addr.setdefault(a+o,(a,o))
REG=b'call 1569(?:09|16|27|32|34)\n'
p1=re.compile(rb'\n[ \t]*i32\.const (\d+)\n[ \t]*([^\n]*)\n[ \t]*([^\n]*)\n[ \t]*([^\n]*)')
p2=re.compile(rb'\n[ \t]*i32\.const 0\n[ \t]*([a-z0-9]+\.(?:atomic\.)?(?:load|store|rmw)[^\n]*?offset=(\d+)[^\n]*)')
pf=re.compile(rb'\n  \(func \(;(\d+);\)')
fstarts=[];fidx=[];hits=[]
with open('WebClient.wat','rb') as f:
    base=0;tail=b''
    while True:
        ch=f.read(1<<26)
        if not ch:break
        buf=tail+ch;last=len(ch)<1<<26
        cut=len(buf) if last else buf.rfind(b'\n',0,len(buf)-2048)
        for m in pf.finditer(buf,0,cut): fstarts.append(base+m.start());fidx.append(int(m.group(1)))
        for m in p1.finditer(buf,0,cut):
            a=int(m.group(1))
            if a in addr:
                nxt=m.group(2).decode();ctx=b' '.join(m.groups()[1:])
                if re.search(rb'call 1569(?:09|16|27|32|34)\b',ctx):continue
                hits.append((addr[a][0],addr[a][1],base+m.start(),nxt))
        for m in p2.finditer(buf,0,cut):
            a=int(m.group(2))
            if a in addr: hits.append((addr[a][0],addr[a][1],base+m.start(),m.group(1).decode()))
        base+=cut;tail=buf[cut:]
out=[]
for a,o,pos,nxt in hits:
    i=bisect.bisect_right(fstarts,pos)-1
    out.append((a,o,pos,fidx[i],nxt))
json.dump(out,open('gate_hits.json','w'));json.dump([fstarts,fidx],open('fstarts.json','w'))
c=collections.Counter(re.sub(r' .*','',x[4]) for x in out)
print("total hits",len(out),"funcs",len(set(x[3] for x in out)),"flags hit",len(set(x[0] for x in out)),"of",len(inv))
print("next-instr histogram:",c.most_common(12))
