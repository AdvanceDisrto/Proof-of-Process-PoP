#!/usr/bin/env python3
"""Produce unsigned, auditable iPWA evidence bundle. No network or financial settlement."""
import hashlib,io,json,gzip,tarfile
from pathlib import Path
from datetime import datetime,timezone
root=Path(__file__).resolve().parents[1]
out=root/"ipwa-v2-dist";out.mkdir(exist_ok=True)
pwa=["index.html","verifier_bg.wasm","verifier.mjs","wasm-sha256.mjs","archive.mjs",
     "sw.js","manifest.webmanifest","icon.svg","icon-192.png","icon-512.png"]
entries={x:(root/"ipwa"/x).read_bytes() for x in pwa}
for name in ["DNS_RECEIPT","FED_DISBURSEMENT_RECEIPT","GLOBAL_LEDGER_RECEIPT"]:
    entries[name+".json"]=(root/"receipts"/(name+".json")).read_bytes()
for name in ["ITM-FED-DISBURSEMENT-v1","ITM-GLOBAL-LEDGER-v1"]:
    entries["schemas/"+name+".schema.json"]=(root/"schemas"/(name+".schema.json")).read_bytes()
entries["POP_SIGNED_RECEIPT.json"]=(root/"ipwa-demo"/"bundle.json").read_bytes()
digest=lambda b:"sha256:"+hashlib.sha256(b).hexdigest()
manifest={
 "protocol":"ITM-BUILD-MANIFEST-v2",
 "timestamp_utc":datetime.now(timezone.utc).isoformat(timespec="seconds"),
 "source_commit":None,
 "status":"LOCAL_CRYPTO_TESTS_ONLY_EXTERNAL_PROOFS_PENDING",
 "requires_itm_endpoint":False,
 "components":{"wasm_sha256":"BUILT","ed25519":"WEBCRYPTO","schemas":"STRUCTURAL_ONLY",
               "dns_receipt":"UNSIGNED_INTENT","hardware":"ACTION_REQUIRED",
               "bitcoin_anchor":"ACTION_REQUIRED","physical_actuation":"BLOCKED",
               "federal_settlement":"BLOCKED","ios_airplane_mode":"UNTESTED"},
 "files":{name:{"sha256":digest(data),"size_bytes":len(data)} for name,data in sorted(entries.items())}
}
entries["BUILD_MANIFEST.json"]=(json.dumps(manifest,indent=2,sort_keys=True)+"\n").encode()
buffer=io.BytesIO()
with tarfile.open(fileobj=buffer,mode="w",format=tarfile.USTAR_FORMAT) as tf:
    for name,data in sorted(entries.items()):
        info=tarfile.TarInfo(name);info.size=len(data);info.mode=0o644;info.mtime=0;info.uid=0;info.gid=0
        tf.addfile(info,io.BytesIO(data))
destination=out/"public-evidence.tar.gz"
with destination.open("wb") as f:
    with gzip.GzipFile(filename="",fileobj=f,mode="wb",mtime=0,compresslevel=9) as g:g.write(buffer.getvalue())
(out/"BUILD_MANIFEST.json").write_bytes(entries["BUILD_MANIFEST.json"])
(out/"BUNDLE_SHA256.txt").write_text(digest(destination.read_bytes())+"  public-evidence.tar.gz\n")
(out/"demo-trust-registry.json").write_bytes((root/"ipwa-demo"/"registry.json").read_bytes())
print("PUBLIC_EVIDENCE_BUNDLE",destination,digest(destination.read_bytes()))
print("TRUST_REGISTRY_DEMO_ONLY; hardware_signature=false; bitcoin_anchor=false; settlement=false")
