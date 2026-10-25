# PoT Vonage + Multi-Chain + iMobile Cellular Layer

This layer turns the requested architecture into deterministic software contracts.

## Built surfaces

- 30 Vonage PoT invention contracts across six product surfaces.
- Multi-chain quorum router for Bitcoin OTS, Ethereum EAS, Polygon EAS, Solana, and L2 evidence.
- iMobile Cellular Orchestra quorum receipt with device TEE and gNodeB edge-attestation inputs.

## Fail-closed law

Provider/network/hardware evidence is input, not fabricated by these modules.

- missing provider evidence -> ACTION_REQUIRED
- cryptographic binding failure -> QUARANTINED
- insufficient independent chain confirmations -> PENDING
- unauthorized edge or missing TEE -> QUARANTINED
- sensor disagreement -> ACTION_REQUIRED
- receipt mismatch -> QUARANTINED

CI can verify state transitions and receipt construction. CI cannot certify a live carrier, blockchain, TEE, gNodeB, or actuator.
