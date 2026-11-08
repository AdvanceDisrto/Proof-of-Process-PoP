"""Strict v1 structural checks. Unknown fields fail closed."""
from __future__ import annotations
import re
from .codec import FormatError
from .crypto import check_hex

ID_RE = re.compile(r"^[A-Za-z0-9_.:-]{1,96}$")
FILENAME_RE = re.compile(r"^[A-Za-z0-9_.-]{1,100}$")


def shape(obj, keys, name):
    if type(obj) is not dict or set(obj) != set(keys):
        raise FormatError(name + ": unknown or missing fields")


def ident(s):
    if type(s) is not str or not ID_RE.fullmatch(s):
        raise FormatError("invalid identifier")


def uint(x, max_value=2**53 - 1):
    if type(x) is not int or not 0 <= x <= max_value:
        raise FormatError("invalid unsigned integer")


def integer(x, max_value=10**12):
    if type(x) is not int or not -max_value <= x <= max_value:
        raise FormatError("invalid signed integer")


def validate_receipt(receipt):
    shape(receipt, ("schema", "issuer_id", "issuer_key_id", "subject", "claim", "claim_sha256",
                    "verdict", "issued_at", "observed_at", "expires_at", "nonce_hex", "evidence_manifest",
                    "evidence_root", "witness_set_root", "responsible_id", "energy_microjoules", "time_basis"),
          "receipt")
    if receipt["schema"] != "ipqr-receipt/v1" or receipt["time_basis"] != "ISSUER_CLOCK_UNTRUSTED":
        raise FormatError("unsupported receipt profile")
    for key in ("issuer_id", "issuer_key_id", "subject", "responsible_id"):
        ident(receipt[key])
    shape(receipt["claim"], ("kind", "observed", "limit", "unit"), "claim")
    if receipt["claim"]["kind"] != "integer_lte":
        raise FormatError("unsupported claim semantics")
    integer(receipt["claim"]["observed"])
    integer(receipt["claim"]["limit"])
    ident(receipt["claim"]["unit"])
    for key in ("issued_at", "observed_at", "expires_at"):
        uint(receipt[key])
    if receipt["expires_at"] <= receipt["issued_at"] or receipt["observed_at"] > receipt["issued_at"]:
        raise FormatError("inconsistent receipt times")
    if receipt["verdict"] not in ("PROVEN_TRUE", "REFUTED_FALSE"):
        raise FormatError("unsupported verdict")
    for key in ("claim_sha256", "evidence_root", "witness_set_root"):
        check_hex(receipt[key])
    check_hex(receipt["nonce_hex"], 32)
    if receipt["energy_microjoules"] is not None:
        uint(receipt["energy_microjoules"])
    manifest = receipt["evidence_manifest"]
    if type(manifest) is not list or not 1 <= len(manifest) <= 8:
        raise FormatError("evidence manifest must have 1-8 entries")
    prev = ""
    for item in manifest:
        shape(item, ("name", "sha256"), "evidence manifest item")
        if type(item["name"]) is not str or not FILENAME_RE.fullmatch(item["name"]):
            raise FormatError("unsafe evidence basename")
        if item["name"] <= prev:
            raise FormatError("evidence entries must be unique and sorted")
        prev = item["name"]
        check_hex(item["sha256"])


def validate_packet(packet):
    shape(packet, ("schema", "receipt", "issuer_signature", "engineer_signature", "witness_signatures"), "packet")
    if packet["schema"] != "ipqr-packet/v1":
        raise FormatError("unsupported packet version")
    validate_receipt(packet["receipt"])
    check_hex(packet["issuer_signature"], 128)
    check_hex(packet["engineer_signature"], 128)
    witnesses = packet["witness_signatures"]
    if type(witnesses) is not list or not 1 <= len(witnesses) <= 16:
        raise FormatError("invalid witness signatures")
    last = ""
    for item in witnesses:
        shape(item, ("id", "signature"), "witness entry")
        ident(item["id"])
        if item["id"] <= last:
            raise FormatError("witness IDs must be unique and sorted")
        last = item["id"]
        check_hex(item["signature"], 128)


