import {decodeWire,verifyPacket} from './verifier.mjs';
const get=id=>document.getElementById(id);
let confirmed=null,active=false;
function reset(){confirmed=null;get('boot').disabled=true;get('hash').textContent='—';get('fingerprint').textContent='—';get('truth').textContent='NOT EVALUATED';stop();}
function stop(){const frame=get('capsule');frame.removeAttribute('srcdoc');frame.src='about:blank';get('runtime').hidden=true;get('stop').disabled=true;active=false;}
get('verify').addEventListener('click',async()=>{
  reset();get('status').textContent='CHECKING PINNED TRUST ANCHOR AND SIGNATURE';get('status').className='';
  try{const packet=await decodeWire(get('wire').value.trim());confirmed=await verifyPacket(packet,get('pin').value.trim());get('status').textContent='SIGNED SOFTWARE CAPSULE VERIFIED · CLAIM TRUTH NOT EVALUATED';get('status').className='good';get('hash').textContent=confirmed.appHash;get('fingerprint').textContent=confirmed.publicKeyFingerprint;get('boot').disabled=false}
  catch(e){confirmed=null;get('status').textContent='REJECTED: '+e.message;get('status').className='bad'}
});
get('boot').addEventListener('click',()=>{
  if(!confirmed||active)return;
  // No ambient permissions, no same-origin, and no network. Signed code is still untrusted.
  const csp="default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; img-src data:; connect-src 'none'; font-src 'none'; base-uri 'none'; form-action 'none'";
  const clean=confirmed.html.replace(/^<!doctype html>/i,'');
  get('capsule').srcdoc=`<!doctype html><meta http-equiv="Content-Security-Policy" content="${csp}">${clean}`;
  get('runtime').hidden=false;get('stop').disabled=false;active=true;
});
get('stop').addEventListener('click',stop);
for(let id of ['pin','wire'])get(id).addEventListener('input',reset);
const canvas=get('rain'),ctx=canvas.getContext('2d');let frame=0;
function draw(){ctx.fillStyle='rgba(2,13,15,.17)';ctx.fillRect(0,0,400,180);ctx.fillStyle='#25b890';ctx.font='12px monospace';for(let x=0;x<25;x++){let y=(frame*3+x*17)%210;ctx.fillText(String.fromCharCode(48+((x+frame)%10)),x*16,y)}frame++;requestAnimationFrame(draw)}
if(!matchMedia('(prefers-reduced-motion: reduce)').matches)draw();
