# i™ rGPU Open Telemetry Trust Boundaries v0.2

- **Not zero-trust by default:** the viewer refuses green verdicts until an
  operator manually pins both public key and SHA-256 fingerprint, obtained
  independently from the WebSocket server.
- **Signature is not provenance of reality:** Ed25519 proves the possession of
  a *software* private key that signed given bytes. It does not prove hardware
  key generation, TPM PCR states, calibrated INA226 measurements, or authentic
  sensor placement. Replayed genuine signed receipts can be shown on a wrong
  object unless the subject is bound and independently checked.
- **Scoped claims:** Genesis is `PROCESS_OBSERVED` and records physical energy
  `null`. Demo-only true/refuted verdicts use tier `SYNTHETIC_DEMO`.
- **Journal:** SQLite WAL + FULL sync, signed hash chain, crash/restart identity
  persistence and startup integrity scan. Root administrators can restore an
  older full database or steal the unencrypted PEM. This is NOT an externally
  immutable or Byzantine-consistent journal. The current browser checks the
  contiguous signed chain from genesis but cannot know about a hidden newer
  branch without an independently witnessed checkpoint.
- **Clock/freshness:** epoch nanoseconds in JavaScript lose integer precision.
  Neither browser nor print preview uses this timestamp as independent freshness
  evidence. Counter-signed trusted time, expiration and revocation remain future
  requirements. The server does not label receipts VALID_FRESH.
- **QR:** `rgpu1z:` is compression of a *complete digitally signed public
  envelope*. Compression does not provide authenticity; Ed25519 still must
  verify. `rgpu1` is NOT an `ipqr1` Open Receipt v1.0 payload.
- **Browser:** no CDN; JavaScript has a strict self-only CSP. The dashboard
  verifies signed payload bytes using Ed25519 native WebCrypto. If WebCrypto
  is unavailable or anchor unpinned, the UI fails closed. The local HTML/JS
  can still be modified by a compromised host: for high assurance, run the
  verifier from a separately trusted, reproducibly built device/app origin.
- **Transport:** loopback-only HTTP and WebSockets, `Origin` validated for WS,
  `Host` restricted to localhost/127.0.0.1; operator-only synthetic POST uses
  an unpredictable shared secret not stored in the browser. HTTP loopback is
  not suitable for public exposure; use authenticated HTTPS reverse proxy,
  mTLS and hardened ops before any non-local use.
- **Printer:** manual preview by default. `TcpPrinter` writes are only delivery
  *attempts*, and cannot establish paper feed or physical authenticity.
- **Medical/physics:** never use this as medical advice or legally dispositive
  evidence; no patient records in this prototype. The signed demo does not
  establish power conservation, impossibility of forging physical values,
  carbon or thermodynamic consistency, or chain of legal custody.

## Known pending gates

Independent public-key provisioning; key rotation/revocation; certificate
attestation, trusted time, ledger checkpoint/witness; hardware signer (TPM2 or
ATECC P-256), physical INA226 measurement, FPGA/programmer connection,
physical printer and independently witnessed paper; protected multicore and
multi-host network infrastructure; deployment security review; clinical validation.
