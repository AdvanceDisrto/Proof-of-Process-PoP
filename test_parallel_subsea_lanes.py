import json

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric import ed25519

from parallel_subsea_lanes import (
    LANE_COUNT,
    SubseaMachine,
    build_merkle_root,
    canonical_json,
    hash_payload,
    hierarchical_lane_counts,
    map_lane,
)


def test_mapping_places_cut_cable_on_lanes_41_through_60():
    assert map_lane(1)["name"] == "MAREA"
    assert map_lane(40)["name"] == "DUNANT"
    assert map_lane(41)["name"] == "SEA-ME-WE 3"
    assert map_lane(60)["name"] == "SEA-ME-WE 3"
    assert map_lane(61)["name"] == "JUPITER"
    assert map_lane(100)["name"] == "2AFRICA"
    assert map_lane(41)["mapping_model"] == "SYNTHETIC_DEMO"


def test_machine_produces_80_verified_and_20_pending():
    result = SubseaMachine().run()
    assert result["total_lanes"] == 100
    assert result["verified_lanes"] == 80
    assert result["pending_lanes"] == list(range(41, 61))
    assert len(result["receipts"]) == 100
    assert result["anchor_status"] == "SIMULATED_NOT_ANCHORED"


def test_receipts_are_unique_and_merkle_root_is_deterministic():
    result = SubseaMachine().run()
    receipts = result["receipts"]
    hashes = [receipt["receipt_hash"] for receipt in receipts]

    assert len(set(hashes)) == 100
    assert result["master_merkle_root"] == build_merkle_root(hashes)
    assert result["master_merkle_root"] == build_merkle_root(list(hashes))


def test_ed25519_signature_binds_auth_payload():
    machine = SubseaMachine()
    machine.execute_lane(41)
    receipt = machine.lane_receipts[0]

    auth_payload = {
        "intent": {
            "lane": 41,
            "action": "sync_global_database",
            "target": "Europe to Asia",
        },
        "result": receipt["process_output"],
        "state": receipt["state"],
    }
    public_key = machine.private_key.public_key()
    public_key.verify(
        bytes.fromhex(receipt["signature"]),
        canonical_json(auth_payload),
    )

    tampered = dict(auth_payload)
    tampered["state"] = "VERIFIED_PROCESS"
    try:
        public_key.verify(
            bytes.fromhex(receipt["signature"]),
            canonical_json(tampered),
        )
    except InvalidSignature:
        pass
    else:
        raise AssertionError("tampered receipt unexpectedly verified")


def test_hierarchical_aggregation_never_materializes_600_trillion_receipts():
    assert hierarchical_lane_counts(600_000_000_000_000) == [
        600_000_000_000,
        600_000_000,
        600_000,
        600,
        1,
    ]


def test_hashing_is_canonical():
    a = {"b": 2, "a": 1}
    b = {"a": 1, "b": 2}
    assert canonical_json(a) == canonical_json(b)
    assert hash_payload(a) == hash_payload(b)


def test_lane_count_constant():
    assert LANE_COUNT == 100
