"""Physical mapping demo: 100 logical lanes mapped to simulated subsea cable paths.

This is a cryptographic/process simulation, not live subsea telemetry.
A cable status of CUT is an injected fault. No external network or physical
cable state is observed by this program.
"""

from __future__ import annotations

import hashlib
import json
import threading
from dataclasses import dataclass
from typing import Iterable

from cryptography.hazmat.primitives.asymmetric import ed25519

LANE_COUNT = 100
LANES_PER_CABLE = 20
MMR_FANOUT = 1000

SUBSEA_CABLES = [
    {"name": "MAREA", "route": "US-Virginia to Spain", "status": "ACTIVE"},
    {"name": "DUNANT", "route": "US-Virginia to France", "status": "ACTIVE"},
    {"name": "SEA-ME-WE 3", "route": "Europe to Asia", "status": "CUT"},
    {"name": "JUPITER", "route": "US to Japan", "status": "ACTIVE"},
    {"name": "2AFRICA", "route": "Europe to Africa", "status": "ACTIVE"},
]


def canonical_json(payload: dict) -> bytes:
    return json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")


def hash_payload(payload: dict) -> str:
    return hashlib.sha256(canonical_json(payload)).hexdigest()


def map_lane(lane_id: int) -> dict:
    """Map a logical lane to a deterministic *simulated* physical tuple."""
    if not 1 <= lane_id <= LANE_COUNT:
        raise ValueError(f"lane_id must be 1..{LANE_COUNT}")

    cable_index = (lane_id - 1) // LANES_PER_CABLE
    local_lane = (lane_id - 1) % LANES_PER_CABLE
    cable = SUBSEA_CABLES[cable_index]

    # Synthetic fiber/wavelength coordinates for the demo only.
    fiber_pair = (local_lane // 4) + 1
    wavelength = (local_lane % 4) + 1

    return {
        "name": cable["name"],
        "route": cable["route"],
        "status": cable["status"],
        "fiber_pair": fiber_pair,
        "wavelength": wavelength,
        "mapping_model": "SYNTHETIC_DEMO",
    }


def build_merkle_root(hashes: list[str]) -> str:
    """Build a deterministic binary Merkle root, duplicating an odd tail."""
    if not hashes:
        return ""
    level = list(hashes)
    while len(level) > 1:
        next_level: list[str] = []
        for i in range(0, len(level), 2):
            right = level[i + 1] if i + 1 < len(level) else level[i]
            next_level.append(
                hashlib.sha256((level[i] + right).encode("ascii")).hexdigest()
            )
        level = next_level
    return level[0]


def hierarchical_lane_counts(total_lanes: int, fanout: int = MMR_FANOUT) -> list[int]:
    """Return counts after each fanout aggregation step.

    This is a bounded mathematical model; it never materializes total_lanes
    receipts. The construction is hierarchical Merkle-style aggregation,
    not a claim that raw global receipts physically exist in this process.
    """
    if total_lanes < 1:
        raise ValueError("total_lanes must be positive")
    if fanout < 2:
        raise ValueError("fanout must be >= 2")

    counts: list[int] = []
    current = total_lanes
    while current > 1:
        current = (current + fanout - 1) // fanout
        counts.append(current)
    return counts


@dataclass
class SubseaMachine:
    private_key: ed25519.Ed25519PrivateKey

    def __init__(self) -> None:
        self.private_key = ed25519.Ed25519PrivateKey.generate()
        self.lane_receipts: list[dict] = []
        self._lock = threading.Lock()

    def execute_lane(self, lane_id: int) -> None:
        physical = map_lane(lane_id)
        intent = {
            "lane": lane_id,
            "action": "sync_global_database",
            "target": physical["route"],
        }

        if physical["status"] == "CUT":
            state = "PENDING_ROUTE"
            process_output = (
                f"iEf-301: SUBSEA_CABLE_CUT on {physical['name']}"
            )
        else:
            state = "VERIFIED_PROCESS"
            process_output = (
                f"Data synced via {physical['name']} "
                f"(Wavelength Lane {lane_id})"
            )

        auth_payload = {
            "intent": intent,
            "result": process_output,
            "state": state,
        }
        signature = self.private_key.sign(canonical_json(auth_payload)).hex()

        receipt_body = {
            "digital_lane": lane_id,
            "physical_cable": physical["name"],
            "route": physical["route"],
            "fiber_pair": physical["fiber_pair"],
            "wavelength": physical["wavelength"],
            "mapping_model": physical["mapping_model"],
            "intent_hash": hash_payload(intent),
            "state": state,
            "process_output": process_output,
            "signature": signature,
        }
        receipt_body["receipt_hash"] = hash_payload(receipt_body)

        with self._lock:
            self.lane_receipts.append(receipt_body)

    def run(self) -> dict:
        threads = [
            threading.Thread(target=self.execute_lane, args=(lane_id,))
            for lane_id in range(1, LANE_COUNT + 1)
        ]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        receipts = sorted(self.lane_receipts, key=lambda r: r["digital_lane"])
        failed_lanes = [
            r["digital_lane"]
            for r in receipts
            if r["state"] != "VERIFIED_PROCESS"
        ]
        master_root = build_merkle_root([r["receipt_hash"] for r in receipts])

        return {
            "total_lanes": LANE_COUNT,
            "physical_routes": [c["name"] for c in SUBSEA_CABLES],
            "verified_lanes": LANE_COUNT - len(failed_lanes),
            "pending_lanes": failed_lanes,
            "master_merkle_root": master_root,
            "anchor_status": "SIMULATED_NOT_ANCHORED",
            "receipts": receipts,
        }


def run_subsea_machine() -> dict:
    machine = SubseaMachine()
    result = machine.run()

    print("=" * 70)
    print("🌊 iKERNEL: Spinning up 100 Digital Lanes across Subsea Cables...")
    print("=" * 70)
    print("\n🧾 MASTER TRUTH RECEIPT (SUBSEA LAYER)")
    print("=" * 70)
    print(f"Total Lanes:         {result['total_lanes']}")
    print(f"Physical Routes:     {', '.join(result['physical_routes'])}")
    print(f"Verified Lanes:      {result['verified_lanes']}")
    print(
        f"Pending (Cut Cable): {len(result['pending_lanes'])} "
        f"(Lanes {min(result['pending_lanes'])} to "
        f"{max(result['pending_lanes'])})"
    )
    print(f"Master Merkle Root:  {result['master_merkle_root']}")
    print("=" * 70)
    print("🔐 iLOCK: anchor operation is NOT executed by this simulation.")
    print("⚠️  Anchor status: SIMULATED_NOT_ANCHORED")
    print("=" * 70)
    return result


if __name__ == "__main__":
    run_subsea_machine()
