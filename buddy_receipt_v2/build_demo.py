#!/usr/bin/env python3
"""Generate demo-only offline viewer with separately pinned ephemeral Ed25519 key.

Never load CIH production signing private key here. No private key persisted.
"""
import json
from pathlib import Path
import qrcode
from buddy_receipt_v2 import make_demo

HERE = Path(__file__).resolve().parent

def build_html(core: str, anchor: str, camera: bool) -> str:
    camera_button = '<button id="cameraBtn" type="button">START CAMERA</button>' if camera else ''
    camera_markup = '<video id="camera" autoplay muted playsinline hidden></video>' if camera else ''
    camera_js = r'''
    async function startCamera() {
      const btn=document.getElementById('cameraBtn');
      if (stream) { stopCamera(); return; }
      if (!window.isSecureContext || !navigator.mediaDevices?.getUserMedia || typeof BarcodeDetector==='undefined') {
        setStatus('CAMERA_UNAVAILABLE: requires a secure origin, permission, and native BarcodeDetector. Use paste mode.', 'warn');
        return;
      }
      try {
        const supported=typeof BarcodeDetector.getSupportedFormats==='function'
          ? await BarcodeDetector.getSupportedFormats():[];
        if (!supported.includes('qr_code')) throw Error('QR_DETECTION_UNSUPPORTED');
        const detector=new BarcodeDetector({formats:['qr_code']});
        stream=await navigator.mediaDevices.getUserMedia({video:{facingMode:{ideal:'environment'}},audio:false});
        video=document.getElementById('camera'); video.srcObject=stream; video.hidden=false;
        btn.textContent='STOP CAMERA';
        await video.play();
        setStatus('CAMERA ACTIVE: scan demo iDAG. Video stays in this browser.', 'warn');
        async function frame() {
          if (!stream)return;
          try {
            const codes=await detector.detect(video);
            if(codes.length){ const raw=codes[0].rawValue;stopCamera();if(raw)await check(raw);return; }
          } catch(err) { setStatus('CAMERA_DECODE_ERROR: '+String(err), 'warn');stopCamera();return; }
          if(stream)timer=setTimeout(()=>{void frame();},150);
        }
        timer=setTimeout(()=>{void frame();},250);
      } catch(err) { stopCamera();setStatus('CAMERA_ERROR: '+String(err), 'warn'); }
    }
    function stopCamera() {
      if(timer)clearTimeout(timer);timer=null;
      if(stream){for(const track of stream.getTracks())track.stop();}
      stream=null;
      const cam=document.getElementById('camera');if(cam){cam.hidden=true;cam.srcObject=null;}
      const btn=document.getElementById('cameraBtn');if(btn)btn.textContent='START CAMERA';
    }
    document.getElementById('cameraBtn').addEventListener('click',()=>{void startCamera();});
    window.addEventListener('pagehide',()=>stopCamera());
    ''' if camera else ''
    kind = 'SCAN + VERIFY' if camera else 'OFFLINE PASTE VERIFIER'
    return '''<!doctype html><html lang="en"><head><meta charset="utf-8" />
<meta name="viewport" content="width=device-width,initial-scale=1" />
<title>iNNOVULIS Buddy™ v2 — '''+kind+'''</title>
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; img-src 'self' data:; media-src 'self' blob:; connect-src 'none'; base-uri 'none'; form-action 'none'; object-src 'none'" />
<style>
*{box-sizing:border-box}body{margin:0;background:radial-gradient(circle at 85% -20%,#155558,#030d17 50%);color:#dafefa;font:14px/1.55 system-ui,Arial,sans-serif;min-height:100vh;padding:16px}
main{max-width:830px;margin:15px auto;border:1px solid #316a71;border-radius:22px;background:#071923;padding:24px;box-shadow:0 20px 80px #0008}
h1{font-size:30px;margin:8px 0;color:#e7ffff;letter-spacing:-.04em}small{color:#72ddd0;font:700 11px ui-monospace,monospace;letter-spacing:.08em}
p{color:#9ac6c8}.controls{display:flex;gap:8px;flex-wrap:wrap;margin:12px 0}
button{border:1px solid #2c9ca0;background:#0a4147;border-radius:10px;padding:10px 15px;color:#e4ffff;font:700 12px system-ui;cursor:pointer}
button:hover{background:#145e60}textarea{min-height:130px;width:100%;padding:12px;background:#031017;border:1px solid #25606b;color:#c6f5ed;border-radius:9px;font:12px/1.5 ui-monospace,monospace;resize:vertical}
#status,#result{padding:13px;border-left:4px solid #e8b25f;background:#071721;margin-top:12px;white-space:pre-wrap;word-break:break-word;font:12px/1.65 ui-monospace,monospace}
#result{max-height:580px;overflow:auto}#result.pass{border-color:#29d8a8}#result.fail{border-color:#fd687e}#result.warn{border-color:#e8b25f}
#camera{max-width:100%;width:450px;border:1px solid #64bfc9;border-radius:9px;display:block;margin:8px 0}#camera[hidden]{display:none}
.notice{border:1px solid #306573;border-radius:9px;padding:12px;margin-top:12px;color:#abd4d0;font-size:12px}code{overflow-wrap:anywhere;color:#a1eae0}
</style></head><body><main>
<small>iNNOVULIS™ CIH ΔiΔ · EPISTEMIC RECEIPT V2 · DEMO ONLY</small>
<h1>Buddy™ '''+kind+'''</h1>
<p>SHA-256 and Ed25519 verified locally against a separate <b>demo-only</b> public key embedded in this viewer. No server call, no code from QR executed, no physical truth determined.</p>
<div class="controls">'''+camera_button+'''<button id="verifyBtn" type="button">VERIFY SIGNED JSON</button><button id="clearBtn" type="button">CLEAR</button></div>
'''+camera_markup+'''
<label for="payload">Paste one complete v2 receipt JSON (or scan)</label>
<textarea id="payload" spellcheck="false" maxlength="65000" placeholder='{"schema":"bitwitness/brain/receipt/v2", ...}'></textarea>
<div id="status" role="status" aria-live="polite">READY · PASTE A RECEIPT TO VERIFY</div>
<div id="result" role="log" aria-live="polite">No receipt has been checked.</div>
<div class="notice"><b>Boundaries:</b> Signatures prove key possession, not the legal owner's identity or whether a claim is true. The displayed prior hash is signed, but full chain linkage cannot be established from one QR. Old signatures may remain valid; age is shown. Local clock may be inaccurate. QR data is not executable.</div>
</main><script>
'''+core+'''
const DEMO_PINNED_PUBLIC_KEY_B64='''+json.dumps(anchor)+''';
const V=globalThis.BuddyReceiptVerifier;
const payload=document.getElementById('payload');
const result=document.getElementById('result');
const status=document.getElementById('status');
let stream=null,timer=null,video=null;
function setStatus(text,level){status.textContent=text;status.style.borderColor=level==='pass'?'#29d8a8':level==='fail'?'#fd687e':'#e8b25f';}
function render(lines,cls){result.textContent=lines.join('\\n');result.className=cls;}
async function check(raw){
  const lines=[];
  let obj;
  try{
    if(typeof raw!=='string'||raw.length>65000)throw Error('RECEIPT_TOO_LARGE');
    obj=JSON.parse(raw);
    const verdict=await V.verifyReceipt(obj,DEMO_PINNED_PUBLIC_KEY_B64);
    if(!verdict.valid)throw Error(verdict.error);
    // TOFU continuity happens only AFTER matching a separately installed trusted anchor.
    const continuity=V.keyContinuity(window.localStorage,obj.brain,obj.signer_pubkey);
    if(continuity.status==='KEY_CHANGED_BLOCK')throw Error('PINNED_SIGNER_CONTINUITY_CHANGED');
    const age=V.formatAge(verdict.age_seconds);
    lines.push('V2 ED25519 SIGNATURE VERIFIED AGAINST DEMO PINNED KEY');
    lines.push('Integrity: '+verdict.integrity);
    lines.push('Signature: '+verdict.signature);
    lines.push('Signer continuity: '+continuity.status);
    lines.push('Signer identity: NOT PROVEN beyond pinned demo key');
    lines.push('Full chain continuity: NOT PROVEN from one receipt');
    lines.push('Brain: '+obj.brain+' ('+obj.kind+')');
    lines.push('Verdict: '+obj.gate_verdict);
    lines.push('Gate checks:');
    for(const check of obj.gate_checks)lines.push('  - '+check);
    lines.push('Issued UTC: '+obj.ts+' ('+age+')');
    if(verdict.age_seconds>3600)lines.push('WARNING: receipt age is over one hour. Freshness suitability must be assessed separately.');
    if(verdict.age_seconds< -60)lines.push('WARNING: timestamp appears to be in the future, check device clock.');
    lines.push('Claims (self-declared): '+obj.claims.join(' | '));
    lines.push('Refusals: '+obj.refusals.join(' | '));
    lines.push('Disclosure: '+obj.disclosure);
    lines.push('Receipt hash: '+obj.receipt_hash);
    lines.push('Signed previous hash: '+obj.prev_hash);
    lines.push('Legacy v1 reference (not independently checked here): '+obj.legacy_receipt_hash);
    lines.push('This DOES NOT prove factual truth, hardware execution, or signer legal identity.');
    render(lines,'pass');setStatus('SIGNATURE VALID · DEMO KEY · FULL CHAIN NOT VERIFIED','pass');
    return true;
  }catch(e){render(['REFUTED / UNVERIFIED: '+(e instanceof Error?e.message:String(e)),
    'No claim, source, signature, or chain was accepted.'],'fail');setStatus('FAIL CLOSED · NO VERIFIED RECEIPT','fail');return false;}
}
document.getElementById('verifyBtn').addEventListener('click',()=>{void check(payload.value);});
document.getElementById('clearBtn').addEventListener('click',()=>{payload.value='';render(['No receipt has been checked.'],'warn');setStatus('READY','warn');});
'''+camera_js+'''
</script></body></html>'''


