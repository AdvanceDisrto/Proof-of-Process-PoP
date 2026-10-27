# iNNOVULIS Causal Integrity — What a DAG Can Actually Prove

The supplied diagrams show several distinct scientific modeling situations. **A graph represents assumptions.** A signature protects its bytes from undetected alteration; it does not automatically validate those assumptions.

| Graph node Z | Arrow pattern | Correct handling in receipt analytics |
| --- | --- | --- |
| Confounder | `Z → X`, `Z → Y`; optionally `X → Y` | Measure plausible pre-treatment confounders before estimating X's effect on Y; unmeasured confounders remain possible. |
| Collider | `X → Z ← Y` | Do not condition on Z without a clear identification argument: this can create spurious dependence. |
| Instrument | `Z → X → Y` | An instrument's exclusion, relevance, and independence assumptions require study; a cryptographic sensor is **not** an instrument by default. |
| Mediator | `X → Z → Y` | Intervening on / adjusting for Z changes the estimand; treat direct vs total effects separately. |

The network visualizations in the uploaded screenshots depict time-varying biological interactions. They are useful analogies for dynamic provenance graphs but **not a proof of quantum hardware** or the existence of an iNNOVULIS sensor network.

## Testable causal controls in a SaaS pipeline

- Define X, Y, time order, sampling scheme, confounders, exclusions and missingness before analysis. Include source identifier, model version and analyst signature as evidence *metadata*.
- Apply validity rules for timestamps, source identifiers, replay resistance, missing fields, duplicates, schema drift, units and out-of-range values.
- Keep original observations and transformations so the analysis can be independently recomputed. A machine may reject invalid source signatures; it cannot algorithmically establish "no hidden confounders".
- Independent corroboration: compare sensor or transaction to separate authenticated source, not another copy of the same data.
- Produce derived receipts including estimand, DAG digest, pre-registered assumption list and confidence/uncertainty, alongside machine signatures and explicit data-lineage boundaries.
- For regulated decisions or possible discrimination involving ethnicity, sex, income, medical status or other protected attributes, require privacy impact review and human oversight. Do not write sensitive personal data to public evidence ledgers.

**Falsification gate:** `SIGNATURE_VERIFIED` and `CAUSAL_CLAIM_SUPPORTED` are separate states. The reference implementation never claims the latter solely from an authenticated event log.
