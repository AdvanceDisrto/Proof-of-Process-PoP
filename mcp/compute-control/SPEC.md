# Compute Control MCP

## Value Proposition

Provide one provider-neutral MCP control plane for compute, AI workloads, connectivity, telecommunications, communications, cryptography, blockchain, and evidence-bearing execution.

The system is designed for conversational infrastructure control: a user can request a GPU/VM/workload operation in natural language while the MCP converts that intent into a scoped backend operation and an auditable PoP execution receipt.

**Core actions**
1. Discover and inspect compute/connectivity resources.
2. Provision and execute controlled workloads.
3. Collect telemetry, provenance, hashes, and PoP execution receipts.

## Why LLM?

**Conversational win:** infrastructure intent can be expressed as a single request such as "run the PoP E2E workload on an AMD ROCm instance and return the execution receipt."

**LLM adds:** intent interpretation, provider selection, workload planning, evidence summarization, and cross-domain orchestration.

**What the LLM lacks:** provider APIs, instance state, SSH transport, GPU telemetry, cellular/telecom state, blockchain endpoints, and authoritative execution receipts. Those are supplied by MCP tools/adapters.

## UI Overview

This MCP is primarily tool-first. A lightweight status/evidence view can summarize:

- provider and instance state
- GPU/ROCm diagnostics
- connectivity/telecom state
- workload execution
- PoP receipt chain

The LLM remains the main conversational surface; the optional view is for inspection and evidence review rather than a full dashboard.

## Product Context

**Repository:** AdvanceDisrto/Proof-of-Process-PoP

**Provider adapters:** RunPod, AWS, Azure, GCP, and future providers.

**Connectivity adapters:** cellular carriers, telecom APIs, internet connectivity, Wi-Fi, Bluetooth, UWB/wireless where provider APIs permit.

**Evidence plane:** PoP receipts, hashes, provenance, execution telemetry, optional external anchors.

**Authentication:** provider-specific credentials and OAuth/API-key flows; secrets are never placed into PoP payloads.

## Domains

- Cloud compute
- CPU/VM/container/bare-metal lifecycle
- GPU and ROCm/CUDA inspection
- AI/ML workload execution
- SSH and remote command execution
- Cellular and telecommunications
- Internet/network connectivity
- Wi-Fi
- Bluetooth/wireless
- Blockchain and crypto provider APIs
- Cryptographic operations and verification
- Chat/messaging provider adapters
- PoP execution receipts and provenance

## Safety and Evidence Rules

- Read/inspect operations are non-destructive by default.
- Mutating operations are policy-gated.
- Destructive lifecycle actions require explicit authorization.
- Physical actuation remains outside this MCP's direct authority and stays behind the existing PoP/aerial/sovereign gates.
- Provider claims are recorded as provider evidence; the MCP does not manufacture hardware attestation.
- A successful API request is not itself a claim of physical truth.
- Every execution-capable operation receives a PoP execution envelope.

## UX Flows

### Discover resources
1. Request compute/connectivity resources by capability.
2. Select provider/resource matching constraints.
3. Return normalized resource information.

### Run workload
1. Resolve provider and instance.
2. Provision or select instance.
3. Verify connectivity and GPU/runtime.
4. Execute workload.
5. Collect logs/metrics and hashes.
6. Emit PoP execution receipt.

### Inspect connectivity
1. Resolve connectivity adapter.
2. Query cellular/telecom/Wi-Fi/Bluetooth/network state.
3. Return normalized telemetry plus evidence references.

### Verify evidence
1. Fetch execution receipt.
2. Verify receipt hash chain/provenance.
3. Optionally verify an external anchor.
4. Report exact evidence boundary.

## Tool Families

**Provider:** list_providers, provider_status, provider_capabilities

**Compute:** list_instance_types, list_instances, get_instance, create_instance, start_instance, stop_instance, restart_instance, terminate_instance

**GPU:** inspect_gpu, inspect_rocm, inspect_cuda, run_gpu_diagnostics

**Workload:** bootstrap_instance, deploy_workload, execute_workload, collect_workload_logs, collect_workload_metrics

**SSH:** open_ssh, execute_ssh_command, upload_artifact, download_artifact, close_ssh

**Connectivity:** inspect_network, inspect_cellular, inspect_telecom, inspect_wifi, inspect_bluetooth, inspect_wireless

**AI:** list_models, inspect_runtime, deploy_model, run_inference, collect_inference_receipt

**Blockchain/Crypto:** inspect_chain_provider, verify_transaction, verify_anchor, hash_artifact, verify_signature

**Evidence:** create_pop_receipt, verify_pop_receipt, get_execution_chain, export_evidence_bundle

## Canonical Execution Envelope

Every mutating or execution-capable operation should record:

- provider
- resource/instance identifier
- capability
- workload
- git commit
- command or request hash
- start/end timestamps
- exit status
- input/output/artifact hashes
- telemetry references
- provider receipt/reference
- PoP receipt hash
- external anchor status
