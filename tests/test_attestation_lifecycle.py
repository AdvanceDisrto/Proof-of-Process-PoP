import base64
import hashlib

import pytest
from fastapi import HTTPException

import main


def _challenge(instance="node-test"):
    return main.issue_attestation_challenge(
        main.ChallengeRequest(
            provider_name="io.net",
            instance_id=instance,
            hardware_type="NVIDIA_GPU_TEE_CANDIDATE",
        )
    )


def _submission(challenge, instance="node-test"):
    evidence = base64.b64encode(b"x" * 128).decode()
    return main.AttestationSubmission(
        instance_id=instance,
        nonce=challenge["challenge_nonce"],
        attestation_token_b64=evidence,
        workload_hash=hashlib.sha256(b"workload").hexdigest(),
    )


def test_structural_attestation_never_promotes_physical_gate():
    main.ACTIVE_CHALLENGES.clear()
    challenge = _challenge()
    result = main.verify_attestation_submission(_submission(challenge))
    assert result["status"] == "EVIDENCE_RECEIVED_UNVERIFIED"
    assert result["physical_gate"] == "ACTION_REQUIRED"
    assert result["materialization"] == "BLOCKED"


def test_nonce_is_single_use_and_replay_is_rejected():
    main.ACTIVE_CHALLENGES.clear()
    challenge = _challenge()
    submission = _submission(challenge)
    main.verify_attestation_submission(submission)
    with pytest.raises(HTTPException) as exc:
        main.verify_attestation_submission(submission)
    assert exc.value.status_code == 403


def test_wrong_nonce_is_rejected_and_consumes_challenge():
    main.ACTIVE_CHALLENGES.clear()
    challenge = _challenge()
    submission = _submission(challenge)
    submission.nonce = "00" * 32
    with pytest.raises(HTTPException) as exc:
        main.verify_attestation_submission(submission)
    assert exc.value.status_code == 401
    assert "node-test" not in main.ACTIVE_CHALLENGES
