import { cihMirrorHandler } from "./cih-mirror.ts";
// MASTER P SIGNING SERVICE
// Generates the orchestrator keypair, signs Decision Receipts with P-256,
// and exposes public verification. Private key lives ONLY in the function
// secret MASTERP_SIGNING_KEY — never in the database.

const SUPABASE_URL = Deno.env.get("SUPABASE_URL")!;
const SERVICE_KEY = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!;
const SIGNING_JWK = Deno.env.get("MASTERP_SIGNING_KEY"); // private JWK, JSON string

const CORS = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Methods": "POST, GET, OPTIONS",
  "Access-Control-Allow-Headers": "content-type",
};

function json(b: unknown, s = 200) {
  return new Response(JSON.stringify(b, null, 2), {
    status: s, headers: { "content-type": "application/json", ...CORS },
  });
}

async function rpc(name: string, args: unknown) {
  const r = await fetch(`${SUPABASE_URL}/rest/v1/rpc/${name}`, {
    method: "POST",
    headers: { "Content-Type": "application/json", apikey: SERVICE_KEY, Authorization: `Bearer ${SERVICE_KEY}` },
    body: JSON.stringify(args),
  });
  if (!r.ok) throw new Error(`${name}: HTTP ${r.status}`);
  return await r.json();
}

const b64u = (b: ArrayBuffer | Uint8Array) => {
  const bytes = b instanceof Uint8Array ? b : new Uint8Array(b);
  return btoa(String.fromCharCode(...bytes)).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
};
const fromB64u = (s: string) => {
  const p = s.replace(/-/g, "+").replace(/_/g, "/");
  return Uint8Array.from(atob(p + "=".repeat((4 - (p.length % 4)) % 4)), (c) => c.charCodeAt(0));
};

async function loadPrivateKey(): Promise<CryptoKey | null> {
  if (!SIGNING_JWK) return null;
  try {
    const jwk = JSON.parse(SIGNING_JWK);
    return await crypto.subtle.importKey("jwk", jwk, { name: "ECDSA", namedCurve: "P-256" }, false, ["sign"]);
  } catch { return null; }
}

Deno.serve(async (req) => {
  const url = new URL(req.url);
  const path = url.pathname;
  // Additive, isolated CIH Ed25519 mirror; do not alter Master P endpoints.
  if (path.endsWith("/cih-mirror")) return await cihMirrorHandler(req);
  if (req.method === "OPTIONS") return new Response(null, { status: 204, headers: CORS });

  // Generate a fresh keypair. Returns the private JWK ONCE — store it as a secret.
  if (path.endsWith("/generate") && req.method === "POST") {
    const kp = await crypto.subtle.generateKey({ name: "ECDSA", namedCurve: "P-256" }, true, ["sign", "verify"]);
    const pubRaw = b64u(await crypto.subtle.exportKey("raw", kp.publicKey));
    const privJwk = await crypto.subtle.exportKey("jwk", kp.privateKey);
    await rpc("masterp_register_authority", {
      p_id: "masterp", p_purpose: "Decision Receipt signing", p_public_key: pubRaw,
    });
    return json({
      ok: true,
      public_key_registered: pubRaw,
      private_key_jwk: privJwk,
      instruction: "Store private_key_jwk as the Supabase Edge Function secret MASTERP_SIGNING_KEY (as a JSON string). It is shown ONCE and never persisted.",
    });
  }

  // Status
  if (path.endsWith("/status") || req.method === "GET") {
    const authority = await rpc("masterp_get_authority", { p_id: "masterp" }).catch(() => null);
    const key = await loadPrivateKey();
    return json({
      service: "Master P Signing Authority",
      signing_key_loaded: Boolean(key),
      public_authority: authority,
      algorithm: "ECDSA_P256_SHA256",
      status: key && authority ? "ready" : "not_configured",
      note: key && authority
        ? "Receipts can be signed and independently verified."
        : !authority ? "No public authority registered. POST /generate to create a keypair."
        : "Public key registered but MASTERP_SIGNING_KEY secret is not set, so signing is unavailable.",
    });
  }

  // Sign a receipt by hash
  if (path.endsWith("/sign") && req.method === "POST") {
    const key = await loadPrivateKey();
    if (!key) return json({ error: "signing_key_not_configured",
      message: "MASTERP_SIGNING_KEY secret is not set. Receipts remain hash-chained (tamper-evident) but unsigned (origin not proven)." }, 503);

    const { receipt_id, payload_hash } = await req.json().catch(() => ({}));
    if (!receipt_id || !payload_hash) return json({ error: "receipt_id and payload_hash required" }, 400);

    const sig = await crypto.subtle.sign({ name: "ECDSA", hash: "SHA-256" }, key,
      new TextEncoder().encode(payload_hash));
    const sigB64 = b64u(sig);
    const saved = await rpc("masterp_sign_receipt", { p_receipt_id: receipt_id, p_signature: sigB64 });
    return json({ ...saved, signature: sigB64 });
  }

  // Publicly verify a receipt — anyone can call this.
  if (path.endsWith("/verify") && req.method === "POST") {
    const { receipt_id } = await req.json().catch(() => ({}));
    if (!receipt_id) return json({ error: "receipt_id required" }, 400);
    const v = await rpc("masterp_verifiable_receipt", { p_id: receipt_id });
    if (!v) return json({ error: "receipt not found" }, 404);
    if (!v.signature) return json({ ...v, verified: false, reason: "receipt is not signed" });

    try {
      const pub = await crypto.subtle.importKey("raw", fromB64u(v.verify_with.public_key),
        { name: "ECDSA", namedCurve: "P-256" }, false, ["verify"]);
      const valid = await crypto.subtle.verify({ name: "ECDSA", hash: "SHA-256" }, pub,
        fromB64u(v.signature), new TextEncoder().encode(v.payload_hash));
      return json({ ...v, verified: valid,
        reason: valid ? "signature valid — receipt origin and integrity confirmed" : "SIGNATURE INVALID — receipt was altered or forged" });
    } catch (e) {
      return json({ ...v, verified: false, reason: `verification error: ${String(e)}` }, 500);
    }
  }

  return json({ endpoints: ["/status", "/generate (POST)", "/sign (POST)", "/verify (POST)"] });
});
