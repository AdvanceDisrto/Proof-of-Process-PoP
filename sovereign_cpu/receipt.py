from __future__ import annotations
import hashlib, json, os, platform, secrets, time
from pathlib import Path
from typing import Any
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ed25519

def sha256_bytes(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()

def sha256_file(path: str | Path) -> tuple[str, int]:
    p = Path(path); h = hashlib.sha256(); size = 0
    with p.open("rb") as f:
        while chunk := f.read(1024 * 1024): size += len(chunk); h.update(chunk)
    return "sha256:" + h.hexdigest(), size

def canonical_json(value: dict[str, Any]) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))

def load_or_create_key(path: str | Path) -> ed25519.Ed25519PrivateKey:
    p = Path(path); p.parent.mkdir(parents=True, exist_ok=True)
    if p.exists(): return serialization.load_pem_private_key(p.read_bytes(), password=None)
    key = ed25519.Ed25519PrivateKey.generate()
    p.write_bytes(key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()))
    try: os.chmod(p, 0o600)
    except OSError: pass
    return key

def build_receipt(*, request: str, response: str, model_path: str | Path, engine_path: str | Path,
                  cpu_threads: int, memory_bytes: int, artifact_bytes: int, network_mode: str,
                  command: str, status: str = "PASS") -> tuple[dict[str, Any], ed25519.Ed25519PrivateKey]:
    model_sha, model_bytes = sha256_file(model_path); engine_sha, _ = sha256_file(engine_path)
    request_sha, output_sha = sha256_bytes(request.encode()), sha256_bytes(response.encode())
    completed_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    receipt: dict[str, Any] = {
        "protocol": "IPROOF-v1", "evidence_id": "cpu-" + secrets.token_hex(16),
        "intent": {"request_sha256": request_sha, "intent_class": "sovereign.cpu.inference"},
        "routing": {"router_version": "sovereign-cpu-v1", "action_id": "cpu.inference", "execution_class": "INTELLIGENCE",
                    "reason": "Local CPU inference through declared engine; no remote model API is part of the execution command.",
                    "module_ids": ["iTensor", "iWay", "iProof", "Gaia"]},
        "execution": {"artifact_id": Path(model_path).name, "artifact_sha256": model_sha,
                      "runtime_version": f"python-{platform.python_version()}|engine-sha256:{engine_sha.removeprefix('sha256:')}",
                      "output_sha256": output_sha, "completed_at": completed_at},
        "resources": {"compute": {"device": f"CPU:{platform.machine()}:{cpu_threads}-threads", "driver": "none", "memory_bytes": memory_bytes},
                      "network": {"mode": network_mode}, "storage": {"artifact_bytes": artifact_bytes or model_bytes}},
        "result": {"status": status, "metrics": {"cpu_threads_used": cpu_threads, "model_bytes": model_bytes, "engine_sha256": engine_sha}},
        "reproduction": {"required": True, "command": command,
                         "environment_hash": sha256_bytes((platform.platform() + "|" + platform.python_version()).encode()),
                         "expected_output_sha256": output_sha}}
    key = load_or_create_key(Path(os.getenv("IPROOF_KEY_PATH", ".sovereign/ed25519-private.pem")))
    receipt["signature"] = key.sign(canonical_json(receipt).encode()).hex()
    return receipt, key
