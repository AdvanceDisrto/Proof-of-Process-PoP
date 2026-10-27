# i™ i-PoP iPWA — offline integrity verifier (prototype)

This directory is an **installable static PWA**, intended to be served under HTTPS at
`/ipwa/`. After an initial successful install, the service worker serves its own
assets from local cache without network fallback. The *receipts themselves* are
read with the browser File API, not uploaded or cached. It does **not** accept
`.tar.gz` bundles yet. No operational government data should be tested here.

## Verify

1. Obtain a trusted key registry through a channel independent of the evidence
   package; confirm its key fingerprints with the appropriate authority.
2. Upload the registry as JSON, then upload a signed receipt bundle as JSON.
3. The verifier recomputes event hashes, parent linkage, domain-separated
   SHA-256 Merkle root, and independently pinned Ed25519 signature(s).
4. A passing result is `LOCAL_CRYPTOGRAPHY_PASSED_ANCHOR_UNVERIFIED`. Both
   payment and physical-actuation gates **remain closed**. No OTS/Bitcoin SPV,
   TEE hardware attestation, eligibility database, government authority,
   healthcare delivery validation, or legal-disqualification check exists here.

### JSON formats

Trust registry (`required_roles` contains at least two distinct signers):

```json
{"protocol":"ITM-POP-TRUST-v1","required_roles":["intent_owner","executor"],"keys":[{"role":"intent_owner","key_id":"person-001","public_key_hex":"<64 lowercase hex>"},{"role":"executor","key_id":"worker-001","public_key_hex":"<64 lowercase hex>"}]}
```

Evidence bundle:

```json
{
  "body": {
    "protocol":"ITM-POP-OFFLINE-v1",
    "intent_hash":"sha256:<64 lowercase hex>",
    "events":[{"sequence":0,"stage":"INTENT","parent_hash":null,"evidence_hash":"sha256:<64 lowercase hex>","event_hash":"sha256:<64 lowercase hex>"}],
    "merkle_root":"sha256:<64 lowercase hex>",
    "anchor":{"type":"OTS_BITCOIN","status":"PENDING","txid":null}
  },
  "signatures":[{"role":"intent_owner","key_id":"person-001","signature_hex":"<128 lowercase hex>"},{"role":"executor","key_id":"worker-001","signature_hex":"<128 lowercase hex>"}]
}
```

The `intent_hash` must equal the first event's `evidence_hash`. `event_hash` is
SHA-256 of `UTF8("i-pop-event-v1\\0") || UTF8(canonical(event_without_event_hash))`.
Merkle leaves are SHA-256 of `UTF8("i-pop-leaf-v1\\0") || raw_event_hash`;
parents are SHA-256 of `UTF8("i-pop-node-v1\\0") || left || right` (duplicate
odd trailing node). The signatures cover canonical `body` bytes; canonical JSON
sorts object keys lexically and rejects floating-point numbers. **This is a
restricted deterministic JSON subset, not complete RFC 8785 JCS.** Encode money
as an integer number of cents or a decimal string.

Never infer proof of *actual service rendered*, a live blacklist result, or
hardware-key possession from a signed JSON assertion alone. Patient identity and
health records must not be put on public blockchain ledgers. Automated
forfeiture/bounties would require lawful review and an appeals mechanism.

To create disposable local demonstration JSON files run:

```bash
node ipwa/make_demo.mjs ./ipwa-demo
```

## Test

```bash
node --test tests/ipwa-verifier.test.mjs
```

Deploy `ipwa/` as static HTTPS content, and check home-screen launch + airplane
mode manually on the actual iPhone and Android versions being supported. PNG 192/512 and an SVG fallback are included, but a browser/PWA is not immune
to OS policy, storage eviction or user uninstall.

## v2 real WebAssembly and TAR.GZ
`verifier_bg.wasm` is SHA-256 built with LLVM/clang from `src/wasm_sha256.c`; signature verification remains browser WebCrypto Ed25519. This is **not a compiled Rust Ed25519 WASM implementation**. The iPWA needs an initial HTTPS load, then cache-only operation for installed assets. Upload `public-evidence.tar.gz` plus a separately validated trust registry. A QR/barcode merely transports the Merkle root; no camera scanner or physical scanner attestations are claimed.
