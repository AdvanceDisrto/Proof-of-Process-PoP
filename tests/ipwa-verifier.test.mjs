import {test} from 'node:test';
import assert from 'node:assert/strict';
import {webcrypto, generateKeyPairSync, sign} from 'node:crypto';
import {readFileSync} from 'node:fs';
import {canonical, hashEvent, merkleRoot, verifyEvidence} from '../ipwa/verifier.mjs';

globalThis.crypto ||= webcrypto;
const keyFor = role => {
  const {publicKey, privateKey} = generateKeyPairSync('ed25519');
  return {role, key_id: `${role}-key`, public_key_hex: publicKey.export({type:'spki',format:'der'}).subarray(-32).toString('hex'), privateKey};
};
const owner = keyFor('intent_owner');
const executor = keyFor('executor');
const trust = {
  protocol: 'ITM-POP-TRUST-v1', required_roles: ['intent_owner', 'executor'],
  keys: [owner, executor].map(({role,key_id,public_key_hex})=>({role,key_id,public_key_hex}))
};
async function fixture() {
  const intentHash = 'sha256:' + 'a'.repeat(64);
  const events = [];
  for (const [stage,evidence_hash] of [['INTENT',intentHash],['ALLOCATED','sha256:'+'b'.repeat(64)],['COMPLETED','sha256:'+'c'.repeat(64)]]) {
    const ev = {sequence:events.length,stage,parent_hash:events.at(-1)?.event_hash || null,evidence_hash};
    ev.event_hash = await hashEvent(ev);
    events.push(ev);
  }
  const body = {
    protocol:'ITM-POP-OFFLINE-v1',intent_hash:intentHash,events,
    merkle_root:await merkleRoot(events.map(ev=>ev.event_hash)),
    anchor:{type:'OTS_BITCOIN',status:'PENDING',txid:null}
  };
  return {body, signatures: [owner,executor].map(({role,key_id,privateKey})=>({
    role,key_id,signature_hex:sign(null,Buffer.from(canonical(body)),privateKey).toString('hex')
  }))};
}
const valid = r => assert.equal(r.status,'LOCAL_CRYPTOGRAPHY_PASSED_ANCHOR_UNVERIFIED',JSON.stringify(r));
const rejected = r => {assert.equal(r.status,'REJECTED',JSON.stringify(r));assert.equal(r.authorized_for_disbursement,false);};

test('valid chain, merkle, independent keys: local integrity passes but actuation stays shut',async()=>{
  const result = await verifyEvidence(await fixture(),trust);
  valid(result);
  assert.equal(result.checked_events,3);
  assert.equal(result.checked_signatures,2);
  assert.equal(result.bitcoin_anchor_verified,false);
  assert.equal(result.authorized_for_actuation,false);
});
test('tampered evidence hash rejected',async()=>{const b=await fixture();b.body.events[1].evidence_hash='sha256:'+'f'.repeat(64);rejected(await verifyEvidence(b,trust));});
test('broken parent link rejected',async()=>{const b=await fixture();b.body.events[2].parent_hash=null;rejected(await verifyEvidence(b,trust));});
test('mismatched Merkle root rejected',async()=>{const b=await fixture();b.body.merkle_root='sha256:'+'e'.repeat(64);rejected(await verifyEvidence(b,trust));});
test('signature bitflip rejected',async()=>{const b=await fixture();b.signatures[0].signature_hex='00'+b.signatures[0].signature_hex.slice(2);rejected(await verifyEvidence(b,trust));});
test('missing independent signature rejected',async()=>{const b=await fixture();b.signatures.pop();rejected(await verifyEvidence(b,trust));});
test('untrusted signer rejected',async()=>{const b=await fixture();const swapped=structuredClone(trust);swapped.keys[0].public_key_hex='c'.repeat(64);rejected(await verifyEvidence(b,swapped));});
test('one signing key may not stand in for both required roles',async()=>{const b=await fixture();const reused=structuredClone(trust);reused.keys[1].public_key_hex=reused.keys[0].public_key_hex;rejected(await verifyEvidence(b,reused));});
test('claiming Bitcoin verified does not make it verified',async()=>{
  const b=await fixture();b.body.anchor.status='VERIFIED';
  b.signatures=[owner,executor].map(({role,key_id,privateKey})=>({role,key_id,signature_hex:sign(null,Buffer.from(canonical(b.body)),privateKey).toString('hex')}));
  const result=await verifyEvidence(b,trust);valid(result);assert.equal(result.bitcoin_anchor_verified,false);
});
test('floating-point signature input rejected',async()=>{
  const b=await fixture();b.body.amount_usd=45.25;
  rejected(await verifyEvidence(b,trust));
});
test('PWA static files, no upload or network fallback',()=>{
  const sw=readFileSync(new URL('../ipwa/sw.js',import.meta.url),'utf8');
  const html=readFileSync(new URL('../ipwa/index.html',import.meta.url),'utf8');
  assert.match(sw,/caches\.match/);assert.doesNotMatch(sw,/\bfetch\(/);
  assert.doesNotMatch(html,/fetch\(/);
  assert.match(html,/serviceWorker\.register/);
});
