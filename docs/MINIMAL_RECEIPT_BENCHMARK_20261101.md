# Receipt T1/T2: 10k local benchmark (non-production)

Executed locally in a Linux Python 3.13.5 environment with cryptography; 10/10 regression tests passed after fixing InvalidSignature handling.

Observed 10,000 operations:
- T1 mint median: 38.278 µs
- T1 verification median: 111.970 µs
- T2 full warrant verification median: 218.336 µs
- Receipt JSON size: 589 bytes
- Mint loop wall time: 0.465980258 s; verification loop wall time: 1.169746061 s.
- Illustrative cost for **both mint + verify**, at an **unverified assumption** of $0.024 per billed vCPU hour, 100% sustained use: about **$0.00109 per million receipts**. NOT a measured cloud bill.
- No GPU throughput, RunPod cluster, production identity, KMS, external timestamp, blockchain, actual model inference or physical receipt printing was observed.

Security boundaries:
- The timestamp in a signed body is self-declared; Ed25519 does not authenticate wall time or source identity without independently enrolled keys.
- JSON sorted-keys canonicalization is not strict RFC 8785 JCS.
- T2 grade asserted by source is limited by independent verifier policy, and a warrant is attribution, not semantic proof.
- No evidence establishes that this is the **global cheapest method**, and purported competitor prices are not apples-to-apples.
- Prior example Merkle algorithm (sorted leaves + duplicated odd leaves) must not be called RFC 6962.
- Screenshot shows RunPod **Create cluster** page; no actual allocated GPU cluster established.

Full source and exact benchmark observation is downloadable as the local conversation artifact, separately from the GitHub files in this PR. GitHub CI must independently test its committed version.
