# iNNOVULIS™ rGPU Cryptographic Telemetry Terminal v0.2

**i™: The machine computes. The individual decides.**

An actual local multi-client telemetry program with persistent software Ed25519 keys,
a hash-linked SQLite receipt journal, an independently pinned WebCrypto verifier
(browser and Node), a Rich terminal monitor, a dark holographic dashboard, optional
80mm ESC/POS *preview* output, and a signed software Genesis receipt.

**The result is a SOFTWARE-ONLY REFERENCE PROTOTYPE, not a certified cryptographic
hardware appliance or medical/physical truth source.** The built-in sensor/TFLOPS/
energy sample mode is explicitly **SYNTHETIC** and requires an operator secret.
It does not claim to execute Tessera-G, PoPC-PU, Z3, TPM/ATECC, INA226 or a GPU.
The current `rgpu1:`/`rgpu1z:` signed receipt is a **new experimental format**, not
compatible with Open Receipt v1.0's `ipqr1` protocol. Interoperation requires a
versioned adapter and separate independent verification.

## Startup

```bash
python -m pip install -e '.[test,monitor]'
export INNOVULIS_OPERATOR_TOKEN="$(python -c 'import secrets; print(secrets.token_urlsafe(36))')"
export INNOVULIS_SYNTHETIC_DEMO=1      # delete in a non-demo environment
python -m rgpu_terminal --data-dir ./private-terminal-data identity
python -m rgpu_terminal --data-dir ./private-terminal-data --port 8768 serve
```

Open **http://127.0.0.1:8768** in a modern browser. The dashboard does NOT
trust the key it learns from the network. Independently transfer the public
key and fingerprint from `identity` output (for example, via an approved
operator-controlled channel), verify them separately, and **manually pin both**
on the client before any green cryptographic result is shown. The browser
uses **native WebCrypto Ed25519**; it does not load JavaScript from a CDN.

A demo event is only emitted after explicit operator authorization. Use the
Dashboard's `SYNTHETIC PASS` / `SYNTHETIC REFUTED` buttons, providing the
local operator token; no outside source can claim physical telemetry.

Optional no-flicker Rich monitor (requires an already running server):

```bash
python -m rgpu_terminal --port 8768 --pin-pub <independently_obtained_64_hex_public_key> monitor
```

**Never put the private PEM in Git, a ZIP release, QR carrier, browser, or a
public website.** The PEM file is mode `0600` in the configured private-data
folder; it remains a local **unencrypted software key**, not protected against
host takeover. Production needs key-encryption/device-root protection,
rotation/revocation, protected backup procedures, independent witnesses and a
security review.

## Reproducible build and tests

```bash
python -m pip install -e '.[test,monitor]'
pytest -q tests/                  # 43 Python tests expected on authoring environment
python ci/export_fixture.py evidence/browser_fixture.json
INNOVULIS_FIXTURE=$PWD/evidence/browser_fixture.json node --test tests/webcrypto.test.mjs
python ci/smoke_live.py           # real HTTP + 2 WebSocket peers and server restart
python ci/render_genesis.py evidence/genesis
python ci/check_physical.py      # read-only, not hardware acceptance
python -m pip wheel . --no-deps --no-build-isolation -w dist
```

Run `ci/smoke_browser.py` optionally on a machine that permits interactive
localhost Chromium. The current container's administrative browser policy
blocked local browser navigation, so no **real Chromium UI acceptance** is
claimed from that attempt. Instead, the exact JavaScript verification module
was tested through Node WebCrypto using real Python-generated Ed25519 signatures.

## Signature contract

The signer commits to **exact UTF-8 bytes** of sorted-key canonical JSON.
It signs `b"iNNOVULIS/RGPU-TELEMETRY/v1\0" || payload_bytes` with Ed25519.
The envelope carries `payload_b64u`, `payload_sha256`, `signature_hex`, and
`issuer_key_fingerprint` (SHA-256 of **raw Ed25519 public key**). The browser:
1. Requires a separately pinned, out-of-band public key and fingerprint.
2. Checks the signed byte hash, domain-separated Ed25519 signature, payload tier.
3. Replays receipts from genesis, verifying strictly increasing sequence numbers
   and each `previous_sha256` link.
4. Displays `REFUTED_FALSE` as a **declared signed conclusion**, not an
   inherently true statement about physical reality.
5. Renders the *complete* signed envelope to an optical carrier only after
   successful local verification. Nothing in the QR is trusted automatically.

No shortened signature or hash-only QR is presented as an independently
verifiable receipt. The `rgpu1z:` optical carrier compresses **public signed
data only** using zlib so it can fit a 576-dot 80mm printer at four pixels per
QR module. It is distinct from the production `ipqr1` standard. Small 58mm
printers must reject unsafe-density output rather than silently drop bytes.

## Multi-client streaming

The FastAPI WebSocket endpoint is bound to `127.0.0.1` by its CLI, enforces
browser `Origin`/`Host`, rejects non-local browser origins, and limits subscribers.
The publish queue is bounded. A slow subscriber gets `resync_required` and a
connection close instead of silently losing signed receipts. History comes
from durable SQLite and can be revalidated from the beginning by every client.
The UI holds at most 50 cards to bound DOM growth.

The printer is an **untrusted carrier**. The optional TCP adapter transmits
only after a separate operator approval and requires a literal private-LAN IP
(or loopback with `emulator_only=True`). A successful socket write is only
`SENT_UNCONFIRMED`, never proof paper was printed or the cutter/paper status is
healthy. Printer status protocols vary by model and are not automatically
trusted. No physical devices are opened by running tests.

## Genesis scope

The sample Genesis receipt truthfully asserts `HUB_INITIALIZED` with
`PROCESS_OBSERVED` for the local Python process. It does **not** assert
`ARCHITECT_PRESENT`, a completed PoPC-PU computation, 0.042 physical joules,
or hardware-backed signing. Its own signed `does_not_prove` names these limits.
The example keys are ephemeral software-only; retain neither the example
private key nor a claim of independently pinned identity from the sample.

For healthcare uses, the current program does not accept patient data, make
diagnoses, provide treatment guidance, or establish HIPAA/FDA/clinical
compliance. Medical safety cannot be inferred from signatures or Z3 alone.
