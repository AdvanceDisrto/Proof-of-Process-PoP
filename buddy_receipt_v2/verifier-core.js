/* Buddy™ v2 I-JSON canonical signed receipt verifier. No network, no eval, no dynamic imports.
 * v1 is LEGACY UNSIGNED and is intentionally NOT accepted as v2.
 * This uses the RFC8785 canonical result for the v2 NO-NUMBERS profile, not a general JCS library.
 */
(function (global) {
  "use strict";
  const REQUIRED = ["schema","brain","kind","role","has_checkpoint","connection_status",
    "external_provider","external_model_version","request_hash","output_hash","claims","refusals",
    "disclosure","gate_verdict","gate_checks","gate_reason","prev_hash","genesis","ts",
    "legacy_receipt_hash","receipt_hash","signer_pubkey","signature"];
  const BODY = REQUIRED.filter(x => !["receipt_hash","signer_pubkey","signature"].includes(x));
  const HEX = /^sha256:[0-9a-f]{64}$/;
  const B64_KEY = /^[A-Za-z0-9+/]{43}=$/;
  const B64_SIG = /^[A-Za-z0-9+/]{86}==$/;
  const TS = /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z$/;
  const VALID_KINDS = new Set(["deterministic","head","router","oracle","external_llm","refusal"]);
  const VALID_VERDICTS = new Set(["ACCEPT","ACCEPT-REFUSAL","REJECT"]);
  const ZERO = "sha256:" + "0".repeat(64);

  function validUnicode(s) {
    for (let i = 0; i < s.length; i++) {
      const n=s.charCodeAt(i);
      if (n >= 0xD800 && n <= 0xDBFF) {
        const next=s.charCodeAt(++i);
        if (!(next >= 0xDC00 && next <= 0xDFFF)) throw Error("INVALID_UNPAIRED_UNICODE_SURROGATE");
      } else if (n >= 0xDC00 && n <= 0xDFFF) throw Error("INVALID_UNPAIRED_UNICODE_SURROGATE");
    }
  }
  function quoted(s) {
    validUnicode(s);
    let out='"';
    for (let i=0;i<s.length;i++) {
      const c=s.charCodeAt(i);
      if (c === 34) out+='\\"';
      else if(c === 92) out+='\\\\';
      else if(c === 8) out+='\\b';
      else if(c === 12) out+='\\f';
      else if(c === 10) out+='\\n';
      else if(c === 13) out+='\\r';
      else if(c === 9) out+='\\t';
      else if(c < 32) out+='\\u'+c.toString(16).padStart(4,'0');
      else out+=s[i];
    }
    return out+'"';
  }
  function canonicalString(value) {
    if(value===null) return 'null';
    if(value===true) return 'true';
    if(value===false) return 'false';
    if(typeof value==='string') return quoted(value);
    if(typeof value==='number' || typeof value==='bigint') throw Error('V2_CANONICAL_PROFILE_PROHIBITS_NUMBERS');
    if(Array.isArray(value)) return '['+value.map(canonicalString).join(',')+']';
    if(value && typeof value==='object' && Object.prototype.toString.call(value)==="[object Object]"){
      return '{'+Object.keys(value).sort().map(k=>quoted(k)+':'+canonicalString(value[k])).join(',')+'}';
    }
    throw Error('UNSUPPORTED_JSON_TYPE');
  }
  function bytes(value){return new TextEncoder().encode(canonicalString(value));}
  function b64(b,exact){
    if(typeof b!=='string'||!new RegExp('^[A-Za-z0-9+/]+={0,2}$').test(b))throw Error('INVALID_BASE64');
    const x=Uint8Array.from(atob(b),c=>c.charCodeAt(0));
    if(x.length!==exact||btoa(String.fromCharCode(...x))!==b)throw Error('INVALID_BASE64_LENGTH_OR_ENCODING');
    return x;
  }
  function hex(b){return Array.from(new Uint8Array(b)).map(v=>v.toString(16).padStart(2,'0')).join('');}
  async function digest(value){return 'sha256:'+hex(await crypto.subtle.digest('SHA-256',bytes(value)));}
  function validate(rec){
    if(!rec||typeof rec!=='object'||Array.isArray(rec))throw Error('RECEIPT_OBJECT_REQUIRED');
    if(Object.keys(rec).length!==REQUIRED.length||REQUIRED.some(f=>!Object.hasOwn(rec,f)))throw Error('RECEIPT_SCHEMA_FIELDS_MISMATCH');
    if(rec.schema!=='bitwitness/brain/receipt/v2')throw Error('UNSUPPORTED_RECEIPT_VERSION');
    if(!VALID_KINDS.has(rec.kind)||!VALID_VERDICTS.has(rec.gate_verdict))throw Error('INVALID_KIND_OR_VERDICT');
    for(const key of ['brain','kind','role','connection_status','external_provider',
      'external_model_version','disclosure','gate_verdict','gate_reason','ts']) {
      if(typeof rec[key]!=='string')throw Error('INVALID_STRING_FIELD_'+key);
    }
    if(!['','n/a','ready','not_connected','unreachable'].includes(rec.connection_status))throw Error('INVALID_CONNECTION_STATUS');
    if(!rec.brain||!rec.disclosure)throw Error('REQUIRED_TEXT_MISSING');
    if(typeof rec.has_checkpoint!=='boolean'||typeof rec.genesis!=='boolean')throw Error('INVALID_BOOLEAN_FIELD');
    if(!TS.test(rec.ts)||!Number.isFinite(Date.parse(rec.ts))||new Date(rec.ts).toISOString()!==rec.ts)throw Error('BAD_RFC3339_UTC_TIMESTAMP');
    for(const k of ['claims','refusals','gate_checks']) {
      if(!Array.isArray(rec[k])||!rec[k].every(x=>typeof x==='string')) throw Error('BAD_ARRAY_'+k);
    }
    for(const k of ['request_hash','prev_hash','legacy_receipt_hash','receipt_hash']) {
      if(typeof rec[k]!=='string'||!HEX.test(rec[k]))throw Error('BAD_HASH_'+k);
    }
    if(rec.output_hash!==''&&(typeof rec.output_hash!=='string'||!HEX.test(rec.output_hash)))throw Error('BAD_OUTPUT_HASH');
    if(!B64_KEY.test(rec.signer_pubkey)||!B64_SIG.test(rec.signature))throw Error('BAD_SIGNATURE_SHAPE');
    if(rec.genesis && rec.prev_hash!==ZERO)throw Error('GENESIS_PARENT_NONZERO');
    bytes(rec); // reject numbers, malformed surrogates and unsupported types
    return rec;
  }
  async function verifyReceipt(rec, independentlyPinnedKeyB64) {
    try {
      validate(rec);
      if(!independentlyPinnedKeyB64||typeof independentlyPinnedKeyB64!=='string')throw Error('INDEPENDENT_TRUST_ANCHOR_REQUIRED');
      const pinned=b64(independentlyPinnedKeyB64,32);
      const claimed=b64(rec.signer_pubkey,32);
      if(!pinned.every((x,i)=>x===claimed[i])) throw Error('UNTRUSTED_SIGNER_PUBLIC_KEY');
      const body=Object.fromEntries(BODY.map(k=>[k,rec[k]]));
      const computed=await digest(body);
      if(computed!==rec.receipt_hash)throw Error('RECEIPT_HASH_MISMATCH');
      const signingPayload={...body,receipt_hash:rec.receipt_hash};
      const pub=await crypto.subtle.importKey('raw',pinned,{name:'Ed25519'},false,['verify']);
      const ok=await crypto.subtle.verify({name:'Ed25519'},pub,b64(rec.signature,64),bytes(signingPayload));
      if(!ok)throw Error('ED25519_SIGNATURE_REFUTED');
      return {valid:true,integrity:'MATCH',signature:'ED25519_VALID',
        signer_identity:'PINNED_KEY_ONLY_NO_LEGAL_IDENTITY',
        chain:'PREV_HASH_SIGNED_NOT_FULL_CHAIN_VERIFIED',
        root:rec.receipt_hash,brain:rec.brain,gate_verdict:rec.gate_verdict,gate_checks:rec.gate_checks,
        ts:rec.ts,age_seconds:Math.round((Date.now()-Date.parse(rec.ts))/1000)};
    } catch(error){
      return {valid:false,error:error instanceof Error?error.message:'VERIFICATION_UNAVAILABLE',
        signature:'NOT_VERIFIED',signer_identity:'NOT_VERIFIED',chain:'NOT_VERIFIED'};
    }
  }
  function keyContinuity(storage,brain,pubkey) {
    // Continuity only: authority must have been established independently first.
    if(!storage)return {status:'STORAGE_UNAVAILABLE'};
    const key='innovulis-buddy-v2-trusted:'+brain;
    try {
      const previous=storage.getItem(key);
      if(previous){
        const saved=JSON.parse(previous);
        return saved.pubkey===pubkey
          ?{status:'KEY_MATCH',first_seen:saved.first_seen}
          :{status:'KEY_CHANGED_BLOCK',first_seen:saved.first_seen};
      }
      const first_seen=new Date().toISOString();
      storage.setItem(key,JSON.stringify({pubkey,first_seen}));
      return {status:'PINNED_KEY_FIRST_SEEN',first_seen};
    }catch{return {status:'STORAGE_UNAVAILABLE'};}
  }
  function formatAge(seconds) {
    if(!Number.isFinite(seconds))return 'AGE UNKNOWN';
    if(seconds < -60)return `${Math.abs(seconds)} seconds IN THE FUTURE (check clock)`;
    if(seconds<60)return `${Math.max(0,seconds)} seconds ago`;
    if(seconds<3600)return `${Math.floor(seconds/60)} minutes ago`;
    if(seconds<86400)return `${Math.floor(seconds/3600)} hours ago`;
    return `${Math.floor(seconds/86400)} days ago`;
  }
  global.BuddyReceiptVerifier=Object.freeze({canonicalString,bytes,digest,verifyReceipt,keyContinuity,formatAge});
})(globalThis);
