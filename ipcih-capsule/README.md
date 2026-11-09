# i™ iNNOVULIS iP.CiH / iMorphus v0.1

A real **software-tier** signed optical *app capsule* + independent open client-side WebCrypto verifier + experimental color carrier. It is **not** hardware-backed, anti-deepfake, a medically reliable oracle, a proof-of-physics or a WebRTC call.

## What works

- `ipcih.core.Issuer` signs a **bounded deterministic passive canvas app** using a real Ed25519 software key. The payload also binds its SHA-256, expiry, nonce, declared issuer, claim, and explicitly `SYNTHETIC_SOFTWARE` evidence tier.
- No self-trusting key. The verifier **requires an independently pinned Ed25519 public key**. A key embedded in the scanned object is *never* authoritative.
- The encoded full signed payload fits a standard QR for the demonstrated small app; decoding it obtains the exact signed bytes. The bootstrap is a separate valid standard QR containing a digest+key fingerprint, which alone **cannot** launch the app.
- `web/verifier.mjs` uses real native `crypto.subtle.verify('Ed25519')` and verifies the exact signed Python canonical bytes (integration tests run with Node native WebCrypto). It separately checks signature, expiry, and application hash before enabling the **manual** launch control.
- The untrusted app executes in an iframe with `sandbox="allow-scripts"`, no `allow-same-origin`, no camera, no microphone, no network access via injected CSP; manual user approval required. Signed code can **still be malicious**; this is an experiment, not a security audit of arbitrary signed software.
- The optional visual matrix effect is a user-interface animation, **not quantum physics**.
- Experimental 4-color `iMorphus` grid encodes data as 2-bit colored cells and decodes *exact pixel files*. It has CRC and SHA-256 checks. **This is not ISO QR, JAB Code, a camera-robust optical codec, nor a 6MB carrier.** Standard phones cannot be expected to read the second layer automatically.
- `ipcih.auditor.audit_assertion` verifies only bounded **submitted integer comparisons**; untranslatable medical, legal, or frontier-model claims return `UNRESOLVED`. There is no theorem prover or remote AI model integration in this module.

## Tests and smoke

```bash
sudo apt-get install -y libzbar0
python -m pip install -e .
python -m unittest discover -s tests -p 'test_*.py' -v
node --test tests/test_browser.mjs
python -m ipcih.demo --output evidence/demo
python -m ipcih.serve --port 8768
```

Open `http://127.0.0.1:8768/`, paste the full `ipcih1z:` string from `evidence/demo/signed_capsule.txt`, and pin the key from `evidence/demo/pinned_pubkey_hex.txt` in a separate trusted step. Click **VERIFY**, then explicitly click **START**. The UI never auto-executes a scanned payload.

**Trust for a real deployment:** a generated demo key is not a trust anchor. Provision/pin trusted keys via an out-of-band verified procedure, implement key rotation and revocation checking, authenticated issue logs, external witnesses, and application-level approval. The demo fixture keys are not protected or permanent. The URL is loopback only.

**Physical acceptance:** No FPGA bitstream, INA226 calibration, PUF, ATECC/TPM, WebRTC call, physical printer, clinical diagnostic validation, or measured joules. Hardware work is kept in existing Tessera/PoPC repos/PRs and is not retroactively credited here.

**Caveats:** QR capacity is bounded by symbol version/error correction/scanner quality, not unlimited. A signature authenticates an issuing key; it does not demonstrate correct human identity, trustworthy software, model honesty, or physical correctness. The code cannot guarantee that a phone or browser leaves zero persistent caches/traces. Rendering a maliciously signed HTML document can be dangerous; only constrained demo-template capsules are issued here.
