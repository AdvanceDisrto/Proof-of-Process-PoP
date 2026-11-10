"""CIH key provisioning tests: ensure private keys never change silently."""
import base64

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from cih_api.provision_keys import prepare_pair, write_once


def test_keypair_is_real_cryptographic_pair():
    values = prepare_pair()
    private = base64.b64decode(values["CIH_ED25519_PRIVATE_KEY_B64"], validate=True)
    public = base64.b64decode(values["CIH_ED25519_PUBLIC_KEY_B64"], validate=True)
    assert len(private) == len(public) == 32
    key = Ed25519PrivateKey.from_private_bytes(private)
    signature = key.sign(b"local-cih-integrity-probe")
    key.public_key().verify(signature, b"local-cih-integrity-probe")
    assert values["key_id"].startswith("ed25519-sha256:")


def test_keyfile_is_non_overwriting(tmp_path):
    path = tmp_path / "private" / "signing-keys.json"
    pair = prepare_pair()
    write_once(path, pair)
    assert path.is_file()
    assert "CIH_ED25519_PRIVATE_KEY_B64" in path.read_text(encoding="utf-8")
    with pytest.raises(FileExistsError):
        write_once(path, prepare_pair())
    assert path.exists()
