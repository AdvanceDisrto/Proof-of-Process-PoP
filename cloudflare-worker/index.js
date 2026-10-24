const PUBLIC_PATHS = new Set(["/", "/index.html", "/favicon.ico", "/health", "/reality/manifest", "/truth-boundary"]);

function json(status, body) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json", "Cache-Control": "no-store" },
  });
}

function hexBytes(value, expectedBytes) {
  if (!new RegExp(`^[0-9a-fA-F]{${expectedBytes * 2}}$`).test(value || "")) return null;
  return Uint8Array.from(value.match(/.{2}/g), (byte) => Number.parseInt(byte, 16));
}

async function verifySignedRequest(request, env) {
  const signatureHex = request.headers.get("X-iPop-Signature");
  const timestampText = request.headers.get("X-iPop-Timestamp");
  const publicKeyHex = env.IPOP_PUBLIC_KEY;

  if (!signatureHex || !timestampText || !publicKeyHex) {
    return { ok: false, status: 401, error: "Missing signature, timestamp, or configured public key." };
  }

  const signature = hexBytes(signatureHex, 64);
  const publicKey = hexBytes(publicKeyHex, 32);
  const timestamp = Number(timestampText);
  const now = Math.floor(Date.now() / 1000);
  if (!signature || !publicKey || !Number.isInteger(timestamp)) {
    return { ok: false, status: 403, error: "Malformed cryptographic headers." };
  }
  if (Math.abs(now - timestamp) > 60) {
    return { ok: false, status: 403, error: "Timestamp outside 60-second acceptance window." };
  }

  const body = request.method === "GET" || request.method === "HEAD" ? "" : await request.clone().text();
  const payload = new TextEncoder().encode(`${timestampText}:${body}`);
  try {
    const key = await crypto.subtle.importKey("raw", publicKey, { name: "Ed25519" }, false, ["verify"]);
    const ok = await crypto.subtle.verify({ name: "Ed25519" }, key, signature, payload);
    return ok ? { ok: true } : { ok: false, status: 403, error: "Ed25519 verification failed." };
  } catch {
    return { ok: false, status: 403, error: "Ed25519 verification unavailable or key invalid." };
  }
}

export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);
    const method = request.method.toUpperCase();
    if (!["GET", "HEAD", "POST"].includes(method)) {
      return json(405, { status: "ACTION_REQUIRED", error: "Method not allowed." });
    }

    if (!PUBLIC_PATHS.has(url.pathname)) {
      const verification = await verifySignedRequest(request, env);
      if (!verification.ok) {
        return json(verification.status, {
          status: "ACTION_REQUIRED",
          error: `EDGE_REJECTION: ${verification.error}`,
          doctrine: "A command is a request. Authority is separate. Evidence closes the action.",
        });
      }
    }

    const originUrl = new URL(request.url);
    originUrl.hostname = env.ORIGIN_HOST || "proofofprocess.onrender.com";
    originUrl.protocol = "https:";
    const headers = new Headers(request.headers);
    headers.set("X-iEdge-Verification", "CLOUDFLARE_ACTIVE");
    headers.set("X-iEdge-Timestamp", Date.now().toString());

    const upstream = await fetch(originUrl, {
      method,
      headers,
      body: method === "GET" || method === "HEAD" ? undefined : request.body,
      redirect: "manual",
    });
    const response = new Response(upstream.body, upstream);
    response.headers.set("X-iEdge-Verification", "CLOUDFLARE_ACTIVE");
    response.headers.set("Cache-Control", "no-store");
    return response;
  },
};
