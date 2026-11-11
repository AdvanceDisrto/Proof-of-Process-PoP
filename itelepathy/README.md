# iNNOVULIS™ iTelepathy — opt-in typed-intent transport (software-only)

This is NOT neural thought decoding, BCI, medical-grade cognition capture,
zero-latency communication or a silicon PUF. Manual typed messages only.

- Native Z3 QF_LIA checks a *submitted* integer against a fixed recipient policy.
- Ed25519 authenticates sender envelope and receiver ACK against separately
  pinned identities. No self-asserted embedded public keys are trusted.
- Ephemeral X25519 + HKDF + AES-256-GCM encrypts message data for a designated
  recipient and authenticates envelope metadata.
- Receiver separately reruns native Z3, enforces allowlisted read-only commands,
  checks consent/expiry and records monotonic sender sequences in SQLite.
- No financial transfer, remote command, door unlock or external execution
  is implemented. Sender and receiver both start **consent disabled**.
- Only 127.0.0.1 transport is used. No external P2P propagation; the demo
  does not set up an independently operated witness or ZK proof.
- A signed acknowledgement contains **message SHA-256**, not message contents.
  It is a portable digital provenance marker, not an assurance of human intent.

Commands (Linux):

```bash
sudo apt-get install -y libz3-4 libz3-dev
python -m pip install 'cryptography>=41'
python -m unittest tests.test_itelepathy_ci -v
python -m itelepathy.demo
```

**Tessera-G / DAGE**: A trusted sender must have a valid digital iTP ACK before
an *application* may attach an intent-delivery status as a DAG node. Existing
Tessera-G tiles propagate dependency statuses but do not verify this
cryptography in hardware. The current iTP demo intentionally creates no such
hardware instruction and makes no behavioral/physical truth claim.

**Security limitations**: No clock attestation, revocation service, double
ratchet, anonymity network, persistent receiver key provisioning, cross-device
consent validation, biological ground truth, independently signed witnesses,
or formal verification of arbitrary natural-language intent. The replay DB
can be rolled back by an administrator. X25519 handshake here provides
ephemeral sender keys but **does not guarantee forward secrecy** if the long-term
recipient decryption key and captured ciphertext are compromised.

**Hardware corrections**: ATECC608C is an ECDSA P-256 secure element, NOT an
Ed25519 PUF. ESP32-C6 supports Wi-Fi 6 and Thread, not Wi-Fi 7.
This software makes no sub-millisecond or 'zero-latency' guarantee.
