// Generate ephemeral DEMO ONLY signed receipts; never deploy these keys.
import {generateKeyPairSync, sign, webcrypto} from 'node:crypto';
import {mkdirSync, writeFileSync} from 'node:fs';
import {resolve} from 'node:path';
import {canonical, hashEvent, merkleRoot} from './verifier.mjs';

globalThis.crypto ||= webcrypto;
const path = resolve(process.argv[2] || './ipwa-demo');
mkdirSync(path, {recursive:true});
const owner = {role:'intent_owner', key_id:'demo-intent'};
const executor = {role:'executor', key_id:'demo-executor'};
for (const who of [owner,executor]) {
  const {publicKey, privateKey} = generateKeyPairSync('ed25519');
  who.public_key_hex = publicKey.export({type:'spki',format:'der'}).subarray(-32).toString('hex');
  who.privateKey = privateKey;
}
const intent_hash = 'sha256:'+'a'.repeat(64);
const events = [];
for(const [stage,evidence_hash] of [
  ['INTENT',intent_hash],['ALLOCATED','sha256:'+'b'.repeat(64)],['COMPLETED','sha256:'+'c'.repeat(64)]
]) {
  const event = {sequence:events.length,stage,parent_hash:events.at(-1)?.event_hash||null,evidence_hash};
  event.event_hash = await hashEvent(event);
  events.push(event);
}
const body = {
  protocol:'ITM-POP-OFFLINE-v1', intent_hash, events,
  merkle_root:await merkleRoot(events.map(ev=>ev.event_hash)),
  anchor:{type:'OTS_BITCOIN',status:'PENDING',txid:null}
};
const registry = {
  protocol:'ITM-POP-TRUST-v1',required_roles:['intent_owner','executor'],
  keys:[owner,executor].map(({role,key_id,public_key_hex})=>({role,key_id,public_key_hex}))
};
const bundle = {body,signatures:[owner,executor].map(({role,key_id,privateKey})=>({
  role,key_id,signature_hex:sign(null,Buffer.from(canonical(body)),privateKey).toString('hex')
}))};
writeFileSync(`${path}/registry.json`,JSON.stringify(registry,null,2)+'\n');
writeFileSync(`${path}/bundle.json`,JSON.stringify(bundle,null,2)+'\n');
console.log(`DEMO ONLY: generated ${path}/registry.json and ${path}/bundle.json; no private key persisted. No hardware, TEE, medical service, government eligibility, Bitcoin anchor, or payment proved.`);
