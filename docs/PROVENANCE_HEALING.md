# i™ Continuous Provenance Healing

## Head

Current base: `6128b6d5907d38591f1b5c3fb70f1ee521c07661`.

The chain is append-only. A failure is never deleted, overwritten, or used as a reason to erase prior history.

## Required lifecycle

```
HEAD
  ↓
FAILURE OBSERVED
  ↓
iEf RECORDS FAILURE
  ↓
CLASSIFY DEPENDENCY SCOPE
  ↓
REPAIR / REPLAY
  ↓
RE-RUN AFFECTED EVIDENCE
  ↓
VERIFY
  ↓
REJOIN CURRENT HEAD
  ↓
CONTINUE
```

## Failure semantics

- REQUIRED_DEPENDENCY_FAILURE: blocks only the affected artifact/action.
- OPTIONAL_OR_UNRELATED_FAILURE: records degradation/action-required and does not globally block unrelated artifacts.
- Every correction references the failure it corrects.
- Replay creates new evidence; it does not mutate the old failure.
- The provenance engine continues even when an individual action halts.

## Current known failures at the base head

- `compute-control-mcp`
- `root-pytest`

These are recorded as observed failures pending actual failure evidence. No root cause is invented.

## Green criteria

A component is green only after its affected evidence is actually re-run and reports success. Overall promotion is green only when the required evidence for that artifact is green. Unrelated optional failures cannot masquerade as universal blockers.

## Receipt fields

`receipt_id, parent_receipt, repository, commit, branch, actor, action, timestamp, input_hash, output_hash, artifact_hashes, evidence, status, failure_code, correction_of, corrected_by, deployment, live_observation, anchor, provenance_hash`.

## Prediction rule

Prediction is advisory only. It may prioritize likely failure causes or next checks, but prediction never becomes verification. The receipt records the prediction and the subsequent evidence separately.
