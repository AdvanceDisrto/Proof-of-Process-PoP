# iTensor Sovereign CPU Gateway

CPU-only execution boundary for iTensor, iWay, iProof and Gaia.

A successful run binds request SHA-256, model-file SHA-256, inference-engine SHA-256, CPU thread declaration, resource observation, output SHA-256, reproduction command and Ed25519 signature into IPROOF-v1.

This does not prove answer truth, machine honesty, or physical air-gap. LOCAL_ONLY_DECLARED is a declared execution policy. Physical isolation requires a separate physical evidence gate.

Run with a locally built llama-cli and GGUF model:

    python -m sovereign_cpu.gateway

POST JSON to /prompt:

    {"prompt":"verify operational state"}

Missing model/engine and non-zero engine exits fail closed with ACTION_REQUIRED.

Constitution: Failure stays recorded. Correction references the failure. New execution must prove the correction. Only successful evidence advances the chain.

The receipt can record execution evidence; it cannot manufacture reality.
