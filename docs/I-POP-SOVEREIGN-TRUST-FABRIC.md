# i™ Sovereign Trust Fabric — draft implementation map

**Status: partial code implemented; live deployment and physical certification NOT CLAIMED.**

## i™ Article XIX: no single point of failure (project specification)

Human owns intent. Buddy assists. Providence evaluates independently verifiable
policy and economic constraints. Scheduler allocates. Sandboxed execution
generates auditable evidence. Receipts make recorded evidence portable. An
independent verifier recalculates cryptography without depending on i™ servers.
Actual physical operation and payment settlement need **independent positive
authorization**; a signature or blockchain timestamp alone cannot grant it.

```
Human / Buddy intent
  ├── iControl permissions (design; no live federal integration)
  ├── Providence policy gate (design; not yet running against agency data)
  ├── iVia scheduler / SPU execution (existing separately audited repo modules)
  ├── i-PoP event receipt -> independently pinned Ed25519 keys
  ├── SHA-256 parent links -> Merkle inclusion root
  ├── Optional OTS / Bitcoin anchoring (NOT independently verified by iPWA v1)
  ├── iPWA offline verifier (implemented: ipwa/*)
  ├── Federal disbursement reference (implemented: federal/*)
  └── Global transfer reference (implemented: global_ledger/*)
       └── Payment/physical-actuation gate: BLOCKED
```

## Domain routing — deployment topology proposal only

| Domain | Proposed trust function | State here |
| --- | --- | --- |
| innovulis.com | Buddy and user experience | Not provisioned in this PR |
| rewinddistro.com | Creator workload request | Not provisioned in this PR |
| infrasili.com | Infrastructure/edge | Not provisioned in this PR |
| strmkrd.cc | Build and deployment services | Not provisioned in this PR |
| igptm.com | Identity and permission UX | Not provisioned in this PR |
| proofofprocess.online | Read-only offline-verifier origin | Not provisioned in this PR |

Domains and DNS **are convenience transports, not necessary sources of
verification authority**. Independent copies of cryptographic verification
materials, trusted-key distribution, update policies and revocation procedures
are required. An installed PWA is still dependent on its operating system,
browser support and local data persistence.

## Implemented proof surfaces

**Static PWA:** `ipwa/verifier.mjs` recomputes hashes, event parents, Merkle
root, and threshold-of-roles signature evidence. Key trust registry is loaded
**separately**, not inferred from receipt. Offline caching is scoped only to
this app's assets. Independent OTS, TEE and hardware/YubiKey evidence is **not**
implemented. Payout and actuator output is always `false`.

**Federal reference:** `federal/disbursement.py` verifies five independently
authorized role signatures and policy assertions. The assertions themselves
have no live upstream legal/medical proof. It **never issues a Treasury payment**
and it **never awards whistleblower bounties**. Duplicate flags are review
referrals, not fraud findings.

**Global cross-border reference:** `global_ledger/transaction.py` verifies
payer/payee and compliance authority signatures over fixed payment intents.
This is a non-settling receipt evaluator, not a wire service or production AML
verification system. An asserted `anchor.status = VERIFIED` remains
`anchor_verified = false` without an independently executed Bitcoin proof.

## Certification / truth boundary

```
Design specified                   -> DESIGN_RECORDED
Local tests successful             -> LOCAL_TESTS_PASSED
CI succeeded on actual commit      -> CI_VERIFIED_FOR_THOSE_TESTS_ONLY
Independent OTS proof missing      -> BITCOIN_ANCHOR_ACTION_REQUIRED
YubiKey / hardware quote missing   -> HARDWARE_ACTION_REQUIRED
Government and bank integrations   -> INTEGRATION_NOT_IMPLEMENTED
Payment / physical action          -> FAIL_CLOSED
```

Do not label test cases with invented key signatures, fictitious receipt
digests, or unverifiable model claims as certified physical execution.
Substantive legal decisions (fraud, forfeiture, suspension of medical providers)
must include due process, privacy safeguards, review and remedies.

### Source-accuracy note

U.S. GAO **FY 2025** reported **$186 billion estimated improper payments**
across 64 programs, including **$153 billion overpayments nationwide**. CMS
reported **$37.39 billion estimated FY 2025 Medicaid improper payments**.
Improper payment does not mean proved fraud. The phrase **"$825B annual fraud"**
does not follow from those GAO figures. ACFE's **12-month median detection
duration** is for surveyed occupational-fraud cases, not all transactions.
A blanket $5T annual fraud figure cannot be presumed from mutually different
estimates without normalization and provenance.
Sources:
- https://www.gao.gov/products/gao-26-108694
- https://www.cms.gov/newsroom/fact-sheets/fiscal-year-2025-improper-payments-fact-sheet
- https://www.acfe.com/about-the-acfe/newsroom-for-media/press-releases/press-release-detail?s=2024-Report-to-the-Nations
