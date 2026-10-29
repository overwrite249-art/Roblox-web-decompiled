// ctors.js - instantiate WebClient.wasm in Node with stub imports, run __wasm_call_ctors
// (all static init, incl. flag registration) and read every flag default from memory,
// incl. strings (libc++ std::string). Needs Node >= 22: node --experimental-wasm-exnref ctors.js
// in: WebClient.wasm, WebClient.wat (first 3 MB, for import signatures), inv_*.json -> runtime_values.json
const fs=require('fs');
const fd=fs.openSync('WebClient.wat','r');const hb=Buffer.alloc(3_000_000);fs.readSync(fd,hb,0,hb.length,0);fs.closeSync(fd);const wat=hb.toString('utf8').split('\n');
const types={};for(const l of wat){const m=l.match(/^\s*\(type \(;(\d+);\) \(func(.*)\)\)\s*$/);if(m){const r=m[2].match(/\(result ([^)]*)\)/);types[m[1]]=r?r[1].trim():''}}
const imports={};const calls={};
for(const l of wat){const m=l.match(/^\s*\(import "([^"]+)" "([^"]+)" \(func \(;(\d+);\) \(type (\d+)\)/);if(!m)continue;
  const [_,mod,name,idx,ty]=m;const rr=l.match(/\(result ([^)]*)\)/);const res=rr?rr[1].trim():(types[ty]||'');(imports[mod]??={});
  imports[mod][name]=(...a)=>{calls[name]=(calls[name]||0)+1;return res==='i64'?0n:(res===''?undefined:0)};}
const memory=new WebAssembly.Memory({initial:4096,maximum:65536,shared:true});imports.env.memory=memory;
const t0=Date.now();
const mod=new WebAssembly.Module(fs.readFileSync('WebClient.wasm'));console.log('compiled in',(Date.now()-t0)/1000,'s');
let EX=null;
imports.env._emscripten_init_main_thread_js=(tb)=>{calls.init_main=(calls.init_main||0)+1;EX._emscripten_thread_init(tb,1,1,1,1<<20,0);EX._emscripten_tls_init();};
if(imports.env.emscripten_get_now) imports.env.emscripten_get_now=()=>performance.now();
const inst=new WebAssembly.Instance(mod,imports);EX=inst.exports;console.log('instantiated (start fn ran)');
const E=inst.exports;let err=null;

try{E.__wasm_call_ctors();console.log('ctors completed OK')}catch(e){err=e.message;console.log('ctors error:',e.message)}
console.log('import calls during init:',JSON.stringify(calls).slice(0,400));
const m8=new Uint8Array(memory.buffer),dv=new DataView(memory.buffer);
const inv=Object.assign(JSON.parse(fs.readFileSync('inv_engine.json')),JSON.parse(fs.readFileSync('inv_luau.json')));
const out={};let ok=0,bad=0;
for(const [a,v] of Object.entries(inv)){const A=+a;
  if(v.type==='String'){const long=m8[A+11]&0x80;let p,n;
    if(long){p=dv.getUint32(A,true);n=dv.getUint32(A+4,true)}else{p=A;n=m8[A+11]}
    if(n>100000||p+n>m8.length){bad++;continue}
    out[a]=Buffer.from(m8.slice(p,p+n)).toString('utf8');ok++;}
  else if(v.type==='Int') out[a]=dv.getInt32(A,true); else out[a]=m8[A];}
fs.writeFileSync('runtime_values.json',JSON.stringify({err,values:out}));
console.log('strings decoded',ok,'bad',bad,'non-empty',Object.entries(inv).filter(([a,v])=>v.type==='String'&&out[a]).length);
let same=0,diff=0,ex=[];for(const [a,v] of Object.entries(inv)){if(v.type==='String'||v.default==null)continue;if(v.default===out[a])same++;else{diff++;if(ex.length<6)ex.push([v.name,v.default,out[a]])}}
console.log('static-vs-runtime defaults: same',same,'diff',diff,JSON.stringify(ex));
const S=Object.entries(inv).filter(([a,v])=>v.type==='String').slice(0,6).map(([a,v])=>[v.name,out[a]]);console.log(JSON.stringify(S).slice(0,600));
process.exit(0);
