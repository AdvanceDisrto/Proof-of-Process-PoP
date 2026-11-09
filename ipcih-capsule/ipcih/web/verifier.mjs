// iP.CiH browser verifier v0.1: WebCrypto Ed25519, pinned independent key.
// Signature authenticates code bytes; it NEVER proves the claim or sensor accuracy.
export const PROTOCOL='ipcih/capsule/v1';
export const MAX_WIRE=12000;
const encoder=new TextEncoder();
export function canonical(value){
  if(value===null||typeof value==='string'||typeof value==='boolean')return JSON.stringify(value);
  if(typeof value==='number'){
    if(!Number.isSafeInteger(value))throw Error('Nonintegral or unsafe numeric field');
    return JSON.stringify(value);
  }
  if(Array.isArray(value))return '['+value.map(canonical).join(',')+']';
  if(typeof value==='object'&&Object.getPrototypeOf(value)===Object.prototype){
    return '{'+Object.keys(value).sort().map(k=>JSON.stringify(k)+':'+canonical(value[k])).join(',')+'}';
  }
  throw Error('unsupported value');
}
export function bytesFromHex(s){
  if(typeof s!=='string'||!/^(?:[0-9a-fA-F]{2})+$/.test(s))throw Error('invalid hex');
  return Uint8Array.from(s.match(/../g),v=>Number.parseInt(v,16));
}
export function fromB64url(s){
  if(typeof s!=='string'||!/^[A-Za-z0-9_-]+$/.test(s))throw Error('bad base64url');
  const base=s.replace(/-/g,'+').replace(/_/g,'/');
  const raw=atob(base+'='.repeat((4-base.length%4)%4));
  const out=Uint8Array.from(raw,ch=>ch.charCodeAt(0));
  let rec=btoa(String.fromCharCode(...out)).replace(/\+/g,'-').replace(/\//g,'_').replace(/=+$/,'');
  if(rec!==s)throw Error('noncanonical base64url');
  return out;
}
export function hex(data){return Array.from(data,b=>b.toString(16).padStart(2,'0')).join('');}
export async function digest(data){return hex(new Uint8Array(await crypto.subtle.digest('SHA-256',data)));}
export async function verifyPacket(packet,pinnedHex,{now=Math.floor(Date.now()/1000)}={}){
  if(!packet||typeof packet!=='object'||Array.isArray(packet)||Object.keys(packet).sort().join(',')!=='body,signature')throw Error('bad envelope');
  const b=packet.body;
  const fields=['app_b64','app_kind','app_sha256','claim','does_not_prove','evidence_tier','expires_at','issued_at','issuer','nonce','v'];
  if(!b||Object.keys(b).sort().join(',')!==fields.join(',')||b.v!==PROTOCOL||b.app_kind!=='passive-local-canvas-v1')throw Error('unsupported schema');
  if(b.evidence_tier!=='SYNTHETIC_SOFTWARE'||!Array.isArray(b.does_not_prove)||b.does_not_prove.length!==4)throw Error('unsupported evidence');
  if(!Number.isSafeInteger(now)||!Number.isSafeInteger(b.issued_at)||!Number.isSafeInteger(b.expires_at)||b.expires_at-b.issued_at<1||b.expires_at-b.issued_at>3600||now>b.expires_at||now<b.issued_at-5)throw Error('not current');
  if(typeof b.nonce!=='string'||!/^[0-9a-f]{24}$/.test(b.nonce)||typeof b.claim!=='string'||b.claim.length<1||b.claim.length>70||/[\x00-\x1f]/.test(b.claim))throw Error('bad claim/nonce');
  const publicKey=bytesFromHex(pinnedHex);
  if(publicKey.length!==32)throw Error('pin public key independently');
  const text=encoder.encode(canonical(b));
  if(text.length>MAX_WIRE)throw Error('oversized');
  const key=await crypto.subtle.importKey('raw',publicKey,{name:'Ed25519'},false,['verify']);
  const signature=fromB64url(packet.signature);
  if(signature.length!==64||!await crypto.subtle.verify({name:'Ed25519'},key,signature,text))throw Error('signature invalid');
  const app=fromB64url(b.app_b64);
  if(app.length>1536||await digest(app)!==b.app_sha256)throw Error('app hash mismatch');
  const html=new TextDecoder('utf-8',{fatal:true}).decode(app);
  // A signature means authorized issuance, NOT permission to execute arbitrary code.
  // Frame CSP and user activation are still required by the host.
  return {status:'SIGNED_SOFTWARE_CAPSULE',html,claim:b.claim,issuer:b.issuer,
    evidenceTier:b.evidence_tier,publicKeyFingerprint:await digest(publicKey),appHash:b.app_sha256,
    truth:'NOT_EVALUATED'};
}
export async function decodeWire(wire){
  if(typeof wire!=='string'||!wire.startsWith('ipcih1z:')||wire.length>MAX_WIRE*2)throw Error('invalid wire');
  const compressed=fromB64url(wire.slice(8));
  if(compressed.length>MAX_WIRE)throw Error('oversized');
  if(typeof DecompressionStream!=='function')throw Error('browser decompression unsupported');
  const stream=new Blob([compressed]).stream().pipeThrough(new DecompressionStream('deflate'));
  // Bound streaming output to protect against decompression bombs.
  const reader=stream.getReader();let total=0,chunks=[];
  try{for(;;){let {done,value}=await reader.read();if(done)break;total+=value.length;if(total>MAX_WIRE){await reader.cancel();throw Error('decompression bomb')}chunks.push(value)}}finally{reader.releaseLock()}
  const merged=new Uint8Array(total);let n=0;for(const part of chunks){merged.set(part,n);n+=part.length}
  const raw=new TextDecoder('utf-8',{fatal:true}).decode(merged);
  const packet=JSON.parse(raw);
  if(canonical(packet)!==raw)throw Error('noncanonical encoded packet');
  return packet;
}
