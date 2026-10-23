import json
from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives import serialization
from core.identity import sign_root,verify_root
from core.process_bound_data import ProcessBoundData

def test_signed_idr_and_tamper():
 k=ed25519.Ed25519PrivateKey.generate();root=sign_root({"spec":"innovulis-idr/1.0","diagnostic_state":{"genesis_anchor":"GENESIS","founder_did":"did:innovulis:test"},"truth_boundary":{"physical_gate":"ACTION_REQUIRED"}},k);pub=k.public_key().public_bytes(serialization.Encoding.Raw,serialization.PublicFormat.Raw).hex();assert verify_root(root,pub)[0];root["truth_boundary"]["physical_gate"]="MEASURED_PASS";assert not verify_root(root,pub)[0]

def test_process_bound_roundtrip_and_tamper():
 p=ProcessBoundData();p.register_process("CREATE","did:test",1);sealed=p.seal_data(b"hello",b"x"*32);assert p.unseal_data(sealed,b"x"*32)==b"hello";bad=json.loads(json.dumps(sealed));bad["process_chain"][0]["actor"]="evil"
 try:p.unseal_data(bad,b"x"*32);assert False
 except ValueError as e:assert str(e).startswith("DEATH:")
