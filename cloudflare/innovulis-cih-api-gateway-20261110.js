/**
 * Scoped API proxy for https://api.innovulis.com/api/v1/*
 * Does not affect /dns, /receipts, /models, /mesh or legacy API gateway routes.
 */
const API_ORIGIN = "https://innovulis-cih-evidence-preview.onrender.com";
const ORIGINS = new Set([
 "https://innovulis.com",
 "https://www.innovulis.com",
 "https://innovulis-cih-portal-preview.onrender.com"
]);
const ALLOWED_PATHS = new Set([
 "/api/v1/health", "/api/v1/architecture",
 "/api/v1/receipts", "/api/v1/verify", "/api/v1/reconcile"
]);
addEventListener("fetch", event => event.respondWith(proxy(event.request)));
function corsHeaders(origin) {
 const h = new Headers();
 if (ORIGINS.has(origin)) {
   h.set("access-control-allow-origin", origin);
   h.set("access-control-allow-methods", "GET, POST, OPTIONS");
   h.set("access-control-allow-headers", "authorization, content-type");
   h.set("access-control-max-age", "600");
 }
 h.set("vary", "Origin");
 h.set("cache-control","no-store");
 h.set("x-content-type-options","nosniff");
 h.set("content-security-policy","default-src 'none'; frame-ancestors 'none'");
 return h;
}
async function proxy(request) {
 const u = new URL(request.url);
 const origin = request.headers.get("origin") || "";
 const cors = corsHeaders(origin);
 if (!ALLOWED_PATHS.has(u.pathname)) return new Response("Not found", {status:404,headers:cors});
 if (origin && !ORIGINS.has(origin)) return new Response("Origin not allowed", {status:403,headers:cors});
 if (request.method === "OPTIONS") return new Response(null, {status:204,headers:cors});
 if (!["GET","HEAD","POST"].includes(request.method)) return new Response("Method not allowed", {status:405,headers:cors});
 if (request.method==="POST" && !["/api/v1/receipts","/api/v1/verify","/api/v1/reconcile"].includes(u.pathname))
   return new Response("Method not allowed", {status:405,headers:cors});
 let body;
 if (request.method==="POST") {
   body=await request.text();
   if (body.length>1024*1024) return new Response("Request too large",{status:413,headers:cors});
 }
 const h = new Headers();
 for (const key of ["accept","content-type","authorization"]) if (request.headers.has(key)) h.set(key, request.headers.get(key));
 const target=API_ORIGIN + u.pathname + u.search;
 try {
  const upstream=await fetch(target,{method:request.method,headers:h,body,redirect:"manual"});
  if(upstream.status>=300&&upstream.status<400) return new Response("Unexpected origin redirect",{status:502,headers:cors});
  const responseHeaders=new Headers(upstream.headers);
  responseHeaders.delete("set-cookie");
  for(const [k,v] of cors.entries()) responseHeaders.set(k,v);
  return new Response(upstream.body,{status:upstream.status,headers:responseHeaders});
 } catch(e) {
  return new Response("CIH origin unavailable",{status:503,headers:cors});
 }
}
