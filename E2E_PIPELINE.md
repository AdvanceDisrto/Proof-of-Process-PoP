# Full E2E Agentic Core + Autonomous Translation

The software E2E path is:

Fabric payload
-> hash-bound agentic inference
-> UNVERIFIED_INFERENCE receipt
-> physical lab gate
-> ACTION_REQUIRED without attestation
-> LAB_DISPATCH_VERIFIED with a test attestation.

The agent never upgrades its own hypothesis to truth.

The lab gate never treats the presence of an inference as physical authorization.
A missing lab TEE is fail-closed.

## Evidence boundary

The CI test uses a synthetic payload and a test attestation string. It proves the
software state transitions only. It does not prove a live LLM, live TEE, robotic
arm, synthesis execution, or OTS/Bitcoin anchor.

A production dispatch gate must additionally verify the TEE quote cryptographically,
bind the command to the exact inference receipt, record a signed physical execution
receipt, and independently verify the external timestamp/anchor before any claim of
live certification.
