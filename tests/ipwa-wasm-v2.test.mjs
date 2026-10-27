import {test} from 'node:test';
import assert from 'node:assert/strict';
import {webcrypto,createHash} from 'node:crypto';
import {readFileSync} from 'node:fs';
import {installWasmInstance,digestWasm} from '../ipwa/wasm-sha256.mjs';
import {parseTar} from '../ipwa/archive.mjs';
globalThis.crypto ||= webcrypto;
const wasm=readFileSync(new URL('../ipwa/verifier_bg.wasm',import.meta.url));
installWasmInstance((await WebAssembly.instantiate(wasm)).instance);
const h=x=>createHash('sha256').update(x).digest('hex');
for(const size of [0,3,55,56,63,64,128,8192,1024*1024]){
 test('WASM SHA256 matches OpenSSL at '+size+' bytes',()=>{
  const input=Buffer.alloc(size,0x5c);
  assert.equal(Buffer.from(digestWasm(new Uint8Array(input))).toString('hex'),h(input));
 });
}
test('WASM cannot be invoked with oversized data',()=>{
 assert.throws(()=>digestWasm(new Uint8Array(8_000_001)),/size exceeded/);
});
test('tar parser rejects non-tar and empty inputs',()=>{
 assert.throws(()=>parseTar(new Uint8Array(0)),/terminator/);
 assert.throws(()=>parseTar(new Uint8Array(128)),/terminator/);
});
