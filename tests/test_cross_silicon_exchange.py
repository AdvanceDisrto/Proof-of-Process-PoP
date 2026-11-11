import json,pathlib,tempfile,unittest
from unittest.mock import patch
from integrations import cross_silicon_exchange as exchange

class CrossSiliconExchangeTests(unittest.TestCase):
    def setUp(self):
        t=tempfile.TemporaryDirectory();self.addCleanup(t.cleanup)
        root=pathlib.Path(t.name)
        self.cpu=root/"cpu";self.arm=root/"arm";self.final=root/"final"
    def genesis(self):
        with patch.object(exchange,"architecture",return_value="x86_64"):
            exchange.generate(self.cpu)
    def edge(self):
        with patch.object(exchange,"architecture",return_value="arm64"):
            exchange.edge_verify(self.cpu,self.arm)
    def finalize(self):
        with patch.object(exchange,"architecture",return_value="x86_64"):
            return exchange.finalize(self.cpu,self.arm,self.final)
    def test_three_step_development_chain(self):
        self.genesis();self.edge()
        result=self.finalize()
        self.assertEqual(result["verdict"],"CROSS_ARCH_DEVELOPMENT_INTEGRITY_PASS")
        self.assertEqual(result["production_trust"],"UNVERIFIED")
        self.assertEqual(result["gpu_execution"],"NOT_EXECUTED")
    def test_cpu_evidence_tamper_is_rejected_by_edge(self):
        self.genesis()
        (self.cpu/"cpu_evidence.bin").write_bytes(b"corrupted")
        with patch.object(exchange,"architecture",return_value="arm64"):
            with self.assertRaises(RuntimeError):exchange.edge_verify(self.cpu,self.arm)
    def test_bad_cpu_key_pin_rejected(self):
        self.genesis()
        path=self.cpu/"cpu_key_pin.json"
        pin=json.loads(path.read_bytes());pin["public_key_hex"]="00"*32
        path.write_text(json.dumps(pin))
        with patch.object(exchange,"architecture",return_value="arm64"):
            with self.assertRaises(RuntimeError):exchange.edge_verify(self.cpu,self.arm)
    def test_edge_result_tamper_rejected_by_cpu(self):
        self.genesis();self.edge()
        (self.arm/"edge_evidence.bin").write_bytes(b"FAKE")
        with self.assertRaises(RuntimeError):self.finalize()
    def test_edge_parent_tamper_rejected(self):
        self.genesis();self.edge()
        path=self.arm/"edge_receipt.json";data=json.loads(path.read_bytes())
        data["body"]["parent"]="sha256:"+"0"*64;path.write_text(json.dumps(data))
        with self.assertRaises(RuntimeError):self.finalize()
    def test_edge_pin_ownership_rejected(self):
        self.genesis();self.edge()
        path=self.arm/"edge_key_pin.json"
        data=json.loads((self.cpu/"cpu_key_pin.json").read_bytes())
        path.write_text(json.dumps(data))
        with self.assertRaises(RuntimeError):self.finalize()
    def test_architecture_guard_at_origin(self):
        with patch.object(exchange,"architecture",return_value="arm64"):
            with self.assertRaises(RuntimeError):exchange.generate(self.cpu)
    def test_architecture_guard_at_edge(self):
        self.genesis()
        with patch.object(exchange,"architecture",return_value="x86_64"):
            with self.assertRaises(RuntimeError):exchange.edge_verify(self.cpu,self.arm)
    def test_architecture_guard_at_final(self):
        self.genesis();self.edge()
        with patch.object(exchange,"architecture",return_value="arm64"):
            with self.assertRaises(RuntimeError):exchange.finalize(self.cpu,self.arm,self.final)
if __name__=="__main__":unittest.main()
