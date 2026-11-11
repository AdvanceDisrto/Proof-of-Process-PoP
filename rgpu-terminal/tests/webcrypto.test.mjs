import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import { webcrypto } from 'node:crypto';
import { verifyEnvelope, fingerprintOf, ZERO, decodeCarrier } from '../rgpu_terminal/static/verify.mjs';
if (!globalThis.crypto) globalThis.crypto=webcrypto;
const fixture=JSON.parse(fs.readFileSync(process.env.INNOVULIS_FIXTURE,'utf8'));
const {genesis,refuted,public_key:pub,fingerprint:fp}=fixture;
function clone(o){return JSON.parse(JSON.stringify(o));}
function b64url(obj){return Buffer.from(JSON.stringify(obj)).toString('base64url');}
test('Browser WebCrypto has a correct out-of-band anchor fingerprint',async()=>{
    assert.equal(await fingerprintOf(pub),fp);
});
test('Browser validates real Python Ed25519 genesis signature and chain',async()=>{
    const v=await verifyEnvelope(genesis,pub,{expectedSequence:1,expectedPrevious:ZERO});
    assert.equal(v.signature_valid,true);assert.equal(v.payload.declared_verdict,'PROCESS_OBSERVED');
    assert.equal(v.physical_truth_verified,false);
});
test('Browser validates real Python Ed25519 second record',async()=>{
    const v=await verifyEnvelope(refuted,pub,{expectedSequence:2,expectedPrevious:genesis.payload_sha256});
    assert.equal(v.payload.source_tier,'SYNTHETIC_DEMO');assert.equal(v.payload.declared_verdict,'REFUTED_FALSE');
});
test('Browser rejects signature tampering',async()=>{
    let bad=clone(genesis);bad.signature_hex='00'.repeat(64);
    await assert.rejects(()=>verifyEnvelope(bad,pub));
});
test('Browser rejects body mutation even if sha256 field unchanged',async()=>{
    let bad=clone(genesis);const payload=JSON.parse(Buffer.from(bad.payload_b64u,'base64url').toString());
    payload.telemetry.physical_joules=999;
    bad.payload_b64u=b64url(payload);
    await assert.rejects(()=>verifyEnvelope(bad,pub));
});
test('Browser rejects substituted public key (no TOFU)',async()=>{
    let other='11'.repeat(32);await assert.rejects(()=>verifyEnvelope(genesis,other));
});
test('Browser rejects client metadata claiming alternative public key',async()=>{
    let bad=clone(genesis);bad.public_key=pub;
    await assert.rejects(()=>verifyEnvelope(bad,pub));
});
test('Browser rejects missing pin',async()=>{
    await assert.rejects(()=>verifyEnvelope(genesis,''));
});
test('Browser rejects sequence rollback',async()=>{
    await assert.rejects(()=>verifyEnvelope(genesis,pub,{expectedSequence:2,expectedPrevious:ZERO}));
});
test('Browser rejects broken previous hash',async()=>{
    await assert.rejects(()=>verifyEnvelope(refuted,pub,{expectedSequence:2,expectedPrevious:ZERO}));
});
test('Browser rejects truncated signature',async()=>{
    let bad=clone(genesis);bad.signature_hex=bad.signature_hex.slice(2);
    await assert.rejects(()=>verifyEnvelope(bad,pub));
});
test('Browser rejects non-rgpu1 carrier',async()=>{
    await assert.rejects(()=>decodeCarrier('ipqr1:not-compatible'));
});
test('Browser decodes complete signed rgpu1 carrier bytes',async()=>{
    const carrier='rgpu1:'+Buffer.from(JSON.stringify(genesis)).toString('base64url');
    const actual=await decodeCarrier(carrier);
    const v=await verifyEnvelope(actual,pub,{expectedSequence:1,expectedPrevious:ZERO});
    assert.equal(v.valid,true);
});
test('Browser rejects malformed carrier data',async()=>{
    await assert.rejects(()=>decodeCarrier('rgpu1:%%%'));
});

test('Browser decompresses complete signed rgpu1z QR carrier',async()=>{
  const carrier=fixture.carrier_compressed;
  const actual=await decodeCarrier(carrier);
  const v=await verifyEnvelope(actual,pub,{expectedSequence:1,expectedPrevious:ZERO});
  assert.equal(v.valid,true);
});
