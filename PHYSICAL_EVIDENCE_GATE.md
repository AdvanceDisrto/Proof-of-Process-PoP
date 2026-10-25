# Physical Evidence Gate

The lab dispatch boundary is now explicit and fail-closed.

~~~
UNVERIFIED_INFERENCE
        |
        v
PHYSICAL EVIDENCE GATE
        |
        +-- missing/invalid TEE quote ----------> ACTION_REQUIRED
        +-- missing/invalid OTS anchor ----------> ACTION_REQUIRED
        +-- unhealthy actuator interlock --------> ACTION_REQUIRED
        +-- command hash mismatch ---------------> QUARANTINED
        |
        +-- all three verified + hash bound -----> LAB_DISPATCH_VERIFIED
~~~

## Evidence contract

A dispatch can advance only when all of the following are independently
verified:

1. teeQuoteVerified — a real hardware-rooted attestation quote has been
   cryptographically verified.
2. otsAnchorVerified — an OpenTimestamps proof has been independently
   verified against the Bitcoin anchor.
3. physicalActuatorInterlockHealthy — the physical device reports a verified
   safe interlock state.
4. commandHash exactly matches the agentic inference hypothesisHash.

The TypeScript implementation does not generate or verify those external
artifacts. It consumes their verified results at the boundary. Synthetic CI
fixtures exercise the state machine only.

## Certification boundary

LAB_DISPATCH_VERIFIED in CI means the software accepted a complete synthetic
evidence bundle. It does not mean a real TEE, Bitcoin anchor, subsea witness,
robotic actuator, or laboratory instrument was observed.

The production promotion remains closed until independent live evidence is
attached to the same inference receipt.
