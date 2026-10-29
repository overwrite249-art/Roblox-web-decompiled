#!/usr/bin/env python3
"""inventory.py - build the engine flag inventory from the registrar calls.
BUILD-SPECIFIC registrar function indices (re-derive for other builds, see README):
  156909 bool FFlag/DFFlag (name, var, kind)   156916 SFFlag
  156927 FLog/DFLog                             156932 FString/DFString/SFString
  156934 FInt/DFInt (var, kind), var -> {i32 default; const char* name; u32 len}
in: mem.img, reg_hits.json, WebClient.wat  ->  out: inv_engine.json"""
import json,re,struct,collections
img=open('mem.img','rb').read();N=len(img)
ident=re.compile(rb'^[A-Za-z_][A-Za-z0-9_]{2,}$')
def s(a):
    if not 0<a<N:return None
    e=img.find(b'\0',a);t=img[a:e]
    return t.decode() if e-a<160 and ident.match(t) else None
def i32(a): return struct.unpack('<i',img[a:a+4])[0] if a+4<=N else 0
def u8(a): return img[a] if a<N else 0
KIND={1:'',2:'D',4:'S'}
inv={}
hits=json.load(open('reg_hits.json'))
for nm,args,fn in hits:
    if fn in(156909,156916): typ='Flag'
    elif fn==156927: typ='Log'
    elif fn==156932: typ='String'
    else: continue
    a=args[1];k=args[2] if len(args)>2 else 1
    d=u8(a) if typ in('Flag','Log') else None
    inv[a]=dict(name=KIND.get(k,'?')+'F'+typ+nm,base=nm,type=typ,kind=k,addr=a,default=d,src='reg%d'%fn)
# FInt via call 156934 (addr,kind)
# pattern in the WAT:  i32.const VAR ; i32.const KIND ; call 156934   (pure-Python scan)
pat=re.compile(rb'i32\.const (-?\d+)\n[ \t]*i32\.const (-?\d+)\n[ \t]*call 156934\n')
with open('WebClient.wat','rb') as f:
    tail=b''
    while True:
        ch=f.read(1<<26)
        if not ch:break
        buf=tail+ch;cut=buf.rfind(b'\n',0,len(buf)-512) if len(ch)==1<<26 else len(buf)
        for m in pat.finditer(buf,0,cut):
            a=int(m.group(1));k=int(m.group(2))
            nm=s(i32(a+4)) or '?unnamed_%d'%a
            inv[a]=dict(name=KIND.get(k,'?')+'FInt'+nm,base=nm,type='Int',kind=k,addr=a,default=i32(a),src='reg156934')
        tail=buf[cut:]
json.dump(inv,open('inv_engine.json','w'))
c=collections.Counter(v['name'][:v['name'].index('F')+1]+v['type'] for v in inv.values())
print("engine flags:",len(inv),dict(c))
for t in ['Flag','Int','Log','String']:
    ex=[(v['name'],v['default']) for v in inv.values() if v['type']==t][:3];print(t,ex)
print("FLog struct sample:",[ (v['name'],struct.unpack('<4i',img[v['addr']:v['addr']+16])) for v in inv.values() if v['type']=='Log'][:2])
