import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {join} from 'node:path';
const here=process.cwd();
const html=readFileSync(join(here,'web/innovulis/index.html'),'utf8');
const ipwa=readFileSync(join(here,'ipwa/index.html'),'utf8');
const sw=readFileSync(join(here,'ipwa/sw.js'),'utf8');
test('home launches local proof instead of claiming absolute real-world truth',()=>{
 assert.match(html,/The End of Trust/);assert.match(html,/Beginning of Proof/);
 assert.match(html,/JUST ASK BUDDY/);assert.match(html,/signature verifies integrity/i);
 assert.match(html,/proofofprocess\.online/);
 assert.doesNotMatch(html,/\$5 Trillion|\$825B|mathematically impossible|fraud eliminated/i);
});
test('proof browser UI is fail closed and local',()=>{
 assert.match(ipwa,/verifyEvidence\(bundle, registry\)/);assert.match(ipwa,/authorized_for_disbursement: false|Disbursement: BLOCKED/);
 assert.match(ipwa,/serviceWorker.register/);assert.match(sw,/Offline asset not cached/);
 assert.match(sw,/caches\.match/);assert.doesNotMatch(sw,/fetch\(event\.request\)/);
});
test('signed math and PNG icons are present',()=>{
 for(const name of ['verifier_bg.wasm','verifier.mjs','wasm-sha256.mjs','archive.mjs','icon-192.png','icon-512.png'])assert.ok(readFileSync(join(here,'ipwa',name)).length>100);
});
