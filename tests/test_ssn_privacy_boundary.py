import copy

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ed25519

from core.line_receipt import create_human_receipt
from core.ssn_sanitizer import SSNSanitizer, SSN_PATTERN


def test_ssn_pattern_is_explicit_and_local():
    assert SSN_PATTERN.search("synthetic: 000-00-0000")
    assert not SSN_PATTERN.search("no-ssn-here")


def test_sanitize_never_returns_raw_match():
    sanitizer = SSNSanitizer(b"m" * 32)
    result = sanitizer.extract_and_tokenize(
        "Applicant synthetic SSN: 000-00-0000", "exec-ssn-1"
    )
    assert "000-00-0000" not in result.text
    assert result.text.count("[SSN_TOKEN_") == 1
    assert result.token_map
    serialized = str(result.token_map)
    assert "000-00-0000" not in serialized
    assert result.receipt["physical_gate"] == "ACTION_REQUIRED"


def test_token_ids_are_random_and_not_raw_hashes():
    sanitizer = SSNSanitizer(b"k" * 32)
    first = sanitizer.extract_and_tokenize("000-00-0000", "exec-a")
    second = sanitizer.extract_and_tokenize("000-00-0000", "exec-a")
    assert set(first.token_map) != set(second.token_map)


def test_approved_reveal_requires_signed_line_receipt():
    sanitizer = SSNSanitizer(b"x" * 32)
    result = sanitizer.extract_and_tokenize("000-00-0000", "exec-2")
    token = next(iter(result.token_map))
    key = ed25519.Ed25519PrivateKey.generate()
    pub = key.public_key().public_bytes(
        serialization.Encoding.Raw, serialization.PublicFormat.Raw
    ).hex()
    intent = sanitizer.reveal_intent_hash(execution_id="exec-2", token=token)
    receipt = create_human_receipt(
        execution_id="exec-2",
        workflow_key="ssn-reveal",
        intent_hash=intent,
        decision="APPROVE",
        actor="synthetic-test-operator",
        signer=key,
    )
    assert sanitizer.reveal_for_human(
        token=token,
        token_map=result.token_map,
        execution_id="exec-2",
        approval_receipt=receipt,
        human_public_key_hex=pub,
    ) == "000-00-0000"


def test_wrong_intent_cannot_reveal():
    sanitizer = SSNSanitizer(b"x" * 32)
    result = sanitizer.extract_and_tokenize("000-00-0000", "exec-3")
    token = next(iter(result.token_map))
    key = ed25519.Ed25519PrivateKey.generate()
    pub = key.public_key().public_bytes(
        serialization.Encoding.Raw, serialization.PublicFormat.Raw
    ).hex()
    receipt = create_human_receipt(
        execution_id="exec-3",
        workflow_key="ssn-reveal",
        intent_hash="sha256:wrong",
        decision="APPROVE",
        actor="synthetic-test-operator",
        signer=key,
    )
    with pytest.raises(ValueError, match="not bound"):
        sanitizer.reveal_for_human(
            token=token,
            token_map=result.token_map,
            execution_id="exec-3",
            approval_receipt=receipt,
            human_public_key_hex=pub,
        )


def test_ciphertext_tamper_is_fail_closed():
    sanitizer = SSNSanitizer(b"z" * 32)
    result = sanitizer.extract_and_tokenize("000-00-0000", "exec-4")
    token = next(iter(result.token_map))
    tampered = copy.deepcopy(result.token_map)
    tampered[token]["ciphertext_hex"] = "00" + tampered[token]["ciphertext_hex"][2:]
    key = ed25519.Ed25519PrivateKey.generate()
    pub = key.public_key().public_bytes(
        serialization.Encoding.Raw, serialization.PublicFormat.Raw
    ).hex()
    receipt = create_human_receipt(
        execution_id="exec-4",
        workflow_key="ssn-reveal",
        intent_hash=sanitizer.reveal_intent_hash(execution_id="exec-4", token=token),
        decision="APPROVE",
        actor="synthetic-test-operator",
        signer=key,
    )
    with pytest.raises(ValueError, match="DEATH"):
        sanitizer.reveal_for_human(
            token=token,
            token_map=tampered,
            execution_id="exec-4",
            approval_receipt=receipt,
            human_public_key_hex=pub,
        )
