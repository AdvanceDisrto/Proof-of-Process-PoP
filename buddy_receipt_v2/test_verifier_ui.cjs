// Execute the actual generated HTML's inline JavaScript with DOM and WebCrypto mocks.
const fs=require('node:fs');const vm=require('node:vm');const assert=require('node:assert/strict');
const path=require('node:path');const here=__dirname;
async function checkViewer(filename){
  const source=fs.readFileSync(path.join(here,filename),'utf8');
  const script=source.match(/<script>([\s\S]*?)<\/script>/)?.[1];
  assert.ok(script && script.length>2000,'real HTML script extracted');
  const stored=new Map();const elems=new Map();
  function elem(id){
    if(!elems.has(id))elems.set(id,{
      id,style:{},value:'',textContent:'',className:'',hidden:false,
      listeners:{},addEventListener(type,fn){this.listeners[type]=fn;},
    });return elems.get(id);
  }
  const ctx={
    crypto:require('node:crypto').webcrypto,TextEncoder,atob,btoa,
    URL, Date, Object,console,Error,Uint8Array,setTimeout,clearTimeout,
    document:{getElementById:elem},
    window:{localStorage:{getItem:k=>stored.get(k)||null,setItem:(k,v)=>stored.set(k,v)},
      addEventListener(){}},
  };
  ctx.globalThis=ctx;
  vm.createContext(ctx);vm.runInContext(script,ctx,{timeout:1000});
  const src=fs.readFileSync(path.join(here,'demo-qr-payload.json'),'utf8');
  const accepted=await vm.runInContext('check('+JSON.stringify(src)+')',ctx);
  assert.equal(accepted,true);
  const text=elem('result').textContent;
  assert.match(text,/Gate checks:/);
  assert.match(text,/Issued UTC:/);
  assert.match(text,/Signer continuity: PINNED_KEY_FIRST_SEEN/);
  assert.match(text,/Signer identity: NOT PROVEN/);
  assert.match(text,/Full chain continuity: NOT PROVEN/);
  assert.match(text,/SHA-256|Receipt hash:/);
  const rechecked=await vm.runInContext('check('+JSON.stringify(src)+')',ctx);
  assert.equal(rechecked,true);
  assert.match(elem('result').textContent,/Signer continuity: KEY_MATCH/);
  const modified=src.replace('40 op 2 == 42','40 op 2 == 9');
  assert.notEqual(src,modified);
  const refused=await vm.runInContext('check('+JSON.stringify(modified)+')',ctx);
  assert.equal(refused,false);
  assert.match(elem('status').textContent,/FAIL CLOSED/);
  console.log(filename+': PASTE_VERIFY_UI_PASS, FRESHNESS_AND_GATE_CHECKS_DISPLAYED, TAMPER_REFUTED');
}
(async()=>{
  await checkViewer('verifier.html');await checkViewer('scanner.html');
  console.log('ACTUAL_HTML_INLINE_JS_UI_TESTS_PASS: 2 generated viewer scripts');
})().catch(e=>{console.error(e);process.exitCode=1});
