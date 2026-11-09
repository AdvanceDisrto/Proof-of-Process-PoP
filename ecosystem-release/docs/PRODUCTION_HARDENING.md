# Production engineering gap closure — ranked plan

**P0 software assurance.** Run every subsystem suite on a clean checkout, align signed format versions and canonicalization, use reproducible wheels, dependency/SBOM security scans, branch protection, code review and independent signature key pinning. Externally anchor the execution transcript root, with revocation and replay controls. This release adds **source inventory + CI test recording**, not a product certification.

**P0 user and safety boundaries.** Restrict demo-signing endpoints and WebSockets to localhost; move credentials to approved HSM/secret storage for any real service; enforce human consent and clinical/legal data rejection until full privacy design. Add explicit `does_not_prove` labels to every UI and document. Never use unrestricted natural-language models to emit domain truth verdicts.

**P1 operability.** Implement bounded outbox retry/dead-letter, multi-reader handling, crash recovery, structured log rotation, health probes, TLS/origin enforcement, resource budgets, disaster-recovery and incident response exercises. Distinguish `SIGNED_BYTES`, `SOURCE_AUTHENTICATED`, `POLICY_CONSISTENT`, `HARDWARE_OBSERVED` and `HUMAN_REVIEWED`.

**P1 optical and interaction.** Field-test iP.CiH camera boot on iOS/Android; audit CSP and iframe sandbox; require user launch approval. JAB/iMorphus color matrices need actual camera error recovery and standards work, not decorative QR finder patterns. WebRTC needs authenticated SDP offer/answer, ICE/STUN/TURN availability, genuine two-peer encryption/consent, mic/camera user-permissions and teardown.

**P1 physical board and manufacturing.** Complete MCU architecture, schematic, fab routing, real FPGA bitstream, secure-element commissioning, calibrated INA226/MCP9808, printed physical scan and independent custody witness. Maintain reversible provisioning and do not automate OTP locks.

**P2 regulated domains.** Design privacy/PHI lifecycle, human clinical safety workflow, FDA applicability, quality system and trial evidence where required. Counsel-approved case facts and legal theories, not automatic Twinions rulings; legal admissibility never follows from cryptography alone.

## Deployment release policy
No production rollout before responsible human safety, security, hardware and operations approvals. This runner intentionally has no production ready API. No auto-merge, no cloud billing, no actual printer writes or sensor coercion.
