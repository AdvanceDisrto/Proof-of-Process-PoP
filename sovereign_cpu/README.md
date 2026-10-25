# iTensor Sovereign CPU Gateway

CPU-only execution boundary for iTensor, iWay, iProof and Gaia.

## Included

- local llama-cli inference gateway with a glass terminal UI
- signed IPROOF-v1 receipts binding request, model, engine and output SHA-256 values
- CPU thread count plus sampled CPU-load and RAM telemetry during inference
- dependency-free recurrent SSM smoke model
- offline tokenizer
- optional PyTorch CPU SSM trainer for real local training from scratch on a supplied corpus

## Run inference

Build llama.cpp separately and place llama-cli at the configured engine path. Place a GGUF model at open_intelligence.gguf or set SOVEREIGN_MODEL. Then run python -m sovereign_cpu.gateway and open the local address shown by Flask.

The gateway accepts no provider URL or API key and invokes only the configured local executable. Missing model/engine and non-zero engine exits fail closed with ACTION_REQUIRED.

## Train from scratch on CPU

Install the optional CPU training runtime from requirements-cpu-training.txt. Then run:

    python -m sovereign_cpu.train_engine corpus.txt --steps 1000 --dim 128 --out sovereign_cpu_model.pt

This is genuine local gradient training of the included recurrent SSM architecture. It is intentionally a small proof model, not a claim of frontier-equivalent intelligence. Foundation-scale capability requires a measured corpus, parameter count, compute budget and evaluation suite.

## Evidence boundary

A receipt binds declared execution evidence. It does not prove that an answer is true, that a machine is honest, or that a physical air-gap exists. LOCAL_ONLY_DECLARED is a software execution policy; physical isolation requires a separate PhysicalEvidenceGate.

Constitution: Failure stays recorded. Correction references the failure. New execution must prove the correction. Only successful evidence advances the chain.

The receipt can record execution evidence; it cannot manufacture reality.
