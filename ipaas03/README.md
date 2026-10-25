# iPAAS 0.3 — receipt-first control core

This repository addition contains a deterministic iPAAS control core:

- SQLite service/deploy state
- hash-chained audit/receipt records
- RBAC
- branch previews
- autoscale policy validation
- Caddy configuration generation
- explicit HIPAA/SOC2 evidence boundaries

The tested local implementation reached 20/20 Python tests.

Important boundary: the bundled compliance engines are evidence-matrix stubs for the control-plane build. They do **not** constitute legal HIPAA/SOC2 certification, vendor BAA evidence, SAML IdP validation, or production deployment proof.

The receipt chain records mutations; it does not manufacture external evidence.

## Verification

```bash
PYTHONPATH=ipaas03 python -m unittest discover -s ipaas03/tests -p "test_*.py" -v
```

The E2E artifact runner used during the build produced:

- 20/20 local test result
- hash-chained audit records
- receipt records
- Caddyfile
- deployment artifact
- HIPAA/SOC2 evidence reports
- a SHA-256 manifest
- an E2E receipt

The actual local artifact output is not represented as a production deployment receipt until CI and the target deployment environment independently verify it.
