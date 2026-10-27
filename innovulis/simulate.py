"""Reproducible, visibly synthetic Alpha-1 demo. No physical sensor / engraving / transfer."""
from __future__ import annotations

import argparse
import hashlib
import json
import tempfile
from pathlib import Path

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives import serialization

from alil.router import Router, SOURCE_DOMAIN, MACHINE_DOMAIN, canonical, pub_hex, sha256, load_json
from alil.verify import verify_chain


def simulate(output: Path) -> dict:
    if output.exists() and any(output.iterdir()):
        raise FileExistsError("No overwrites: use an empty output directory")
    output.mkdir(parents=True, exist_ok=True)
    runtime = output / "runtime"
    runtime.mkdir()
    # NEVER persist secrets in a produced evidence artifact. Disposable keys live in memory.
    source = Ed25519PrivateKey.generate()
    machine = Ed25519PrivateKey.generate()
    registry = {"protocol": "ITM-TRUST-REGISTRY-v1", "keys": {"alpha-source-demo": {
        "role": "source", "source_id": "alpha-1-simulator", "active": True,
        "public_key_hex": pub_hex(source)}}}
    registry_raw = canonical(registry)
    registry_path = runtime / "registry.json"
    registry_path.write_bytes(registry_raw)
    # key file is ephemeral and removed before output is returned
    with tempfile.TemporaryDirectory(prefix="alpha1-demo-keys-") as private_dir:
        keypath = Path(private_dir) / "machine.raw"
        keypath.write_bytes(machine.private_bytes(serialization.Encoding.Raw, serialization.PrivateFormat.Raw,
                                                 serialization.NoEncryption()))
        keypath.chmod(0o600)
        engine = Router(runtime, registry_path, keypath, "alpha-machine-demo", sha256(registry_raw))
        raw_intent = {"kind": "ITM-ALPHA1-SIMULATED-INTENT-v1", "action": "DEMO_TRANSFER_ONLY",
                      "amount_minor": 10000, "currency": "DEMO", "to": "EXAMPLE_RECIPIENT",
                      "operator_authority": "NOT_ATTESTED", "intent_approved": False,
                      "physical_sensor_data": "SIMULATED", "secure_time_attested": False}
        receipt = {"protocol": "ITM-INGRESS-RECEIPT-v1", "source_id": "alpha-1-simulator",
                   "receipt_id": "alpha1-genesis-demo", "key_id": "alpha-source-demo",
                   "body": raw_intent}
        receipt["signature_hex"] = source.sign(SOURCE_DOMAIN + canonical(receipt)).hex()
        (runtime / "inbox").mkdir(exist_ok=True)
        (runtime / "inbox" / "alpha1-genesis-demo.json").write_bytes(canonical(receipt) + b"\n")
        stats = engine.cycle_once()
        if stats["ACCEPTED"] != 1:
            raise RuntimeError("demo source receipt not accepted")
        evidence = verify_chain(runtime / "records", pub_hex(machine))
        event = load_json((runtime / "records" / "000000000001.json").read_bytes())
    outcome = {
       "protocol": "ITM-ALPHA1-DEMO-EXECUTION-v1", "simulated": True,
       "signing_keys": "THROWAWAY_EPHEMERAL_DEMO", "physical_device_present": False,
       "telemetry_measured": False, "substrate_engraved": False, "money_transferred": False,
       "legal_or_financial_rights_changed": False, "biometric_verification": False,
       "causal_graph_hidden_confounders_ruled_out": False,
       "receipt_source_signature_verified": True, "machine_chain_signature_verified": True,
       "machine_public_key_ed25519": pub_hex(machine),
       "source_registry_sha256": sha256(registry_raw),
       "machine_event_hash": sha256(MACHINE_DOMAIN + canonical(event["event"])),
       "machine_receipt": event, "verification": evidence,
    }
    (output / "ALPHA1_DEMONSTRATION.json").write_bytes(canonical(outcome) + b"\n")
    (output / "README.txt").write_text(
      "SIMULATED DATA ONLY. No hardware fabricated, no sapphire engraved, no funds sent.\n"
      "Source & machine signatures verify mathematical integrity with demo keys.\n"
      "No time, identity, sensor, legal, or physical truth independently proven.\n")
    return outcome


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--out", type=Path, default=Path("alpha1-demo-output"))
    args = p.parse_args()
    x = simulate(args.out)
    print(json.dumps({k:x[k] for k in ["protocol", "simulated", "physical_device_present", "money_transferred", "machine_event_hash"]}, indent=2))
