/**
 * iNNOVULIS™ CIH ΔiΔ — OPTIONAL Supabase Edge receipt mirror.
 *
 * No Auth0 / Supabase Auth / caller API key. verify_jwt=false is intentional:
 * this handler authenticates the signed CIH node receipt against an independent
 * operator-enrolled public key in public.cih_node_trust. Every write uses the
 * Supabase Edge runtime's server-only service_role key, never a browser secret.
 *
 * This is replication of a locally committed receipt, not issuance or truth
 * certification. No automatic enrollment or acceptance of submitted public keys.
 */
const PROJECT = "https://tkrxmdonmxpeockpbazl.supabase.co";
const MAX_BYTES = 32768;
const PREFIX = "ed25519-sha256:";
const HEX64 = /^[0-9a-f]{64}$/;
const KEY_ID = /^ed25519-sha256:[0-9a-f]{24}$/;
const KRDID = /^[a-z][a-z0-9_-]{2,62}\.krdid$/;
const HEADERS = { "content-type": "application/json; charset=utf-8", "cache-control": "no-store" };

type Dict = Record<string, unknown>;

function json(value: unknown, status = 200): Response {
  return new Response(JSON.stringify(value), { status, headers: HEADERS });
}
function obj(value: unknown): value is Dict {
  return value !== null && typeof value === "object" && !Array.isArray(value);
}
function canonical(value: unknown): string {
  if (value === null || typeof value === "string" || typeof value === "boolean") {
    return JSON.stringify(value);
  }
  if (typeof value === "number" && Number.isFinite(value)) return JSON.stringify(value);
  if (Array.isArray(value)) return "[" + value.map(canonical).join(",") + "]";
  if (!obj(value)) throw new Error("INVALID_CANONICAL_JSON");
  return "{" + Object.keys(value).sort()
    .map(k => JSON.stringify(k) + ":" + canonical(value[k])).join(",") + "}";
}
function hex(bytes: ArrayBuffer | Uint8Array): string {
  const data = bytes instanceof Uint8Array ? bytes : new Uint8Array(bytes);
  return Array.from(data, byte => byte.toString(16).padStart(2, "0")).join("");
}
function base64Bytes(input: string, expectedLength: number): Uint8Array {
  if (!/^[A-Za-z0-9+/]+={0,2}$/.test(input)) throw new Error("INVALID_B64");
  const decoded = atob(input);
  if (decoded.length !== expectedLength) throw new Error("INVALID_B64_LENGTH");
  return Uint8Array.from(decoded, c => c.charCodeAt(0));
}
async function sha(data: Uint8Array): Promise<string> {
  return hex(await crypto.subtle.digest("SHA-256", data));
}
async function boundedText(req: Request): Promise<string> {
  if (Number(req.headers.get("content-length") || "0") > MAX_BYTES) throw new Error("REQUEST_TOO_LARGE");
  if (!req.body) throw new Error("BODY_REQUIRED");
  const reader = req.body.getReader();
  const chunks: Uint8Array[] = [];
  let total = 0;
  try {
    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      total += value.length;
      if (total > MAX_BYTES) { await reader.cancel(); throw new Error("REQUEST_TOO_LARGE"); }
      chunks.push(value);
    }
  } finally {
    reader.releaseLock();
  }
  const all = new Uint8Array(total);
  let pos = 0;
  for (const part of chunks) { all.set(part, pos); pos += part.length; }
  return new TextDecoder("utf-8", { fatal: true }).decode(all);
}
function findSecret(value: unknown): string | null {
  if (typeof value === "string" && value.startsWith("sb_secret_")) return value;
  if (Array.isArray(value)) for (const x of value) { const s = findSecret(x); if (s) return s; }
  if (obj(value)) for (const v of Object.values(value)) { const s = findSecret(v); if (s) return s; }
  return null;
}
function credentials(): { url: string; headers: HeadersInit } | null {
  const envURL = Deno.env.get("SUPABASE_URL");
  if (envURL && envURL.replace(/\/$/, "") !== PROJECT) return null;
  const legacy = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY") || "";
  let newer = "";
  try { newer = findSecret(JSON.parse(Deno.env.get("SUPABASE_SECRET_KEYS") || "{}")) || ""; }
  catch { /* reject invalid structured secrets; prefer legacy default */ }
  const key = newer || legacy;
  if (!key || key.startsWith("sb_publishable_")) return null;
  const headers: Record<string, string> = { "apikey": key, "content-type": "application/json" };
  if (!key.startsWith("sb_secret_")) headers.authorization = "Bearer " + key;
  return { url: PROJECT, headers };
}
async function dbGet(path: string, access: ReturnType<typeof credentials>): Promise<Dict[] | null> {
  if (!access) return null;
  const response = await fetch(access.url + "/rest/v1/" + path, { headers: access.headers, signal: AbortSignal.timeout(6000) });
  if (!response.ok) return null;
  const values: unknown = await response.json();
  return Array.isArray(values) && values.every(obj) ? values : null;
}
function validReceipt(input: unknown): input is Dict & { body: Dict; body_sha256: string; signature_b64: string; key_id: string } {
  if (!obj(input) || !obj(input.body)) return false;
  if (typeof input.body_sha256 !== "string" || !HEX64.test(input.body_sha256)) return false;
  if (typeof input.key_id !== "string" || !KEY_ID.test(input.key_id)) return false;
  if (typeof input.signature_b64 !== "string" || !/^[A-Za-z0-9+/]{86}==$/.test(input.signature_b64)) return false;
  if (input.storage_status !== "LOCAL_SQLITE_COMMITTED") return false;
  const body = input.body;
  if (body.schema !== "innovulis.cih.receipt.v0.1" ||
      body.operation !== "evidence_digest_validation" ||
      typeof body.claim !== "string" || body.claim.length < 3 ||
      typeof body.requester_subject !== "string" || !KRDID.test(body.requester_subject) ||
      !obj(body.request_identity) || body.request_identity.krdid !== body.requester_subject ||
      body.request_identity.method !== "LOCAL_ENROLLED_KRDID_ED25519" ||
      typeof body.evidence_sha256 !== "string" || !HEX64.test(body.evidence_sha256) ||
      !Array.isArray(body.parent_receipt_hashes) ||
      body.parent_receipt_hashes.length > 32 ||
      !body.parent_receipt_hashes.every(v => typeof v === "string" && HEX64.test(v)) ||
      typeof body.warrant !== "string" ||
      !body.warrant.includes("KRDID_SIGNATURE_VERIFIED") ||
      !body.warrant.includes("SIGNED_BY_CIH")) return false;
  return true;
}
async function handle(req: Request): Promise<Response> {
  if (req.method === "GET") {
    return json({
      service: "innovulis-cih-signed-receipt-mirror",
      status: "READY_FOR_TRUSTED_SIGNED_RECEIPTS",
      authentication: "ENROLLED_CIH_NODE_ED25519",
      replica: "SUPABASE_POSTGRES_SECONDARY_ONLY",
      issues_receipts: false,
      evidence_truth_attested: false,
    });
  }
  if (req.method !== "POST") return json({ error: "METHOD_NOT_ALLOWED" }, 405);

  let input: unknown;
  try { input = JSON.parse(await boundedText(req)); }
  catch { return json({ error: "INVALID_OR_OVERSIZE_RECEIPT" }, 400); }
  if (!validReceipt(input)) return json({ error: "SIGNED_RECEIPT_REQUIRED" }, 401);

  const access = credentials();
  if (!access) return json({ error: "EDGE_SERVER_STORAGE_CREDENTIAL_UNAVAILABLE" }, 503);

  // A caller-supplied public key is NEVER an authority. The key must already
  // exist and be active in the operator-managed DB trust registry.
  const trust = await dbGet(
    "cih_node_trust?select=key_id,public_key_b64,public_key_sha256&active=eq.true&key_id=eq." +
      encodeURIComponent(input.key_id),
    access,
  );
  if (trust === null) return json({ error: "TRUST_STORE_UNAVAILABLE" }, 503);
  if (trust.length !== 1) return json({ error: "CIH_NODE_NOT_ENROLLED" }, 403);

  try {
    const row = trust[0];
    if (typeof row.public_key_b64 !== "string" || typeof row.public_key_sha256 !== "string") {
      return json({ error: "INVALID_PINNED_NODE_KEY" }, 503);
    }
    const pub = base64Bytes(row.public_key_b64, 32);
    const pubHash = await sha(pub);
    if (row.public_key_sha256 !== pubHash || PREFIX + pubHash.slice(0, 24) !== input.key_id) {
      return json({ error: "PINNED_NODE_KEY_MISMATCH" }, 503);
    }
    const signedBody = new TextEncoder().encode(canonical(input.body));
    if (await sha(signedBody) !== input.body_sha256) return json({ error: "RECEIPT_BODY_HASH_MISMATCH" }, 403);
    const sig = base64Bytes(input.signature_b64, 64);
    const key = await crypto.subtle.importKey("raw", pub, { name: "Ed25519" }, false, ["verify"]);
    if (!await crypto.subtle.verify("Ed25519", key, sig, signedBody)) {
      return json({ error: "REFUTED_SIGNATURE" }, 403);
    }
  } catch {
    return json({ error: "INVALID_SIGNED_RECEIPT" }, 403);
  }

  const record = {
    receipt_hash: input.body_sha256,
    requester_subject: input.body.requester_subject,
    receipt_body: input.body,
    signature_b64: input.signature_b64,
    key_id: input.key_id,
  };
  let response: Response;
  try {
    response = await fetch(access.url + "/rest/v1/cih_receipts", {
      method: "POST",
      headers: { ...access.headers, "prefer": "return=minimal" },
      body: JSON.stringify(record),
      signal: AbortSignal.timeout(7000),
    });
  } catch {
    return json({ error: "REPLICA_STORAGE_UNAVAILABLE" }, 503);
  }

  if (response.status === 409) {
    // Idempotence only when the full stored signed content matches.
    const found = await dbGet(
      "cih_receipts?select=receipt_hash,requester_subject,receipt_body,signature_b64,key_id&receipt_hash=eq." +
        input.body_sha256, access,
    );
    if (found?.length === 1) {
      const old = found[0];
      if (old.receipt_hash === record.receipt_hash &&
          old.requester_subject === record.requester_subject &&
          old.signature_b64 === record.signature_b64 &&
          old.key_id === record.key_id &&
          canonical(old.receipt_body) === canonical(record.receipt_body)) {
        return json({ status: "REPLICA_ALREADY_PRESENT", receipt_hash: input.body_sha256 }, 200);
      }
    }
    return json({ error: "REPLICA_HASH_CONFLICT" }, 409);
  }
  if (![200, 201, 204].includes(response.status)) {
    return json({ error: "REPLICA_STORAGE_UNAVAILABLE" }, 503);
  }
  return json({
    status: "REPLICA_ACKNOWLEDGED",
    receipt_hash: input.body_sha256,
    authenticated_as: "PINNED_CIH_NODE_ED25519",
    storage: "SUPABASE_POSTGRES_SECONDARY",
    does_not_prove: ["physical truth", "hardware attestation", "tamper-proof remote database", "network consensus"],
  }, 200);
}
Deno.serve(async (req) => {
  try { return await handle(req); }
  catch { return json({ error: "EDGE_REPLICA_INTERNAL_ERROR" }, 503); }
});
