# STRMKRD Modular Trust Node Universal API v0 — software acceptance only

The Rev0 API is deliberately **local-host only** and interoperable through JSON, rather than attempting to run identical hardware code on iOS, Windows and Linux. Actual I2C register access is supported through the **Linux board adapter** only; Windows, macOS, iOS, and independent auditors can consume signed artifacts or implement interoperable clients when an authenticated transport is implemented separately.

## Tested functionality

- `GET /api/v1/status`: reports software readiness, not hardware availability.
- `GET /api/v1/observation`: local API token required; reads actual MCP9808 and INA226 registers on `/dev/i2c-1` via existing Rev0 bring-up and runs real Z3 range checks. Missing hardware -> HTTP 503. Returns **UNAUTHENTICATED** evidence and `receipt: NOT_MINTED`.
- `GET /api/v1/receipt`: always HTTP 503 because no provisioned secure-element signer and physical evidence binding are available. The API does **not** forge hardware signatures or report a fake ipQR image.
- `POST /api/v1/verify`: independent, offline PEM-pinned **ECDSA P-256 / SHA-256** canonical JSON signature verification. Demonstrated on **explicitly synthetic test-only** software keys. Valid signature proves data integrity from its pinned key, not accuracy of a physical measurement.

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -r hardware/strmkrd-node/requirements-hardware.txt
pip install 'fastapi>=0.110,<1' 'uvicorn>=0.30,<1' 'httpx>=0.27,<1'
STRMKRD_LOCAL_TOKEN='<long random 32+ char token>' python hardware/strmkrd-node/universal_api.py
# localhost-only:
curl http://127.0.0.1:8768/api/v1/status
curl -H 'X-API-Key: <token>' http://127.0.0.1:8768/api/v1/observation
```

**Security boundaries:** API uses a locally configured 24+ character token; loopback only; no CORS or LAN/Internet exposure. Client-supplied public keys must be independently provisioned/pinned: accepting arbitrary keys in a verification request proves only self-consistency. No transport mutual TLS, no durable replay protection or cross-device access provided.

**Hardware and display:** ATECC608B/C supports P-256, not native Ed25519. A Raspberry Pi CM4 uses dedicated dual board-to-board connectors. An M.2 Key-M NVMe connector is **not** a standard CPU/SoM interface and cannot accept Intel NUC/Pi CM4/ESP32 interchangeably. The current high-density radial ipQR format has no verified print-camera/E-Ink profile for a low-resolution 2.13-inch panel; neither standard QR nor NFC interchangeability is established.

**Acceptance:** This is a standalone Rev0 software adapter. It has not been wired to live QoW/PoP/CIH. Real hardware, FPGA/PIC, calibration, secure provisioning, true hardware signatures, durable sensor evidence, printed scanning, and production deployment remain NOT_VERIFIED.
