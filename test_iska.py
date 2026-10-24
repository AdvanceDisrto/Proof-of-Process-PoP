from iska_authority import generate_root_identity, issue_delegation, sign_receipt, verify_delegation, verify_receipt, fingerprint

def test_root_authorizes_provider_without_leaving_root_private_key_in_receipt():
    root, root_id, root_public = generate_root_identity()
    delegated, cert = issue_delegation(root, root_id, root_public, now=1000)
    assert verify_delegation(cert, now=1001)
    receipt = sign_receipt(delegated, cert, {
        "instance_id": "node-01",
        "workload_hash": "a" * 64,
        "physical_gate": "ACTION_REQUIRED",
    }, now=1001).to_dict()
    assert verify_receipt(receipt, now=1001)
    assert "private" not in str(receipt).lower()

def test_receipt_tampering_fails():
    root, root_id, root_public = generate_root_identity()
    delegated, cert = issue_delegation(root, root_id, root_public, now=2000)
    receipt = sign_receipt(delegated, cert, {"physical_gate": "ACTION_REQUIRED"}, now=2001).to_dict()
    receipt["receipt"]["physical_gate"] = "MEASURED_PASS"
    assert not verify_receipt(receipt, now=2001)

def test_expired_delegation_fails():
    root, root_id, root_public = generate_root_identity()
    _, cert = issue_delegation(root, root_id, root_public, ttl_seconds=10, now=3000)
    assert verify_delegation(cert, now=3009)
    assert not verify_delegation(cert, now=3010)

def test_fingerprint_is_sha256():
    root, root_id, root_public = generate_root_identity()
    delegated, cert = issue_delegation(root, root_id, root_public, now=4000)
    receipt = sign_receipt(delegated, cert, {"physical_gate": "ACTION_REQUIRED"}, now=4001).to_dict()
    assert fingerprint(receipt).startswith("sha256:")
