"""Extract exact canonical, domain-separated signed bytes from a wire receipt.

This file does not generate or trust identity. C verifier rechecks the
SHA-256 receipt identifier and Ed25519 signature with OpenSSL on the target CPU.
"""
from __future__ import annotations
import argparse,json,pathlib
from integrations.hardware_neutral_receipt import DOMAIN,canonical

def export(receipt_path,output_dir):
    receipt=json.loads(pathlib.Path(receipt_path).read_bytes())
    if not isinstance(receipt,dict) or set(receipt)!={"body","receipt_id","signature","external_anchor"}:
        raise ValueError("RECEIPT_STRUCTURE")
    sig=receipt["signature"]
    if not isinstance(sig,dict) or sig.get("algorithm")!="Ed25519":
        raise ValueError("UNSUPPORTED_SIGNATURE_ALGORITHM")
    path=pathlib.Path(output_dir);path.mkdir(parents=True,exist_ok=True)
    (path/"message.bin").write_bytes(DOMAIN+canonical(receipt["body"]))
    for name,value in (("public_key.hex",sig["public_key_hex"]),
                       ("signature.hex",sig["signature_hex"]),
                       ("receipt_id.txt",receipt["receipt_id"])):
        if not isinstance(value,str) or not value.isascii() or "\n" in value:
            raise ValueError("INVALID_HEX_FIELD")
        (path/name).write_text(value,encoding="ascii")
if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--receipt",required=True);p.add_argument("--out",required=True)
    args=p.parse_args();export(args.receipt,args.out)
