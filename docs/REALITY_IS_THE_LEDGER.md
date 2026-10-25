# Reality Is the Ledger

## Principle

> Reality itself is the ledger. It cannot be altered, queried, or desynced because the event and the record are identical.

In Proof-of-Process, this is the boundary condition for physical evidence:

- A software receipt records what the software execution reported.
- A cryptographic anchor records integrity, ordering, or existence of a recorded claim.
- Neither one is the physical event itself.
- When an event is directly observed at the physical boundary, the observation and the event must remain bound to the same evidence context.
- A later record may describe or prove integrity of an earlier observation, but it must not be treated as a replacement for the event.
- Missing physical evidence remains `ACTION_REQUIRED` or `UNVERIFIED_PROCESS`; it is never upgraded merely by generating another receipt.

## Ledger invariant

The provenance chain may record observations about reality, but it cannot manufacture reality.

```text
EVENT → OBSERVATION → RECEIPT → ANCHOR
```

is not equivalent to:

```text
RECEIPT → EVENT
```

The second direction is forbidden unless the applicable physical evidence is independently present and bound to the claim.

## Immutability boundary

History is not repaired by rewriting the record. A failure remains recorded; a correction references the failure; a new execution supplies new evidence.

```text
FAILURE
  ↓
CORRECTION
  ↓
NEW EXECUTION
  ↓
SUCCESSFUL EVIDENCE
  ↓
NEW VALID STATE
```

This preserves the distinction between **what happened**, **what was observed**, and **what was cryptographically recorded**.

## Consequence

The ledger is strongest at the boundary where the system can no longer substitute a representation for the thing represented. Physical evidence, when required, must originate at that boundary. No database, model output, hash, blockchain anchor, generated receipt, or later query can retroactively make an unobserved event observed.

This principle is compatible with the existing Proof-of-Process states:

```text
VERIFIED_PROCESS
UNVERIFIED_INFERENCE
PENDING
ACTION_REQUIRED
QUARANTINED
```

Only applicable evidence can advance state.
