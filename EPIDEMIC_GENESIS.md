# Epidemic Genesis Intelligence

The repository's epistemic-genesis layer models a variant as a transmissible method,
claim, representation, practice, or receipt. Genesis is generation/mutation/recombination.
The epidemic is graph propagation, selection, retention, forgetting, and quarantine.

## Generate-and-test

Each agent has a generator and a tester. A receipt can provide a strong self-consistency
signal without establishing external truth. The model therefore keeps receipt strength
separate from external verification.

## Population dynamics

For a variant x, exposure pressure is driven by adopted neighbors. The model exposes
R0 and effective Rt, mutation pressure, fidelity, contradiction detection, and quarantine.
It is intentionally a bounded executable model rather than a claim that the deployed PoP
service is an autonomous AGI.

## Honest boundary

A high-R0 variant can spread confidence quickly when its receipt is persuasive but its
external verification is weak. A strong external checker is what distinguishes propagation
of confidence from propagation of verified correctness.

Physical network evidence remains VERIFIED_PROCESS only. No network telemetry promotes the
physical gate to MEASURED_PASS.


## Recursive application: eGi tests eGi

The model is itself an epistemic variant. Therefore its own evidence is classified by the same rules it applies to other variants.

- File presence is an **existence receipt**, not a function receipt.
- Unit/simulation tests are **behavior receipts** when they drive non-degenerate mutation, rejection, propagation, or quarantine cases.
- Render build/deploy proves deployability, not model validity.
- The external calibration harness consumes an observed adoption curve and can return CALIBRATED or QUARANTINED; it must not silently promote a failed fit.
- The current calibration fixture is the Coleman-Katz-Menzel tetracycline diffusion dataset distributed by CoMuNeLab. The fixture is derived from the published node adoption-date field; codes 18/98/99 are excluded from the observed-adoption denominator because they represent no prescription or unavailable data. The resulting fixture has 17 monthly cumulative adoption points over the observed-adoption subset.
- A calibration attempt is a behavior receipt. A successful calibration is a separate claim and remains ACTION_REQUIRED until the stated error threshold is met.

### Tester observability

Every substantive claim should name its tester and whether the tester's output is machine-readable. This prevents a tester from becoming a decorative reference. In particular, the push-triggered GitHub Actions result remains an observability gap when the connected endpoint cannot expose the specific run result. That gap is recorded in tester_observability.json rather than hidden in prose.

### Definitional boundary

intelligence = quality of generation + discrimination of testing is the project's operational definition. It is DEFINITIONAL, not an empirical verification result.

### Current recursive result

The eGi layer currently demonstrates executable behavioral tests and an external calibration attempt, but it does not claim that the model is calibrated. If the calibration tester fails, that failure is itself the correct eGi output: quarantine the model claim, retain the evidence, and revise the model or its parameters.