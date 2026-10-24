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
        "why": "The fixed eGi diffusion candidate is compared against a Bass-style baseline on the same 17-point CKM reduction; the claim is conditional on that reduction.",
    },
    "eGi_specific_parameters_identified_by_CKM": {
        "tier": "REFUTED",
        "evidence_type": "identifiability_boundary",
        "tester": "CKM data schema",
        "tester_observable": True,
        "why": "This row refutes the claim that CKM identifies eGi-specific parameters; it does not refute the existence or usefulness of those parameters. CKM records adoption timing but not local tests, receipt strength, contradictions, quarantine, or mutation lineage.",
    },
    "eGi_calibration_claim": {
        "tier": "ACTION_REQUIRED",
        "evidence_type": "external_calibration",
        "tester": "tools/epidemic_calibration.py",
        "tester_observable": True,
        "why": "The fixed eGi candidate failed the pre-registered RMSE criterion and did not outperform the baseline comparator; this is not evidence that no bounded eGi parameterization could fit CKM.",
    },
    "supersession_is_distinct_from_quarantine": {
        "tier": "VERIFIED_PROCESS",
        "evidence_type": "behavior_receipt",
        "tester": "tests/test_epidemic_genesis.py",
        "tester_observable": True,
        "why": "The behavioral test now requires successor adoption before an adopted/retained predecessor transitions to SUPERSEDED, and confirms it is not QUARANTINED.",
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
    "github_push_workflow_result_for_run_40133000883": {
        "tier": "VERIFIED_PROCESS",
        "evidence_type": "CI_observability",
        "tester": "GitHub Actions run API",
        "tester_observable": True,
        "why": "Run 40133000883 completed successfully and its machine-readable artifact included run_id, commit SHA, tester manifest, calibration output, and master receipt.",
    },
    "github_actions_observability_channel_is_closed": {
        "tier": "ACTION_REQUIRED",
        "evidence_type": "observability_scope",
        "tester": "GitHub Actions",
        "tester_observable": True,
        "why": "One observed run proves observability for that execution; it does not prove that every future push-triggered workflow will be observable.",
    },
    "eGi_positive_control_promotes_known_good_candidate": {
        "tier": "VERIFIED_PROCESS",
        "evidence_type": "positive_control_behavior_receipt",
        "tester": "tools/epidemic_calibration.py",
        "tester_observable": True,
        "why": "A synthetic curve generated by the same fixed eGi simulator was recovered with RMSE 0.0 and beat the Bass comparator; this demonstrates a promotion path in a round-trip control, not external model discrimination.",
    },
    "external_ground_truth_positive_control_discriminates_models": {
        "tier": "VERIFIED_PROCESS",
        "evidence_type": "external_ground_truth_positive_control",
        "tester": "tools/epidemic_calibration.py",
        "tester_observable": True,
        "why": "The control fits noisy data generated by a preregistered Bass process using the actual Bass grid-search fitter. The exact p=0.084 report is a grid point at 0.001 resolution, not fifteen-digit parameter recovery. This supports the narrower claim that the harness can reject the fixed eGi candidate on known-Bass data; it does not establish bidirectional discrimination.",
    },
    "external_ground_truth_discrimination_bidirectional": {
        "tier": "ACTION_REQUIRED",
        "evidence_type": "symmetric_external_ground_truth_control",
        "tester": "tools/epidemic_calibration.py",
        "tester_observable": True,
        "why": "Both known-Bass and known-eGi noisy processes must be fit by the corresponding model and rejected by the competitor before the bidirectional discrimination claim is promoted.",
    },
    "custom_domain_edge_smoke_tester_blind": {
        "tier": "ACTION_REQUIRED",
        "evidence_type": "edge_smoke_observability_boundary",
        "tester": "custom-domain edge smoke",
        "tester_observable": False,
        "why": "A 403 at the custom domain leaves the tester unable to distinguish Cloudflare policy blocking from origin health or proxy-path behavior. This is tester blindness at the edge, not a validated origin failure.",
    },
    "ckm_eGi_minus_bass_delta_90_percent_ci": {
        "tier": "VERIFIED_PROCESS",
        "evidence_type": "paired_bootstrap_comparative_receipt",
        "tester": "tools/epidemic_calibration.py",
        "tester_observable": True,
        "why": "The pre-registered 90% paired bootstrap interval for the CKM eGi-minus-Bass RMSE delta was [0.006491, 0.015391], excluding zero; this supports the comparative finding that eGi performed worse on this curve.",
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
