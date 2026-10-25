# i Real AI Brain Integration

The PoP brain composes the five pinned i repositories as one governed capability fabric.

## Sources

- STRMKRD-AI: native foundation intelligence, specialist models, deterministic kernels, memory, tools, routing, provenance and heterogeneous compute.
- STRMKRD: ecosystem governance, identity, trust, build/deploy/recovery governance.
- Intelligent-Assistant-Nexus: Buddy brain, Orbit agents, memory, tools, observer/learner/verifier/builder/communicator roles, missions, knowledge and model routing.
- AIA-AC: model/artifact registration, inference receipts, lineage, controlled evolution and evidence-aware compute placement.
- iBare-Metal: physical-node preflight, operator approval, commissioning and physical evidence binding.

## Brain contract

PERCEIVE -> REASON -> BIND -> VERIFY -> AUTHORIZE -> ACT -> OBSERVE -> iReceipt -> FEEDBACK

Physical execution adds the hard boundary:

physical node -> read-only preflight -> operator approval -> iBare-Metal commissioning -> iBOBBY workload plane -> Matrix observation -> iReceipt / HRTF when physical evidence applies

## Native-model rule

Federation does not turn repository presence, a model catalog, an architecture description, or a generated hash into a live-model claim.

Promotion is evidence gated:

SOURCE_DECLARED -> AVAILABLE -> EXECUTED -> VERIFIED_PROCESS

Failures remain recorded. Corrections reference failures. A new execution must prove the correction. Only successful evidence advances the chain.

Physical capabilities remain ACTION_REQUIRED until authentic physical evidence is present.

## What is implemented here

The PoP repository now contains:

1. A pinned five-repository brain capability manifest at docs/brain/federated-brain-v1.json.
2. A TypeScript FederatedIBrain boundary at src/core/brain/federated_brain.ts.
3. The existing five git submodule integrations, preserving their independent histories.

This is the brain's integration and governance layer. It does not pretend that every upstream model is loaded into the current runner.

## Evidence boundary

A real model or capability becomes executable only when the corresponding runtime is present and an execution receipt records what actually happened. A physical-node claim additionally requires physical evidence.

