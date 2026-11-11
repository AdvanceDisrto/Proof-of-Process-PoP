"""Adversarial software tests ONLY: simulate register bytes and P-256 private key."""
import subprocess, unittest
from unittest.mock import patch
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec, utils
from hardware.physical import gates

class FakeBus:
    def __init__(self, values=None):
        self.reg={0xfe:0x4954,0xff:0x6022}
        self.reg.update(values or {})
    def read_word_data(self,address,register):return self.reg[register]

class PhysicalGateTests(unittest.TestCase):
    def test_identity_word_endianness(self):
        self.assertEqual(gates.ina226_word(0x4954),0x5449)
    def test_identity_word_wrong_types(self):
        for v in (-1,False,65536,"none",2.6):
            with self.assertRaises(gates.GatePending):gates.ina226_word(v)
    def test_ina226_known_registers_pass_as_unattested(self):
        r=gates.identify_ina226(FakeBus())
        self.assertFalse(r["hardware_authenticated"])
        self.assertEqual(r["registers"],"PASS_UNATTESTED")
    def test_ina226_wrong_manufacturer_rejected(self):
        with self.assertRaises(gates.GatePending):
            gates.identify_ina226(FakeBus({0xfe:0}))
    def test_ina226_wrong_die_rejected(self):
        with self.assertRaises(gates.GatePending):
            gates.identify_ina226(FakeBus({0xff:0}))
    def test_ina226_wrong_address_rejected(self):
        with self.assertRaises(gates.GatePending):
            gates.identify_ina226(FakeBus(),0x81)
    def test_p256_valid_signature_only_proves_key_possession(self):
        sk=ec.generate_private_key(ec.SECP256R1())
        pub=sk.public_key().public_bytes(serialization.Encoding.PEM,serialization.PublicFormat.SubjectPublicKeyInfo)
        def signer(d):return sk.sign(d,ec.ECDSA(utils.Prehashed(hashes.SHA256())))
        r=gates.challenge_signer(pub,signer)
        self.assertEqual(r["challenge_signature"],"PASS")
        self.assertEqual(r["gate"],"PENDING_INDEPENDENT_HARDWARE_ATTESTATION")
    def test_forged_p256_signature_rejected(self):
        sk=ec.generate_private_key(ec.SECP256R1())
        pub=sk.public_key().public_bytes(serialization.Encoding.PEM,serialization.PublicFormat.SubjectPublicKeyInfo)
        with self.assertRaises(gates.GatePending):
            gates.challenge_signer(pub,lambda d:b"invalid signature")
    def test_p256_384_curve_rejected(self):
        sk=ec.generate_private_key(ec.SECP384R1())
        pub=sk.public_key().public_bytes(serialization.Encoding.PEM,serialization.PublicFormat.SubjectPublicKeyInfo)
        self.assertFalse(gates.verify_p256_digest(pub,b"0"*32,b"1"*64))
    def test_p256_malformed_randomness_rejected(self):
        sk=ec.generate_private_key(ec.SECP256R1())
        pub=sk.public_key().public_bytes(serialization.Encoding.PEM,serialization.PublicFormat.SubjectPublicKeyInfo)
        with self.assertRaises(gates.GatePending):
            gates.challenge_signer(pub,lambda d:b"a",lambda n:b"only one byte")
    def test_p256_external_command_format_validation(self):
        with self.assertRaises(gates.GatePending):
            gates.signer_command("echo",b"invalid")
    def test_p256_external_command_missing_rejected(self):
        with self.assertRaises(gates.GatePending):
            gates.signer_command("/absolutely/missing/test-signer",b"unused")
    def test_no_hardware_success_claim_on_ci_runner(self):
        r=gates.readiness(i2c="/sys/not/a/real/i2c/bus")
        self.assertEqual(r["physical_acceptance"],"ACTION_REQUIRED")
        self.assertEqual(r["physical_printer"],"NOT_TESTED")
        self.assertEqual(r["atecc608c_hardware_signing"],"NOT_TESTED")
    def test_cli_readiness_no_write(self):
        with patch("builtins.print"):
            self.assertEqual(gates.main(["readiness"]),0)
    def test_cli_sensor_requires_operator_approval(self):
        with patch("builtins.print"):
            self.assertEqual(gates.main(["ina226","--shunt-ohms","0.1",
                                    "--calibration-id","lab","--device-id","pi"]),2)
    def test_cli_signer_requires_operator_approval(self):
        with patch("builtins.print"):
            self.assertEqual(gates.main(["p256-challenge","--binary","/bin/echo",
                                         "--trusted-pem","/tmp/a"]),2)
if __name__=="__main__":unittest.main()
