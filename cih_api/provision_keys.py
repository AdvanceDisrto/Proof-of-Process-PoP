"""Generate a persistent CIH Ed25519 keypair once, without printing secrets.

Run from your cloned repo:
  .\\.venv\\Scripts\\python.exe -m cih_api.provision_keys

Result: %LOCALAPPDATA%\\iNNOVULIS\\CIH\\signing-keys.json on Windows.
The secret file must be protected as a credential and never added to Git.
No rotation, database deployment, or server configuration happens automatically.
"""
from __future__ import annotations

import base64
import getpass
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey


def default_destination() -> Path:
    parent = os.environ.get("LOCALAPPDATA")
    return (Path(parent) if parent else Path.home() / ".local" / "share") / "iNNOVULIS" / "CIH" / "signing-keys.json"


def prepare_pair() -> dict[str, str]:
    key = Ed25519PrivateKey.generate()
    private = key.private_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PrivateFormat.Raw,
        encryption_algorithm=serialization.NoEncryption(),
    )
    public = key.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    assert len(private) == len(public) == 32
    return {
        "CIH_ED25519_PRIVATE_KEY_B64": base64.b64encode(private).decode("ascii"),
        "CIH_ED25519_PUBLIC_KEY_B64": base64.b64encode(public).decode("ascii"),
        "key_id": "ed25519-sha256:" + hashlib.sha256(public).hexdigest()[:24],
    }


def write_once(path: Path, payload: dict[str, str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        raise FileExistsError("An existing CIH keypair was found. It will NOT be overwritten.")
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as out:
            json.dump(payload, out, indent=2, sort_keys=True)
            out.write("\n")
            out.flush()
            os.fsync(out.fileno())
        if sys.platform == "win32":
            principal = subprocess.check_output(["whoami"], text=True).strip()
            # Fail closed if Windows cannot restrict the newly created file.
            subprocess.run(
                ["icacls", str(path), "/inheritance:r", "/grant:r", principal + ":(F)"],
                check=True, capture_output=True, text=True,
            )
        else:
            path.chmod(0o600)
    except BaseException:
        path.unlink(missing_ok=True)
        raise


def main() -> None:
    path = default_destination()
    keys = prepare_pair()
    try:
        write_once(path, keys)
    except FileExistsError as exc:
        raise SystemExit(str(exc)) from exc
    print("Keypair created. Private key was NOT printed.")
    print("Secret file:", path)
    print("Public key fingerprint:", keys["key_id"])
    print("Next: copy both CIH_ED25519_*_B64 values into your approved Render secret store.")
    print("Do not post the file, store it in Git, or treat this receipt key as physical attestation.")


if __name__ == "__main__":
    main()
