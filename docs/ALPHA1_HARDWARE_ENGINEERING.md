# iNNOVULIS Model Alpha-1 — Physical Receipt Device
**Engineering feasibility design, not a verified product or fabricated prototype.**

## 1. Functional system architecture

```text
Human button / optional authenticated user input     Digital issuer feed (offline transfer)
                   |                                         |
             Input conditioner                    Import verifier / signature checks
                   |                                         |
             Monotonic event gate <--------------------------+
                   |
         MCU / immutable boot policy
          |           |           |
     Secure element  sensors    trusted key registry (provisioned)
       (sign only)    |            |
          +--------> CANONICAL RECORD HASH <----+
                         |
                 ECDSA/Ed25519 signature via qualified signing module
                         |
                 two-phase write + verification
                      /     \
          append-only/WORM    physical QR / micro-engrave / label
            local log                |
                      \             /
                independent scanning & verification
```

### Practical baseline bill of functions

| Proposed block | Feasible baseline | What is **not** established |
| --- | --- | --- |
| Human intent | Physical confirmation button + operator credential | Unforgeable intent, absence of coercion |
| Signal / environment | Temperature, pressure, event counter, device clock with uncertainty | Absolute ambient truth, unattested nanosecond UTC |
| Compute / state | Locked-down microcontroller with measured/verified boot, bounded RAM and fault monitoring | A device with no state, no memory and no failure modes |
| Hardware key | Audited secure element/HSM with non-exportable EdDSA *where available*; test component capability and firmware | PUF automatically equals a private key or zero key-extraction risk |
| Local archive | Transactional flash or other tested tamper-evident, bounded log; an external append-only witness improves rollback detection | Local-only archive cannot be rolled back by privileged attacker |
| Physical output | Machine-readable QR/Data Matrix etched or laser-marked on rated medium; optical scanner reads payload | Dynamic holography or unforgeability via thermodynamics |
| Housing | Tamper-evident seal, detection switches, optional zeroization | Every tamper attempt causes certain destruction |

**Important engineering constraint:** A fully air-gapped physical unit cannot receive remote software commands or broadcast telemetry. A physically separate, authenticated one-way export carrier can bridge receipts, but the bridge requires an explicit threat model. For regulated time, deploy a qualified RTC or authenticated time source; an air-gapped RTC clock is not automatically authoritative.

## 2. Substrate material candidates

**Baseline A, recommended for first prototype:** Engraved sapphire **window or rigid coupon** bonded to metal/polymer holder. Synthetic sapphire is crystalline aluminium oxide (`Al₂O₃`), hard and optically transparent but brittle; it is *not* inherently a flexible crystalline polymer. Test laser mark readability, abrasion, humidity, thermal cycle and impact.

**Baseline B:** Flexible polycarbonate/PET tamper-evident laminate printed or laser marked with a secure physical label; favorable for wallet-sized or curved receipts but not an atomic engraving method. Use physical removal evidence where possible.

**Research candidate C:** Sapphire-coated polymer laminate / thin-film optical marking, only after third-party materials testing. Claims about lanthanide dopants, reversible refraction indices, molecular displacement, or self-destruct threshold require controlled microscopy and accelerated-aging measurement, not user-interface simulation.

## 3. Receipt payload (not personally identifying by default)

```json
{
  "protocol": "ITM-ALPHA1-DEVICE-RECEIPT-v1",
  "device_key_id": "registered-device-public-key-reference",
  "event_counter": 1,
  "intent_commitment_sha256": "64-lowercase-hex",
  "evidence_commitment_sha256": "64-lowercase-hex",
  "capture_time": {"unix_ms": null, "time_source": "UNVERIFIED"},
  "device_attestation": {"verified": false, "evidence_digest": null},
  "physical_media": {"method": "PENDING_TEST", "readback_verified": false},
  "issuer_signature": "64-byte-Ed25519-signature-hex-only-after-real-signing",
  "truth_claims": {"external_event_verified": false, "human_authority_verified": false}
}
```

Signature binds a versioned canonical byte encoding; the printed QR should contain either the complete minimal signed receipt (capacity permitting) or a content hash **plus authenticated retrieval instructions**. A raw digest alone does not prove what is printed is true. A real-life long-lived receipt requires revocation, custody, key rotation, independent anchoring and archiving procedures.

## 4. Verification and qualification plan

1. Characterize readout error, QR symbol capacity and post-abrasion optical contrast; maintain raw measurement dataset.
2. Confirm hardware RNG, key generation, export protection and EdDSA capability on the **actual selected device**; review vendor certifications, physical attacks, power fault injection and side channels.
3. Implement monotonic counter and power-cut tests. Measure durability and state recovery after 1,000 controlled restarts and interrupted writes, with falsification criteria established before testing.
4. Calibrate sensors, record uncertainty. Never infer coercion from temperature or radio fluctuations.
5. Verify credential binding, optional operator authentication, signature and trust chain with an entirely separate validator.
6. Test supply-chain custody: scan at origin and destination, compare independent events, quarantine discrepancies.
7. Run threat model, ESD/EMC qualification and applicable product electrical safety/consumer regulatory checks before commercial hardware claims.
8. Build a real physical prototype, collect third-party laboratory receipts and only then advance beyond `HARDWARE_CONCEPT`.

## 5. Device maturity gate

`HARDWARE_DESIGN_DRAFT` — No manufactured Alpha-1 is attested by this package. No 4.82 THz resonance, 14-attosecond latency, 99.98% coherence, 1.2 mK tamper delta, 1.63 GB/s or physical certification percentage was measured. UI mock metrics must carry `SIMULATED` badges.
