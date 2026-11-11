# iNNOVULIS™ Buddy™ — Signed Epistemic Receipts v2 (demonstration)

**Status: executable, software-verified demonstration. NOT production CIH, not hardware-backed, not a truth oracle.**

## Why v2 rather than rewriting v1

Your actual Windows BrainGate receipts have `schema: bitwitness/brain/receipt/v1`, `confidence`, `prev_hash` and `receipt_hash`, but **no Ed25519 signature**. The v1 canonical bytes and existing hashes must not be silently rewritten. This package preserves the legacy v1 format and tests; it adds a **separate signed v2 projection** with `schema: bitwitness/brain/receipt/v2`. A v2 receipt references its original v1 hash using `legacy_receipt_hash` without claiming the browser has verified that historical source.

The small change in this package's `brain_registry.py` is a fail-closed **pre-append chain check** applied to both regular dispatch and refusal, but it does not change v1's fields or hashing algorithm. That preserves existing v1 hash compatibility.

## Standard: independently verify the signed facts

The signed envelope has precisely the 23 fields in `buddy_receipt_v2.schema.json`; `confidence` is deliberately **absent from v2** and is still part of the legacy v1 record/attempt. The v2 receipt contains names, version, request/output hash references, declared refusals and gate checks, timestamp, predecessor hash, v1 reference, and the Ed25519 signature.

1. **Canonicalization profile.** The v2 signed envelope uses an RFC 8785-compatible **number-free I-JSON profile**. Values may be strings, booleans, null, arrays, or objects; **numbers are rejected**, avoiding Python/JavaScript floating-point rendering differences. Dictionary keys sort by UTF-16 code units; Unicode strings are serialized with RFC 8785 escaping, including literal `café`, `日本語`, emoji, U+2028, and U+2029; lone surrogates are rejected. This helper is NOT a general-purpose implementation for arbitrary numerical JSON.
2. **Receipt hash.** `body` = every v2 field **except** `receipt_hash`, `signer_pubkey`, and `signature`. `receipt_hash` = `"sha256:" + SHA256(UTF8(canonical(body)))`.
3. **Signature.** `signed` = `body` plus `receipt_hash`. `signature` = Base64(Ed25519.sign(private_key, UTF8(canonical(signed)))). `signer_pubkey` is a raw 32-byte Ed25519 public key in Base64, included for display/identification.
4. **Independent trust.** The verifier MUST compare that claimed public key to a trusted public key installed **separately** from the QR before accepting the signature. The included viewer contains the **demo public key** when generated. The QR itself never grants trust. TOFU records subsequent key **continuity** by brain only *after* the key passes the independently pinned check.
5. **Timestamp.** `ts` must be a UTC RFC3339 string with exactly 3 fractional decimal digits, e.g. `2026-11-11T03:21:04.123Z`; the viewer displays age and warns when older than one hour or apparently in the future. Its clock is **not** a trusted time source.
6. **Chain.** The signer checks the entire v2 in-memory chain before signing a new entry and rejects a mismatched predecessor or genesis flag. `SignedBrainDispatcher.verify_chain` checks the local chain. **A QR with one receipt cannot prove full linkage without additional previously trusted context or externally pinned genesis/checkpoint.**

These receipts demonstrate a software policy gate that produced or refused an output. They do NOT prove that the stated facts are true, that a clinical outcome happened, that a model cannot hallucinate, that a quantum device ran, that a witness independently inspected the system, or that signing keys belong to a particular legal organization.

## Contents

- `brain_registry.py` — original BrainGate 21-worker implementation plus fail-closed pre-append legacy chain guard (v1 format unchanged).
- `buddy_receipt_v2.py` — actual Ed25519 v2 signing and independent Python verification with a versioned schema.
- `buddy_receipt_v2.schema.json` — strict JSON Schema draft 2020-12, 23 fields, no extra properties.
- `verifier-core.js` — browser + Node WebCrypto Ed25519 and canonicalization implementation. No network calls, no dynamically executed QR code.
- `verifier.html` — **fully offline** dependency-free paste verifier with key pinned inside viewer HTML.
- `scanner.html` — same offline verification plus an opt-in camera pathway using built-in `BarcodeDetector` where the browser supports it. There is **no CDN**; camera still needs browser support, user permission, and a secure context.
- `buddy-signed-v2-qr.png` — QR for a **demo** signed receipt. Optical payload is ~1.1 KB (QR Version 24-L); a full React app cannot fit inside it.
- `demo-qr-payload.json` — exact text encoded in that PNG.
- `signed-receipt-chain-v2.json` — real demo signatures on Calculator, OracleHumanReview refusal, and disconnected Claude refusal, chain hashes, and explicit `does_not_prove` boundaries.
- `demo-public-trust-anchor.json` — public key and SHA256 fingerprint generated **alongside the reviewed viewer**, not dynamically from the QR. Private demo key is never saved.
- `Run_Buddy_V2_Windows.ps1` — Windows PowerShell 5.1-compatible (UTF-8 BOM, ASCII-only commands) one-command test entry point; add `-Serve` to start the local verifier.
- `build_demo.py` — regenerate the demonstration with a NEW ephemeral signer and matching pinned HTML (requires Python `qrcode` to regenerate the QR image; tests do not require it).
- `test_v2.py` — Python signature, schema, v1 compatibility, tamper, chain, timestamp and Unicode tests.
- `test_v2_node.cjs` — independent JavaScript/WebCrypto verification, canonical cross-language vectors, TOFU and tamper checks.
- `test_verifier_ui.cjs` — actual generated HTML verifier script tested with simulated DOM; not a browser hardware test.
- `canonical-vectors.json` — cross-implementation UTF-8 canonicalization test vectors, including 1-million-character test digest.

