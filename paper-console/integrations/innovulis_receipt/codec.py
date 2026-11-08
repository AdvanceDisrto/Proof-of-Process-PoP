"""Strict size-limited canonical JSON profile and compact ipQR v1 carrier.

This is our own specified canonical profile, NOT RFC 8785/JCS. Inputs must
conform exactly to the schema. NaN, duplicate JSON keys, floats and non-UTF8
wire encodings are invalid for this v1 profile. Large blobs are not printable.
"""
from __future__ import annotations
import base64
import hashlib
import json
import zlib
from typing import Any

MAX_WIRE_BYTES = 65536
MAX_QR_TEXT_BYTES = 3000
QR_PREFIX = "ipqr1:"


class FormatError(ValueError):
    pass


def _check_json(obj: Any, depth: int = 0) -> None:
    if depth > 20:
        raise FormatError("object nesting exceeds 20")
    if obj is None or type(obj) in (bool, int, str):
        if type(obj) is int and abs(obj) > (2**53 - 1):
            raise FormatError("integer outside portable JSON range")
        if isinstance(obj, str) and len(obj) > 32768:
            raise FormatError("oversized text field")
        return
    if type(obj) is list:
        if len(obj) > 128:
            raise FormatError("oversized array")
        for v in obj:
            _check_json(v, depth + 1)
        return
    if type(obj) is dict:
        if len(obj) > 64 or any(type(k) is not str for k in obj):
            raise FormatError("invalid object keys")
        for v in obj.values():
            _check_json(v, depth + 1)
        return
    raise FormatError("unsupported canonical JSON type")


def canonical(obj: Any) -> bytes:
    _check_json(obj)
    blob = json.dumps(obj, sort_keys=True, ensure_ascii=True,
                      allow_nan=False, separators=(",", ":")).encode("ascii")
    if len(blob) > MAX_WIRE_BYTES:
        raise FormatError("oversized document")
    return blob


def _no_duplicates(pairs):
    result = {}
    for k, v in pairs:
        if k in result:
            raise FormatError("duplicate JSON key: " + k[:50])
        result[k] = v
    return result


def parse_json(blob: bytes | str):
    if isinstance(blob, str):
        blob = blob.encode("utf-8", errors="strict")
    if len(blob) > MAX_WIRE_BYTES:
        raise FormatError("oversized input")
    try:
        obj = json.loads(blob, object_pairs_hook=_no_duplicates,
                         parse_constant=lambda _: (_ for _ in ()).throw(FormatError("NaN disallowed")))
        canonical(obj)
        return obj
    except (UnicodeError, json.JSONDecodeError, TypeError, OverflowError) as err:
        raise FormatError("malformed JSON") from err


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _pack_qr(packet: dict) -> bytes:
    """QR-only compact, typed binary profile. Signed bytes remain canonical JSON.

    Binary encoding is *not* an additional signature. Unknown fields are
    rejected before packing and after unpacking.
    """
    import msgpack
    from .schema import validate_packet
    validate_packet(packet)
    r = packet["receipt"]
    if sha256(canonical(r["claim"])) != r["claim_sha256"]:
        raise FormatError("refusing to normalize a malformed signed claim into a printable QR")
    row = [r["issuer_id"], r["issuer_key_id"], r["subject"],
           r["claim"]["observed"], r["claim"]["limit"], r["claim"]["unit"],
           r["verdict"], r["issued_at"], r["observed_at"], r["expires_at"],
           bytes.fromhex(r["nonce_hex"]),
           [[e["name"], bytes.fromhex(e["sha256"])] for e in r["evidence_manifest"]],
           bytes.fromhex(r["evidence_root"]), bytes.fromhex(r["witness_set_root"]),
           r["responsible_id"], r["energy_microjoules"]]
    compact = [1, row, bytes.fromhex(packet["issuer_signature"]),
               bytes.fromhex(packet["engineer_signature"]),
               [[w["id"], bytes.fromhex(w["signature"])] for w in packet["witness_signatures"]]]
    return msgpack.packb(compact, use_bin_type=True)


