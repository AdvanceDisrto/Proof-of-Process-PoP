import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
const script=readFileSync(new URL('../web/edge/public-router.js',import.meta.url),'utf8');
test('all configured public hosts route to approved static origins only',()=>{
  for(const s of ['innovulis.com','www.innovulis.com','proofofprocess.online','www.proofofprocess.online'])assert.ok(script.includes('"'+s+'"'));
  assert.match(script,/ipop-public-verifier\.onrender\.com/);
  assert.match(script,/innovulis-public-web\.onrender\.com/);
});
test('no static write endpoints, credentials forwarded or receipt approvals',()=>{
  assert.match(script,/request.method!=="GET"/);
  assert.match(script,/headers.delete\("set-cookie"\)/);
  assert.match(script,/disbursements_authorized:false/);
  assert.doesNotMatch(script,/localStorage|privateKey|fetch\(request\.url\)/);
});
