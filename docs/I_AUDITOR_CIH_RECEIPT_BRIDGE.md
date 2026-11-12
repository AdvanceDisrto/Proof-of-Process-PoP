# i™ AI Auditor → CIH ΔiΔ receipt bridge (review-only, v1.2)

## Actual connection

`i_audit_bridge.audit_exact_spans(sources, claims)` performs a **narrow**
deterministic exact-span textual check and emits a coverage/refusal report.
`i_audit_bridge.to_cih_receipt_request(report)` transforms that report into
the **existing** `cih_api.app.ReceiptRequest` JSON contract, including its
`expected_evidence_sha256` calculated with the same sorted UTF-8 JSON encoding.

An already-enrolled caller must sign that request using the existing
`cih_api.krdid.signed_bytes(krdid, timestamp, nonce, payload, "/api/v1/receipts")`
protocol, and submit it to `POST /api/v1/receipts` with the existing four
`X-Krdid-*` headers. The server authenticates, checks the digest, signs the
receipt using configured CIH Ed25519 keys, commits to local SQLite, and returns
a bounded signed receipt. **No bypass, new public minting endpoint, or key is
introduced by this PR.** AgentI stays observational.

Run the new end-to-end tests in an actual checkout:

```powershell
py -3 -m pip install -r cih_api/requirements.txt -r cih_api/requirements-dev.txt
py -3 -m pytest -q cih_api/test_app.py cih_api/test_i_audit_bridge.py
```

## Evidence and release gate matrix

| Auditor requirement | Implemented here | Boundaries |
| --- | --- | --- |
| Binary evidence gate | YES — exact match / refuse | NOT semantic entailment or factual truth |
| Span-level citation | YES — codepoint [start,end) and verbatim quote | Not a natural-language inference engine |
| Provenance | YES — source/version/hash/retrieval timestamp | Source identity, authority unverified |
| Offline replay | PARTIAL — report digest replayable | Original source bytes must be retained separately |
| Refusal | YES — recorded per unsupported claim | Not an automated legal judgment |
| Numeric guard | PARTIAL — exact quote rejects changed literals | Cross-document arithmetic and units not evaluated |
| Coverage | YES — supported/requested count and ratio | No FAR-NE = 0.0 guarantee |
| Source poisoning | PARTIAL — source content treated as data only | No injection benchmark or secure LLM sandbox validated |
| Storage and integrity | Via existing authenticated CIH receipts | External immutable storage / OTS not proven |
| Human oversight | REQUIRED declared in receipt | No reviewer workflow implemented here |

## Deterministic input and output example

```python
import hashlib
from i_audit_bridge import audit_exact_spans, to_cih_receipt_request

document = "The allocation limit is 15 kW."
source = {
    "source_id": "demo://allocation-policy", "version": "v1", "text": document,
    "expected_sha256": hashlib.sha256(document.encode()).hexdigest(),
    "retrieved_at_utc": "2026-11-11T19:00:00Z",
}
statement = {
    "claim": document, "quote": document, "start": 0, "end": len(document),
    "source_id": source["source_id"], "source_version": source["version"],
}
report = audit_exact_spans([source], [statement])
signed_endpoint_request = to_cih_receipt_request(report)
# The caller must use their enrolled KRDID key and existing signature protocol
# before POSTing this request to CIH. No signing is done in this module.
```

## Release discipline

This change is only proposed in a draft PR. No merge, production deployment,
cloud DNS update, user PII ingestion, 800M-agent deployment, 4zz certification,
EU AI Act conformity declaration, ISO 42001 certification, or ISO/IEC 17025
accreditation is represented by these tests.

Prior Windows v0.4.2 recovery E2E failure remains **OPEN** pending its actual
`recovery_regression.log`. Physical EPU consumption remains `NOT_MEASURED`.
No OTS/Bitcoin anchoring, trusted hardware, live multi-region failover, iFace
media or actual BCI headset processing is asserted.

**Traceable evidence is not automatically truthful evidence.**