def _unpack_qr(raw: bytes) -> dict:
    import msgpack
    from .schema import validate_packet
    try:
        obj = msgpack.unpackb(raw, raw=False, strict_map_key=True,
                              max_str_len=MAX_WIRE_BYTES,
                              max_bin_len=MAX_WIRE_BYTES, max_array_len=128, max_map_len=64)
        if type(obj) is not list or len(obj) != 5 or obj[0] != 1:
            raise FormatError("unknown ipQR binary profile")
        _, row, issuer_sig, engineer_sig, signed_witnesses = obj
        if type(row) is not list or len(row) != 16:
            raise FormatError("invalid QR compact receipt layout")
        def raw_hex(value, n):
            if type(value) is not bytes or len(value) != n:
                raise FormatError("invalid binary signature or commitment")
            return value.hex()
        (issuer_id, issuer_key_id, subject, observed, limit, unit,
         verdict, issued, observation, expiry, nonce, entries, evidence_root,
         witnesses_root, engineer_id, energy) = row
        if type(entries) is not list:
            raise FormatError("invalid binary evidence entries")
        manifest = []
        for item in entries:
            if type(item) is not list or len(item) != 2:
                raise FormatError("invalid binary manifest row")
            manifest.append({"name": item[0], "sha256": raw_hex(item[1], 32)})
        if type(signed_witnesses) is not list:
            raise FormatError("invalid binary witness set")
        signed = []
        for item in signed_witnesses:
            if type(item) is not list or len(item) != 2:
                raise FormatError("invalid binary witness row")
            signed.append({"id": item[0], "signature": raw_hex(item[1], 64)})
        claim = {"kind": "integer_lte", "observed": observed, "limit": limit, "unit": unit}
        receipt = {"schema": "ipqr-receipt/v1", "issuer_id": issuer_id,
                   "issuer_key_id": issuer_key_id, "subject": subject,
                   "claim": claim, "claim_sha256": sha256(canonical(claim)),
                   "verdict": verdict, "issued_at": issued, "observed_at": observation,
                   "expires_at": expiry, "nonce_hex": raw_hex(nonce, 16),
                   "evidence_manifest": manifest, "evidence_root": raw_hex(evidence_root, 32),
                   "witness_set_root": raw_hex(witnesses_root, 32),
                   "responsible_id": engineer_id, "energy_microjoules": energy,
                   "time_basis": "ISSUER_CLOCK_UNTRUSTED"}
        packet = {"schema": "ipqr-packet/v1", "receipt": receipt,
                  "issuer_signature": raw_hex(issuer_sig, 64),
                  "engineer_signature": raw_hex(engineer_sig, 64),
                  "witness_signatures": signed}
        validate_packet(packet)
        return packet
    except (TypeError, ValueError, OverflowError, KeyError, IndexError,
            msgpack.exceptions.ExtraData, msgpack.exceptions.FormatError,
            msgpack.exceptions.StackError, msgpack.exceptions.OutOfData) as err:
        raise FormatError("corrupted QR compact receipt") from err


def encode_qr_text(packet: dict) -> str:
    # This encoding is specifically ipqr1 msgpack/zlib/b64url. It is not an
    # arbitrary object or URL to an issuer-controlled service.
    frame = QR_PREFIX + base64.urlsafe_b64encode(
        zlib.compress(_pack_qr(packet), 9)).decode("ascii").rstrip("=")
    if len(frame) > MAX_QR_TEXT_BYTES:
        raise FormatError("receipt too large for portable single-QR profile")
    return frame


def decode_qr_text(text: str) -> dict:
    if not isinstance(text, str) or not text.startswith(QR_PREFIX) or len(text) > MAX_QR_TEXT_BYTES:
        raise FormatError("unsupported or oversized ipQR frame")
    chunk = text[len(QR_PREFIX):]
    if not chunk or any(c not in "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_" for c in chunk):
        raise FormatError("invalid base64url frame")
    try:
        data = base64.urlsafe_b64decode(chunk + "=" * (-len(chunk) % 4))
        obj = zlib.decompressobj()
        raw = obj.decompress(data, MAX_WIRE_BYTES + 1)
        if len(raw) > MAX_WIRE_BYTES or obj.unconsumed_tail or not obj.eof or obj.unused_data:
            raise FormatError("oversized or malformed compressed QR frame")
        return _unpack_qr(raw)
    except (ValueError, zlib.error, UnicodeError, OverflowError) as err:
        raise FormatError("corrupt compressed ipQR frame") from err

def read_json_file(path: str):
    from pathlib import Path
    with Path(path).open("rb") as f:
        data = f.read(MAX_WIRE_BYTES + 1)
    return parse_json(data)
