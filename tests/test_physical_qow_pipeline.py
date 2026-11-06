"""Negative and positive tests for the synthetic physical-to-trust fabric bridge."""
import asyncio
import copy
import tempfile
import unittest
from pathlib import Path

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from integrations.physical_qow_pipeline import (
    LocalCIH, generate_qow, public_key_hex, signed_object, synthetic_sensor_event,
    validate_cih, verify_bound_qow, verify_signed_object, verify_pop, verify_carrier,
    create_carrier, execute_pipeline, formal_predicates,
)
from integrations.qow_pop_bridge import qow_domain_receipt
from proof.parallel_pop import aggregate as pop_aggregate
from qow.truthculator import canonical, digest
from qow.independent_verifier import independent_check


class PhysicalQoWPipelineTests(unittest.TestCase):
    def setUp(self):
        self.device = Ed25519PrivateKey.generate()
        self.cih_key = Ed25519PrivateKey.generate()
        self.qow_key = Ed25519PrivateKey.generate()
        self.carrier_key = Ed25519PrivateKey.generate()
        self.device_pub = public_key_hex(self.device)
        self.cih_pub = public_key_hex(self.cih_key)
        self.qow_pub = public_key_hex(self.qow_key)
        self.carrier_pub = public_key_hex(self.carrier_key)
        self.sensor = synthetic_sensor_event(self.device, 500)
        self.hub = LocalCIH(self.cih_key, self.device_pub)
        self.cih = self.hub.ingest(self.sensor)

    def mint(self):
        return generate_qow(self.sensor, self.cih, self.qow_key)

    def test_authentic_synthetic_sensor(self):
        self.assertTrue(verify_signed_object(self.sensor, self.device_pub))
        self.assertTrue(verify_signed_object(self.cih, self.cih_pub))

    def test_sensor_tamper_rejected(self):
        forged = copy.deepcopy(self.sensor)
        forged["body"]["measurement"] = 600
        with self.assertRaises(ValueError):
            LocalCIH(self.cih_key, self.device_pub).ingest(forged)

    def test_wrong_device_pin_rejected(self):
        wrong = public_key_hex(Ed25519PrivateKey.generate())
        with self.assertRaises(ValueError):
            LocalCIH(self.cih_key, wrong).ingest(self.sensor)

    def test_sequence_replay_rejected(self):
        with self.assertRaises(ValueError):
            self.hub.ingest(self.sensor)

    def test_sequence_gap_rejected(self):
        skipped = synthetic_sensor_event(self.device, 500, 4)
        with self.assertRaises(ValueError):
            self.hub.ingest(skipped)

    def test_cih_record_tamper_rejected(self):
        changed = copy.deepcopy(self.cih)
        changed["body"]["state_commitment"] = "sha256:" + "a" * 64
        with self.assertRaises(ValueError):
            validate_cih(self.sensor, changed, self.device_pub, self.cih_pub)

    def test_real_z3_policy_true(self):
        receipt = self.mint()
        self.assertEqual(receipt["body"]["verdict"], "PROVEN_TRUE")
        verify_bound_qow(receipt, self.sensor, self.cih, self.qow_pub)

    def test_real_z3_policy_out_of_range_fail_closed(self):
        sensor = synthetic_sensor_event(self.device, 900)
        cih = LocalCIH(self.cih_key, self.device_pub).ingest(sensor)
        receipt = generate_qow(sensor, cih, self.qow_key)
        self.assertEqual(receipt["body"]["verdict"], "REFUTED_FALSE")
        with self.assertRaises(ValueError):
            verify_bound_qow(receipt, sensor, cih, self.qow_pub)

    def test_qow_policy_mismatch_rejected_even_with_valid_signature(self):
        receipt = self.mint()
        receipt["body"]["hypothesis"] = "(> observed_centi -100)"
        raw = canonical(receipt["body"])
        receipt["receipt_hash"] = digest(raw)
        receipt["signature"] = self.qow_key.sign(raw).hex()
        with self.assertRaises(ValueError):
            verify_bound_qow(receipt, self.sensor, self.cih, self.qow_pub)

    def test_pop_merkle_and_signature(self):
        receipt = self.mint()
        domain = asyncio.run(qow_domain_receipt(
            receipt, self.qow_pub, lambda r: independent_check(r, self.qow_pub)
        ))
        master = pop_aggregate([domain])
        verify_pop(domain, master, receipt)
        tampered = copy.deepcopy(master)
        tampered["body"]["merkle_root"] = "sha256:" + "b" * 64
        with self.assertRaises(ValueError):
            verify_pop(domain, tampered, receipt)

    def test_forged_carrier_rejected(self):
        receipt = self.mint()
        domain = asyncio.run(qow_domain_receipt(
            receipt, self.qow_pub, lambda r: independent_check(r, self.qow_pub)
        ))
        master = pop_aggregate([domain])
        carrier = create_carrier(
            receipt, self.sensor, self.cih, domain, master, self.carrier_key
        )
        carrier["body"]["pop_merkle_root"] = "sha256:" + "a" * 64
        with self.assertRaises(ValueError):
            verify_carrier(
                carrier, self.carrier_pub, self.sensor, self.cih,
                receipt, domain, master,
            )

    def test_end_to_end_optical_payload(self):
        with tempfile.TemporaryDirectory() as folder:
            evidence = execute_pipeline(folder)
            self.assertEqual(
                evidence["status"],
                "ACCEPT_SYNTHETIC_PHYSICAL_TO_QOW_POP_PIPELINE",
            )
            self.assertEqual(evidence["gates"]["registered_png_ipqr"], "PASS")
            self.assertEqual(evidence["gates"]["real_physical_sensor"], "NOT_VERIFIED")
            self.assertTrue((Path(folder) / "physical_qow_ipqr.png").exists())
            self.assertTrue((Path(folder) / "physical_qow_smoke.json").exists())


if __name__ == "__main__":
    unittest.main()
