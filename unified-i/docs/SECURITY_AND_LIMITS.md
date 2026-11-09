# Security Threat Model & Acceptance Boundaries

## Threats covered in executable tests

- Signed claim body mutated after signing: signature verification fails.
- Missing or substituted public-key pin: fails closed.
- Expired or future-dated software receipt: fails closed.
- Wrong subject, changed evidence digest, changed source tier, rollback in strict sequence floor: rejected.
- Non-finite numerical metadata, arbitrary free text posing as a formal proof: rejected or UNRESOLVED.
- Local HTTP API access without operator token: 401.
- Local claim request without deliberate synthetic-demo consent: 403.
- MCP9808 register manufacturer/device mismatch or I²C failure: no sample accepted.
- P-256 signer callback absent, signature failure or mismatched pinned key: no acceptance.
- Physical acceptance gate without actual required external evidence: remains PENDING.
- iStick provisioning: impossible through included scripts; forced nonzero HOLD.
- ESC/POS bytes are generated but never sent to real hardware by this package.

## Risks not eliminated

1. **Issuer key compromise**: existing ipQR v1 verifier supports signed revocation snapshots; production needs trusted distribution, clock, rollback defense and historical key-compromise policy. This unified manifest itself does not implement full revocation.
2. **Trust-anchor substitution**: the signed receipt's embedded key is not trusted. Production pins need an out-of-band approved key ceremony.
3. **Data origin authenticity**: a signature doesn't establish that a sensor measured a physical target or that an AI prediction was true.
4. **Sensor spoofing**: bare I²C can be replayed or spoofed. Separate tamper evidence, hardware attestation and external calibration are not implemented.
5. **SQLite rollback**: local journal is hash-linked, not immutable without signed external checkpoints and an independently verified latest serial.
6. **Printer substitution**: an attacker can replace a receipt with another legitimate signed receipt. Subject binding, evidence freshness and human inspection remain necessary.
7. **Web/Capsule code risk**: signed arbitrary HTML is not safe. Existing iP.CiH uses bounded known templates, explicit user launch approval and sandbox restrictions; no permanent storage or guaranteed zero trace is claimed.
8. **WebRTC metadata**: standard WebRTC typically exchanges ICE candidates/signaling data; STUN/TURN providers and peers can observe metadata. Media stream encryption is not biometric identity or liveness proof. No WebRTC feature is part of this release.
9. **Color-optics**: current iMorphus matrix has only exact-pixel decoding; printed/camera robust performance is not tested. Fake QR finders are not standards-compliant QR bootstraps.
10. **Legal/medical**: model agreement and Z3 formalization cannot override experts or meet legal/clinical regulatory requirements without domain-specific validation.
11. **Manufacturing**: constant GND plane cannot make power analysis mathematically impossible. No DPA/EMA, USB SI, EMI/ESD, ingress or shock certification has been performed.

## Identity and physical receipts

A physical secure-element signature must be verified over a challenge that cryptographically binds the receipt digest, nonce, explicit issued/expiry times and signer's key ID. The currently implemented P-256 challenge is tested only with a software callback and deliberately reports `hardware_provenance_verified=false` even on cryptographic success. Separate independent device attestation is needed for source upgrades.

## Data minimization

No PHI, child records, legal complaint details, biometric templates, or live BCI captures are accepted or stored by the integrated demonstration. The immutable-ish receipt hash doesn't imply human consent and can leak metadata if made public. Production requires a privacy threat model and retention/deletion policy.

## Legal/health language

Never present system receipts as a medical diagnosis, a court order, proof of a crime, a guaranteed liability shield, or a replacement for qualified human judgement. A demonstration with signed inputs is only proof of those digital inputs and the bounded calculation under declared assumptions.
