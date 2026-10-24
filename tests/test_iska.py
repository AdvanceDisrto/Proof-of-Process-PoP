import time

from cryptography.hazmat.primitives import serialization

from iska.authority import (
    fingerprint,
    generate_root_identity,
    issue_delegation,
    sign_receipt,
    verify_delegation,
    verify_receipt,
)


def test_root_never_needed_by_provider_to_verify_chain():
    root, root_id, root_public = generate_root_identity()
    delegated, cert = issue_delegation(root, root_id, root_public, now=1_000)
    assert verify_delegation(cert, now=1_001)
    payload = {
        "instance_id": "node-01",
        "workload_hash": "a" * 64,
        "physical_gate": "ACTION_REQUIRED",
    }
    signed = sign_receipt(delegated, cert, payload, now=1_001).to_dict()
    assert verify_receipt(signed, now=1_001)
    assert "root_private" not in str(signed)
    assert root.private_bytes(
        serialization.Encoding.Raw,
        serialization.PrivateFormat.Raw,
        serialization.NoEncryption(),
    ).hex() not in str(signed)


def test_tampering_invalidates_receipt():
    root, root_id, root_public = generate_root_identity()
    delegated, cert = issue_delegation(root, root_id, root_public, now=2_000)
    signed = sign_receipt(
        delegated,
        cert,
        {"instance_id": "node-01", "physical_gate": "ACTION_REQUIRED"},
        now=2_001,
    ).to_dict()
    signed["receipt"]["instance_id"] = "attacker"
    assert not verify_receipt(signed, now=2_001)


def test_expired_delegation_fails_closed():
    root, root_id, root_public = generate_root_identity()
    _, cert = issue_delegation(root, root_id, root_public, ttl_seconds=10, now=3_000)
    assert verify_delegation(cert, now=3_009)
    assert not verify_delegation(cert, now=3_010)


def test_fingerprint_is_cryptographic_and_deterministic():
    root, root_id, root_public = generate_root_identity()
    delegated, cert = issue_delegation(root, root_id, root_public, now=int(time.time()))
    receipt = sign_receipt(
        delegated,
        cert,
        {"physical_gate": "ACTION_REQUIRED", "workload_hash": "b" * 64},
    ).to_dict()
    assert fingerprint(receipt).startswith("sha256:")
    assert fingerprint(receipt) == fingerprint(dict(receipt))