## Run on Windows from the **EXTRACTED FOLDER**, not Proof-of-Process-PoP

Extract the ZIP to e.g. `C:\Users\New Customer\Downloads\Buddy_Signed_Receipt_v2`, then open PowerShell:

```powershell
Set-Location "$env:USERPROFILE\Downloads\Buddy_Signed_Receipt_v2"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File ".\Run_Buddy_V2_Windows.ps1"
# Or run these equivalent commands individually:
python brain_registry.py --tests
python -m unittest -v test_v2
node test_v2_node.cjs
node test_verifier_ui.cjs
python -m http.server 8768
```

The `python -m unittest` tests need `cryptography`, already in your CIH Python environment. If your global Python lacks it, run the tests using your CIH repository's `.venv\Scripts\python.exe` with the absolute file path, without replacing the project environment. `jsonschema` is **optional** for the extra JSON Schema validator test and will be marked skipped when missing. **Do not install new dependencies blindly.**

Open `http://127.0.0.1:8768/verifier.html` in Chrome/Edge. Paste the entire contents of `demo-qr-payload.json` and select **VERIFY SIGNED JSON**. It should display `SIGNATURE VALID`, gate checks, signed timestamp with age, and clear scope limits. Then edit the pasted `claims` and verify again; it must show `FAIL CLOSED`.

For camera testing, open `scanner.html` in a browser with a supported native QR `BarcodeDetector` implementation. A *phone* cannot directly access your desktop's 127.0.0.1. Put the reviewed viewer on a trusted HTTPS origin before testing on a phone; do not use patient data. Open the scanner first, click **START CAMERA**, grant permission and point it at the displayed `buddy-signed-v2-qr.png`. Unsupported browsers can use paste mode. No phone camera or physical receipt print was demonstrated during this build.

**IMPORTANT:** If you run `python build_demo.py` again, it produces a **new demo signer** and regenerates the QR, public anchor, receipts and verifier HTML. Do not mix artifacts from different runs or silently reset a previously observed trusted signer. A new demo trust root must be reviewed and installed deliberately.

## Executed software evidence

- 21/21 original BrainGate unit tests PASS.
- 11/11 Python v2 and v1-compatibility tests PASS; strict JSON Schema validation PASS when `jsonschema` available.
- 15/15 independent JavaScript/WebCrypto test cases PASS, including real Python-issued Ed25519 signatures, modified claims, changed public key, missing trust anchor, mismatched format, UTF-16 key order, U+2028/U+2029, and a 1,000,000-character canonicalization test.
- The two *actual generated HTML inline verifier scripts* passed DOM-simulation tests, showing gate checks, freshness, signer continuity, tamper rejection.
- Optical QR decoded byte-for-byte using ZBar/pyzbar in the preparation environment.
- Browser integration attempt was blocked by `net::ERR_BLOCKED_BY_ADMINISTRATOR`. Therefore **real browser/phone camera tests remain ACTION_REQUIRED**.

## Deployment safety

The `v2` signer uses a new **ephemeral test key**. It is NOT wired to the production CIH Ed25519 private key, `.krdid` enrolment, Supabase service credentials, real sensors, cloud Worker, or patient data. No deployment or merge is required for this demo. Do not make protected repositories public or merge changes without owner approval.

**Accurate claim:** “The offline verifier confirms the hash and Ed25519 signature against a separately installed demo public key, displays policy gate checks and receipt age, and makes the limits of signer identity and full chain verification explicit.”

## Three-receipt INTERNAL signed chain — corrected filenames

Earlier suggested paths `receipt-1.json`, `receipt-2.json`, `receipt-3.json` do NOT exist. The actual files are:

- `receipt-1-Calculator.json`
- `receipt-2-OracleHumanReview.json`
- `receipt-3-Claude.json`

All three already occur in `signed-receipt-chain-v2.json`. The viewer now accepts a single signed receipt or a complete three-receipt envelope/array. It verifies each SHA-256 and Ed25519 signature against the separately pinned DEMO key, then verifies genesis and both signed parent links.

On Windows, in the extracted demo folder:

```powershell
$folder = Join-Path $env:USERPROFILE 'Downloads\Buddy_Signed_Receipt_v2'
Set-Location -LiteralPath $folder
node .\verify_signed_chain.cjs
$raw = Get-Content -LiteralPath (Join-Path $folder 'signed-receipt-chain-v2.json') -Raw -Encoding UTF8
$bundle = $raw | ConvertFrom-Json
if ($bundle.receipts.Count -ne 3) { throw 'EXPECTED_THREE_SIGNED_RECEIPTS' }
Set-Clipboard -Value $raw
Write-Host 'THREE_RECEIPT_JSON_COPIED_NOT_VERIFIED_BY_CLIPBOARD'
```

Reload `http://127.0.0.1:8768/verifier.html` while the existing Python server runs, click the JSON textarea, paste (Ctrl+A then Ctrl+V), and choose VERIFY SIGNED JSON. It should display INTERNAL CHAIN VERIFIED, explicitly NOT EXTERNALLY ANCHORED. The old viewer accepts just one receipt; install the updated viewer with its matching already-pinned demo trust key.

Never regenerate only one of the QR, pinned key, signed chain, or viewer: build_demo.py creates a fresh ephemeral key each time. The updated prebuilt upgrade ZIP preserves the original demo key, receipt hashes, and QR. Reordering the chain, dropping a member, or altering a middle receipt must be rejected.

The phone QR still contains ONE receipt, not the complete chain. An optical phone scan requires a trusted HTTPS scanner, camera permission and native BarcodeDetector support. One QR cannot establish independent external ledger anchoring or the full three-receipt continuity.
