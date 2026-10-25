const PUBLIC_PATHS = new Set(["/", "/index.html", "/favicon.ico", "/health", "/reality/manifest", "/truth-boundary", "/developer", "/developer/"]);

function json(status, body) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json", "Cache-Control": "no-store" },
  });
}

function developerPortal() {
  return new Response(`<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>i™ Developer Receipt Console</title><style>
  :root{color-scheme:dark;--g:#5fffe1;--m:#8aa8a1;--glass:rgba(7,18,20,.72);--line:rgba(95,255,225,.22)}*{box-sizing:border-box}body{margin:0;min-height:100vh;background:radial-gradient(circle at 50% 12%,#123b3b 0,#071012 30%,#010304 72%);color:#effffb;font:14px/1.5 Inter,system-ui,sans-serif}.shell{max-width:1180px;margin:auto;padding:28px}.top{display:flex;justify-content:space-between;gap:16px;align-items:center}.brand{font:800 20px ui-monospace,monospace;letter-spacing:.12em}.brand i{color:var(--g);font-style:normal}.badge{border:1px solid var(--line);border-radius:999px;padding:7px 11px;color:var(--g);font:700 10px ui-monospace,monospace}.hero{display:grid;grid-template-columns:1.1fr .9fr;gap:18px;margin-top:28px}.glass{background:var(--glass);border:1px solid var(--line);border-radius:28px;backdrop-filter:blur(20px);box-shadow:inset 0 1px rgba(255,255,255,.05),0 24px 80px rgba(0,0,0,.35)}.panel{padding:24px}h1{font-size:clamp(38px,7vw,78px);line-height:.92;margin:16px 0;letter-spacing:-.055em}.muted{color:var(--m)}.receipt{padding:25px;transform:perspective(900px) rotateY(-7deg);border:1px solid var(--g);box-shadow:0 0 55px rgba(95,255,225,.13)}.receipt h2{font:800 26px ui-monospace,monospace;letter-spacing:.14em;margin:0}.state{display:inline-block;margin:16px 0;border:1px solid var(--line);border-radius:999px;padding:7px 10px;color:var(--g);font:700 10px ui-monospace,monospace}.rows{display:grid;gap:13px;border-top:1px solid var(--line);padding-top:16px}.row span{display:block;color:var(--m);font:700 9px ui-monospace,monospace;letter-spacing:.12em}.row b{font:600 12px ui-monospace,monospace;word-break:break-all}.grid{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin-top:16px}.card{padding:16px}.card small{color:var(--m);font:700 9px ui-monospace,monospace;letter-spacing:.12em}.card strong{display:block;color:var(--g);margin-top:8px}.flow{margin-top:16px;padding:18px;font:700 11px ui-monospace,monospace;color:#c8fff5}.flow i{color:var(--g);font-style:normal}.actions{display:flex;gap:9px;flex-wrap:wrap;margin-top:20px}button{border:1px solid var(--line);background:rgba(95,255,225,.05);color:#effffb;border-radius:13px;padding:10px 13px;cursor:pointer}@media(max-width:800px){.hero,.grid{grid-template-columns:1fr}.receipt{transform:none}.top{align-items:flex-start;flex-direction:column}}</style></head><body><main class="shell"><header class="top"><div class="brand"><i>i</i>™ DEVELOPER RECEIPT CONSOLE</div><div class="badge">EVIDENCE FIRST · FAIL CLOSED</div></header><section class="hero"><div class="glass panel"><div class="badge">JUST ASK BUDDY™</div><h1>The backend,<br>operated as a receipt.</h1><p class="muted">Source → build → verify → anchor → deploy. Infrastructure details stay behind the evidence surface until explicitly opened.</p><div class="actions"><button onclick="load()">Refresh evidence</button><button onclick="location.href='/truth-boundary'">Truth boundary</button><button onclick="location.href='/reality/manifest'">Raw manifest</button></div></div><article class="glass receipt"><h2>🧾 RECEIPT</h2><div class="state" id="state">CHECKING</div><div class="rows"><div class="row"><span>MANIFEST</span><b id="hash">Loading…</b></div><div class="row"><span>PHYSICAL GATE</span><b id="gate">Loading…</b></div><div class="row"><span>EDGE</span><b id="edge">CLOUDFLARE_ACTIVE</b></div><div class="row"><span>OBSERVED</span><b id="time">—</b></div></div></article></section><section class="grid"><div class="glass card"><small>SOURCE</small><strong>GitHub · main</strong></div><div class="glass card"><small>BUILD</small><strong>CI evidence</strong></div><div class="glass card"><small>ANCHOR</small><strong id="anchor">ACTION_REQUIRED</strong></div><div class="glass card"><small>IAUTO</small><strong>WATCHING</strong></div></section><div class="glass flow">SOURCE <i>→</i> BUILD <i>→</i> VERIFY <i>→</i> ANCHOR <i>→</i> DEPLOY <i>→</i> 🧾 RECEIPT</div></main><script>
async function load(){document.getElementById('time').textContent=new Date().toISOString();try{const r=await fetch('/reality/manifest',{headers:{accept:'application/json'}});if(!r.ok)throw new Error('HTTP '+r.status);const d=await r.json();document.getElementById('state').textContent=d.state||'UNKNOWN';document.getElementById('hash').textContent=d.master_manifest_hash||'UNCLAIMED / NOT SEALED';document.getElementById('gate').textContent=d.physical_gate||'ACTION_REQUIRED';document.getElementById('anchor').textContent=(d.does_not_prove||[]).includes('external blockchain anchoring')?'ACTION_REQUIRED':'EVIDENCED'}catch(e){document.getElementById('state').textContent='ACTION_REQUIRED';document.getElementById('hash').textContent='EVIDENCE API OFFLINE';document.getElementById('gate').textContent='ACTION_REQUIRED';document.getElementById('anchor').textContent='ACTION_REQUIRED'}}load();setInterval(load,15000);
</script></body></html>`, {headers:{"content-type":"text/html; charset=utf-8","cache-control":"no-store"}});
}

