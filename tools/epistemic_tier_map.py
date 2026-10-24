"""Machine-readable honest tier map for Epistemic Genesis claims.

Every claim names its evidence type and tester observability. Existence receipts
are deliberately separated from behavioral/function receipts.
"""

TIER_MAP = {

    "ckm_diffusion_submodel_has_external_comparator": {
        "tier": "VERIFIED_PROCESS",
        "evidence_type": "comparative_calibration_receipt",
        "tester": "tools/epidemic_calibration.py",
        "tester_observable": True,
        "why": "The fixed eGi diffusion candidate is compared against a Bass-style baseline on the same 17 CKM-derived adoption points.",
    },
    "eGi_specific_parameters_identified_by_CKM": {
        "tier": "REFUTED",
        "evidence_type": "identifiability_boundary",
        "tester": "CKM data schema",
        "tester_observable": True,
        "why": "CKM records adoption timing but not local tests, receipt strength, contradictions, quarantine, or mutation lineage; kappa and mutation are therefore not identifiable from this dataset.",
    },
    "eGi_calibration_claim": {
        "tier": "ACTION_REQUIRED",
        "evidence_type": "external_calibration",
        "tester": "tools/epidemic_calibration.py",
        "tester_observable": True,
        "why": "The fixed eGi candidate failed the pre-registered RMSE criterion and did not outperform the baseline comparator.",
    },
    "supersession_is_distinct_from_quarantine": {
        "tier": "VERIFIED_PROCESS",
        "evidence_type": "behavior_receipt",
        "tester": "tests/test_epidemic_genesis.py",
        "tester_observable": True,
        "why": "The model now has a distinct SUPERSEDED state so displacement by a successor is not mislabeled as contradiction-driven quarantine.",
    },
    "epidemic_genesis_model_exists": {
        "tier": "EXISTENCE_RECEIPT",
        "evidence_type": "repository_presence",
        "tester": "GitHub source tree",
        "tester_observable": True,
        "why": "The model file and documentation are present in main; this does not establish behavioral correctness.",
    },
    "epidemic_genesis_generator_changes_variants_under_mutation": {
        "tier": "VERIFIED_PROCESS",
        "evidence_type": "behavior_receipt",
        "tester": "tests/test_epidemic_genesis.py",
        "tester_observable": True,
        "why": "The test exercises mutation/copy behavior rather than checking only return types.",
    },
    "epidemic_genesis_tester_rejects_weak_external_evidence": {
        "tier": "VERIFIED_PROCESS",
        "evidence_type": "behavior_receipt",
        "tester": "tests/test_epidemic_genesis.py",
        "tester_observable": True,
        "why": "The tester is exercised with weak self-consistency evidence and must reject it.",
    },
    "epidemic_genesis_graph_propagation_and_quarantine_are_exercised": {
        "tier": "VERIFIED_PROCESS",
        "evidence_type": "simulation_behavior_receipt",
        "tester": "tests/test_epidemic_genesis.py",
        "tester_observable": True,
        "why": "The test drives propagation, R0/Rt, failure, and contradiction-triggered quarantine.",
    },
    "epidemic_genesis_calibration_harness_runs": {
        "tier": "VERIFIED_PROCESS",
        "evidence_type": "external_calibration_attempt",
        "tester": "tools/epidemic_calibration.py",
        "tester_observable": True,
        "why": "The harness consumes an externally sourced adoption curve and emits a machine-readable calibration result.",
    },
    "epidemic_genesis_calibrated_against_observed_epidemic": {
        "tier": "ACTION_REQUIRED",
        "evidence_type": "external_calibration",
        "tester": "tools/epidemic_calibration.py",
        "tester_observable": True,
        "why": "The current calibration run is intentionally not promoted unless RMSE meets the stated threshold.",
    },
    "intelligence_as_generate_and_test": {
        "tier": "DEFINITIONAL",
        "evidence_type": "definition",
        "tester": "none",
        "tester_observable": False,
        "why": "This is the project's operational definition of intelligence, not an empirical finding.",
    },
    "github_push_workflow_result_is_machine_observable": {
        "tier": "VERIFIED_PROCESS",
        "evidence_type": "CI_observability",
        "tester": "GitHub Actions",
        "tester_observable": False,
        "why": "The push-triggered workflow result was independently read from the GitHub Actions run API for the observed run.",
    },
    "high_r0_variant_is_verified_truth": {
        "tier": "REFUTED",
        "evidence_type": "logical_boundary",
        "tester": "model definition",
        "tester_observable": True,
        "why": "R0 above one measures propagation potential; it does not establish external correctness.",
    },
    "receipt_self_consistency_is_external_truth": {
        "tier": "REFUTED",
        "evidence_type": "logical_boundary",
        "tester": "model definition",
        "tester_observable": True,
        "why": "A cryptographic receipt can bind an observed process without independently proving the payload's truth.",
    },
    "today_ai_can_generate_new_solver_code": {
        "tier": "PROVEN_LAW",
        "evidence_type": "established_capability",
        "tester": "field evidence",
        "tester_observable": True,
        "why": "Program synthesis and LLM code generation are established capabilities/fields.",
    },
    "physical_gate_opens": {
        "tier": "REFUTED",
        "evidence_type": "hardware_boundary",
        "tester": "TEE/physical attestation requirement",
        "tester_observable": True,
        "why": "No network telemetry or software receipt supplies a hardware TEE quote.",
    },
    "method_success_proves_agi": {
        "tier": "REFUTED",
        "evidence_type": "scope_boundary",
        "tester": "task verifier",
        "tester_observable": True,
        "why": "Success on a bounded task establishes only task-specific verified process behavior.",
    },
}

if __name__ == "__main__":
    import json
    print(json.dumps(TIER_MAP, indent=2, sort_keys=True))
