from __future__ import annotations

import hashlib
import time
from typing import Callable

from core.crypto import canonical, sha
from tools.gate import physical_gate
from tools.pop_graph import CognitiveGraph


class NetworkProofBridge:
    """Bind network observations to the existing PoP graph.

    The caller supplies a signing function so private-key custody stays outside
    this library. The bridge never promotes a network event to physical trust.
    """

    def __init__(
        self,
        sign_fn: Callable[[dict], str],
        public_key: str,
        *,
        graph: CognitiveGraph | None = None,
        clock: Callable[[], float] = time.time,
    ) -> None:
        self.sign_fn = sign_fn
        self.public_key = public_key
        self.graph = graph or CognitiveGraph(root_hash=sha(b"network-edge-genesis"))
        self.clock = clock

    def sign_and_emit(self, payload: dict) -> dict:
        now = self.clock()
        event = dict(payload)
        event.setdefault("observed_at_unix", now)
        body = {
            "spec": "innovulis-network-receipt/1.0",
            "issued_utc": now,
            "network_event": event,
            "ilogic": {
                "truth_axis": "ESTABLISHED",
                "attestation_axis": "UNATTESTED",
                "tier": "VERIFIED_PROCESS",
                "physical_gate": physical_gate(None, None),
            },
            "issuer_pubkey": self.public_key,
        }
        body["signature"] = self.sign_fn(body)
        body["receipt_sha256"] = sha(canonical(body))
        node_id = f"net-{hashlib.sha256(canonical(event)).hexdigest()[:24]}-{int(now * 1000)}"
        self.graph.add_raw_node(node_id, None, "network_event", body)
        return {
            **body,
            "node_id": node_id,
            "graph_registry_root": self.graph.to_receipt()["registry_root"],
        }


def build_opennds_payload(
    method: str,
    client_mac: str,
    *,
    client_ip: str | None = None,
    gateway: str | None = None,
    client_token: str | None = None,
    session_start: str | None = None,
    session_end: str | None = None,
    custom: str | None = None,
) -> dict:
    payload = {
        "source": "opennds",
        "event_type": method,
        "client_mac": client_mac,
        "client_ip": client_ip,
        "gateway": gateway,
        "session_start": session_start,
        "session_end": session_end,
        "custom": custom,
    }
    if client_token:
        payload["client_token_sha256"] = hashlib.sha256(client_token.encode()).hexdigest()
    return payload
