from __future__ import annotations
import os, subprocess, time
from pathlib import Path
from flask import Flask, jsonify, request
from .receipt import build_receipt
app = Flask(__name__)
ROOT = Path(os.getenv("SOVEREIGN_ROOT", ".")).resolve()
MODEL = Path(os.getenv("SOVEREIGN_MODEL", ROOT / "open_intelligence.gguf")).resolve()
ENGINE = Path(os.getenv("SOVEREIGN_ENGINE", ROOT / "llama-cli")).resolve()
THREADS = int(os.getenv("SOVEREIGN_THREADS", "8")); MAX_TOKENS = int(os.getenv("SOVEREIGN_MAX_TOKENS", "128"))

def _memory_bytes() -> int:
    try:
        for line in Path("/proc/meminfo").read_text().splitlines():
            if line.startswith("MemTotal:"): return int(line.split()[1]) * 1024
    except (OSError, ValueError): pass
    return 0

def run_local(prompt: str) -> tuple[str, str]:
    if not MODEL.is_file(): raise FileNotFoundError(f"model not found: {MODEL}")
    if not ENGINE.is_file(): raise FileNotFoundError(f"engine not found: {ENGINE}")
    command = [str(ENGINE), "-m", str(MODEL), "-p", f"User: {prompt}\\nAssistant:", "-t", str(THREADS), "-n", str(MAX_TOKENS), "--no-warmup"]
    proc = subprocess.run(command, cwd=str(ROOT), capture_output=True, text=True, timeout=600, check=False)
    if proc.returncode != 0: raise RuntimeError(f"llama-cli failed ({proc.returncode}): {proc.stderr[-2000:]}")
    output = proc.stdout.split("Assistant:", 1)[-1].strip()
    if not output: raise RuntimeError("local engine produced empty output")
    return output, " ".join(command)

@app.get("/")
def home():
    return jsonify({"service":"iTensor Sovereign CPU Gateway","protocol":"IPROOF-v1","state":"LOCAL_ONLY","model":MODEL.name,
                    "network_policy":"DECLARED_LOCAL_ONLY","truth_boundary":"Receipt binds declared execution evidence; it does not prove answer truth or physical air-gap."})

@app.post("/prompt")
def prompt():
    data=request.get_json(silent=True) or {}; user_prompt=str(data.get("prompt","")).strip()
    if not user_prompt: return jsonify({"error":"prompt is required"}), 400
    try:
        response, command = run_local(user_prompt); size=MODEL.stat().st_size
        receipt,_=build_receipt(request=user_prompt,response=response,model_path=MODEL,engine_path=ENGINE,cpu_threads=THREADS,
                                memory_bytes=_memory_bytes(),artifact_bytes=size,network_mode="LOCAL_ONLY_DECLARED",command=command)
        return jsonify({"response":response,"receipt":receipt})
    except Exception as exc: return jsonify({"error":str(exc),"status":"ACTION_REQUIRED"}), 503

if __name__=="__main__": app.run(host="127.0.0.1",port=int(os.getenv("SOVEREIGN_PORT","5000")),debug=False)
