"""STRMKRD Rev0 localhost API. No counterfeit silicon attestation or fake QoW minting.

Run (after installing hardware requirements and fastapi/uvicorn):
    STRMKRD_LOCAL_TOKEN=<random-long-token> python hardware/strmkrd-node/universal_api.py
On unsupported hardware, /api/v1/observation returns 503 instead of fabricating evidence.
The offline verifier supports externally pinned, versioned ECDSA-P256 signatures.
"""
from __future__ import annotations

import hashlib
import hmac
import importlib.util
import json
import os
from pathlib import Path
import sys
from typing import Callable

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel, Field


SCHEMA = "strmkrd/rev0/p256-signed-test-observation/v1"
ALG = "ECDSA-P256-SHA256-DER"
SOURCE_TIER = "UNAUTHENTICATED_I2C_OBSERVATION"


def _load_observer():
    path = Path(__file__).resolve().with_name("observer.py")
    spec = importlib.util.spec_from_file_location("strmkrd_observer_api", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def canonical(data: object) -> bytes:
    """Deterministic Python JSON (not a claim of RFC 8785/JCS)."""
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
                      allow_nan=False).encode("utf-8")


def verify_p256(receipt: dict, pinned_public_key_pem: str) -> dict:
    """Offline-only cryptographic integrity verification. Trust pin is mandatory."""
    try:
        if not isinstance(receipt, dict) or not isinstance(pinned_public_key_pem, str):
            raise ValueError("malformed request")
        if not pinned_public_key_pem.startswith("-----BEGIN PUBLIC KEY-----"):
            raise ValueError("external public key pin required")
        body, sig = receipt["body"], receipt["signature"]
        if (not isinstance(body, dict) or body.get("spec") != SCHEMA
                or body.get("source_tier") not in ("SYNTHETIC_SIMULATOR", SOURCE_TIER)):
            raise ValueError("unsupported receipt schema or source tier")
        if (not isinstance(sig, dict) or sig.get("algorithm") != ALG
                or sig.get("encoding") != "DER-HEX"):
            raise ValueError("wrong signature algorithm or encoding")
        key = serialization.load_pem_public_key(pinned_public_key_pem.encode("ascii"))
        if not isinstance(key, ec.EllipticCurvePublicKey) or not isinstance(key.curve, ec.SECP256R1):
            raise ValueError("pinned key is not P-256")
        if not hmac.compare_digest(receipt["body_sha256"], "sha256:" + hashlib.sha256(canonical(body)).hexdigest()):
            raise ValueError("body digest mismatch")
        key.verify(bytes.fromhex(sig["value"]), canonical(body), ec.ECDSA(hashes.SHA256()))
        return {"valid": True, "verdict": "SIGNED_PAYLOAD_INTEGRITY_ONLY",
                "evidence_source": body["source_tier"],
                "does_not_prove": ["hardware secure-element signer", "physical sensor accuracy",
                                   "mathematical premises describe reality", "clinical safety",
                                   "external timestamp or Merkle inclusion"]}
    except (KeyError, TypeError, ValueError, InvalidSignature, UnicodeError, AttributeError):
        return {"valid": False, "verdict": "INVALID_OR_UNTRUSTED_SIGNATURE"}


def sign_test_only_p256(body: dict, private_key: ec.EllipticCurvePrivateKey) -> dict:
    """TEST UTILITY. Never pass this as evidence of native ATECC hardware signing."""
    if body.get("source_tier") != "SYNTHETIC_SIMULATOR" or body.get("spec") != SCHEMA:
        raise ValueError("test signing allowed only for synthetic test schema")
    raw = canonical(body)
    return {"body": body,
            "body_sha256": "sha256:" + hashlib.sha256(raw).hexdigest(),
            "signature": {"algorithm": ALG, "encoding": "DER-HEX",
                          "value": private_key.sign(raw, ec.ECDSA(hashes.SHA256())).hex()}}


class VerifyInput(BaseModel):
    receipt: dict = Field()
    pinned_public_key_pem: str = Field(min_length=70, max_length=4096)


def create_app(*, token: str, probe: Callable[[], dict] | None = None) -> FastAPI:
    """Injectable probe is only for tests; production reads real Linux I2C."""
    if not isinstance(token, str) or len(token) < 24:
        raise ValueError("explicit API token of at least 24 characters required")
    app = FastAPI(title="STRMKRD Universal Node Rev0", version="0.1.0")
    observer = _load_observer()

    def require_key(value: str | None) -> None:
        if not value or not hmac.compare_digest(value, token):
            raise HTTPException(401, "invalid local API key")

    @app.get("/api/v1/status")
    def status():
        return {"status": "SOFTWARE_AVAILABLE",
                "source": "LINUX_I2C_ONLY", "hardware_device": "NOT_VERIFIED",
                "trusted_signer": "NOT_PROVISIONED", "photonic_spu": "NOT_PRESENT",
                "ipqr_camera": "NOT_VERIFIED", "qow_minting": "NOT_ENABLED",
                "transport": "LOOPBACK_ONLY"}

    @app.get("/api/v1/observation")
    def observation(x_api_key: str | None = Header(default=None)):
        require_key(x_api_key)
        try:
            reading = probe() if probe is not None else observer.bringup.hardware_probe(1, 0x40, False)
            if (reading.get("source_tier") != SOURCE_TIER
                    or reading.get("silicon_signature") != "NOT_PRESENT"
                    or reading.get("physical_device_authentication") != "NOT_VERIFIED"):
                raise ValueError("observation source must remain unauthenticated")
            math = observer.check_observation(reading)
        except (OSError, RuntimeError, ValueError, KeyError, TypeError) as exc:
            raise HTTPException(503, "HARDWARE_OR_POLICY_GATE_NOT_VERIFIED") from exc
        return {"spec": "strmkrd/rev0/local-observation/v1", "observation": reading,
                "formal_policy": math, "receipt": "NOT_MINTED",
                "authenticity": "NOT_VERIFIED"}

    @app.post("/api/v1/verify")
    def verify(req: VerifyInput):
        # No self-reported key from the receipt is trusted. Caller MUST pin issuer externally.
        return verify_p256(req.receipt, req.pinned_public_key_pem)

    @app.get("/api/v1/receipt")
    def receipt(x_api_key: str | None = Header(default=None)):
        require_key(x_api_key)
        raise HTTPException(503, "NO_PROVISIONED_HARDWARE_SIGNER_OR_PHYSICAL_EVIDENCE_BINDING")

    return app


def main():
    import uvicorn
    token = os.environ.get("STRMKRD_LOCAL_TOKEN", "")
    app = create_app(token=token)
    # The machine-local listener is intentionally not a cross-device network endpoint.
    uvicorn.run(app, host="127.0.0.1", port=8768, access_log=False)


if __name__ == "__main__":
    main()
