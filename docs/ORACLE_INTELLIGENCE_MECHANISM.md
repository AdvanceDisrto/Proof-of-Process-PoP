# i™️ 🧾 Oracle Intelligence Mechanism Architecture

## Canonical synthesis

The Process of Truth Epidemic Genesis Intelligence (PoT-eGI) is organized as an **Oracle Intelligence Mechanism**: probabilistic intelligence is allowed to generate hypotheses, while deterministic evidence gates control what may be accepted, dispatched, or physically executed.

The governing law is:

> **Intelligence generates possibilities. The mechanism verifies evidence. The receipt records the process.**

The architecture does **not** equate a software receipt with physical truth. Software verification, live external attestations, hardware attestation, and physical execution remain distinct evidence boundaries.

## Four Oracle pillars

### 1. Sensory Oracle — perceive

**Role:** bind incoming observations to available device/network evidence before intelligence consumes them.

Representative surfaces:

- iMobile Cellular Orchestra
- carrier/network identity and attestation integrations
- TEE/Secure Enclave evidence
- cellular/network edge evidence

**Fail-closed rule:** missing or invalid required evidence produces `QUARANTINED` or `ACTION_REQUIRED`; it does not become verified data merely because an application received it.

### 2. Cognitive Oracle — reason

**Role:** correlate verified inputs, generate hypotheses, and propose next actions.

Representative surfaces:

- eGI / Root Cause Agent
- multimodal models
- graph analysis
- epidemiological models

The cognitive layer may produce an `UNVERIFIED_INFERENCE` receipt containing the hypothesis commitment and provenance references. It cannot self-certify the hypothesis as physical truth.

### 3. Consensus Oracle — bind time and structure

**Role:** verify the evidence needed to establish provenance, temporal ordering, and external consensus.

Representative surfaces:

- ChainOracle
- OpenTimestamps
- Ethereum/EAS or other configured attestations
- configured blockchain/indexing providers

**Fail-closed rule:** unavailable, unconfirmed, contradictory, or insufficient external evidence remains `PENDING` / `ACTION_REQUIRED` / `QUARANTINED` according to the gate contract.

A timestamp or blockchain anchor proves existence/ordering of a commitment; it does not independently prove that the underlying proposition is true.

### 4. Actuation Oracle — verify before physical effect

**Role:** enforce the final deterministic gate between a proposed command and physical execution.

Representative surfaces:

- PhysicalEvidenceGate
- hardware TEE evidence
- actuator/interlock state
- exact command commitment
- regulatory/evidence receipt integrations

**Fail-closed rule:** every required proof must satisfy the gate contract. A missing proof cannot be substituted with model confidence or prose.

## RPCEgi execution loop

`PERCEIVE → REASON → BIND → VERIFY → ACT → RECEIPT → FEEDBACK`

1. **PERCEIVE** — acquire an observation and its available attestation evidence.
2. **REASON** — generate a bounded hypothesis.
3. **BIND** — commit the hypothesis and required provenance to deterministic identifiers/anchors.
4. **VERIFY** — evaluate the configured evidence quorum and hardware/physical gates.
5. **ACT** — permit physical execution only when the gate contract passes.
6. **RECEIPT** — record the exact process, state, hashes, and evidence references.
7. **FEEDBACK** — return independently verified results to the sensory/data layer.

## State law

| Layer | Software/process state | Missing external evidence |
|---|---|---|
| Sensory | `VERIFIED_PROCESS` when its software contract passes | `ACTION_REQUIRED` / `QUARANTINED` |
| Cognitive | `UNVERIFIED_INFERENCE` | cannot self-certify |
| Consensus | `VERIFIED_PROCESS` when its configured checks pass | `PENDING` / `ACTION_REQUIRED` |
| Actuation | `VERIFIED_PROCESS` only after gate checks pass | `ACTION_REQUIRED` |
| Physical reality | separate evidence domain | never inferred from software CI |

## The i™️ 🧾 boundary

**i™️** is the interface/binding mechanism: it carries identity, input, computation, state, and gate transitions through explicit contracts.

**🧾** is the receipt mechanism: it records what process was actually performed, what hashes/identifiers were bound, which gates passed or failed, and which external evidence is still required.

The receipt is therefore an **evidence record**, not a magic certificate of reality.

## What “truth” means here

The architecture uses a deliberately operational definition:

1. **Consistency** — the process and receipt do not contradict their own commitments.
2. **Factual evidence** — claims are supported by independently checkable evidence appropriate to the claim.
3. **Repeatability** — the verification procedure can be rerun against the same commitments and evidence.
4. **Boundary honesty** — a missing physical, carrier, blockchain, or hardware proof remains missing.

This prevents the system from converting model confidence, successful compilation, or a deployment into a claim of physical truth.

## Current implementation boundary

The repository can establish software/process evidence through its tests, native components, receipts, and fail-closed state contracts.

The following remain external evidence gates until actually supplied and verified:

- live carrier/device attestation
- live blockchain confirmations
- genuine hardware TEE attestation
- physical actuator/interlock evidence
- physical laboratory or real-world outcome evidence

**Canonical invariant:**

> **The mind may propose. The mechanism may verify. The receipt may record. Only the required evidence boundary may authorize the next state.**