def validate_trust(trust):
    shape(trust, ("schema", "anchor_id", "issuer_keys", "witnesses", "engineers", "revocation_authority", "issuance_log_authority", "policy"),"trust anchor")
    if trust["schema"] != "ipqr-anchor/v1":
        raise FormatError("unsupported trust anchor")
    ident(trust["anchor_id"])
    for label, arr, maximum in (("issuer_keys",trust["issuer_keys"],16),
                                ("witnesses",trust["witnesses"],16),
                                ("engineers",trust["engineers"],16)):
        if type(arr) is not list or not 1 <= len(arr) <= maximum:
            raise FormatError("invalid anchor " + label)
        prev = ""
        for item in arr:
            keys = ("id", "public_key", "valid_from", "valid_until") if label != "engineers" else (
                "id", "public_key", "valid_from", "valid_until", "name", "organization", "role")
            shape(item,keys,label + " entry")
            ident(item["id"])
            if item["id"] <= prev:
                raise FormatError(label + " key IDs must be unique and sorted")
            prev = item["id"]
            check_hex(item["public_key"])
            for k in ("valid_from", "valid_until"):
                uint(item[k])
            if item["valid_from"] >= item["valid_until"]:
                raise FormatError("invalid key interval")
            if label == "engineers":
                for k in ("name", "organization", "role"):
                    if type(item[k]) is not str or not 1 <= len(item[k]) <= 120:
                        raise FormatError("incomplete accountable human")
    # Quorum must be made of distinct keys, not merely duplicated identities.
    all_pubkeys = [item["public_key"] for keyset in
                   (trust["issuer_keys"], trust["witnesses"], trust["engineers"])
                   for item in keyset]
    if len(set(all_pubkeys)) != len(all_pubkeys):
        raise FormatError("anchor reuses one signing key for multiple identities")
    a = trust["revocation_authority"]
    shape(a,("id", "public_key"),"revocation authority")
    ident(a["id"])
    check_hex(a["public_key"])
    all_ids = [item["id"] for pool in
               (trust["issuer_keys"], trust["witnesses"], trust["engineers"])
               for item in pool] + [a["id"]]
    if len(set(all_ids)) != len(all_ids):
        raise FormatError("trust anchor identity IDs collide across roles")
    if a["public_key"] in set(all_pubkeys):
        raise FormatError("revocation authority must use a separate signing key")
    log_authority=trust["issuance_log_authority"]
    shape(log_authority,("id", "public_key"),"issuance log authority")
    ident(log_authority["id"])
    check_hex(log_authority["public_key"])
    if (log_authority["id"] in set(all_ids) or
        log_authority["public_key"] in set(all_pubkeys + [a["public_key"]])):
        raise FormatError("issuance log authority must be independently named and keyed")
    p = trust["policy"]
    shape(p,("witness_threshold", "max_receipt_age_seconds", "max_clock_skew_seconds",
             "max_observation_lag_seconds", "max_revocation_age_seconds",
             "minimum_revocation_serial", "max_evidence_file_bytes",
             "minimum_log_serial", "max_log_age_seconds"),"anchor policy")
    for v in p.values():
        uint(v)
    if not 1 <= p["witness_threshold"] <= len(trust["witnesses"]):
        raise FormatError("impossible witness quorum")
    if not 0 < p["max_receipt_age_seconds"] <= 31_536_000:
        raise FormatError("unsafe receipt max age")
    if not 0 <= p["max_clock_skew_seconds"] <= 3600:
        raise FormatError("unsafe clock skew")
    if not 0 < p["max_revocation_age_seconds"] <= 604800:
        raise FormatError("unsafe revocation age")
    if not 0 < p["max_evidence_file_bytes"] <= 32*1024*1024:
        raise FormatError("unsafe evidence size")
    if not 0 < p["max_log_age_seconds"] <= 604800:
        raise FormatError("unsafe issuance log freshness limit")


def validate_revocations(envelope):
    shape(envelope, ("snapshot", "signature"), "revocation envelope")
    check_hex(envelope["signature"],128)
    s = envelope["snapshot"]
    shape(s, ("schema", "authority_id", "serial", "issued_at", "next_update", "revoked_keys"),"snapshot")
    if s["schema"] != "ipqr-revocations/v1":
        raise FormatError("invalid revocation schema")
    ident(s["authority_id"])
    for k in ("serial", "issued_at", "next_update"):
        uint(s[k])
    if not s["issued_at"] < s["next_update"]:
        raise FormatError("bad revocation time interval")
    r = s["revoked_keys"]
    if type(r) is not list or len(r) > 64:
        raise FormatError("invalid revocation list")
    last = ""
    for item in r:
        shape(item,("id","reason"),"revoked key")
        ident(item["id"])
        if item["id"] <= last:
            raise FormatError("revoked entries must be unique and sorted")
        last = item["id"]
        if item["reason"] not in ("COMPROMISED","WITHDRAWN","RETIRED"):
            raise FormatError("invalid revocation reason")


def validate_issuance_log(envelope):
    """Signed small complete digest manifest, not a public transparency service."""
    shape(envelope,("checkpoint", "signature"),"issuance-log envelope")
    check_hex(envelope["signature"], 128)
    checkpoint=envelope["checkpoint"]
    shape(checkpoint,("schema","authority_id","serial","issued_at","entries","merkle_root"),
          "issuance-log checkpoint")
    if checkpoint["schema"] != "ipqr-issuance/v1":
        raise FormatError("unsupported issuance log profile")
    ident(checkpoint["authority_id"])
    uint(checkpoint["serial"])
    uint(checkpoint["issued_at"])
    check_hex(checkpoint["merkle_root"])
    e=checkpoint["entries"]
    if type(e) is not list or not 1 <= len(e) <= 64:
        raise FormatError("invalid issuance log entries")
    prev=""
    for digest in e:
        check_hex(digest)
        if digest <= prev:
            raise FormatError("issuance log entries must be sorted and unique")
        prev=digest
