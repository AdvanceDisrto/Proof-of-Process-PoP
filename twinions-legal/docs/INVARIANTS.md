# Twinions Legal DAG — security and correctness invariants

1. Slot IDs are exactly 1–18, ordered and stable. Only user-defined names are
   assigned. Slots 3,4,6,9–13,15–17 are undefined and cannot be approved by
   supplying a TSV file; a reviewed schema release is necessary.
2. Each `EVIDENCE_ATTACHED` or `CONTESTED` state MUST reference a SHA-256
   identifier for a regular local file hashed before gate assignment.
3. Evidence file bytes are never copied into SQLite. File authenticity and
   chain of custody are not inferred from content hashes.
4. `NOTICE_EVIDENCE`, `REPLY_EVIDENCE`, and `COUNSEL_REVIEW_EVIDENCE` record
   operator-submitted file hashes; they do not establish actual service,
   receipt of notice, counsel identity, or a legal right to reply.
5. `EVIDENCE_REVIEW_REQUIRED` must remain whenever any user gate definition,
   evidence or due-process record is incomplete. A completely filled
   workflow could only yield `DRAFT_FOR_COUNSEL`.
6. The native Z3 SMT proof only checks internal boolean workflow constraints.
   `SAT`, `UNSAT`, and `UNKNOWN` do not map to legal merits.
7. Signed demo receipts contain `source_tier=SOFTWARE_DEMO` and
   `legal_filing_authority=NONE`. A signer key must be pinned independently.
8. The web viewer is loopback-only, read-only, authenticated by an operator
   token and must not include user content in `innerHTML` or executable code.
9. Any broken journal chain blocks all output until investigated; hash linkage
   alone does not defeat privileged local rewriting or file deletion.
10. C++ iStick host validator cannot execute on CH340E, which is a USB UART
    bridge. Secure element ATECC608A signs P-256, not Ed25519; temperature
    MCP9808 alone does not measure joules or validate a computation.
11. Human counsel is responsible for legal analysis. No automated "do not file",
    "certified for filing" or "criminal/civil liability established" decision.
12. Schematic/netlist, routable PCB, fab stackup/90-ohm proof, ERC/DRC,
    manufacturing files, physically measured EMI and adversarial security
    evidence are absent; no claimed physical reduction to practice.
