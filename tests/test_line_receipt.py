from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives import serialization
from core.line_receipt import create_human_receipt,verify_human_receipt
def test_line_receipt():
 k=ed25519.Ed25519PrivateKey.generate();r=create_human_receipt(execution_id="e",workflow_key="w",intent_hash="sha256:x",decision="APPROVE",actor="did:test",signer=k);pub=k.public_key().public_bytes(serialization.Encoding.Raw,serialization.PublicFormat.Raw).hex();assert verify_human_receipt(r,pub)
