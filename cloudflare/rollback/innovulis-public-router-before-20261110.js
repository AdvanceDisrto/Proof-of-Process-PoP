/**
 * iNNOVULIS public-site release router.
 * Read-only static portal + iPWA; preserves existing Proof-of-Process /api/ routes.
 * No receipt data is collected by the router. No automatic approval of receipts.
 */
const SITES = Object.freeze({
 "innovulis.com":"https://innovulis-public-web.onrender.com",
 "www.innovulis.com":"https://innovulis-public-web.onrender.com",
 "proofofprocess.online":"https://ipop-public-verifier.onrender.com",
 "www.proofofprocess.online":"https://ipop-public-verifier.onrender.com"
});
addEventListener("fetch", event => event.respondWith(route(event.request)));
async function route(request) {
 const incoming = new URL(request.url);
 const target = SITES[incoming.hostname.toLowerCase()];
 if(!target)return new Response("Unconfigured public domain",{status:421});
 const legacy = incoming.hostname.endsWith("proofofprocess.online") &&
    /^\/api(?:\/|$)/.test(incoming.pathname);
 const origin = legacy ? "https://proofofprocess.onrender.com" : target;
 if(!legacy && request.method!=="GET" && request.method!=="HEAD")
    return new Response("Read-only public verifier",{status:405,headers:{"Allow":"GET, HEAD"}});
 if(incoming.pathname==="/__innovulis_release_status"&&!legacy){
    return Response.json({protocol:"ITM-PUBLIC-RELEASE-v1",status:"RENDER_STATIC_ORIGIN",role:target.includes("verifier")?"VERIFIER":"LANDING",hardware_attested:false,bitcoin_anchored:false,disbursements_authorized:false});
 }
 const url = new URL(incoming.pathname + incoming.search,origin);
 try {
    // Strip cookies/authorization and sensitive headers for public-static requests.
    const safeHeaders = new Headers();
    if(request.headers.has("accept"))safeHeaders.set("accept",request.headers.get("accept"));
    if(request.headers.has("if-none-match"))safeHeaders.set("if-none-match",request.headers.get("if-none-match"));
    const response=await fetch(url.toString(),legacy?request:new Request(url.toString(),{method:request.method,headers:safeHeaders,redirect:"follow"}));
    if(legacy)return response;
    const headers=new Headers(response.headers);
    headers.delete("set-cookie");
    headers.set("x-content-type-options","nosniff");
    headers.set("referrer-policy","no-referrer");
    headers.set("permissions-policy","camera=(), microphone=(), geolocation=(), payment=()");
    headers.set("x-frame-options","DENY");
    headers.set("x-innovulis-public-release","2026-10-27");
    if(incoming.pathname.endsWith(".wasm"))headers.set("content-type","application/wasm");
    headers.set("cache-control",incoming.pathname.endsWith("/sw.js")||incoming.pathname==="/"?"no-cache":"public, max-age=300");
    headers.set("content-security-policy",target.includes("verifier")?
     "default-src 'self'; script-src 'self' 'unsafe-inline' 'wasm-unsafe-eval'; style-src 'self' 'unsafe-inline'; connect-src 'self'; img-src 'self' data:; object-src 'none'; base-uri 'none'; form-action 'none'; frame-ancestors 'none'":
     "default-src 'none'; style-src 'unsafe-inline'; img-src 'self' data:; base-uri 'none'; object-src 'none'; form-action 'none'; frame-ancestors 'none'");
    return new Response(response.body,{status:response.status,statusText:response.statusText,headers});
 } catch(_){
    return new Response("Public static release origin unavailable",{status:503,headers:{"Cache-Control":"no-store"}});
 }
}
