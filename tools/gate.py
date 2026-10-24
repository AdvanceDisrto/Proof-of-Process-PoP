"""Fail-closed physical attestation gate. Presence is not proof."""

TRUSTED_TEE_ROOTS = {
    "AMD_SEV_SNP_ROOT_CA",
    "INTEL_TDX_ROOT_CA",
    "NVIDIA_TEE_ROOT_CA_2026",
    "ARM_CCA_ROOT_CA",
    "APPLE_SEP_ROOT_CA",
}


def tee_quote_is_attested(q) -> bool:
    if not isinstance(q, dict):
        return False
    chain = q.get("vendor_chain")
    if not isinstance(chain, list) or not chain:
        return False
    if chain[-1] not in TRUSTED_TEE_ROOTS:
        return False
    return bool(q.get("measurement"))


def energy_is_measured(e) -> bool:
    if not isinstance(e, dict):
        return False
    joules = e.get("joules")
    if not isinstance(joules, (int, float)) or isinstance(joules, bool):
        return False
    return str(e.get("source", "")).startswith("signed:")


def physical_gate(tee_quote=None, energy=None) -> str:
    if tee_quote_is_attested(tee_quote) and energy_is_measured(energy):
        return "MEASURED_PASS"
    return "ACTION_REQUIRED"
