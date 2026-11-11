"""Only route for a VERIFIED_DIGITAL_RECEIPT. No self-asserted verifier flags accepted."""
from __future__ import annotations
from pathlib import Path
from .codec import Event, event_from_verifier


class VerificationNotReady(RuntimeError):
    pass


class IndependentReceiptGate:
    def __init__(self, *, trust: dict, revocations: dict, issuance_log: dict,
                 independently_pinned_anchor_sha256: str, expected_subject: str,
                 evidence_dir: str | Path | None, expected_nonce_hex: str | None = None):
        self.trust = trust
        self.revocations = revocations
        self.issuance_log = issuance_log
        self.pin = independently_pinned_anchor_sha256
        self.subject = expected_subject
        self.evidence_dir = evidence_dir
        self.nonce = expected_nonce_hex

    def check(self, signed_packet: dict, *, now: int | None = None,
              carrier: str | None = None) -> tuple[Event, dict]:
        try:
            from innovulis_receipt.engine import verify
        except ImportError as exc:
            raise VerificationNotReady("Install or explicitly bundle the open-verifier v1.0 package") from exc
        decision = verify(signed_packet, self.trust, self.revocations, self.issuance_log,
                          expected_anchor_sha256=self.pin,
                          expected_subject=self.subject, evidence_dir=self.evidence_dir,
                          expected_nonce_hex=self.nonce, current_time=now).to_dict()
        # Even a rejected packet can be recorded, but it MUST NEVER be represented as verified.
        if decision.get("receipt_sha256") and decision.get("claim_verdict"):
            event = event_from_verifier(signed_packet, decision, carrier=carrier, when=now)
        else:
            raise VerificationNotReady("Receipt has no structurally acceptable signed body; record rejection in audit channel")
        return event, decision
