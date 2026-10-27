// Positive and negative checks for exported public signals and a valid dev proof.
import assert from 'node:assert/strict';
import {readFileSync,writeFileSync} from 'node:fs';
import {createRequire} from 'node:module';
const require=createRequire(import.meta.url);
const snarkjs=require('snarkjs');
const vk=JSON.parse(readFileSync('build/DEV_ONLY_verification_key.json'));
const proof=JSON.parse(readFileSync('build/DEV_ONLY_proof.json'));
const signals=JSON.parse(readFileSync('build/DEV_ONLY_public.json'));
assert.equal(signals[0],'1','expected public heuristic flag true');
assert.equal(await snarkjs.groth16.verify(vk,signals,proof),true,'proof must verify');
const forged=[...signals];forged[0]='0';
assert.equal(await snarkjs.groth16.verify(vk,forged,proof),false,'tampered public output must fail');
writeFileSync('build/DEV_ONLY_verification_result.json',JSON.stringify({
 status:'DEVELOPMENT_PROOF_VERIFIED',tamper_test:'REJECTED',
 trusted_setup:'NO_SINGLE_CI_RUNNER',court_or_legal_truth:'NOT_PROVEN',
 external_signature_binding:'NOT_PROVEN',settlement_authorized:false},null,2));
console.log('POSITIVE_AND_NEGATIVE_GROTH16_PROOF_TESTS_PASS');

