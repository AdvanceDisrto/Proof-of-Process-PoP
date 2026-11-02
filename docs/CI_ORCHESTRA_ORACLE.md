# i™ CI/CD Orchestra Oracle — bounded integration

## Implementation
- `integrations/ci_oracle.py` translates a restricted JSON/YAML intent to Woodpecker, Jenkins or Bitbucket pipeline configurations. It is a **generator**, not a scheduler or deployment engine.
- `integrations/ci_sign_gate.py` verifies an **already issued** PoP Ed25519 envelope against a pinned trusted public key. It does not produce a new signature.
- `tests/test_ci_oracle.py` tests engine output, command allowlists, tampering, trusted-key checks, and fail-closed requirements.
- `bitbucket-pipelines.yml` is a candidate for copying to a Bitbucket repository after workspace authorization and repository creation.

## Supported intent (JSON is a YAML 1.2 subset)
```json
{"project":"innovulis-pop","steps":["compile","frontier_tests","receipt_tests","ci_tests","sign_gate"]}
```
Run: `python -m integrations.ci_oracle --intent docs/ci-intent.example.json --engine bitbucket --output /tmp/bitbucket-pipelines.yml`.

The generator intentionally rejects arbitrary shell/Groovy content, unknown step identifiers, duplicate stages and missing/misordered sign gates. The output is only a candidate configuration. Do not accept a project-provided untrusted string as an executable command.

## Trust and signing boundary
```
CODE / SOURCE HASH -> TESTS -> OBSERVED BUILD -> TRUSTED EXTERNAL SIGNER
                      -> SIGNED PoP RECEIPT -> PINNED PUBLIC KEY VERIFIER
                      -> RELEASE GATE (separately authorized)
```
The external signer must be separately deployed. The release job needs `POP_CI_SIGNED_RECEIPT` pointing to an actual receipt JSON path and `POP_CI_TRUSTED_PUBKEY` containing a *pre-pinned* 32-byte Ed25519 public key in hex. Do not derive the trust key from the same untrusted receipt. This verifier checks integrity and key attribution only. It does not confirm ML-DSA, Sigstore/Rekor, Bitcoin, a TEE, live inference or physical operations.

## Bitbucket caveats
The workspace URL does not prove that the connected GitHub account can read/write Bitbucket. Nothing in this change has been pushed to Bitbucket. The proposed Bitbucket pipeline runs tests by default. Manual `verified-evidence` deliberately requires a trusted receipt to already be supplied, and rejects missing evidence. CI steps on public runners cannot access a laptop's `127.0.0.1:11434`. Use an authenticated, isolated self-hosted runner with appropriate controls, not an exposed Ollama service.

## Woodpecker/Jenkins caveats
No CI server or agent was provisioned by this change. Do not mount `/var/run/docker.sock` into arbitrary CI jobs or enable unrestricted CI public registration. Pin container digests, restrict runners, scope credentials, configure authentication and TLS before deploying.

## Current claims
SOURCE COMMITTED is distinguishable from TESTS PASSING, DEPLOYED, SIGNED, ANCHORED or LIVE INFERENCE. Never publish synthetic Rekor UUIDs or ephemeral signer keys as independent provenance.
