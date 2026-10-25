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
    return jsonify({"service":"iTensor Sovereign CPU Gateway","protocol":"IPROOF-v1","state":"LOCAL_ONLY","model":MODEL.name,
                    "network_policy":"DECLARED_LOCAL_ONLY","truth_boundary":"Receipt binds declared execution evidence; it does not prove answer truth or physical air-gap."})

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
