"""Evidence-first inference adapters for PoP. No secret logging or self-certification.

This module emits UNSIGNED observations. An existing trusted PoP signer/verifier
must promote them. No provider identity, checkpoint, TEE, or factual correctness
is independently attested by the transport response.
"""
from __future__ import annotations
import hashlib
import json
import os
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any

class InferenceBlocked(RuntimeError):
    pass

def canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()

def digest(value: Any) -> str:
    return "sha256:" + hashlib.sha256(canonical(value)).hexdigest()

@dataclass(frozen=True)
class Provider:
    name: str
    model: str
    url: str
    env_key: str | None
    source: str
    ownership: str

def providers() -> dict[str, Provider]:
    return {
        "openai_api": Provider("openai_api", os.getenv("INNOVULIS_OPENAI_MODEL", "gpt-4o-mini"),
            "https://api.openai.com/v1/chat/completions", "OPENAI_API_KEY", "api", "proprietary-api"),
        "deepseek_api": Provider("deepseek_api", os.getenv("INNOVULIS_DEEPSEEK_MODEL", "deepseek-chat"),
            "https://api.deepseek.com/chat/completions", "DEEPSEEK_API_KEY", "api", "third-party-api"),
        "groq_api": Provider("groq_api", os.getenv("INNOVULIS_GROQ_MODEL", ""),
            "https://api.groq.com/openai/v1/chat/completions", "GROQ_API_KEY", "api", "third-party-api"),
        "ollama_local": Provider("ollama_local", os.getenv("INNOVULIS_OLLAMA_MODEL", "deepseek-r1:7b"),
            "http://127.0.0.1:11434/v1/chat/completions", None, "self-hosted-endpoint", "checkpoint-unattested"),
    }

def post_json(url: str, payload: dict, key: str | None = None, timeout: float = 30) -> dict:
    headers = {"Content-Type": "application/json"}
    if key:
        headers["Authorization"] = "Bearer " + key
    request = urllib.request.Request(url, data=canonical(payload), headers=headers, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = response.read(5_000_000)
        data = json.loads(body)
        if not isinstance(data, dict):
            raise InferenceBlocked("Invalid provider response object")
        return data
    except (urllib.error.URLError, TimeoutError, ValueError) as exc:
        raise InferenceBlocked("Provider request failed: " + type(exc).__name__) from None

def get_json(url: str, key: str, timeout: float = 30) -> dict:
    request = urllib.request.Request(url, headers={"Authorization": "Bearer " + key})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            data = json.loads(response.read(5_000_000))
        if not isinstance(data, dict):
            raise InferenceBlocked("Invalid status response object")
        return data
    except (urllib.error.URLError, TimeoutError, ValueError):
        raise InferenceBlocked("Provider status request failed") from None

def generate(prompt: str, provider_name: str, *, allow_external: bool = False,
             transport=post_json) -> dict:
    registry = providers()
    if provider_name not in registry:
        raise InferenceBlocked("Unknown provider")
    p = registry[provider_name]
    if p.source == "api" and not allow_external:
        raise InferenceBlocked("Third-party API requires explicit authorization")
    if not p.model:
        raise InferenceBlocked("A specific model must be configured")
    key = os.getenv(p.env_key) if p.env_key else None
    if p.env_key and not key:
        raise InferenceBlocked("Provider credential unavailable")
    if not isinstance(prompt, str) or not prompt.strip():
        raise InferenceBlocked("Prompt required")
    started = time.monotonic()
    response = transport(p.url, {"model": p.model, "messages": [{"role": "user", "content": prompt}]}, key)
    try:
        content = response["choices"][0]["message"]["content"]
        if not isinstance(content, str):
            raise ValueError
    except (KeyError, IndexError, TypeError, ValueError):
        raise InferenceBlocked("Provider returned no text") from None
    observed = {
        "schema": "ipqr/pop-inference-observation/1",
        "verification_state": "UNVERIFIED_INFERENCE",
        "provider": p.name, "requested_model": p.model,
        "reported_model": response.get("model"), "source": p.source,
        "ownership": p.ownership, "prompt_sha256": digest(prompt),
        "output_sha256": digest(content), "output": content,
        "latency_ms_observed": round((time.monotonic() - started) * 1000, 2),
        "provider_response_id": response.get("id"),
        "capability_not_verified": ["provider_identity", "checkpoint_weights",
            "TEE_attestation", "factual_accuracy", "external_anchor"],
    }
    observed["observation_sha256"] = digest(observed)
    return observed

class RunPodAsync:
    """Asynchronous *single job* interface; batching requires a compatible custom worker."""
    def __init__(self, endpoint_id: str | None = None, key: str | None = None,
                 transport_post=post_json, transport_get=get_json):
        self.endpoint_id = endpoint_id or os.getenv("RUNPOD_BATCH_ENDPOINT_ID")
        self.key = key or os.getenv("RUNPOD_API_KEY")
        if not self.endpoint_id or not self.endpoint_id.replace("-", "").replace("_", "").isalnum():
            raise InferenceBlocked("Invalid or missing RunPod endpoint ID")
        if not self.key:
            raise InferenceBlocked("RunPod credential unavailable")
        self.url = "https://api.runpod.ai/v2/" + self.endpoint_id
        self.post = transport_post
        self.get = transport_get

    def submit(self, inputs: list, model: str, *, authorized: bool = False) -> dict:
        if not authorized:
            raise InferenceBlocked("Explicit RunPod job authorization required")
        if not inputs or not model:
            raise InferenceBlocked("Input items and model required")
        payload = {"input": {"model": model, "batch_data": inputs}}
        answer = self.post(self.url + "/run", payload, self.key)
        job_id = answer.get("id")
        if not isinstance(job_id, str) or not job_id or "/" in job_id or "?" in job_id:
            raise InferenceBlocked("No valid provider job ID acknowledged")
        return {
            "schema": "ipqr/pop-batch-observation/1",
            "phase": "SUBMISSION_ACKNOWLEDGED", "verification_state": "UNVERIFIED",
            "provider": "runpod", "endpoint_id": self.endpoint_id,
            "job_id": job_id, "request_sha256": digest(payload),
            "receipt_status": "UNSIGNED_OBSERVATION",
        }

    def poll(self, submission: dict) -> dict:
        job_id = submission.get("job_id")
        if submission.get("endpoint_id") != self.endpoint_id or not isinstance(job_id, str) or not job_id or "/" in job_id or "?" in job_id:
            raise InferenceBlocked("Submission does not match endpoint")
        response = self.get(self.url + "/status/" + job_id, self.key)
        state = response.get("status")
        if state not in {"COMPLETED", "FAILED", "CANCELLED", "TIMED_OUT", "IN_QUEUE", "IN_PROGRESS"}:
            raise InferenceBlocked("Unknown RunPod job state")
        if state == "COMPLETED" and "output" not in response:
            raise InferenceBlocked("Completed job returned no output")
        result = {
            "schema": "ipqr/pop-batch-observation/1",
            "phase": "TERMINAL_OBSERVATION" if state in {"COMPLETED", "FAILED", "CANCELLED", "TIMED_OUT"} else "PENDING",
            "verification_state": "UNVERIFIED",
            "job_id": job_id, "provider_state": state,
            "submission_sha256": digest(submission),
            "output_sha256": digest(response["output"]) if state == "COMPLETED" else None,
            "receipt_status": "UNSIGNED_OBSERVATION",
        }
        return result
