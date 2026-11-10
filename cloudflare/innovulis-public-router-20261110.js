/**
 * iNNOVULIS public-site router, 2026-11-10.
 * Site origin cutover from prior public landing to reviewed CIH portal.
 * Keeps Proof-of-Process hosts and legacy verifier API isolated.
 * Dedicated CIH API paths are scoped; no arbitrary-origin proxy.
 */
const SITES = Object.freeze({
  "innovulis.com": "https://innovulis-cih-portal-preview.onrender.com",
  "www.innovulis.com": "https://innovulis-cih-portal-preview.onrender.com",
  "proofofprocess.online": "https://ipop-public-verifier.onrender.com",
  "www.proofofprocess.online": "https://ipop-public-verifier.onrender.com"
});
const CIH_API = "https://innovulis-cih-evidence-preview.onrender.com";
const RELEASE = "CIH-PUBLIC-2026-11-10";
const METHODS = ["GET","HEAD","POST"];
const CIH_ALLOWED = new Set([
  "/api/v1/health", "/api/v1/architecture", "/api/v1/receipts",
  "/api/v1/verify", "/api/v1/reconcile"
]);

addEventListener("fetch", event => event.respondWith(route(event.request)));

function hardenedHeaders(response, isVerifier, isHtml) {
  const headers = new Headers(response.headers);
  headers.delete("set-cookie");
  headers.set("x-content-type-options", "nosniff");
  headers.set("referrer-policy", "strict-origin-when-cross-origin");
  headers.set("permissions-policy", isVerifier
    ? "camera=(), microphone=(), geolocation=(), payment=()"
    : "camera=(), microphone=(self), geolocation=(), payment=()");
  headers.set("x-frame-options", "DENY");
  headers.set("x-innovulis-public-release", RELEASE);
  headers.set("cache-control", isHtml ? "no-cache" : "public, max-age=300");
  headers.set("content-security-policy", isVerifier
    ? "default-src 'self'; script-src 'self' 'unsafe-inline' 'wasm-unsafe-eval'; style-src 'self' 'unsafe-inline'; connect-src 'self'; img-src 'self' data:; object-src 'none'; base-uri 'none'; form-action 'none'; frame-ancestors 'none'"
    : "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; connect-src 'self' https://api.innovulis.com; img-src 'self' data:; object-src 'none'; base-uri 'none'; form-action 'self'; frame-ancestors 'none'");
  return headers;
}

async function route(request) {
  const incoming = new URL(request.url);
  const host = incoming.hostname.toLowerCase();
  const target = SITES[host];
  if (!target) return new Response("Unconfigured public domain", {status:421});
  const verifier = host.endsWith("proofofprocess.online");
  const legacy = verifier && /^\/api(?:\/|$)/.test(incoming.pathname);
  const isCih = !verifier && CIH_ALLOWED.has(incoming.pathname);
  const origin = legacy ? "https://proofofprocess.onrender.com" : isCih ? CIH_API : target;

  if (incoming.pathname === "/__innovulis_release_status" && !verifier) {
    return Response.json({
      protocol: RELEASE, status: "CIH_PORTAL_ORIGIN",
      role: "LANDING", api_status: "/api/v1/health",
      hardware_attested: false, bitcoin_anchored: false,
      legal_certification: false
    }, {headers: {"cache-control": "no-store", "x-innovulis-public-release": RELEASE}});
  }

  if (!legacy && !isCih && request.method !== "GET" && request.method !== "HEAD") {
    return new Response("Public website is read-only", {status:405,headers:{"allow":"GET, HEAD"}});
  }
  if (isCih && !METHODS.includes(request.method)) {
    return new Response("Method not allowed", {status:405,headers:{"allow":"GET, HEAD, POST"}});
  }
  if (isCih && request.method === "POST" && !["/api/v1/receipts","/api/v1/reconcile","/api/v1/verify"].includes(incoming.pathname)) {
    return new Response("Method not allowed", {status:405,headers:{"allow":"GET"}});
  }
  const url = new URL(incoming.pathname + incoming.search, origin);
  try {
    if (legacy) return fetch(request);
    const headers = new Headers();
    for (const key of ["accept","if-none-match","content-type"]) {
      if (request.headers.has(key)) headers.set(key, request.headers.get(key));
    }
    if (isCih && request.headers.has("authorization")) {
      headers.set("authorization", request.headers.get("authorization"));
    }
    let body;
    if (isCih && request.method === "POST") {
      body = await request.text();
      if (body.length > 1024 * 1024) return Response.json({detail:"REQUEST_TOO_LARGE"}, {status:413});
    }
    const upstream = await fetch(url.toString(), new Request(url.toString(), {
      method:request.method, headers, body, redirect:"manual"
    }));
    if (upstream.status >= 300 && upstream.status < 400) {
      return new Response("Upstream redirect blocked", {status:502});
    }
    const outHeaders = hardenedHeaders(upstream, verifier, !isCih && (incoming.pathname === "/" || incoming.pathname.endsWith(".html")));
    if (isCih) {
      outHeaders.set("cache-control","no-store");
      outHeaders.set("content-security-policy","default-src 'none'; frame-ancestors 'none'");
    }
    if (incoming.pathname.endsWith(".wasm") && !isCih) outHeaders.set("content-type","application/wasm");
    return new Response(upstream.body, {status:upstream.status,statusText:upstream.statusText,headers:outHeaders});
  } catch (_) {
    return new Response(isCih ? "CIH API unavailable" : "Static site origin unavailable",
                        {status:503,headers:{"cache-control":"no-store"}});
  }
}
