# i™ Provenance Receipt Schema

The receipt covers the observable process rather than private model reasoning.

## Event types

`SOURCE_OBSERVED`, `BUILD_STARTED`, `FAILURE_DETECTED`, `iEf_CLASSIFIED`, `CORRECTION_STARTED`, `REPLAY`, `EVIDENCE_VERIFIED`, `STATE_REJOINED`, `DEPLOYMENT_CONTINUED`, `OBSERVED_LIVE`, `ANCHOR_SUBMITTED`.

## State rule

The process may halt an action; the provenance chain never halts.

## Verification rule

`PREDICTED` is never equivalent to `VERIFIED`. Green is emitted only from observed evidence.

## Rejoin rule

A replay must identify the failure being corrected and the current head it rejoins. Historical events remain addressable.
