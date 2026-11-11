// iNNOVULIS independent browser verifier. No CDN, no runtime keys from envelope.
// WebCrypto Ed25519 verifies the EXACT bytes signed by the Python issuer.
const domain = new TextEncoder().encode('iNNOVULIS/RGPU-TELEMETRY/v1\0');
const ZERO = '0'.repeat(64);
export { ZERO };

export function hexBytes(hex, n=null) {
  if (typeof hex !== 'string' || !/^(?:[0-9a-f]{2})+$/.test(hex) || (n !== null && hex.length !== n*2)) {
    throw new Error('Invalid lowercase hexadecimal field');
  }
  return Uint8Array.from(hex.match(/../g), x => parseInt(x, 16));
}
function b64urlBytes(value) {
  if (typeof value !== 'string' || value.length > 32768 || !/^[A-Za-z0-9_-]+$/.test(value)) {
    throw new Error('Bad base64url content');
  }
  const base64=value.replace(/-/g, '+').replace(/_/g, '/');
  // Browser uses atob; Node 22+ provides it in our test harness too.
  const raw=atob(base64+'='.repeat((4-base64.length%4)%4));
  const encoded=btoa(raw).replace(/\+/g,'-').replace(/\//g,'_').replace(/=+$/,'');
  if (encoded!==value) throw new Error('Noncanonical base64url');
  return Uint8Array.from(raw, c => c.charCodeAt(0));
}
function toHex(bytes) {
  return Array.from(new Uint8Array(bytes), n=>n.toString(16).padStart(2,'0')).join('');
}
export async function sha256hex(bytes) {
  if (!globalThis.crypto?.subtle) throw new Error('Secure WebCrypto context required');
  return toHex(await crypto.subtle.digest('SHA-256', bytes));
}
export async function fingerprintOf(publicKeyHex) {
  return sha256hex(hexBytes(publicKeyHex,32));
}
export async function verifyEnvelope(envelope, pinnedPublicHex, options={}) {
  // The anchor comes ONLY from explicit operator pinning, never envelope.public_key.
  const expectedKeys=['schema','payload_b64u','payload_sha256','signature_hex','issuer_key_fingerprint'];
  if (!envelope || typeof envelope !== 'object' || Array.isArray(envelope) ||
      Object.keys(envelope).sort().join('|')!==expectedKeys.sort().join('|') ||
      envelope.schema !== 'innovulis/rgpu-envelope/v1') throw new Error('Malformed envelope');
  const key=hexBytes(pinnedPublicHex,32);
  const expectedFingerprint=await sha256hex(key);
  if (envelope.issuer_key_fingerprint !== expectedFingerprint) throw new Error('Pinned key mismatch');
  const payloadBytes=b64urlBytes(envelope.payload_b64u);
  if (payloadBytes.length>16384) throw new Error('Payload exceeds limit');
  const computedHash=await sha256hex(payloadBytes);
  if (computedHash !== envelope.payload_sha256) throw new Error('Receipt SHA-256 mismatch');
  const signature=hexBytes(envelope.signature_hex,64);
  const keyObject=await crypto.subtle.importKey('raw',key,{name:'Ed25519'},false,['verify']);
  const signed=new Uint8Array(domain.length+payloadBytes.length);
  signed.set(domain);signed.set(payloadBytes,domain.length);
  const isValid=await crypto.subtle.verify({name:'Ed25519'},keyObject,signature,signed);
  if (!isValid) throw new Error('Cryptographic signature invalid');
  const payload=JSON.parse(new TextDecoder('utf-8',{fatal:true}).decode(payloadBytes));
  if (!payload || typeof payload !== 'object' || Array.isArray(payload) ||
      payload.schema!=='innovulis/rgpu-receipt/v1' ||
      !Number.isSafeInteger(payload.sequence) || payload.sequence<1 ||
      typeof payload.previous_sha256 !== 'string' ||
      !/^[0-9a-f]{64}$/.test(payload.previous_sha256) ||
      typeof payload.claim !== 'string' ||
      !['LOCAL_SOFTWARE_ONLY','SYNTHETIC_DEMO'].includes(payload.source_tier) ||
      !['PROCESS_OBSERVED','PROVEN_TRUE','REFUTED_FALSE','UNRESOLVED'].includes(payload.declared_verdict) ||
      !Number.isFinite(payload.timestamp_ns) || payload.timestamp_ns<1e18) {
    // JS numbers cannot exactly represent epoch nanoseconds: never claim
    // authoritative freshness using this number in a browser.
    throw new Error('Signed data shape invalid');
  }
  if (options.expectedSequence!==undefined && payload.sequence!==options.expectedSequence) throw new Error('Sequence gap/replay');
  if (options.expectedPrevious!==undefined && payload.previous_sha256!==options.expectedPrevious) throw new Error('Hash chain mismatch');
  if (payload.source_tier==='SYNTHETIC_DEMO' && payload.claim!=='SYNTHETIC_TELEMETRY') throw new Error('Tier/claim mismatch');
  if (payload.source_tier==='LOCAL_SOFTWARE_ONLY' && (payload.claim!=='HUB_INITIALIZED' || payload.declared_verdict!=='PROCESS_OBSERVED')) throw new Error('Tier/claim mismatch');
  if (payload.source_tier==='SYNTHETIC_DEMO' && payload.telemetry?.physical_joules!==null) throw new Error('Synthetic receipt cannot claim physical joules');
  return {valid:true,signature_valid:true,chain_checked:options.expectedSequence!==undefined && options.expectedPrevious!==undefined,
    payload, hash:computedHash, digital_scope:'SIGNED_SOFTWARE_RECORD_ONLY', physical_truth_verified:false};
}
export async function decodeCarrier(carrier) {
  if (typeof carrier !== 'string') throw new Error('Invalid QR carrier');
  if (carrier.startsWith('rgpu1:')) {
    const bytes=b64urlBytes(carrier.slice(6));
    if (bytes.length>16384)throw new Error('Carrier too large');
    return JSON.parse(new TextDecoder('utf-8',{fatal:true}).decode(bytes));
  }
  if (!carrier.startsWith('rgpu1z:')) throw new Error('Unsupported carrier: not ipqr1');
  // Compression is only transport; Ed25519 covers the original exact payload.
  if (typeof DecompressionStream==='undefined')throw new Error('Browser lacks deflate support');
  const packed=b64urlBytes(carrier.slice(7));
  if (packed.length>12288)throw new Error('Compressed carrier too large');
  const reader=new Blob([packed]).stream().pipeThrough(new DecompressionStream('deflate')).getReader();
  const chunks=[];let total=0;
  try {
    while (true){
      const {done,value}=await reader.read();if(done)break;
      total+=value.length;
      if(total>16384)throw new Error('Carrier decompression limit exceeded');
      chunks.push(value);
    }
  } finally { reader.releaseLock(); }
  const raw=new Uint8Array(total);let pos=0;
  for (const chunk of chunks){raw.set(chunk,pos);pos+=chunk.length;}
  return JSON.parse(new TextDecoder('utf-8',{fatal:true}).decode(raw));
}
