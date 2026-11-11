import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch
from tools.amd_external_gate_probe import GATES, probe

class ReadinessTests(unittest.TestCase):
    def test_eight_external_gates_fail_closed(self):
        record = probe()
        self.assertEqual(len(GATES), 8)
        self.assertFalse(record['external_activated'])
        self.assertTrue(all(v.startswith('PENDING') for v in record['gates'].values()))

    def test_no_false_amd_gpu_claim_without_device(self):
        with tempfile.TemporaryDirectory() as temp:
            with patch('tools.amd_external_gate_probe.shutil.which', return_value=None):
                record = probe(Path(temp))
        self.assertFalse(record['amd']['kfd_exists'])
        self.assertFalse(record['amd']['dri_exists'])
        self.assertFalse(record['amd']['amd_smi_present'])
        self.assertEqual(record['amd']['actual_amd_gpu_execution'], 'NOT_PERFORMED')

    def test_has_explicit_nonproofs(self):
        self.assertGreaterEqual(len(probe()['does_not_prove']), 3)

if __name__ == '__main__':
    unittest.main()
