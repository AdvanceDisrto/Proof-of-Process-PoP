"""Machine-readable honest tier map for Epistemic Genesis claims."""

TIER_MAP = {
    "today_ai_can_generate_new_solver_code": {
        "tier": "PROVEN_LAW",
        "why": "Program synthesis and LLM code generation are established capabilities/fields.",
    },
    "system_can_evaluate_generated_solver": {
        "tier": "VERIFIED_PROCESS",
        "why": "The repository can execute generated code and bind the observed result to receipts.",
    },
    "epistemic_genesis_prototype_is_implementable_today": {
        "tier": "VERIFIED_PROCESS",
        "why": "The CCE prototype is runnable in the repository test environment.",
    },
    "verifier_accepts_without_trusting_model": {
        "tier": "VERIFIED_PROCESS",
        "why": "The verifier recomputes success from execution hashes and exit status; this is a software verification property, not a physical law.",
    },
    "invented_method_is_fundamental_new_way_of_knowing": {
        "tier": "JUDGMENT",
        "why": "The prototype emits code inside an existing computational substrate; novelty of epistemology is not established by the receipt.",
    },
    "method_is_safe": {
        "tier": "ACTION_REQUIRED",
        "why": "Resource limits and a child socket policy are tested, but this is not a complete adversarial sandbox or alignment proof.",
    },
    "physical_gate_opens": {
        "tier": "REFUTED",
        "why": "No hardware attestation or measured physical evidence is supplied by this prototype.",
    },
    "method_success_proves_agi": {
        "tier": "REFUTED",
        "why": "Success on a bounded task establishes only task-specific verified process behavior.",
    },
    "entity_is_alive_or_conscious": {
        "tier": "REFUTED",
        "why": "The implementation is an engineered software process; no consciousness evidence is established.",
    },
}

if __name__ == "__main__":
    import json
    print(json.dumps(TIER_MAP, indent=2, sort_keys=True))
