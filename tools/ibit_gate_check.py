#!/usr/bin/env python3
"""Fail-closed validation of iBit run receipts. Stdlib only; no trust in embedded keys."""
import argparse, hashlib, json, pathlib, sys

def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode()

def verify_master(master, evidence_root):
    errors = []
    if master.get("schema") != "ibit/master-run/v1":
        errors.append("wrong master schema")
    if master.get("physical_gate") != "ACTION_REQUIRED":
        errors.append("physical_gate must remain ACTION_REQUIRED")
    if not master.get("does_not_prove"):
        errors.append("does_not_prove missing")
    artifacts = master.get("artifacts")
    if not isinstance(artifacts, list) or not artifacts:
        errors.append("no artifacts listed")
        artifacts = []
    seen = set()
    for item in artifacts:
        path = item.get("path", "")
        if not path or pathlib.PurePosixPath(path).is_absolute() or ".." in pathlib.PurePosixPath(path).parts or path in seen:
            errors.append("unsafe or duplicate artifact path")
            continue
        seen.add(path)
        file = evidence_root / path
        if not file.is_file():
            errors.append(f"missing artifact: {path}")
            continue
        raw = file.read_bytes()
        actual = "sha256:" + hashlib.sha256(raw).hexdigest()
        if actual != item.get("sha256"):
            errors.append(f"hash mismatch: {path}")
        if len(raw) != item.get("bytes"):
            errors.append(f"size mismatch: {path}")
    # Hash matching is necessary, never sufficient for accepting an Ed25519 signature.
    return {"verdict": "INTEGRITY_CHECK_PASSED_SIGNATURE_UNVERIFIED" if not errors else "REJECT", "errors": errors, "artifacts_checked": len(seen)}

def main():
    p = argparse.ArgumentParser()
    p.add_argument("evidence_dir", type=pathlib.Path)
    args = p.parse_args()
    try:
        master = json.loads((args.evidence_dir / "MASTER_RUN_RECEIPT.json").read_text())
        result = verify_master(master, args.evidence_dir)
    except Exception as exc:
        result = {"verdict": "REJECT", "errors": [str(exc)]}
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["verdict"] == "INTEGRITY_CHECK_PASSED_SIGNATURE_UNVERIFIED" else 1

if __name__ == "__main__":
    sys.exit(main())
