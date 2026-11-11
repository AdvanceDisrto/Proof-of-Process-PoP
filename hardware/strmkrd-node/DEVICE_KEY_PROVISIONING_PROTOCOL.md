# STRMKRD Rev0 — Silicon Device-Key Protocol (PROVISIONING HOLD)

Status: Engineering manufacturing protocol only. No hardware was provisioned/locked. The modular interposer is not a FIPS-validated cryptographic module.

## Correct trust model

New design target: Microchip ATECC608C, with exact variant and SKU separately approved. ATECC608C performs ECDSA P-256, NOT Ed25519, and cannot be used as a fake Ed25519 signer. The QoW/PoP Ed25519 signers remain separate software identities. The product must explicitly version any device signature algorithm; hardware signing a hash is not proof that sensor data or solver axioms are truthful.

Different ATECC608C SKUs have different factory slot/lock policies. ATECC608C-TNGTLS/TFLXTLS often ship with pre-provisioned keys or certificate configurations. Blank configurable variants require careful config-zone/data-zone programming and irreversible lock steps. Some device signing commands refuse to operate until relevant zones are locked. No script in this repository executes irreversible Lock, config writes or GenKey operations.

## Physical provisioning and verification flow

0. **Isolated intake:** verify distributor, component SKU, bus/rail voltage, PCB revision, ESD conditions, actual package orientation, qualified operator, serial-number register response and jig ID. ATECC default 7-bit I2C address is usually 0x60 (0xC0 is its 8-bit I2C write address). Software-provided voltage numbers are not proof of voltage; independently measure VDD.
1. **Read-only inventory:** use Microchip CryptoAuthLib proper wake/command/CRC16 protocol to retrieve the 9-byte unique serial, configuration and lock status. Do not use an arbitrary register-pointer read at address 0x03. Raw serial uniqueness is not strong device attestation.
2. **Key policy review:** select authorized P-256 signing slot according to exact SKU, key rotation/lock behavior, certificate trust anchor, device/board association, audit-log retention, revocation, manufacturing operator roles, and recovery plan. Ensure private keys are never exported to the host or GitHub artifacts. Archival of public keys/CA certificates only.
3. **Two-person approval:** obtain documented dual sign-off before irreversible programming or locking. Program with version-pinned, vendor-reviewed CryptoAuthLib tooling at an isolated station and record irreversible operations. Not implemented in this repository intentionally.
4. **Independent challenge:** verifier generates unpredictable nonce; bind nonce, device serial, key slot, board ID, policy schema, evidence hashes and verifier challenge ID into domain-separated canonical bytes. Hash with SHA-256. Device emits ECDSA-P256 response through CryptoAuthLib. Verify signature offline with a pinned public key/certificate, anti-replay state and documented revocation policy.
5. **Software bridge:** validate the signature with algorithm=ECDSA-P256-SHA256; do not pass P-256 bytes into Ed25519 verifier. Only after separately verified trust anchors/provisioning/physical sensor calibration can a CIH adapter promote sensor evidence to physical tier. The existing software pipeline can then issue separate Ed25519 QoW receipts. No claimed on-chip Z3 solver or instant hardware zeroization.
6. **Acceptance:** test authentic signatures, bad signatures, wrong keys, nonce replay, bus short-read/CRC errors, power loss, key-slot policy and safe shutdown. Document that signatures establish private-key possession only; physical device authenticity requires real manufacturing trust chain evidence.

## Read-only computer acceptance

factory_provisioning_gate.py checks a versioned P-256 SHA-256 proof-of-possession JSON using a genuine ECDSA verifier. It never accesses I2C, never modifies device configuration, never claims FIPS 140-3, and always emits hardware_origin=NOT_VERIFIED unless a separate manufacturer-backed attestation process is performed. The local demonstration uses an ephemeral software test key only; it is not a silicon signature.

## Operator sign-off

- [ ] Real silicon read through vendor CryptoAuthLib and inspected physically
- [ ] Exact SKU, certificate and slot policy approved and provisioned in factory
- [ ] Two-person authorization for irreversible locks
- [ ] Public key + serial + board ID bound into validated factory record
- [ ] Independent P-256 challenge-response succeeds and rejects altered bytes
- [ ] Hardware signer signs only approved measurements, with durable counters
- [ ] Physical camera, calibration and security evaluation performed separately
- [ ] No undocumented Ed25519, FIPS Level 4, NATO or zeroization claims

Sources: https://github.com/MicrochipTech/cryptoauthlib and https://onlinedocs.microchip.com/oxy/GUID-D9C7E12A-2E8F-497A-B0A0-38A2BA302F6D-en-US-2/GUID-134F9AD5-FB18-4C5D-A6A7-69ED7F6F468B.html
