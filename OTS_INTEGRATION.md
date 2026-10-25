# OpenTimestamps Integration Boundary

The PoP repository now calls the real \`ots\` CLI rather than synthesizing a
Merkle proof in JavaScript.

## State model

- \`PENDING_BLOCK\`: the \`.ots\` receipt was requested or exists, but Bitcoin
  anchoring has not been independently verified.
- \`ANCHORED_IN_LEDGER\`: \`ots upgrade\` completed successfully; this still
  requires \`ots verify\` before being used as physical evidence.
- \`verify() == true\`: the external OTS client verified the receipt.

The implementation never treats a generated SHA-256 value as an OTS proof.

## Live calendar

Set \`OTS_CALENDAR_URL\` to the real calendar endpoint. The default is the local
development endpoint \`http://127.0.0.1:14788\`.

The repository does not claim that a local \`otsd\`, Bitcoin node, or anchor
exists merely because this code is present.

## Certification boundary

A CI fixture can prove command construction and fail-closed states. It cannot
create a real Bitcoin anchor without a running calendar/Bitcoin environment.
A real \`LAB_DISPATCH_VERIFIED\` promotion still requires an independently
verified \`.ots\` proof tied to the exact inference hash.
