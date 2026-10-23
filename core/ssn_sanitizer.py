from __future__ import annotations

import hashlib
import hmac
import json
import re
import secrets
import time
from dataclasses import dataclass
from typing import Any

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

from core.line_receipt import verify_human_receipt

SPEC = "innovulis-ssn-privacy-boundary/1.0"
SSN_PATTERN = re.compile(r"(?<!\d)(?:\d{3}-\d{2}-\d{4}|\d{9})(?!\d)")


def canonical(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
    ).encode("utf-8")


@dataclass(frozen=True)
class SanitizedSSN:
    text: str
    token_map: dict[str, dict[str, Any]]
    receipt: dict[str, Any]


class SSNSanitizer:
    """Local privacy boundary: raw SSNs are consumed before any model/provider call."""

    def __init__(self, master_key: bytes):
        if len(master_key) != 32:
            raise ValueError("master_key must be exactly 32 bytes")
        self._master_key = master_key

    def _derive_key(self, execution_id: str, purpose: bytes) -> bytes:
        return HKDF(
            algorithm=hashes.SHA256(),
            length=32,
            salt=None,
            info=b"innovulis-ssn/v1:" + purpose + b":" + execution_id.encode("utf-8"),
        ).derive(self._master_key)

    def _encrypt(self, raw_ssn: str, token: str, execution_id: str) -> tuple[str, str, str]:
        nonce = secrets.token_bytes(12)
        aad = canonical({"spec": SPEC, "token": token, "execution_id": execution_id})
        ciphertext = AESGCM(self._derive_key(execution_id, b"encryption")).encrypt(
            nonce, raw_ssn.encode("ascii"), aad
        )
        commitment_key = self._derive_key(execution_id, b"commitment")
        commitment = hmac.new(
            commitment_key, raw_ssn.encode("ascii"), hashlib.sha256
        ).hexdigest()
        return nonce.hex(), ciphertext.hex(), commitment

    def extract_and_tokenize(self, text: str, execution_id: str) -> SanitizedSSN:
        """Return text containing only opaque tokens plus encrypted server-side metadata."""
        token_map: dict[str, dict[str, Any]] = {}
        pieces: list[str] = []
        cursor = 0
        for match in SSN_PATTERN.finditer(text):
            pieces.append(text[cursor : match.start()])
            token = f"[SSN_TOKEN_{secrets.token_hex(16)}]"
            nonce_hex, ciphertext_hex, commitment = self._encrypt(
                match.group(), token, execution_id
            )
            token_map[token] = {
                "spec": SPEC,
                "execution_id": execution_id,
                "nonce_hex": nonce_hex,
                "ciphertext_hex": ciphertext_hex,
                "value_commitment": "hmac-sha256:" + commitment,
            }
            pieces.append(token)
            cursor = match.end()
        pieces.append(text[cursor:])
        sanitized = "".join(pieces)

        receipt = {
            "spec": "innovulis-ssn-receipt/1.0",
            "execution_id": execution_id,
            "timestamp_utc_ns": time.time_ns(),
            "token_count": len(token_map),
            "token_ids": sorted(token_map),
            "sanitized_text_hash": "sha256:"
            + hashlib.sha256(sanitized.encode("utf-8")).hexdigest(),
            "proves": [
                "the local boundary replaced matched SSN-shaped values with opaque tokens",
                "the token payloads are authenticated-encrypted",
                "the model-facing text contains no matched raw SSN-shaped value",
            ],
            "does_not_prove": [
                "a formal zero-knowledge proof",
                "that unrelated application code cannot access the raw input",
                "that an upstream provider could not receive raw data through another path",
                "SSN ownership or SSA identity validation",
                "uncoerced human consent",
                "physical TPM-backed key custody",
            ],
            "physical_gate": "ACTION_REQUIRED",
            "disclosure": "timestamp_utc_ns is software clock evidence, not physical picosecond precision.",
        }
        return SanitizedSSN(sanitized, token_map, receipt)

    @staticmethod
    def reveal_intent_hash(*, execution_id: str, token: str) -> str:
        body = {
            "spec": SPEC,
            "execution_id": execution_id,
            "token": token,
            "action": "reveal_ssn",
        }
        return "sha256:" + hashlib.sha256(canonical(body)).hexdigest()

    def reveal_for_human(
        self,
        *,
        token: str,
        token_map: dict[str, dict[str, Any]],
        execution_id: str,
        approval_receipt: dict[str, Any],
        human_public_key_hex: str,
    ) -> str:
        """Decrypt only after a valid signed APPROVE receipt bound to this token/execution."""
        if token not in token_map:
            raise ValueError("SSN token not found")
        if not verify_human_receipt(approval_receipt, human_public_key_hex):
            raise ValueError("UNAUTHORIZED: invalid human approval receipt")
        body = approval_receipt["body"]
        if body.get("human_decision") != "APPROVE":
            raise ValueError("UNAUTHORIZED: reveal was not approved")
        expected = self.reveal_intent_hash(execution_id=execution_id, token=token)
        if body.get("execution_id") != execution_id or body.get("intent_hash") != expected:
            raise ValueError("UNAUTHORIZED: approval is not bound to this SSN reveal intent")

        payload = token_map[token]
        if payload.get("execution_id") != execution_id:
            raise ValueError("DEATH: token belongs to a different execution")
        aad = canonical({"spec": SPEC, "token": token, "execution_id": execution_id})
        try:
            raw = AESGCM(self._derive_key(execution_id, b"encryption")).decrypt(
                bytes.fromhex(payload["nonce_hex"]),
                bytes.fromhex(payload["ciphertext_hex"]),
                aad,
            )
        except Exception as exc:
            raise ValueError("DEATH: authenticated SSN decryption failed") from exc
        return raw.decode("ascii")
