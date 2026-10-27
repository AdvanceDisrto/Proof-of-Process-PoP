#!/usr/bin/env python3
"""Fail-closed structural integrity checks for the UAA-1.0 *document*.

These checks establish presence/shape only, not cross-model compliance.
"""
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = ROOT / "standards" / "UAA-1.0.md"

class ProtocolChecks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = PROTOCOL.read_text(encoding="utf-8")

    def test_sections_present_in_order(self):
        matches = list(re.finditer(r"^## SECTION ([1-8]) — ", self.source, re.M))
        self.assertEqual([int(m.group(1)) for m in matches], list(range(1, 9)))

    def test_eight_accountability_requirements(self):
        section = self.source.split("## SECTION 3 —", 1)[1].split("## SECTION 4 —", 1)[0]
        self.assertEqual([int(n) for n in re.findall(r"^([1-8])\. ", section, re.M)], list(range(1, 9)))

    def test_receipt_fields(self):
        fields = ("MODEL", "PROVIDER", "MODEL VERSION", "DATE",
                  "USER REQUEST", "ACTIONS ACTUALLY EXECUTED", "TOOLS ACTUALLY USED",
                  "ARTIFACTS CREATED", "TESTS ACTUALLY RUN",
                  "DEPLOYMENTS INDEPENDENTLY CONFIRMED", "PROVES",
                  "DOES_NOT_PROVE", "UNFINISHED WORK", "UNVERIFIED CLAIMS",
                  "INDEPENDENT AUDIT", "CRYPTOGRAPHIC SIGNATURE",
                  "TEXTUAL ACKNOWLEDGMENT", "VERDICT")
        receipt = self.source.split("## SECTION 7 —", 1)[1].split("## SECTION 8 —", 1)[0]
        self.assertTrue(all(f"{field}:" in receipt for field in fields))

    def test_refuses_independent_audit_claim(self):
        self.assertIn("NOT AN INDEPENDENT AUDIT", self.source)
        self.assertIn("A receipt can record evidence.", self.source)
        self.assertIn("It cannot manufacture evidence.", self.source)
        self.assertIn("Do not present this acknowledgment as evidence of future compliance.", self.source)

    def test_no_placeholder_certificate(self):
        self.assertIn("TEXTUAL ACKNOWLEDGMENT", self.source)
        self.assertIn("Do not invent a successful execution or cryptographic signature.", self.source)

if __name__ == "__main__":
    unittest.main(verbosity=2)
