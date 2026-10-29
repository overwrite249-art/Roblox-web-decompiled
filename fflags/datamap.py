#!/usr/bin/env python3
"""datamap.py - list the 2,994 data segments (all passive) -> segs.json [addr|None, file_off, len]"""
import json,struct
b=open('WebClient.wasm','rb').read()
def uleb(i):
    r=s=0
    while True:
        x=b[i];i+=1;r|=(x&0x7f)<<s;s+=7
        if x<0x80:return r,i
def sleb(i):
    r=s=0
    while True:
        x=b[i];i+=1;r|=(x&0x7f)<<s;s+=7
        if x<0x80:
            if x&0x40:r-=1<<s
            return r,i
i=8;secs={}
while i<len(b):
    sid=b[i];sz,j=uleb(i+1);secs.setdefault(sid,[]).append((j,sz));i=j+sz
start,sz=secs[11][0];n,i=uleb(start);segs=[]
for k in range(n):
    flag,i=uleb(i)
    if flag in(0,2):
        if flag==2:_,i=uleb(i)
        op=b[i];i+=1;assert op==0x41,(k,op);addr,i=sleb(i);assert b[i]==0x0b;i+=1
    else: addr=None
    ln,i=uleb(i);segs.append((addr,i,ln));i+=ln
json.dump(segs,open('segs.json','w'))
act=[s for s in segs if s[0] is not None]
print("segments:",len(segs),"active:",len(act),"passive:",len(segs)-len(act))
if act:
    print("mem range: 0x%x - 0x%x"%(min(s[0] for s in act),max(s[0]+s[2] for s in act)))
else:
    print("all segments are passive -> memory addresses come from memory.init in the start function (memmap.py)")
