# Universal Signature Engine (USE)

The Universal Signature Engine is the provenance boundary for iTensor signatures.

## Principle

A signature is an observed imprint that can be evaluated against evidence. An author is the process, entity, or organizing force attributed to that imprint.

The engine separates:

1. Observation — what was actually captured.
2. Attribution — who or what is claimed as the author.
3. Verification — whether available evidence supports the claim.
4. Ledger binding — where the observation is recorded.
5. Provenance continuity — how new evidence relates to prior evidence.

A SHA-256 digest binds data to a representation. It does not authenticate the producer. Ed25519 can authenticate a signed claim, but a valid signature does not prove that the underlying physical event happened. Physical, biological, geological, and cosmological signatures therefore require explicit evidence adapters.

## Six provenance tiers

| Tier | Author | Example imprint | Ledger |
|---|---|---|---|
| 1 | PHYSICS | CMB, gravitational waves, spectral lines | SPACETIME |
| 2 | GEOLOGY | stratigraphy, fossils | CRUST |
| 3 | BIOLOGY | DNA, biometrics | GENOME |
| 4 | HUMAN | marks, seals, electronic authorization | PAPER / BLOCKCHAIN |
| 5 | MACHINE | Ed25519, machine receipts, C2PA | BLOCKCHAIN / PAPER |
| 6 | CIVILIZATION | technosignatures | GALAXY |

These are provenance classes, not interchangeable proof strengths. A CMB observation is not cryptographically signed by the universe, and a blockchain timestamp does not prove the physical event that preceded it.

## AI-brain integration

The intended Buddy/iTensor loop is:

PERCEIVE → CLASSIFY AUTHOR → CAPTURE IMPRINT → CHECK IDENTITY → VERIFY EVIDENCE → BIND LEDGER → ISSUE RECEIPT

The AI may propose an interpretation. The verification layer decides the evidence state.

Supported states:

- VERIFIED
- UNVERIFIED_INFERENCE
- PENDING
- ACTION_REQUIRED
- QUARANTINED

Prediction is never verification.

## Process law

USE follows the Proof-of-Process invariant:

> Failure stays recorded. Correction references the failure. New execution proves the correction. Only successful evidence advances the chain.

The engine therefore never converts unsupported observations into VERIFIED. Domain verification must arrive through an evidence adapter that produces a new verification result.

For cryptographic machine signatures:

- the canonical payload is signed, not surrounding prose;
- the receipt hash identifies the represented evidence;
- Ed25519 authenticates the signer/key;
- parent and correction references preserve history;
- external anchors provide ordering/existence evidence;
- no digital layer is allowed to claim physical reality merely because a signature is valid.

## Constitutional boundary

The six-tier matrix is a useful model of provenance across reality, but it is not a claim that every physical imprint is literally unforgeable or mathematically self-authenticating. The engine records what evidence exists and what that evidence establishes.

**No participant edits the past process record. A participant can only produce a new process event that references prior evidence.**
