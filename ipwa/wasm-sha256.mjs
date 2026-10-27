/* Actual WebAssembly SHA-256 engine; browser WebCrypto checks Ed25519. */
let engine=null;
export function installWasmInstance(instance){
 const ex=instance?.exports;
 if(!ex?.memory||typeof ex.sha256_digest!=='function'||!ex.__heap_base)throw Error('WASM ABI incomplete');
 const heap=Number(ex.__heap_base.value);
 if(!Number.isSafeInteger(heap)||heap<1024)throw Error('bad WASM heap');
 engine={e:ex,heap};
}
export async function initializeWasm(){
 const result=await fetch(new URL('./verifier_bg.wasm',import.meta.url),{cache:'no-store'});
 if(!result.ok)throw Error('WASM cache missing: '+result.status);
 installWasmInstance((await WebAssembly.instantiate(await result.arrayBuffer())).instance);
 return true;
}
export function digestWasm(bytes){
 if(!engine||!(bytes instanceof Uint8Array)||bytes.length>8000000)throw Error('WASM digest not ready or size exceeded');
 const {e,heap}=engine;const out=heap+bytes.length+16;
 if(e.memory.buffer.byteLength<out+32)e.memory.grow(Math.ceil((out+32-e.memory.buffer.byteLength)/65536));
 const view=new Uint8Array(e.memory.buffer);
 view.set(bytes,heap);e.sha256_digest(heap,bytes.length,out);
 const digest=Uint8Array.from(view.subarray(out,out+32));
 view.fill(0,heap,out+32);return digest;
}
export function isWasmReady(){return !!engine;}
