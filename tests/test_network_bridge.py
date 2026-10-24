from cryptography.hazmat.primitives.asymmetric import ed25519

from core.crypto import public_hex, sign
from network_bridge.pop_bridge import NetworkProofBridge, build_opennds_payload
from tools.gate import physical_gate


def test_network_receipt_is_signed_and_fail_closed():
    key = ed25519.Ed25519PrivateKey.generate()
    bridge = NetworkProofBridge(
        lambda body: sign(key, body),
        public_hex(key),
        clock=lambda: 1700000000.0,
    )
    receipt = bridge.sign_and_emit(
        {
            "source": "test",
            "event_type": "association",
            "client_mac": "00:11:22:33:44:55",
        }
    )
    assert receipt["ilogic"]["truth_axis"] == "ESTABLISHED"
    assert receipt["ilogic"]["attestation_axis"] == "UNATTESTED"
    assert receipt["ilogic"]["tier"] == "VERIFIED_PROCESS"
    assert receipt["ilogic"]["physical_gate"] == "ACTION_REQUIRED"
    assert receipt["node_id"].startswith("net-")
    assert receipt["graph_registry_root"].startswith("sha256:")
    assert receipt["signature"].startswith("ed25519:")
    assert physical_gate(None, None) == "ACTION_REQUIRED"


def test_opennds_token_is_hashed_not_recorded():
    payload = build_opennds_payload(
        "client_auth",
        "00:11:22:33:44:55",
        client_token="secret-token",
    )
    assert "client_token_sha256" in payload
    assert payload["client_token_sha256"] != "secret-token"
    assert "client_token" not in payload
