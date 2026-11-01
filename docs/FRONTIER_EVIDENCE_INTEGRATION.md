# Frontier inference evidence integration (review candidate)

This directory integrates **OpenAI, DeepSeek, Groq, local Ollama, and RunPod async status** as evidence-producing adapters. It does not replace the PoP proof engine or claim an existing model/hardware runtime is online.

## Entry points
- `integrations/frontier_evidence.py`: `generate(prompt, provider_name, allow_external=...)` and `RunPodAsync`.
- `tests/test_frontier_evidence.py`: deterministic, mocked transport tests.

## Gates and source of truth
- External inference requires an explicit `allow_external=True` for each call. No automatic vendor fallback.
- RunPod submission requires explicit `authorized=True` and an existing configured endpoint and credential.
- Local Ollama is fixed at loopback, and its reported model name **does not attest the checkpoint**.
- Do not put PII or confidential data in third-party prompts without an independent authorization and data policy.
- The RunPod input `batch_data` is **a proposed custom-worker schema**, not a documented universal RunPod batch format. Worker compatibility must be demonstrated before deployment.
- API response IDs and model fields are provider-reported, not independently authenticated model/checkpoint evidence.
- The observation includes a deterministic SHA-256 for integrity checking, but **it is UNSIGNED**.
- A trusted signing key, independent PoP verification, persistent append-only log, external witness, checkpoint attestation, and TEE must be verified separately. Do not promote `UNVERIFIED_INFERENCE` to `VERIFIED_PROCESS` automatically.
- PoP's existing physical gate remains unchanged. No relay, SCADA, financial action or paid resource allocation is introduced.

## Suggested local checks
```bash
python -m unittest discover -s tests -p test_frontier_evidence.py -v
python -m compileall -q integrations/frontier_evidence.py tests/test_frontier_evidence.py
```

Live provider execution must be performed only in an authorized environment with corresponding server-side API credentials or a reachable Ollama service. Keep secrets out of output, Git and receipts. A RunPod job requires a custom batch-aware worker. Review the repo's existing receipt APIs before wiring a trusted signer; this change deliberately does not invent an iTensor signing interface.

## Delivery and limitations
This is a **draft integration** targeting `AdvanceDisrto/Proof-of-Process-PoP`, not a full ecosystem import. The actual tests, CI, live model calls, iTensor dual signatures, and external anchoring must be observed independently. Merge only after review and authorization.
