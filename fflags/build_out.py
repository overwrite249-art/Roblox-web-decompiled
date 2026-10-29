#!/usr/bin/env python3
"""build_out.py - final step of the flag analysis.
 * annotates the full decompile (dec_full/*.txt -> out/functions/*.c): flag variable
   addresses become FFlag::Name / &DFInt::Name, string pointers get /*"text"*/
 * writes one file per flag: out/flags/<Prefix>/<Name>.c with every read site
   (+-10 lines of decompiled context) and out/flags.csv
in: mem.img inv_engine.json inv_luau.json runtime_values.json gate_hits.json dec_full/ (all in build/)"""
import json,re,os,glob,collections,csv,shutil
img=open('mem.img','rb').read();N=len(img)
inv={}
for f in('inv_engine.json','inv_luau.json'):
    for k,v in json.load(open(f)).items(): inv[int(k)]=v
rt=json.load(open('runtime_values.json'))['values']
for a,v in inv.items():
    if v['type']=='String': v['default']=rt.get(str(a))
PFX={('Flag',1):'FFlag',('Flag',2):'DFFlag',('Flag',4):'SFFlag',('Int',1):'FInt',('Int',2):'DFInt',('Log',1):'FLog',('Log',2):'DFLog',
     ('String',1):'FString',('String',2):'DFString',('String',4):'SFString'}
for a,v in inv.items(): v['prefix']=PFX.get((v['type'],v['kind']),'F?');v['ref']=v['prefix']+'::'+v['base']
field={}
for a,v in inv.items():
    field[a]=v['ref']
    if v['type']=='String':
        for o,n in((4,'.size'),(8,'.cap'),(11,'.sso_len')): field.setdefault(a+o,v['ref']+n)
SZ={'byte':1,'ubyte':1,'short':2,'ushort':2,'int':4,'uint':4,'long':8,'ulong':8,'float':4,'double':8}
strc={}
def lit(x):
    if x in strc:return strc[x]
    r=None
    if 1024<=x<N and img[x-1]==0:
        e=img.find(b'\0',x)
        if 3<=e-x<=400:
            t=img[x:e]
            if all(32<=c<127 or c in(9,10) for c in t):
                t=t.decode();r=(t[:70]+'…' if len(t)>70 else t).replace('\\','\\\\').replace('"','\\"').replace('\n','\\n').replace('*/','*\\/')
    strc[x]=r;return r
mem=re.compile(r'(?<![\w.\]])(\d{4,9})\[(-?\d+)\]:(\w+)(?:@\d+)?')
num=re.compile(r'(?<![\w.\[@])(\d{4,9})(?![\w\[\]])')
chr_=re.compile(r'(:(ubyte|byte|ushort|short|int|uint|long|ulong)(?:@\d+)?\s*(?:\^|==|!=)\s*)(-?\d+)L?(?![\w/])')
def annotate(line):
    def m1(m):
        b,k,t=int(m.group(1)),int(m.group(2)),m.group(3);a=b+k*SZ.get(t,1)
        return field[a] if a in field else m.group(0)
    line=mem.sub(m1,line)
    def m2(m):
        x=int(m.group(1))
        if x in field: return '&'+field[x]
        s=lit(x);return f'{x}/*"{s}"*/' if s else m.group(0)
    line=num.sub(m2,line)
    def m3(m):
        t,n=m.group(2),int(m.group(3));k=SZ.get(t,0)
        if not k or k>8:return m.group(0)
        try:bs=(n%(1<<(8*k))).to_bytes(k,'little')
        except OverflowError:return m.group(0)
        txt=bs.rstrip(b'\0') if k>1 else bs
        if txt and all(32<=c<127 for c in txt) and (k==1 or len(txt)>=2):
            return m.group(0)+'/*"'+txt.decode().replace('\\','\\\\').replace('"','\\"').replace('*/','*\\/')+'"*/'
        return m.group(0)
    return chr_.sub(m3,line)
# per-flag gate sites (which functions read which flag)
hits=json.load(open('gate_hits.json'));sites=collections.defaultdict(lambda:collections.defaultdict(int));init=collections.Counter()
for a,o,pos,f,nxt in hits:
    if f==273:init[a]+=1          # f273 = __wasm_call_ctors (static init / registration)
    else:sites[a][f]+=1
