import hashlib, json
from sovereign_cpu.receipt import build_receipt, canonical_json
from sovereign_cpu.toy_ssm import run_smoke

def test_cpu_ssm_is_deterministic(): assert run_smoke([1,2,3,4,5]) == run_smoke([1,2,3,4,5])

def test_iproof_receipt_binds_model_and_output(tmp_path,monkeypatch):
    model=tmp_path/"model.gguf"; engine=tmp_path/"llama-cli"; model.write_bytes(b"model"); engine.write_bytes(b"engine")
    monkeypatch.setenv("IPROOF_KEY_PATH",str(tmp_path/"key.pem"))
    receipt,key=build_receipt(request="hello",response="world",model_path=model,engine_path=engine,cpu_threads=8,memory_bytes=1234,artifact_bytes=5,network_mode="LOCAL_ONLY_DECLARED",command="local")
    assert receipt["protocol"]=="IPROOF-v1"
    assert receipt["execution"]["artifact_sha256"]=="sha256:"+hashlib.sha256(b"model").hexdigest()
    assert receipt["execution"]["output_sha256"]=="sha256:"+hashlib.sha256(b"world").hexdigest()
    sig=bytes.fromhex(receipt.pop("signature")); key.public_key().verify(sig,canonical_json(receipt).encode())

def test_receipt_does_not_claim_truth_or_air_gap(tmp_path,monkeypatch):
    model=tmp_path/"model.gguf"; engine=tmp_path/"llama-cli"; model.write_bytes(b"m"); engine.write_bytes(b"e")
    monkeypatch.setenv("IPROOF_KEY_PATH",str(tmp_path/"key.pem"))
    receipt,_=build_receipt(request="x",response="y",model_path=model,engine_path=engine,cpu_threads=1,memory_bytes=0,artifact_bytes=1,network_mode="LOCAL_ONLY_DECLARED",command="local")
    text=json.dumps(receipt).lower(); assert "truth" not in text and "air-gap" not in text
