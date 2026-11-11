"""iRECEIPT x86_64 -> arm64 -> x86_64 exchange (development CI).

Each step runs on its own machine and transports only JSON/evidence/public keys.
Public keys are provisionally pinned by the CI artifact handoff, not an independently
registered production trust root. No GPU/MCU, ML-DSA or hardware attestation.
"""
from __future__ import annotations
import argparse,json,platform,pathlib,sys
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives import serialization
from integrations.hardware_neutral_receipt import canonical,digest,observation,sign,verify

def architecture():
    value=platform.machine().lower()
    if value in ("x86_64","amd64"): return "x86_64"
    if value in ("aarch64","arm64"): return "arm64"
    raise RuntimeError("UNSUPPORTED_ARCHITECTURE:"+value)

def public_hex(key):
    return key.public_key().public_bytes(
        serialization.Encoding.Raw,serialization.PublicFormat.Raw).hex()

def save(directory,name,body):
    path=pathlib.Path(directory);path.mkdir(parents=True,exist_ok=True)
    (path/name).write_bytes(canonical(body))
def read(directory,name):
    return json.loads((pathlib.Path(directory)/name).read_bytes())
def load_bytes(directory,name):
    return (pathlib.Path(directory)/name).read_bytes()

def generate(out):
    if architecture()!="x86_64":raise RuntimeError("CPU_ORIGIN_REQUIRES_NATIVE_X86_64")
    payload=canonical({"task":"verify arithmetic definition of octet",
                       "device_architecture_reported":architecture(),
                       "operation":"compute_observation",
                       "source":"GITHUB_CI_DEVELOPMENT"})
    key=Ed25519PrivateKey.generate()
    body=observation(device_class="CPU",operation="compute_observation",
                     evidence_bytes=payload,request_id="cross-silicon-ci-intent-v1")
    receipt=sign(body,key.sign,public_hex(key))
    save(out,"cpu_receipt.json",receipt)
    (pathlib.Path(out)/"cpu_evidence.bin").write_bytes(payload)
    save(out,"cpu_key_pin.json",{"public_key_hex":public_hex(key),
         "pin_scope":"CI_ARTIFACT_HANDOFF_NOT_INDEPENDENT_PRODUCTION_TRUST"})
    return {"stage":"CPU_ORIGIN","architecture":architecture(),"receipt_id":receipt["receipt_id"]}

def edge_verify(source,out):
    if architecture()!="arm64":raise RuntimeError("EDGE_VERIFIER_REQUIRES_NATIVE_ARM64")
    cpu=read(source,"cpu_receipt.json")
    cpu_evidence=load_bytes(source,"cpu_evidence.bin")
    cpu_pin=read(source,"cpu_key_pin.json")["public_key_hex"]
    if not verify(cpu,{cpu_pin},cpu_evidence):raise RuntimeError("CPU_SIGNATURE_OR_EVIDENCE_INVALID")
    if cpu["body"]["parent"] is not None or cpu["body"]["operation"]!="compute_observation":
        raise RuntimeError("CPU_INTENT_POLICY_REJECTED")
    if json.loads(cpu_evidence).get("device_architecture_reported")!="x86_64":
        raise RuntimeError("CPU_ARCHITECTURE_CLAIM_INVALID")
    edge_data=canonical({"result":"CPU_RECEIPT_SIGNATURE_AND_EVIDENCE_MATCH",
                          "verified_receipt_id":cpu["receipt_id"],
                          "device_architecture_reported":architecture(),
                          "verification_scope":"DEVELOPMENT_INTEGRITY_ONLY"})
    key=Ed25519PrivateKey.generate()
    body=observation(device_class="CPU",operation="compute_observation",
                     evidence_bytes=edge_data,request_id="cross-silicon-ci-edge-v1",
                     parent=cpu["receipt_id"])
    edge=sign(body,key.sign,public_hex(key))
    save(out,"edge_receipt.json",edge)
    (pathlib.Path(out)/"edge_evidence.bin").write_bytes(edge_data)
    save(out,"edge_key_pin.json",{"public_key_hex":public_hex(key),
         "pin_scope":"CI_ARTIFACT_HANDOFF_NOT_INDEPENDENT_PRODUCTION_TRUST"})
    return {"stage":"EDGE_VERIFY","architecture":architecture(),
            "verified_receipt_id":cpu["receipt_id"],"receipt_id":edge["receipt_id"]}

def finalize(source,edge_dir,out):
    if architecture()!="x86_64":raise RuntimeError("FINAL_HUB_REQUIRES_NATIVE_X86_64")
    cpu=read(source,"cpu_receipt.json");edge=read(edge_dir,"edge_receipt.json")
    cpu_key=read(source,"cpu_key_pin.json")["public_key_hex"]
    edge_key=read(edge_dir,"edge_key_pin.json")["public_key_hex"]
    if cpu_key==edge_key:raise RuntimeError("ROLE_KEY_COLLISION")
    if not verify(cpu,{cpu_key},load_bytes(source,"cpu_evidence.bin")):
        raise RuntimeError("CPU_RECEIPT_INVALID")
    if not verify(edge,{edge_key},load_bytes(edge_dir,"edge_evidence.bin")):
        raise RuntimeError("EDGE_RECEIPT_INVALID")
    ed=json.loads(load_bytes(edge_dir,"edge_evidence.bin"))
    if (edge["body"]["parent"]!=cpu["receipt_id"]
        or ed.get("verified_receipt_id")!=cpu["receipt_id"]
        or ed.get("result")!="CPU_RECEIPT_SIGNATURE_AND_EVIDENCE_MATCH"
        or ed.get("device_architecture_reported")!="arm64"):
        raise RuntimeError("EDGE_PARENT_OR_CLAIM_INVALID")
    assessment={"schema":"ipqr/cross-silicon-ci-assessment/v1",
                "verdict":"CROSS_ARCH_DEVELOPMENT_INTEGRITY_PASS",
                "observed_ci_job_architectures":["x86_64","arm64","x86_64"],
                "receipt_ids":[cpu["receipt_id"],edge["receipt_id"]],
                "production_trust":"UNVERIFIED","gpu_execution":"NOT_EXECUTED",
                "mcu_execution":"NOT_EXECUTED","hardware_attestation":"NOT_PROVIDED",
                "key_pin_scope":"ARTIFACT_HANDOFF_ONLY","external_anchor":None}
    save(out,"cross_silicon_assessment.json",assessment)
    return assessment

def main():
    parser=argparse.ArgumentParser()
    sub=parser.add_subparsers(dest="stage",required=True)
    a=sub.add_parser("cpu-generate");a.add_argument("--out",required=True)
    b=sub.add_parser("arm-verify");b.add_argument("--source",required=True);b.add_argument("--out",required=True)
    c=sub.add_parser("cpu-finalize");c.add_argument("--source",required=True)
    c.add_argument("--edge",required=True);c.add_argument("--out",required=True)
    opts=parser.parse_args()
    if opts.stage=="cpu-generate":result=generate(opts.out)
    elif opts.stage=="arm-verify":result=edge_verify(opts.source,opts.out)
    else:result=finalize(opts.source,opts.edge,opts.out)
    print(json.dumps(result,sort_keys=True))
if __name__=="__main__":main()
