# i™ iNNOVULIS / Twinions Legal Evidence Review v0.1

**EXECUTABLE LOCAL PROTOTYPE — NOT A LEGAL RULING, MEDICAL DIAGNOSIS, FILING CERTIFICATION, OR PHYSICAL TRUST ANCHOR.**

This is a source-backed case-intake workbench connected conceptually to iP.CiH,
Buddy and the iStick. A local operator can hash documents without copying the
raw files into the database, attach those SHA-256 hashes to an explicit
18-slot case review workflow, record evidence of notice/opportunity to reply,
compare two AI outputs without treating either as truth, produce a draft print
preview, and issue a signed **software-only** review receipt. A restricted
loopback browser viewer displays status without trusting submitted HTML.

The user's prior text specified names for ONLY seven of 18 slots: 1, 2, 5, 7,
8, 14, 18. The other **11 stay undefined** until provided/approved by counsel.
The tool never substitutes made-up gates or certifies a case as `PROVEN_TRUE`.

## Install and run

```bash
python -m pip install -e '.[test]'
python -m pytest -q tests/
python -m twinions_legal demo --out evidence/demo
python hardware/readiness.py
```

To create an independent local test case and hash an actual local document:

```bash
python -m twinions_legal create --db ./private/legal.db --case CASE-001
python -m twinions_legal attach --db ./private/legal.db --case CASE-001 \
  --file ./local_document.pdf --label 'source document (authentication not assumed)'
python -m twinions_legal gate --db ./private/legal.db --case CASE-001 \
  --number 5 --status MISSING
python -m twinions_legal status --db ./private/legal.db --case CASE-001
python -m twinions_legal log-check --db ./private/legal.db
python -m twinions_legal report --db ./private/legal.db --case CASE-001 \
  --out ./private/review.html
```

To attach actual evidence for a gate, use the SHA-256 returned by `attach`:

```bash
python -m twinions_legal gate --db ./private/legal.db --case CASE-001 \
  --number 5 --status EVIDENCE_ATTACHED --evidence-hash <64-HEX-CHARS>
```

`EVIDENCE_ATTACHED` means *a matching file was locally hashed*—nothing about
legal sufficiency or authenticity. To record process evidence for notification,
reply or human review, first hash the corresponding document and use:

```bash
python -m twinions_legal record --db ./private/legal.db --case CASE-001 \
  --kind NOTICE_EVIDENCE --evidence-hash <64-HEX-CHARS> --actor-label 'operator-entered label'
```

There are corresponding `REPLY_EVIDENCE` and `COUNSEL_REVIEW_EVIDENCE`
records. These mean that an operator supplied a file hash—not that a notice was
legally served or that an attorney's identity/license was verified.

## Local browser viewer

Set a high-entropy session token; don't put confidential data in a public URL:

```bash
export TWINIONS_OPERATOR_TOKEN="$(python -c 'import secrets; print(secrets.token_urlsafe(32))')"
python -m twinions_legal serve --db ./private/legal.db --port 8776
# open http://127.0.0.1:8776
```

The viewer is read-only, bound to `127.0.0.1`, uses an operator header for the
case endpoint, disables caching, sends a strict CSP, and constructs HTML with
text nodes rather than evaluating model/evidence content. This is a software
prototype; do not put real sensitive legal or healthcare records into the
public repository, CI, demo logs or network scanner.

## C++ host-side iStick integration

The `hardware/innovulis_istick.cpp` builds an **18-slot workflow validator
for the connected host**, not firmware on the CH340E USB UART chip.

```bash
g++ -std=c++17 -O2 -Wall -Wextra -Werror -pedantic \
  hardware/innovulis_istick.cpp -o innovulis_istick_host
python -m twinions_legal cpp-export --db ./private/legal.db \
  --case CASE-001 --out ./private/gates.tsv
./innovulis_istick_host ./private/gates.tsv
```

It checks exactly 18 ordered slots, explicit statuses and hashed evidence
identifiers, and always returns `legal_merits=NOT_DETERMINED` and
`filing_authority=NONE`. **It never executes on the proposed USB stick**;
CH340E has no general-purpose processor or I2C host. A revised hardware design
must add an MCU/host bridge, valid schematic/routed PCB and secure-element
provisioning procedure. No Gerbers, STL proof of physical protection, fabricated
unit, or key lock exists in this release. Run `hardware/readiness.py` to
confirm the current `BLOCKED_NO_FABRICABLE_PCB` gate.

## Cryptographic and model-assessment boundaries

- Native `libz3` is used solely to check whether explicitly declared boolean
  **workflow** conditions are logically consistent. `SAT` is *not* evidence a
  legal claim is true; `UNSAT` is *not* a court ruling or a "fatal case".
- The example Ed25519 receipt is signed by a freshly generated SOFTWARE key
  and validated against a separately provided public key. It does not claim
  ATECC hardware, legal notice, notarization, or certified filing.
- The local SQLite hash chain detects partial tampering but can be rewritten
  in full by an actor who controls the database and keys. External timestamps,
  audit logs and off-host anchors are needed for stronger provenance.
- A textual conflict between model outputs only means `CONFLICT_DETECTED`.
  An AI cannot use Z3 alone to adjudicate factual disputes about radiology,
  safety, malice, probable cause or a court's legal conclusions.
- Paper, QR, and web screens are untrusted carriers; the receipt is only as
  authoritative as an independently established trust anchor and its evidence.

## Security, privacy and legal use

The application does NOT automatically submit legal filings, contact parties,
certify service, store patient data, initiate adversarial allegations or decide
any individual case. It is an organizational tool for human counsel review.
The developer did not establish legal advice, privilege, attorney-client
confidentiality, encryption at rest or HIPAA compliance. Use only synthetic
records in the GitHub Actions CI.

For context, the U.S. Supreme Court's *Thompson v. Clark* (2022) considered
favorable termination in a particular Fourth Amendment §1983 malicious-
prosecution claim. The exact legal analysis depends on jurisdiction, claims,
actors, defenses, timeliness and actual documentary evidence; do not hard-code
legal merits from case-name keywords.

Source: https://www.law.cornell.edu/supremecourt/text/20-659

## Acceptance

`LOCAL_EVIDENCE_WORKFLOW_PASS` may be issued after actual runnable tests.
`CERTIFIED_FOR_FILING`, `MALICIOUS_PROSECUTION_PROVED`, `FIPS_LOCKED`,
`HW_SIGNED`, `FAB_READY`, and `COURT_ACCEPTED` are **never issued by this tool**.
