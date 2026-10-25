# Physical Integration Boundary

This layer adds typed adapters for TEE, OpenTimestamps, actuator/interlock evidence, exact command binding, and quarantine records.

It deliberately does **not** manufacture physical evidence.

- TEE evidence is accepted only after an external hardware quote verifier reports success.
- OTS evidence is accepted only after an external verifier has verified the proof against a Bitcoin block.
- Actuator evidence requires an observed healthy interlock and a 64-hex command hash.
- OTS and actuator hashes must both equal the Agentic Core `hypothesisHash`.
- Any mismatch is quarantined; missing/unverified evidence remains `ACTION_REQUIRED`.

The CI fixtures exercise the software boundary only. Boolean verifier results, fixture quote bytes, and fixture block heights are **not** live AMD/Intel/ARM/NVIDIA attestation, Bitcoin verification, or robot execution.

Production adapters must feed independently verified evidence into these interfaces. Until then the physical gate remains `ACTION_REQUIRED`.
