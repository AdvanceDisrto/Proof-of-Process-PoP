from __future__ import annotations

import hashlib
import time

from network_bridge.pop_bridge import NetworkProofBridge


def stream_gnmi(client, bridge: NetworkProofBridge, subscribe_request: dict) -> None:
    """Bind each received gNMI protobuf message to a PoP receipt."""
    for response in client.Subscribe(subscribe_request):
        raw = response.SerializeToString()
        receipt = bridge.sign_and_emit(
            {
                "source": "cisco_catalyst_gnmi",
                "event_type": "hardware_state_stream",
                "timestamp": time.time(),
                "raw_state_sha256": hashlib.sha256(raw).hexdigest(),
                "raw_state_bytes": len(raw),
            }
        )
        print(f"[SAPU] gNMI receipt {receipt['receipt_sha256'][:24]}...")
