"""Provider-node evidence forwarder.

This agent never fabricates a quote. Set POP_ATTESTATION_TOKEN_B64 to evidence
collected by the provider/vendor attestation tooling and POP_WORKLOAD_FILE to the
exact workload artifact being bound.
"""

import hashlib
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

GATEWAY_URL = os.getenv("POP_GATEWAY_URL", "https://www.proofofprocess.online").rstrip("/")
PROVIDER_NAME = os.getenv("POP_PROVIDER", "UNSPECIFIED")
INSTANCE_ID = os.getenv("POP_INSTANCE_ID", os.uname().nodename)
HARDWARE_TYPE = os.getenv("POP_HARDWARE_TYPE", "UNSPECIFIED")
WORKLOAD_FILE = Path(os.getenv("POP_WORKLOAD_FILE", "main.py"))


def post_json(path: str, payload: dict) -> dict:
    request = urllib.request.Request(
        f"{GATEWAY_URL}{path}",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=15) as response:
        return json.loads(response.read())


def run() -> int:
    token = os.getenv("POP_ATTESTATION_TOKEN_B64")
    if not token:
        print("ACTION_REQUIRED: POP_ATTESTATION_TOKEN_B64 is absent; refusing to fabricate evidence.")
        return 2
    if not WORKLOAD_FILE.is_file():
        print(f"ACTION_REQUIRED: workload file not found: {WORKLOAD_FILE}")
        return 2

    workload_hash = hashlib.sha256(WORKLOAD_FILE.read_bytes()).hexdigest()
    challenge = post_json(
        "/api/lifecycle/challenge",
        {
            "provider_name": PROVIDER_NAME,
            "instance_id": INSTANCE_ID,
            "hardware_type": HARDWARE_TYPE,
        },
    )
    result = post_json(
        "/api/lifecycle/verify",
        {
            "instance_id": INSTANCE_ID,
            "nonce": challenge["challenge_nonce"],
            "attestation_token_b64": token,
            "workload_hash": workload_hash,
        },
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["physical_gate"] == "ACTION_REQUIRED" else 3


if __name__ == "__main__":
    try:
        raise SystemExit(run())
    except (urllib.error.URLError, TimeoutError) as exc:
        print(f"ACTION_REQUIRED: gateway transmission failed: {exc}")
        raise SystemExit(2)