function hexBytes(value, expectedBytes) {
  if (!new RegExp(`^[0-9a-fA-F]{${expectedBytes * 2}}$`).test(value || "")) return null;
  return Uint8Array.from(value.match(/.{2}/g), (byte) => Number.parseInt(byte, 16));
}

async function verifySignedRequest(request, env) {
  const signatureHex = request.headers.get("X-iPop-Signature");
  const timestampText = request.headers.get("X-iPop-Timestamp");
  const publicKeyHex = env.IPOP_PUBLIC_KEY;
  if (!signatureHex || !timestampText || !publicKeyHex) return { ok:false,status:401,error:"Missing signature, timestamp, or configured public key." };
  const signature=hexBytes(signatureHex,64), publicKey=hexBytes(publicKeyHex,32), timestamp=Number(timestampText), now=Math.floor(Date.now()/1000);
  if(!signature||!publicKey||!Number.isInteger(timestamp)) return {ok:false,status:403,error:"Malformed cryptographic headers."};
  if(Math.abs(now-timestamp)>60) return {ok:false,status:403,error:"Timestamp outside 60-second acceptance window."};
  const body=request.method==="GET"||request.method==="HEAD"?"":await request.clone().text();
  const payload=new TextEncoder().encode(`${timestampText}:${body}`);
  try{
    const key=await crypto.subtle.importKey("raw",publicKey,{name:"Ed25519"},false,["verify"]);
    return await crypto.subtle.verify({name:"Ed25519"},key,signature,payload)?{ok:true}:{ok:false,status:403,error:"Ed25519 verification failed."};
  }catch{return {ok:false,status:403,error:"Ed25519 verification unavailable or key invalid."};}
}

export default {
  async fetch(request, env) {
    const url=new URL(request.url), method=request.method.toUpperCase();
    if(method==="GET"&&(url.pathname==="/developer"||url.pathname==="/developer/")) return developerPortal();
    if(!["GET","HEAD","POST"].includes(method)) return json(405,{status:"ACTION_REQUIRED",error:"Method not allowed."});
    if(!PUBLIC_PATHS.has(url.pathname)){
      const verification=await verifySignedRequest(request,env);
      if(!verification.ok) return json(verification.status,{status:"ACTION_REQUIRED",error:`EDGE_REJECTION: ${verification.error}`,doctrine:"A command is a request. Authority is separate. Evidence closes the action."});
    }
    const originUrl=new URL(request.url); originUrl.hostname=env.ORIGIN_HOST||"proofofprocess.onrender.com"; originUrl.protocol="https:";
    const headers=new Headers(request.headers); headers.set("X-iEdge-Verification","CLOUDFLARE_ACTIVE"); headers.set("X-iEdge-Timestamp",Date.now().toString());
    try{
      const upstream=await fetch(originUrl,{method,headers,body:method==="GET"||method==="HEAD"?undefined:request.body,redirect:"manual"});
      const response=new Response(upstream.body,upstream); response.headers.set("X-iEdge-Verification","CLOUDFLARE_ACTIVE"); response.headers.set("Cache-Control","no-store"); return response;
    }catch(error){
      console.error(JSON.stringify({event:"origin_fetch_failed",path:url.pathname,error:String(error)}));
      return json(502,{status:"ACTION_REQUIRED",error:"Origin unavailable; edge failed closed."});
    }
  }
};
