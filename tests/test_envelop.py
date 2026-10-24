from copy import deepcopy
from tools.envelop import Envelop, Content, verify, jcs, sha

def _contents():
    return [Content("a.json", "receipt", b'{"x":1}'), Content("b.log", "log", b"line\n")]

def _env(**kw):
    e = Envelop(Envelop.keypair())
    return e, e.seal(_contents(), purpose="test", **kw)

def test_seal_verify_roundtrip():
    e, env = _env()
    blobs = {c.path: c.data for c in _contents()}
    v = verify(env, blobs)
    assert v["ok"], v["errors"]
    assert v["physical_gate"] == "ACTION_REQUIRED"

def test_payload_tamper_detected():
    _, env = _env()
    blobs = {c.path: c.data for c in _contents()}
    blobs["a.json"] = b'{"x":2}'
    v = verify(env, blobs)
    assert not v["ok"] and any("content_hash_mismatch" in x for x in v["errors"])

def test_kind_relabel_breaks_manifest():
    _, env = _env()
    env2 = deepcopy(env)
    env2["contents"][0]["kind"] = "log"
    blobs = {c.path: c.data for c in _contents()}
    v = verify(env2, blobs)
    assert not v["ok"] and "manifest_mmr_root_mismatch" in v["errors"]

def test_signature_tamper_detected():
    _, env = _env()
    env["purpose"] = "edited"
    blobs = {c.path: c.data for c in _contents()}
    v = verify(env, blobs)
    assert not v["ok"] and any("signature_invalid" in x for x in v["errors"])

def test_presence_does_not_open_gate():
    _, env = _env(tee_quote="q", energy=1.0)
    assert env["physical_gate"] == "ACTION_REQUIRED"
    blobs = {c.path: c.data for c in _contents()}
    assert verify(env, blobs)["physical_gate"] == "ACTION_REQUIRED"

def test_gate_tamper_without_attestation_rejected():
    _, env = _env()
    attacker = Envelop(Envelop.keypair())
    forged = deepcopy(env)
    forged["physical_gate"] = "MEASURED_PASS"
    forged["issuer_pubkey"] = attacker.pub
    forged["from"] = attacker.pub
    body = {k: v for k, v in forged.items() if k not in ("signature", "envelop_sha256")}
    forged["signature"] = attacker._priv.sign(jcs(body)).hex()
    forged["envelop_sha256"] = sha(jcs(body))
    blobs = {c.path: c.data for c in _contents()}
    v = verify(forged, blobs)
    assert not v["ok"] and any("gate_mismatch" in x for x in v["errors"])

def test_attested_objects_open_gate():
    _, env = _env(
        tee_quote={"vendor_chain": ["AMD_SEV_SNP_ROOT_CA"], "measurement": "deadbeef"},
        energy={"joules": 1.0, "source": "signed:lab-a"},
    )
    blobs = {c.path: c.data for c in _contents()}
    v = verify(env, blobs)
    assert v["ok"] and v["physical_gate"] == "MEASURED_PASS"

def test_envelop_sha_tamper():
    _, env = _env()
    env["envelop_sha256"] = "sha256:" + "0" * 64
    blobs = {c.path: c.data for c in _contents()}
    assert not verify(env, blobs)["ok"]