def main():
    all_data, key, anchor = make_demo()
    for i, receipt in enumerate(all_data['receipts']):
        (HERE / f'receipt-{i+1}-{receipt["brain"]}.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    (HERE/'signed-receipt-chain-v2.json').write_text(json.dumps(all_data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    (HERE/'demo-public-trust-anchor.json').write_text(json.dumps(anchor,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    core=(HERE/'verifier-core.js').read_text(encoding='utf-8')
    for camera in (False,True):
        (HERE/('scanner.html' if camera else 'verifier.html')).write_text(build_html(core,anchor['public_key_b64'],camera),encoding='utf-8')
    raw=json.dumps(all_data['receipts'][0],ensure_ascii=False,separators=(',',':'))
    (HERE/'demo-qr-payload.json').write_text(raw,encoding='utf-8')
    qr=qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_L,box_size=8,border=4)
    qr.add_data(raw.encode('utf-8'),optimize=0);qr.make(fit=True)
    qr.make_image(fill_color='black',back_color='white').save(HERE/'buddy-signed-v2-qr.png')
    print('BUDDY_SIGNED_V2_DEMO_GENERATED')
    print('size_bytes:',len(raw.encode('utf-8')),'QR_version:',qr.version)
    print('trust_fingerprint_sha256:',anchor['public_key_sha256'])

if __name__=='__main__':main()
