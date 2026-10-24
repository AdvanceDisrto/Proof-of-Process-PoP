"""Fail-closed provider-aware hardware attestation router for i™ physical gates.

Provider catalog entries are capability policy, not runtime evidence. A provider can be
eligible for an attested run without promoting the physical gate. MEASURED_PASS is only
possible after a fresh evidence bundle is verified by the evidence verifier.
"""

from dataclasses import asdict, dataclass
from typing import Iterable


@dataclass(frozen=True)
class Provider:
    name: str
    confidential_compute: bool
    attestation: str
    policy_state: str
    notes: str


PROVIDERS = (
    Provider(
        "io.net",
        True,
        "TEE_ATTESTATION_CANDIDATE",
        "ELIGIBLE_FOR_ATTESTATION",
        "Confidential Compute/TEE is documented; runtime evidence must still be collected and verified.",
    ),
    Provider(
        "Hyperstack",
        False,
        "UNAVAILABLE",
        "COMPUTE_ONLY",
        "Hyperstack documents Confidential Computing as not currently available.",
    ),
    Provider(
        "Runpod",
        False,
        "NOT_ESTABLISHED_BY_PROVIDER_DOCS",
        "COMPUTE_ONLY",
        "Secure Cloud/H100 availability is not itself a hardware attestation receipt.",
    ),
    Provider(
        "Akamai",
        False,
        "NOT_ESTABLISHED_BY_PROVIDER_DOCS",
        "COMPUTE_ONLY",
        "GPU availability is not itself a hardware attestation receipt.",
    ),
)


def route(require_attestation: bool = True, providers: Iterable[Provider] = PROVIDERS) -> dict:
    candidates = [
        provider
        for provider in providers
        if not require_attestation or provider.confidential_compute
    ]
    if not candidates:
        return {
            "status": "ACTION_REQUIRED",
            "physical_gate": "ACTION_REQUIRED",
            "reason": "No configured provider satisfies the attestation policy.",
        }

    selected = candidates[0]
    return {
        "status": selected.policy_state,
        "physical_gate": "ACTION_REQUIRED",
        "selected_provider": selected.name,
        "attestation": selected.attestation,
        "provider": asdict(selected),
        "next_action": "Provision, collect fresh nonce-bound hardware evidence, then verify it.",
        "does_not_prove": [
            "physical execution occurred",
            "the requested workload ran on the attested device",
            "energy was calibrated or workload-exclusive",
            "fabricated i™ silicon exists",
        ],
    }


if __name__ == "__main__":
    import json

    print(json.dumps(route(require_attestation=True), indent=2, sort_keys=True))
