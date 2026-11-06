"""iNNOVULIS signed sensor -> local CIH -> QoW Z3 -> real PoP -> ipQR.

All measurement inputs are SYNTHETIC. No attached device, calibration,
trusted sensor hardware, clinical dose approval, or physical camera test.
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import secrets
from dataclasses import asdict
from pathlib import Path
from typing import Any

from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey, Ed25519PublicKey,
)
from cryptography.hazmat.primitives import serialization

from core.crypto import canonical as pop_canonical, sha as pop_sha, verify as pop_verify
from proof.parallel_pop import (
    aggregate as pop_aggregate, merkle as pop_merkle, verify_domain,
    DomainReceipt,
)
from integrations.qow_pop_bridge import qow_domain_receipt

# CI checks out the actual QoW main merge at a fixed SHA under _qow_checkout.
from qow.truthculator import canonical, digest, verify_receipt
from qow.truthculator_v2 import TruthculatorV2
from qow.independent_verifier import independent_check
from qow.ipqr import encode as optical_encode, decode as optical_decode

GENESIS_STATE = "sha256:" + "0" * 64
POLICY = {
    "spec": "innovulis/policy/demo-storage-temperature/v1",
    "unit": "centi_celsius",
    "min_centi": 200,
    "max_centi": 800,
    "domain": "SYNTHETIC_PACKAGE_STORAGE",
    "does_not_prove": "pharmaceutical stability, dose accuracy, clinical safety",
}


def public_key_hex(private_key: Ed25519PrivateKey) -> str:
    return private_key.public_key().public_bytes(
        serialization.Encoding.Raw, serialization.PublicFormat.Raw
    ).hex()


def signed_object(body: dict, key: Ed25519PrivateKey) -> dict:
    raw = canonical(body)
    return {
        "body": body,
        "receipt_hash": digest(raw),
        "signature": key.sign(raw).hex(),
    }


def verify_signed_object(obj: dict, trusted_public_key_hex: str) -> bool:
    try:
        body = obj["body"]
        raw = canonical(body)
        if not isinstance(trusted_public_key_hex, str):
            return False
        if obj["receipt_hash"] != digest(raw):
            return False
        Ed25519PublicKey.from_public_bytes(
            bytes.fromhex(trusted_public_key_hex)
        ).verify(bytes.fromhex(obj["signature"]), raw)
        return True
    except (KeyError, TypeError, ValueError, Exception):
        return False


def synthetic_sensor_event(
    device_key: Ed25519PrivateKey, value_centi: int = 500, sequence: int = 1
) -> dict:
    if type(value_centi) is not int or not (-10000 <= value_centi <= 20000):
        raise ValueError("invalid synthetic measurement")
    if type(sequence) is not int or sequence < 1:
        raise ValueError("invalid sequence")
    return signed_object(
        {
            "spec": "innovulis/physical-sensor-evidence/v1",
            "device_id": "SYNTHETIC-SENSOR-001",
            "kind": "temperature",
            "unit": "centi_celsius",
            "measurement": value_centi,
            "sequence": sequence,
            "nonce": secrets.token_hex(16),
            "source_tier": "SYNTHETIC_SIMULATOR",
            "trusted_time": False,
            "hardware_attestation": "NOT_PRESENT",
        },
        device_key,
    )


class LocalCIH:
    """In-memory test CIH; no networking, persistent replay store or TEE."""

    def __init__(self, cih_key: Ed25519PrivateKey, pinned_device_pubkey: str):
        self._cih_key = cih_key
        self._device_pub = pinned_device_pubkey
        self._sequence = 0
        self._state = GENESIS_STATE
        self._seen: set[str] = set()

    def ingest(self, sensor: dict) -> dict:
        if not verify_signed_object(sensor, self._device_pub):
            raise ValueError("sensor signature or device key invalid")
        event = sensor["body"]
        if (
            event.get("spec") != "innovulis/physical-sensor-evidence/v1"
            or event.get("source_tier") != "SYNTHETIC_SIMULATOR"
            or event.get("unit") != POLICY["unit"]
            or event.get("kind") != "temperature"
            or type(event.get("measurement")) is not int
            or type(event.get("sequence")) is not int
        ):
            raise ValueError("sensor evidence schema invalid")
        if event["sequence"] != self._sequence + 1:
            raise ValueError("sensor event sequence replay or gap")
        if sensor["receipt_hash"] in self._seen:
            raise ValueError("sensor evidence replay")
        previous = self._state
        commitment = digest(
            b"innovulis-cih-state-v1:" +
            bytes.fromhex(previous[7:]) +
            bytes.fromhex(sensor["receipt_hash"][7:])
        )
        record = signed_object(
            {
                "spec": "innovulis/cih-local-evidence/v1",
                "source_mode": "SYNTHETIC_SIMULATOR",
                "device_id": event["device_id"],
                "sequence": event["sequence"],
                "measurement": event["measurement"],
                "unit": event["unit"],
                "sensor_evidence_hash": sensor["receipt_hash"],
                "previous_state_commitment": previous,
                "state_commitment": commitment,
                "verified_device_pubkey": self._device_pub,
                "does_not_prove": [
                    "real device observed this measurement",
                    "sensor calibration or physical tamper resistance",
                    "trusted source time or cloud quorum",
                ],
            },
            self._cih_key,
        )
        self._seen.add(sensor["receipt_hash"])
        self._sequence += 1
        self._state = commitment
        return record


def validate_cih(sensor: dict, cih: dict, device_pub: str, cih_pub: str) -> None:
    if not verify_signed_object(sensor, device_pub):
        raise ValueError("sensor authentication failed")
    if not verify_signed_object(cih, cih_pub):
        raise ValueError("CIH signature invalid")
    s, c = sensor["body"], cih["body"]
    if (
        c.get("spec") != "innovulis/cih-local-evidence/v1"
        or c.get("source_mode") != "SYNTHETIC_SIMULATOR"
        or s.get("source_tier") != "SYNTHETIC_SIMULATOR"
        or c.get("sensor_evidence_hash") != sensor["receipt_hash"]
        or c.get("verified_device_pubkey") != device_pub
        or c.get("device_id") != s.get("device_id")
        or c.get("sequence") != s.get("sequence")
        or c.get("measurement") != s.get("measurement")
        or c.get("unit") != s.get("unit")
        or c.get("previous_state_commitment") != GENESIS_STATE
        or s.get("sequence") != 1
    ):
        raise ValueError("CIH source linkage or sequence invalid")
    expected = digest(
        b"innovulis-cih-state-v1:" +
        bytes.fromhex(GENESIS_STATE[7:]) +
        bytes.fromhex(sensor["receipt_hash"][7:])
    )
    if c.get("state_commitment") != expected:
        raise ValueError("CIH state commitment mismatch")


def formal_predicates(sensor_value: int) -> tuple[str, list[str], str]:
    decl = "(declare-const observed_centi Int)"
    axioms = ["(= observed_centi " + str(sensor_value) + ")"]
    hypothesis = "(and (<= 200 observed_centi) (<= observed_centi 800))"
    return decl, axioms, hypothesis


def generate_qow(
    sensor: dict, cih: dict, qow_key: Ed25519PrivateKey
) -> dict:
    decl, axioms, hypothesis = formal_predicates(sensor["body"]["measurement"])
    engine = TruthculatorV2(qow_key, "SYNTHETIC-CIH-QOW")
    qow = engine.compute(
        "DEMO_STORAGE_TEMPERATURE_POLICY",
        "Synthetic sensor input and CIH record committed to this mathematical policy check",
        decl, axioms, hypothesis,
    )
    # Bind provenance and policy into the signed QoW body.
    qow["body"]["input_evidence"] = {
        "sensor_event_sha256": sensor["receipt_hash"],
        "cih_receipt_sha256": cih["receipt_hash"],
        "policy_sha256": digest(canonical(POLICY)),
        "source_tier": "SYNTHETIC_SIMULATOR",
    }
    raw = canonical(qow["body"])
    qow["receipt_hash"] = digest(raw)
    qow["signature"] = qow_key.sign(raw).hex()
    return qow


def verify_bound_qow(
    qow: dict, sensor: dict, cih: dict, pinned_qow_pub: str
) -> None:
    if not verify_receipt(qow, pinned_qow_pub).get("ok"):
        raise ValueError("QoW signature or signer key invalid")
    body = qow["body"]
    if body.get("claim_id") != "DEMO_STORAGE_TEMPERATURE_POLICY":
        raise ValueError("unexpected claim identity")
    expected = {
        "sensor_event_sha256": sensor["receipt_hash"],
        "cih_receipt_sha256": cih["receipt_hash"],
        "policy_sha256": digest(canonical(POLICY)),
        "source_tier": "SYNTHETIC_SIMULATOR",
    }
    if body.get("input_evidence") != expected:
        raise ValueError("signed QoW provenance is not bound to sensor/CIH")
    decl, axioms, hyp = formal_predicates(sensor["body"]["measurement"])
    if (body.get("declarations"), body.get("axioms"), body.get("hypothesis")) != (decl, axioms, hyp):
        raise ValueError("signed QoW predicates diverge from approved policy")
    rechecked = independent_check(qow, pinned_qow_pub)
    if not rechecked.get("ok") or rechecked.get("verdict") != "PROVEN_TRUE":
        raise ValueError("fresh independent Z3 policy check failed")


def verify_pop(
    domain: DomainReceipt, master: dict, qow: dict
) -> None:
    if not verify_domain(domain):
        raise ValueError("signed PoP domain invalid")
    if domain.body.get("domain") != "QUANTUM_OF_WORK" or domain.body.get("state") != "VERIFIED_PROCESS":
        raise ValueError("PoP domain incomplete")
    if domain.body.get("payload", {}).get("qow", {}).get("qow_receipt_hash") != qow["receipt_hash"]:
        raise ValueError("PoP evidence does not reference QoW receipt")
    body = master["body"]
    if (
        body.get("state") != "VERIFIED_PROCESS"
        or body.get("merkle_root") != pop_merkle([domain])
        or body.get("domains_count") != 1
        or body.get("domain_receipts") != [asdict(domain)]
        or master.get("master_receipt_id") != pop_sha(pop_canonical(body))
    ):
        raise ValueError("PoP aggregate Merkle link invalid")
    signer = body.get("signer", "").split(":", 1)
    if len(signer) != 2 or signer[0] != "ed25519":
        raise ValueError("PoP aggregate signer malformed")
    if not pop_verify(signer[1], body, master["signature"]):
        raise ValueError("PoP aggregate signature invalid")


def create_carrier(
    qow: dict, sensor: dict, cih: dict, domain: DomainReceipt,
    master: dict, carrier_key: Ed25519PrivateKey,
) -> dict:
    return signed_object(
        {
            "spec": "ipqr/synthetic-sensor-cih-qow-pop/v1",
            "source_mode": "SYNTHETIC_SIMULATOR",
            "qow_receipt": qow,
            "sensor_event_sha256": sensor["receipt_hash"],
            "cih_receipt_sha256": cih["receipt_hash"],
            "pop_domain_receipt_id": domain.receipt_id,
            "pop_master_receipt_id": master["master_receipt_id"],
            "pop_merkle_root": master["body"]["merkle_root"],
            "does_not_prove": [
                "smartphone photo accepted",
                "sensor physical authenticity",
                "safe medical dosing or FDA compliance",
            ],
        },
        carrier_key,
    )


def verify_carrier(
    carrier: dict, pinned_carrier_key: str, sensor: dict, cih: dict,
    qow: dict, domain: DomainReceipt, master: dict,
) -> None:
    if not verify_signed_object(carrier, pinned_carrier_key):
        raise ValueError("carrier signature invalid")
    b = carrier["body"]
    if b.get("spec") != "ipqr/synthetic-sensor-cih-qow-pop/v1" or b.get("source_mode") != "SYNTHETIC_SIMULATOR":
        raise ValueError("carrier schema invalid")
    expected = {
        "qow_receipt": qow,
        "sensor_event_sha256": sensor["receipt_hash"],
        "cih_receipt_sha256": cih["receipt_hash"],
        "pop_domain_receipt_id": domain.receipt_id,
        "pop_master_receipt_id": master["master_receipt_id"],
        "pop_merkle_root": master["body"]["merkle_root"],
    }
    if any(b.get(k) != v for k, v in expected.items()):
        raise ValueError("carrier has invalid references")


def execute_pipeline(output_dir: str | Path, value_centi: int = 500) -> dict:
    target = Path(output_dir)
    target.mkdir(parents=True, exist_ok=True)
    sensor_key, cih_key = Ed25519PrivateKey.generate(), Ed25519PrivateKey.generate()
    qow_key, carrier_key = Ed25519PrivateKey.generate(), Ed25519PrivateKey.generate()
    device_pub = public_key_hex(sensor_key)
    cih_pub = public_key_hex(cih_key)
    qow_pub = public_key_hex(qow_key)
    carrier_pub = public_key_hex(carrier_key)

    sensor = synthetic_sensor_event(sensor_key, value_centi)
    hub = LocalCIH(cih_key, device_pub)
    cih = hub.ingest(sensor)
    validate_cih(sensor, cih, device_pub, cih_pub)
    qow = generate_qow(sensor, cih, qow_key)
    verify_bound_qow(qow, sensor, cih, qow_pub)

    # The callback performs a fresh Z3 execution on actual QoW source.
    domain = asyncio.run(qow_domain_receipt(
        qow, qow_pub, lambda receipt: independent_check(receipt, qow_pub)
    ))
    master = pop_aggregate([domain])
    verify_pop(domain, master, qow)

    carrier = create_carrier(qow, sensor, cih, domain, master, carrier_key)
    image_path = target / "physical_qow_ipqr.png"
    optical_stats = optical_encode(carrier, str(image_path))
    recovered = optical_decode(str(image_path))
    verify_carrier(recovered, carrier_pub, sensor, cih, qow, domain, master)

    public_evidence = {
        "spec": "innovulis/physical-qow-e2e-smoke/v1",
        "evidence_tier": "SYNTHETIC_SIGNED_SOFTWARE",
        "sensor": sensor,
        "cih": cih,
        "qow": qow,
        "pop_domain": asdict(domain),
        "pop_master": master,
        "ipqr_carrier": carrier,
        "trusted_public_keys": {
            "sensor": device_pub, "cih": cih_pub,
            "qow": qow_pub, "carrier": carrier_pub,
        },
        "optical": optical_stats,
        "gates": {
            "signed_simulated_sensor": "PASS",
            "local_cih_verification": "PASS",
            "independent_z3": "PASS",
            "signed_qow": "PASS",
            "signed_pop_merkle": "PASS",
            "registered_png_ipqr": "PASS",
            "real_physical_sensor": "NOT_VERIFIED",
            "phone_camera_print": "NOT_VERIFIED",
            "calibration": "NOT_VERIFIED",
            "clinical_safety": "NOT_VERIFIED",
            "TEE_ZK_RFC3161": "NOT_IMPLEMENTED",
        },
        "status": "ACCEPT_SYNTHETIC_PHYSICAL_TO_QOW_POP_PIPELINE",
    }
    (target / "physical_qow_smoke.json").write_text(json.dumps(public_evidence, indent=2))
    print(json.dumps({
        "status": public_evidence["status"],
        "sensor_event_hash": sensor["receipt_hash"],
        "cih_receipt_hash": cih["receipt_hash"],
        "qow_receipt_hash": qow["receipt_hash"],
        "pop_master_receipt_id": master["master_receipt_id"],
        "pop_merkle_root": master["body"]["merkle_root"],
        "optical": optical_stats, "gates": public_evidence["gates"]
    }, indent=2))
    return public_evidence


if __name__ == "__main__":
    execute_pipeline("artifacts/physical_qow")
