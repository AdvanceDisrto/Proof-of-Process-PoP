import {ZERO, verifyEnvelope, decodeCarrier, fingerprintOf} from './verify.mjs';

const byId=id=>document.getElementById(id);
const state={pinned:null,lastSequence:0,lastHash:ZERO,syncing:false,again:false,ws:null,rendered:0};
const storageKey='innovulis_rgpu_pinned_pub_v1';
const pinMsg=byId('pinHelp');
const status=byId('trustStatus');
function trustLabel(message,tone){status.textContent=message;status.className='pill '+tone;}
function chainLabel(message,tone){const e=byId('chainState');e.textContent=message;e.className='tag '+tone;}
function appendLine(payload,hash,verified,label){
  const node=document.createElement('article');
  const refuted=payload?.declared_verdict==='REFUTED_FALSE';
  node.className='entry '+(!verified?'bad':refuted?'bad':payload?.source_tier==='SYNTHETIC_DEMO'?'warn':'');
  const top=document.createElement('div');top.className='top';
  const seq=document.createElement('span');seq.textContent='BLOCK #'+(payload?.sequence ?? 'INVALID');
  const t=document.createElement('span');t.textContent=(payload?.source_tier ?? 'INVALID');
  top.append(seq,t);node.append(top);
  const title=document.createElement('div');title.className='title';
  title.textContent=(payload?.claim ?? 'REJECTED')+' / '+(payload?.declared_verdict ?? 'INVALID');
  node.append(title);
  const h=document.createElement('div');h.className='meta';h.textContent='SHA-256 '+hash;node.append(h);
  const badge=document.createElement('div');badge.className='status';badge.textContent=label;node.append(badge);
  const feed=byId('feed');feed.prepend(node);while(feed.children.length>50)feed.lastChild.remove();
}
function paint(p,h,seq){
  byId('sequence').textContent='#'+seq;
  byId('sourceTier').textContent=p.source_tier;
  byId('verdict').textContent=p.declared_verdict+' (DECLARED)';
  const en=p.telemetry||{};
  byId('joules').textContent=en.physical_joules===null && en.simulated_joules===undefined?'NOT MEASURED':
    en.simulated_joules!==undefined?`${en.simulated_joules} J DEMO ONLY`:'NOT MEASURED';
  byId('verdict').style.color=p.declared_verdict==='REFUTED_FALSE'?'var(--red)': 'var(--aqua)';
  const qr=byId('qrcode');qr.replaceChildren();
  const img=document.createElement('img');img.alt='Complete signed rgpu1 receipt optical carrier; independent scanning still required';
  img.src='/api/receipt/'+seq+'/qr.svg';
  qr.append(img);
}
async function syncHistory(){
  if(!state.pinned){trustLabel('ANCHOR UNPINNED','caution');return;}
  if(state.syncing){state.again=true;return;}
  state.syncing=true;
  try{
    do{
      state.again=false;
      let batches=0;
      while(batches++<100){
        const r=await fetch('/api/history?after='+state.lastSequence+'&limit=100',{cache:'no-store'});
        if(!r.ok)throw new Error('History retrieval failed');
        const data=await r.json();const entries=data.envelopes;
        if(!Array.isArray(entries))throw new Error('Invalid history response');
        for(const envelope of entries){
          const receipt=await verifyEnvelope(envelope,state.pinned,
            {expectedSequence:state.lastSequence+1,expectedPrevious:state.lastHash});
          state.lastHash=receipt.hash;state.lastSequence=receipt.payload.sequence;
          appendLine(receipt.payload,receipt.hash,true,
            '✓ ED25519 VALID • CHAIN LINKED • '+receipt.digital_scope);
          paint(receipt.payload,receipt.hash,receipt.payload.sequence);
        }
        if(entries.length<100)break;
      }
      if(batches>100)throw new Error('History exceeds bounded browser verification limit; perform offline archival verification');
      trustLabel('PINNED KEY • ED25519 VERIFIED','good');
      chainLabel('CHAIN VALID TO #'+state.lastSequence,'good');
    }while(state.again);
  }catch(e){
    chainLabel('CHAIN UNVERIFIABLE','bad');
    trustLabel('VERIFICATION FAILED','bad');
    appendLine(null,'NOT VERIFIED',false,String(e.message).slice(0,150));
    // Do not advance cursor or display new green receipts after error.
  }finally{state.syncing=false;}
}
async function pinKey(){
  const pub=byId('pinPublic').value.trim().toLowerCase();
  const expected=byId('pinFingerprint').value.trim().toLowerCase();
  try{
    if(!/^[0-9a-f]{64}$/.test(pub)||!/^[0-9a-f]{64}$/.test(expected))throw new Error('Enter both 64-character hex values');
    if(await fingerprintOf(pub)!==expected)throw new Error('Public key/fingerprint mismatch');
    localStorage.setItem(storageKey,pub);
    state.pinned=pub;state.lastSequence=0;state.lastHash=ZERO;
    byId('feed').replaceChildren();byId('qrcode').textContent='VERIFYING HISTORY';
    pinMsg.textContent='Local browser pin set. Keep independent key record; it must NOT come only from this server.';
    await syncHistory();
  }catch(e){pinMsg.textContent='PIN REJECTED: '+e.message;trustLabel('ANCHOR UNTRUSTED','bad');}
}
byId('pinKey').addEventListener('click',pinKey);
byId('forgetKey').addEventListener('click',()=>{
  localStorage.removeItem(storageKey);state.pinned=null;state.lastSequence=0;state.lastHash=ZERO;
  trustLabel('ANCHOR UNPINNED','caution');chainLabel('CHAIN NOT CHECKED','caution');
  byId('feed').replaceChildren();byId('qrcode').textContent='PIN REQUIRED FOR SIGNATURE VERIFICATION';
});
async function verifyCarrierText(value){
  if(!state.pinned){pinMsg.textContent='First pin the Ed25519 key using an independent source.';return;}
  try{
    const receipt=await verifyEnvelope(await decodeCarrier(value.trim()),state.pinned);
    appendLine(receipt.payload,receipt.hash,true,'✓ SIGNATURE VALID • CHAIN/FRESHNESS NOT CHECKED FOR STANDALONE CARRIER');
  }catch(e){appendLine(null,'NOT VERIFIED',false,'✗ CARRIER REJECTED: '+e.message);}
}
byId('verifyCarrier').addEventListener('click',()=>verifyCarrierText(byId('carrierInput').value));
byId('camera').addEventListener('click',async()=>{
  if(!('BarcodeDetector' in globalThis)||!navigator.mediaDevices?.getUserMedia){
    byId('qrHelp').textContent='Camera decoding not supported here. Use a compatible offline scanner to copy rgpu1 text.';return;
  }
  const video=document.createElement('video');video.autoplay=true;video.playsInline=true;video.width=280;
  byId('qrcode').replaceChildren(video);
  let stream;
  try{
    stream=await navigator.mediaDevices.getUserMedia({video:{facingMode:'environment'}});
    video.srcObject=stream;await video.play();
    const detector=new BarcodeDetector({formats:['qr_code']});
    for(let count=0;count<15;count++){
      const result=await detector.detect(video);
      if(result.length){await verifyCarrierText(result[0].rawValue);break;}
      await new Promise(resolve=>setTimeout(resolve,500));
    }
  }catch(e){byId('qrHelp').textContent='Camera unavailable: '+e.message;}
  finally{stream?.getTracks().forEach(track=>track.stop());byId('qrcode').textContent='SCANNER SESSION ENDED';}
});
async function demo(outcome){
  const token=byId('operatorToken').value;
  if(token.length<32){pinMsg.textContent='Enter local operator secret to run synthetic test.';return;}
  const result=await fetch('/api/demo/tick',{method:'POST',headers:{'Content-Type':'application/json',
    'x-innovulis-operator-token':token},body:JSON.stringify({outcome})});
  if(!result.ok){pinMsg.textContent='Demo rejected (disabled or invalid token): HTTP '+result.status;return;}
  await syncHistory();
}
byId('demoPass').addEventListener('click',()=>demo('PASS'));
byId('demoRefuted').addEventListener('click',()=>demo('REFUTED'));
function connect(delay=1000){
  const protocol=location.protocol==='https:'?'wss:':'ws:';
  const ws=new WebSocket(protocol+'//'+location.host+'/ws');state.ws=ws;
  ws.onopen=()=>{byId('connection').textContent='CONNECTED / UNTRUSTED TRANSPORT';byId('connection').className='pill caution';syncHistory();};
  ws.onmessage=e=>{
    try{const event=JSON.parse(e.data);
      if(event.type==='receipt'||event.type==='resync_required'||event.type==='hello')syncHistory();
    }catch{};
  };
  ws.onclose=()=>{
    byId('connection').textContent='OFFLINE';byId('connection').className='pill bad';
    setTimeout(()=>connect(Math.min(delay*2,30000)),delay);
  };
}
try{const cached=localStorage.getItem(storageKey);if(cached&&/^[0-9a-f]{64}$/.test(cached)){
  state.pinned=cached;byId('pinPublic').value=cached;
  fingerprintOf(cached).then(f=>byId('pinFingerprint').value=f).then(syncHistory);
}}catch(e){console.warn('Local pin storage unavailable',e);}
connect();
