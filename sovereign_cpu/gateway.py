from __future__ import annotations
import os, subprocess, threading, time
from pathlib import Path
from flask import Flask, jsonify, request
from .receipt import build_receipt
app = Flask(__name__)
ROOT = Path(os.getenv("SOVEREIGN_ROOT", ".")).resolve()
MODEL = Path(os.getenv("SOVEREIGN_MODEL", ROOT / "open_intelligence.gguf")).resolve()
ENGINE = Path(os.getenv("SOVEREIGN_ENGINE", ROOT / "llama-cli")).resolve()
THREADS = int(os.getenv("SOVEREIGN_THREADS", "8")); MAX_TOKENS = int(os.getenv("SOVEREIGN_MAX_TOKENS", "128"))

def _memory():
    total = used = 0
    try:
        values = {}
        for line in Path("/proc/meminfo").read_text().splitlines():
            k, v = line.split()[:2]; values[k] = int(v) * 1024
        total = values.get("MemTotal", 0)
        available = values.get("MemAvailable", 0)
        used = max(0, total - available)
    except (OSError, ValueError): pass
    return total, used

def _cpu_percent(prev=None):
    try:
        fields = Path("/proc/stat").read_text().splitlines()[0].split()[1:]
        nums = list(map(int, fields)); idle = nums[3] + (nums[4] if len(nums) > 4 else 0); total = sum(nums)
        if prev is None: return (total, idle), None
        dt = total - prev[0]; di = idle - prev[1]
        return (total, idle), (100.0 * (dt - di) / dt if dt else 0.0)
    except (OSError, ValueError, IndexError): return prev, None

def _sample_loop(stop, samples):
    prev, _ = _cpu_percent();
    while not stop.wait(0.25):
        prev, load = _cpu_percent(prev); total, used = _memory()
        if load is not None: samples["cpu_peak_percent"] = max(samples["cpu_peak_percent"], load)
        samples["ram_peak_bytes"] = max(samples["ram_peak_bytes"], used); samples["ram_total_bytes"] = total

def run_local(prompt: str):
    if not MODEL.is_file(): raise FileNotFoundError(f"model not found: {MODEL}")
    if not ENGINE.is_file(): raise FileNotFoundError(f"engine not found: {ENGINE}")
    command = [str(ENGINE), "-m", str(MODEL), "-p", f"User: {prompt}\\nAssistant:", "-t", str(THREADS), "-n", str(MAX_TOKENS), "--no-warmup"]
    samples = {"cpu_peak_percent": 0.0, "ram_peak_bytes": 0, "ram_total_bytes": _memory()[0]}
    stop = threading.Event(); sampler = threading.Thread(target=_sample_loop, args=(stop, samples), daemon=True); sampler.start()
    try:
        proc = subprocess.run(command, cwd=str(ROOT), capture_output=True, text=True, timeout=600, check=False)
    finally:
        stop.set(); sampler.join(timeout=1)
    if proc.returncode != 0: raise RuntimeError(f"llama-cli failed ({proc.returncode}): {proc.stderr[-2000:]}")
    output = proc.stdout.split("Assistant:", 1)[-1].strip()
    if not output: raise RuntimeError("local engine produced empty output")
    return output, " ".join(command), samples

@app.get("/")
def home():
    return "<!doctype html><html><head><meta name=\"viewport\" content=\"width=device-width,initial-scale=1\"><title>iTensor | Sovereign CPU</title><style>:root{color-scheme:dark}body{margin:0;background:#030607;color:#eef7f5;font:15px ui-monospace,monospace}main{max-width:1000px;margin:auto;padding:28px}.glass{border:1px solid #1e3432;border-radius:22px;background:#07100fee;box-shadow:0 20px 80px #000;padding:24px}.brand{color:#73ffe2;letter-spacing:.14em;font-weight:800}.status{display:inline-block;border:1px solid #285c52;border-radius:999px;padding:5px 10px;color:#73ffe2;font-size:11px}.terminal{min-height:420px;max-height:60vh;overflow:auto;margin:22px 0;padding:18px;border-radius:16px;background:#010202;border:1px solid #142321}.row{margin:0 0 18px;white-space:pre-wrap}.you{color:#d7e7e4}.core{color:#8affd9}.receipt{font-size:11px;color:#7b9792}.bar{display:flex;gap:10px}input{flex:1;background:#07100f;border:1px solid #24564e;color:white;padding:14px;border-radius:12px}button{background:#73ffe2;border:0;color:#00110d;padding:14px 20px;border-radius:12px;font-weight:900}</style></head><body><main><section class=\"glass\"><div class=\"brand\">iTENSOR · SOVEREIGN CPU GATEWAY</div><p><span class=\"status\">LOCAL CPU / IPROOF-V1</span></p><div id=\"terminal\" class=\"terminal\"></div><div class=\"bar\"><input id=\"q\" placeholder=\"Enter directive...\" autocomplete=\"off\"><button id=\"go\">EXECUTE</button></div></section></main><script>const q=document.querySelector('#q'),t=document.querySelector('#terminal');function add(cls,label,text){const d=document.createElement('div');d.className='row '+cls;d.textContent=label+': '+text;t.appendChild(d);t.scrollTop=t.scrollHeight}async function send(){const p=q.value.trim();if(!p)return;q.value='';add('you','YOU',p);try{const r=await fetch('/prompt',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({prompt:p})});const d=await r.json();if(!r.ok)throw Error(d.error||'execution failed');add('core','SOVEREIGN CORE',d.response);add('receipt','iProof',d.receipt.execution.output_sha256+' · '+d.receipt.signature.slice(0,20)+'…')}catch(e){add('receipt','ACTION REQUIRED',e.message)}}document.querySelector('#go').onclick=send;q.addEventListener('keydown',e=>{if(e.key==='Enter')send()});</script></body></html>"

@app.post("/prompt")
def prompt():
    data=request.get_json(silent=True) or {}; user_prompt=str(data.get("prompt","")).strip()
    if not user_prompt: return jsonify({"error":"prompt is required"}), 400
    try:
        response, command, samples = run_local(user_prompt); size=MODEL.stat().st_size
        receipt,_=build_receipt(request=user_prompt,response=response,model_path=MODEL,engine_path=ENGINE,cpu_threads=THREADS,
                                memory_bytes=samples["ram_total_bytes"],artifact_bytes=size,network_mode="LOCAL_ONLY_DECLARED",command=command)
        receipt["result"]["metrics"].update({"cpu_load_percent_peak":round(samples["cpu_peak_percent"],2),
                                             "ram_used_bytes_peak":samples["ram_peak_bytes"],"ram_total_bytes":samples["ram_total_bytes"]})
        # Signature must cover the final telemetry fields.
        from .receipt import canonical_json, load_or_create_key
        key=load_or_create_key(Path(os.getenv("IPROOF_KEY_PATH",".sovereign/ed25519-private.pem")))
        receipt.pop("signature",None); receipt["signature"]=key.sign(canonical_json(receipt).encode()).hex()
        return jsonify({"response":response,"receipt":receipt})
    except Exception as exc: return jsonify({"error":str(exc),"status":"ACTION_REQUIRED"}), 503

if __name__=="__main__": app.run(host="127.0.0.1",port=int(os.getenv("SOVEREIGN_PORT","5000")),debug=False)
