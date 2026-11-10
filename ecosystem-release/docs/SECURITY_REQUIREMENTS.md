# Open verification and adversarial system requirements

Threats include forged/modified receipts; genuine receipts attached to the wrong subject; replay of stale approvals; retired/compromised keys; malicious issuer or colluding witnesses; malicious printer, screen or QR; fake INA226/MCP9808 input; hostile WebRTC or NFC handshake; HTML sandbox escape; and tampered local SQLite data.

Mandatory controls:

1. Pin public issuer trust anchors independently of the scanned code. Keys embedded in the QR are untrusted until verified against an external registry.
2. Verify complete exact bytes, signature, claim subject, nonce, issuance window, expiration, witness and revocation policy, and independent log freshness. Missing inputs must produce **UNRESOLVED/REJECTED**; never infer that signatures prove truth.
3. Z3 SAT means satisfiable **under encoded premises**. UNSAT means contradiction in those premises; it does not prove a medical diagnosis false or a prosecution malicious.
4. Identity and human judgment remain separate. Three demo keys from one program are not three independent witnesses; no model can establish source reliability by self-declaration.
5. Local signed receipts can be faithfully transported by paper, screen, NFC, BLE or optical codes but these carriers can be copied or substituted. Subject and freshness binding is necessary.
6. iP.CiH must require a human launch action and restrictive sandbox after independent verification. Do not automatically grant camera/microphone, storage or executable privilege; no claim that RAM is automatically wiped on tab closure.
7. Energy samples measure power over time subject to sensor accuracy and spoofing. No Landauer calculation or Joule count uniquely demonstrates a particular computation.
8. All CI jobs and smoke tests are non-destructive, software-only, unprivileged and local-first. No key-zone programming, actual FPGA flashing or public WebSocket binding.
9. Cryptographic, clinical and legal concerns require separate responsible authority and documented review. A receipt is *evidence*; it is not automatically admissible, an identity certificate, a regulator approval or a liability shield.
10. The SHA256 linked test transcript can be rewritten if the root isn't externally pinned or attested. CI build-provenance and independent comparison of source/artifact hashes are needed.

Fail-closed statuses: `PASS_SOFTWARE_ONLY` for executed successful tools, `FAIL` for nonzero exits or missing success markers, `NOT_RUN` for unexecuted software gates, `PENDING_INDEPENDENT_EVIDENCE` for all physical/external gates.