need={f for d in sites.values() for f in d}
# annotate the WHOLE decompile (dec_full/bNNN.txt -> out/functions/bNNN.c); keep only flag readers in RAM
funcs={};ffile={}
os.makedirs('out/functions',exist_ok=True)
for fn in sorted(glob.glob('dec_full/b*.txt')):
    cur=None;buf=[];base=os.path.basename(fn).replace('.txt','.c')
    with open(fn) as f, open('out/functions/'+base,'w') as w:
        for line in f:
            al=annotate(line);w.write(al)
            m=re.match(r'(?:export )?function f(\d+)',line)
            if m:cur=int(m.group(1));buf=[];ffile[cur]=base
            if cur is not None and cur in need:buf.append(al.rstrip('\n'))
            if cur is not None and line.startswith('}'):
                if cur in need:funcs[cur]=buf
                cur=None
    print("annotated",fn,flush=True)
print("annotated functions:",len(ffile),"flag readers kept:",len(funcs),flush=True)
def fmtdef(v):
    d=v['default']
    if v['type']=='Flag':return 'true' if d else 'false'
    if v['type']=='String':return 'null (unknown)' if d is None else json.dumps(d)
    return str(d)
KDESC={1:'static (read once at startup)',2:'dynamic (can change at runtime)',4:'synchronized (server-replicated)'}
W=10;MAXSITES=40;rows=[]
shutil.rmtree('out/flags',ignore_errors=True)
for a,v in sorted(inv.items(),key=lambda x:x[1]['name']):
    d=f"out/flags/{v['prefix']}";os.makedirs(d,exist_ok=True)
    tok=re.compile(re.escape(v['ref'])+r'(?![\w])')
    fl=sites.get(a,{});nsites=sum(fl.values())
    out=[f"// {v['name']}",f"// C++ name : {v['ref']}",f"// Type     : {v['type'].lower()}  |  {KDESC.get(v['kind'],'?')}",
         f"// Default  : {fmtdef(v)}   (compiled into WebClient.wasm; live value comes from ClientSettings)",
         f"// Storage  : linear memory @ {a}   (source: {v['src']})",
         f"// Reads    : {nsites} direct code site(s) in {len(fl)} function(s)"+(f"; +{init[a]} in static init" if init[a] else ''),""]
    if not fl:
        out.append("// No direct reads in compiled code. Either looked up by name at runtime (FastFlag registry / Lua),\n// read only during static init, or compiled in but unused in this build.")
    shown=0
    for f,c in sorted(fl.items(),key=lambda x:-x[1]):
        L=funcs.get(f)
        if L is None or shown>=MAXSITES:continue
        idx=[i for i,l in enumerate(L) if tok.search(l)]
        if not idx:continue
        out.append(f"// ---- {L[0].split('(')[0].replace('export ','').replace('function ','')}   ({len(L)} lines, see out/functions/{ffile.get(f,'?')}) ----")
        out.append(L[0])
        rng=[];
        for i in idx:
            s,e=max(1,i-W),min(len(L)-1,i+W)
            if rng and s<=rng[-1][1]+1:rng[-1][1]=max(rng[-1][1],e)
            else:rng.append([s,e])
        for s,e in rng:
            if s>1:out.append("  …")
            for i in range(s,e+1):out.append(L[i]+('   // <<< '+v['ref'] if i in idx else ''))
        if rng[-1][1]<len(L)-1:out.append("  …");out.append("}")
        out.append("");shown+=1
    rest=[f for f in fl if f not in funcs]
    if len(fl)>shown: out.append(f"// ({len(fl)-shown} more function(s) read this flag: "+", ".join('f%d'%f for f in list(fl)[shown:shown+200])+")")
    open(f"{d}/{v['base']}.c",'w').write('\n'.join(out)+'\n')
    rows.append([v['name'],v['prefix'],v['type'],KDESC.get(v['kind'],'?').split(' ')[0],fmtdef(v),a,nsites,len(fl),' '.join('f%d'%f for f in list(fl)[:20])])
with open('out/flags.csv','w',newline='') as f:
    w=csv.writer(f);w.writerow(['name','prefix','type','kind','default','address','code_read_sites','functions','first_functions']);w.writerows(rows)
print("flags written:",len(rows),"with reads:",sum(1 for r in rows if r[6]),flush=True)
