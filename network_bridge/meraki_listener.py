from __future__ import annotations

import time
from collections.abc import Callable

from network_bridge.pop_bridge import NetworkProofBridge


def iter_network_events(dashboard, network_id: str):
    """Yield all currently available Meraki network events."""
    response = dashboard.networks.getNetworkEvents(
        network_id,
        productType="wireless",
        includedEventTypes=["association", "authentication"],
        total_pages="all",
    )
    yield from response.get("events", [])


def poll_meraki_events(
    dashboard,
    network_id: str,
    bridge: NetworkProofBridge,
    *,
    interval_seconds: int = 60,
    sleep: Callable[[float], None] = time.sleep,
) -> None:
    """Poll read-only Meraki telemetry and emit PoP receipts."""
    seen: set[tuple[str, str]] = set()
    while True:
        try:
            for event in iter_network_events(dashboard, network_id):
                key = (
                    str(event.get("occurredAt", "")),
                    str(event.get("clientMac") or event.get("clientId") or ""),
                )
                if key in seen:
                    continue
                seen.add(key)
                bridge.sign_and_emit(
                    {
                        "source": "cisco_meraki",
                        "event_type": event.get("type"),
                        "client_mac": event.get("clientMac"),
                        "description": event.get("description"),
                        "timestamp": event.get("occurredAt"),
                        "network_id": event.get("networkId", network_id),
                    }
                )
        except Exception as exc:
            print(f"[Meraki] poll error: {exc}")
        sleep(interval_seconds)
