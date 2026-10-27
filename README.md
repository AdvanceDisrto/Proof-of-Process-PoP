# i™ iNNOVULIS — Threshold Receipt Mesh / Article XIX reference

**Scope: real source code and unit tests, not a live BFT network or issued legal certification.**

This review build addresses the three independently actionable failures in the previous blueprint: all jurors in one pod; containers with host-wide privileges masquerading as PUFs; and on-chain approval counts without cryptographic voting / rotation. Cryptographic attestations confirm that **configured keys endorsed a receipt hash**, not that any physical, legal or financial event is objectively true. No action in this repository can freeze somebody else's money, certify an indictment, or automatically transfer assets.

## Trust boundaries

1. Three separately registered **Ed25519 juror public keys**, each associated with one role. The signed payload commits to `receipt_sha256`, `policy_sha256`, a 128-bit request nonce, approval or rejection, issue and expiry timestamps. Each signed payload is verified under a separately pinned trust registry SHA-256. At least **2 of 3** distinct valid approvals are required, with a valid negative vote acting as a veto. The relay signs a new machine receipt (`ITM-RELAY-SIGNED-RECEIPT-v1`) whose permission flags remain **false**. The heuristic/consensus decision must never be mistaken for real-world causality or legal adjudication.
2. `contracts/EpistemicReceiptQuorum.sol` implements a **different cryptographic domain**: five secp256k1 Ethereum EIP-712 validator keys. Three distinct, ordered signatures bound to the chain, verifying contract, receipt root, validator epoch and short deadline confirm the root in a non-custodial registry. It does not independently verify juror signatures or ZKP proofs. Governance rotation/pause requires a **separate 3-of-5** governor-key quorum, typed data including epoch, nonce and deadline. Node key rotation always preserves five active node slots and increments epoch. No unilateral `owner` or `onlyArbitrator` key exists.
3. The Kubernetes manifests are **review-only, intentionally unpublishable** (use `registry.invalid`). Each juror is a different hardened Deployment with same-label anti-affinity. The relay and verifier are in different namespaces with explicit ingress/egress NetworkPolicies. **The CNI must be checked and an actual denied connection demonstrated**; the YAML itself proves no physical isolation, genuine PUF, or independent provider. TPM2 is a separate unprovisioned bare-metal reference with a device-plugin requirement, and cannot claim PUF authenticity on its own.
4. The optional API (`threshold.server`) binds **127.0.0.1** by default and requires *independently provisioned* pinned registry, raw 32-byte relay Ed25519 key (mode 0400), and a random bearer token. Payloads limited to 16KiB. No external forwarding, financial settlement, autonomous deployment, or remote origin is enabled.

## Verified development test commands

```bash
python -m pip install 'cryptography>=43,<48' 'pytest>=8,<10' 'fastapi>=0.115,<1' 'httpx>=0.27,<1' 'uvicorn>=0.30,<1' 'PyYAML>=6,<7'
python -m pytest -q tests/test_quorum.py tests/test_relay_api.py tests/test_k8s_review.py
cd contracts
npm install --no-audit --no-fund --ignore-scripts
npm test               # builds with solc 0.8.24 and executes adversarial tests in Ganache
```

CI compiles the actual Solidity bytecode, checks `3 of 5` and `2 of 3` failure/success cases, rejects duplicate/expired/wrong-domain attestations and proves governance key rotation/pausing in a throwaway EVM. No mainnet/testnet assets are deployed. Do not promote this to a production service without a security review, source-lock pinning, HSM integration, real CNI isolation checks, on-chain audit, and operator approval.

## API example

`POST /v1/quorum` accepts a **JSON document** containing: `protocol=ITM-JUROR-QUORUM-BATCH-v1`, `receipt_sha256`, `policy_sha256`, `request_nonce`, `attestations` with source `juror`, `decision`, `issued_at`, `expires_at`, `signature_hex`. Authentication uses a separately configured bearer token; a valid response contains the machine `evaluation` and an Ed25519 `relay_signature_hex`. No validation means no receipt. **Importantly, clients must independently verify the response signature and pinned relay key**; JSON label `QUORUM_APPROVED` alone is untrusted.

## Falsification and deployment gates

- 1 or 2 EVM votes cannot confirm; 3 distinct valid signatures can. Signatures expire and cannot be reused for other contract, chain, root or node epoch. Duplicate root rejected; high-s ECDSA rejected.
- Node rotation must require 3 of 5 governors, invalidate old keys and old node-epoch signatures, and keep five nodes. Governance nonce must advance for pause/resume/replacement. The current prototype has no recovery path if ≥3 governance keys are lost or compromised; that is a design review blocker.
- Valid source-signed approval alone cannot make false sensor measurements true. AI hallucinations cannot be universally detected by DAG topology alone. ZKP circuits prove a mathematical relation to declared inputs, not source integrity.
- Kubernetes scheduling and policy enforcement must be established with **runtime probes**, signed container images and attested physical inventory. Five containers is not evidence of five hardware roots; three cloud pods may share a control plane.
- Never claim an AND-threshold attack cost like `3/5 hardware AND 2/3 models AND 51% oracles AND 3/5 DAO` until **every gate is demonstrably wired together**, independent, and fail-closed. This reference does NOT implement an oracle majority, an HSM signature, a real PUF, BFT state-machine replication or financial escrow.

## Status legend

`LOCAL_TEST_PASS`: a concrete test passed. `CI_PASS`: remote workflow passed on an exact commit. `ACTION_REQUIRED`: lack of sufficient evidence or authorization. `BLOCKED`: no settlement or physical actuation. `NOT_DEPLOYED`: the repo is not the cluster.

Never label demos `IMMUTABLE REALITY`, `PHYSICALLY CERTIFIED`, or `CRIME PROVEN`.

