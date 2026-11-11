import { cihMirrorHandler } from "../supabase/functions/strmkrd-signing/cih-mirror.ts";
const enc = new TextEncoder();
function assert(condition: unknown, message: string): asserts condition {
  if (!condition) throw new Error(message);
}
function canon(value: unknown): string {
  if (value === null || ["boolean","string","number"].includes(typeof value)) return JSON.stringify(value);
  if (Array.isArray(value)) return "[" + value.map(canon).join(",") + "]";
  const data = value as Record<string,unknown>;
  return "{" + Object.keys(data).sort().map(k => JSON.stringify(k)+":"+canon(data[k])).join(",") + "}";
}
function hex(input: ArrayBuffer): string {
  return [...new Uint8Array(input)].map(v => v.toString(16).padStart(2, "0")).join("");
}
function b64(input: ArrayBuffer): string {
  return btoa(String.fromCharCode(...new Uint8Array(input)));
}
async function fixture() {
  const kp = await crypto.subtle.generateKey({name:"Ed25519"}, true, ["sign", "verify"]) as CryptoKeyPair;
  const pub = await crypto.subtle.exportKey("raw", kp.publicKey);
  const keyHash = hex(await crypto.subtle.digest("SHA-256",pub));
  const body = {
    schema: "innovulis.cih.receipt.v0.1",
    operation: "evidence_digest_validation",
    claim: "CIH self-declared test input digest matched",
    requester_subject: "local-test-node.krdid",
    request_identity: {krdid:"local-test-node.krdid",method:"LOCAL_ENROLLED_KRDID_ED25519"},
    evidence_sha256: "a".repeat(64),
    parent_receipt_hashes: [],
    warrant: "SELF_DECLARED_SOURCE; KRDID_SIGNATURE_VERIFIED; SIGNED_BY_CIH",
    does_not_prove:["physical truth","hardware attestations"],
  };
  const contents=enc.encode(canon(body));
  const receipt={
    body, body_sha256:hex(await crypto.subtle.digest("SHA-256",contents)),
    signature_b64:b64(await crypto.subtle.sign("Ed25519",kp.privateKey,contents)),
    key_id:"ed25519-sha256:"+keyHash.slice(0,24),
    storage_status:"LOCAL_SQLITE_COMMITTED",
  };
  return {receipt, trust:{key_id:receipt.key_id,public_key_b64:b64(pub),public_key_sha256:keyHash}};
}
function req(body: unknown, method="POST") {
  return new Request("https://tkrxmdonmxpeockpbazl.supabase.co/functions/v1/strmkrd-signing/cih-mirror",{
    method, headers:{"content-type":"application/json"},body:method==="POST"?JSON.stringify(body):undefined,
  });
}
async function mocked<T>(trust: unknown[], action: "pass"|"offline"|"duplicate", cb:()=>Promise<T>):Promise<{value:T;writes:number}> {
  const previousFetch=globalThis.fetch;
  const previousURL=Deno.env.get("SUPABASE_URL");
  const previousKey=Deno.env.get("SUPABASE_SERVICE_ROLE_KEY");
  const previousSecret=Deno.env.get("SUPABASE_SECRET_KEYS");
  Deno.env.set("SUPABASE_URL","https://tkrxmdonmxpeockpbazl.supabase.co");
  Deno.env.set("SUPABASE_SERVICE_ROLE_KEY","header.payload.signature");
  Deno.env.set("SUPABASE_SECRET_KEYS","{}");
  let writes=0;
  globalThis.fetch = async (input: RequestInfo | URL, init?: RequestInit):Promise<Response> => {
    const url=String(input);
    if (url.includes("/cih_node_trust?")) return new Response(JSON.stringify(trust),{status:200});
    if (url.endsWith("/cih_receipts") && init?.method==="POST") {
      writes++;
      if (action==="offline") throw new Error("simulated remote outage");
      return new Response("",{status:action==="duplicate"?409:201});
    }
    if (url.includes("/cih_receipts?")) return new Response("[]",{status:200});
    throw new Error("Unexpected URL " + url);
  };
  try { return {value:await cb(),writes}; }
  finally {
    globalThis.fetch = previousFetch;
    if (previousURL === undefined) Deno.env.delete("SUPABASE_URL"); else Deno.env.set("SUPABASE_URL",previousURL);
    if (previousKey === undefined) Deno.env.delete("SUPABASE_SERVICE_ROLE_KEY"); else Deno.env.set("SUPABASE_SERVICE_ROLE_KEY",previousKey);
    if (previousSecret === undefined) Deno.env.delete("SUPABASE_SECRET_KEYS"); else Deno.env.set("SUPABASE_SECRET_KEYS",previousSecret);
  }
}
Deno.test("GET reports readiness but does not fabricate proof",async()=>{
  const r=await cihMirrorHandler(new Request("https://example.test",{method:"GET"}));
  assert(r.status===200,"GET health");
  const data=await r.json();
  assert(data.issues_receipts===false,"remote does not issue");
  assert(data.evidence_truth_attested===false,"remote does not adjudicate truth");
});
Deno.test("anonymous unsigned POST refused before database write",async()=>{
  const r=await cihMirrorHandler(req({}));
  assert(r.status===401,"unsigned request rejected");
});
Deno.test("trusted CIH node signed receipt is mirrored after cryptographic verification",async()=>{
  const {receipt,trust}=await fixture();
  const result=await mocked([trust],"pass",()=>cihMirrorHandler(req(receipt)));
  assert(result.writes===1,"one remote write");
  assert(result.value.status===200,"acknowledged");
  const data=await result.value.json();
  assert(data.status==="REPLICA_ACKNOWLEDGED","database acknowledgement");
  assert(data.receipt_hash===receipt.body_sha256,"same cryptographic root");
});
Deno.test("tampering with signed body invalidates receipt",async()=>{
  const {receipt,trust}=await fixture();
  receipt.body.claim="Changed claim without recomputing signature";
  const result=await mocked([trust],"pass",()=>cihMirrorHandler(req(receipt)));
  assert(result.writes===0,"no write when tampered");
  assert(result.value.status===403,"tampering must fail closed");
});
Deno.test("unregistered self-signed Ed25519 key is never authority",async()=>{
  const {receipt}=await fixture();
  const result=await mocked([],"pass",()=>cihMirrorHandler(req(receipt)));
  assert(result.value.status===403,"unregistered node is forbidden");
  assert(result.writes===0,"no write");
});
Deno.test("trusted key hash must match fingerprint and pinned registry",async()=>{
  const {receipt,trust}=await fixture();
  const result=await mocked([{...trust,public_key_sha256:"f".repeat(64)}],"pass",()=>cihMirrorHandler(req(receipt)));
  assert(result.value.status===503,"corrupt pinned key fails closed");
  assert(result.writes===0,"no write");
});
Deno.test("database outage never mislabels a remote replica as acknowledged",async()=>{
  const {receipt,trust}=await fixture();
  const result=await mocked([trust],"offline",()=>cihMirrorHandler(req(receipt)));
  assert(result.value.status===503,"outage is unavailable, not success");
});
Deno.test("duplicate database hash without matching content is NOT accepted",async()=>{
  const {receipt,trust}=await fixture();
  const result=await mocked([trust],"duplicate",()=>cihMirrorHandler(req(receipt)));
  assert(result.value.status===409,"duplicate conflict requires equality verification");
});
