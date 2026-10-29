#!/usr/bin/env python3
"""luau2.py - recover Luau FValue<bool>/FValue<int> flags by following the linked lists
built in static init. BUILD-SPECIFIC list heads: bool @19628440 {u8 value; u8 dynamic; name@4; next@8},
int @19628492 {i32 value; u8 dynamic@4; name@8; next@12}  -> inv_luau.json"""
import json,re,collections
img=open('mem.img','rb').read();N=len(img)
ident=re.compile(rb'^[A-Za-z_][A-Za-z0-9_]{2,}$')
def s(a):
    if not 0<a<N:return None
    e=img.find(b'\0',a);t=img[a:e]
    return t.decode() if e-a<160 and ident.match(t) else None
pat=re.compile(rb'i32\.const (\d+)\n\s*i32\.const (-?\d+)\n\s*i32\.store(8|16)?\n')
st=collections.defaultdict(list)
with open('WebClient.wat','rb') as f:
    tail=b''
    while True:
        ch=f.read(1<<26)
        if not ch:break
        buf=tail+ch;cut=buf.rfind(b'\n',0,len(buf)-512) if len(ch)==1<<26 else len(buf)
        for m in pat.finditer(buf,0,cut):
            a=int(m.group(1))
            if a>=N: st[a].append((int(m.group(3) or 32),int(m.group(2))))
        tail=buf[cut:]
L={'Flag':dict(head=19628440,name=4,next=8,dyn=1,w=8),'Int':dict(head=19628492,name=8,next=12,dyn=4,w=32)}
bases={}
for T,c in L.items():
    for w,v in st.get(c['head'],[]): bases[v]=T
rev=collections.defaultdict(list)
for a,lst in st.items():
    for w,v in lst:
        if w==32: rev[v].append(a)
changed=True
while changed:
    changed=False
    for B,T in list(bases.items()):
        c=L[T]
        for w,v in st.get(B+c['next'],[]):
            if w==32 and v not in bases and v>=N: bases[v]=T;changed=True
        for X in rev.get(B,[]):
            B2=X-c['next']
            if B2 not in bases and any(w==32 and s(v) for w,v in st.get(B2+c['name'],[])): bases[B2]=T;changed=True
out={};cnt=collections.Counter()
for B,T in bases.items():
    c=L[T];nm=next((s(v) for w,v in st.get(B+c['name'],[]) if w==32 and s(v)),None)
    if not nm:continue
    val=0;dyn=0
    for w,v in st.get(B,[]):
        if T=='Flag': val=v&0xff; dyn=(v>>8)&0xff if w==16 else dyn
        elif w==32: val=v
    for w,v in st.get(B+c['dyn'],[]):
        if w==8: dyn=v&0xff
    k=2 if dyn else 1;nmf=('D' if dyn else '')+'F'+T+nm
    out[str(B)]=dict(name=nmf,base=nm,type=T,kind=k,addr=B,default=val,src='luau_fvalue');cnt[nmf.split(nm)[0]]+=1
json.dump(out,open('inv_luau.json','w'))
print("Luau FValue flags:",len(out),dict(cnt))
print([ (v['name'],v['default']) for v in out.values() if v['base'] in('LuauCodeGenFastpcall','LuauCodeGenMaxTotalSize','LuauBytecodeFold','LuauCodeGenBlockSize')])
