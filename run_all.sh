#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

RUN_ID="${GITHUB_RUN_ID:-local-$(date -u +%Y%m%dT%H%M%SZ)}"
OUT="evidence/run-all/$RUN_ID"
mkdir -p "$OUT"

log_step() {
  local name="$1"; shift
  echo
  echo "======================================================================"
  echo "RUN-ALL :: $name"
  echo "======================================================================"
  "$@" 2>&1 | tee "$OUT/$name.log"
}

echo "======================================================================"
echo "i™ MONOREPO — RUN ALL INTEGRATED PROOF-OF-PROCESS SURFACES"
echo "======================================================================"
echo "run_id=$RUN_ID"
echo "physical_gate=ACTION_REQUIRED"
echo "rule=The receipt can record reality; it cannot manufacture reality."

python3 -m pip install --quiet -r requirements.txt

log_step ibare make test-ibare
log_step platform_architecture make test-platform-architecture
log_step render make test-render
log_step polyglot make test-polyglot
log_step iska make test-iska
log_step imcp make test-imcp
log_step ledger make test-ledger
log_step truth_engine make test-truth
log_step tee_scrape make test-tee-scrape
log_step antimatter make test-antimatter
log_step antimatter_tiered make test-am-tiered
log_step ambient make test-ambient
log_step omnipresent make test-omnipresent
log_step buddy_liveness make test-buddy-liveness
log_step inetty make test-inetty
log_step mmr make test-mmr

log_step pytest_all python3 -m pytest -q

python3 - <<'PY' > "$OUT/host_capabilities.json"
import json, platform, os
print(json.dumps({
    "spec": "innovulis-run-all-host-capabilities/1.0",
    "machine": platform.machine(),
    "system": platform.system(),
    "tee_devices": {
        "amd_sev_snp": os.path.exists("/dev/sev-guest"),
        "intel_tdx": os.path.exists("/dev/tdx-guest"),
        "intel_sgx": os.path.exists("/dev/sgx_enclave"),
    },
    "physical_gate": "ACTION_REQUIRED",
    "does_not_prove": [
        "hardware attestation", "TEE execution", "measured energy",
        "physical radio execution"
    ],
}, indent=2))
PY

python3 - <<'PY' > "$OUT/gate_verification.json"
import json
from tools.gate import physical_gate
cases = {
    "bare_presence": physical_gate("q", 1.0),
    "untrusted_structure": physical_gate(
        {"vendor_chain": ["SELF_SIGNED"], "measurement": "x"},
        {"joules": 1.0, "source": "signed:lab"},
    ),
    "attested_shape": physical_gate(
        {"vendor_chain": ["AMD_SEV_SNP_ROOT_CA"], "measurement": "x"},
        {"joules": 1.0, "source": "signed:lab"},
    ),
}
print(json.dumps({
    "spec": "innovulis-physical-gate-verification/1.0",
    "cases": cases,
    "physical_gate": "ACTION_REQUIRED",
    "host_tee_present": False,
    "the_central_rule": "Presence is not proof.",
}, indent=2))
PY


python3 -m pytest tests/test_envelop.py tests/test_ilogic.py -q --no-header

python3 - <<'PY'
import json
from pathlib import Path
from tools.envelop import Envelop, Content, verify
from tools.ilogic import Engine, Claim, Rule, ESTABLISHED, ATTESTED, UNATTESTED, MODE_EVIDENCE

E = Path("evidence")
E.mkdir(exist_ok=True)
claims = [
    Claim("c:sha256-known-vector", "sha256", "matches_nist_vector", 1, ESTABLISHED, UNATTESTED),
    Claim("c:isa-detected", "host", "isa_is_x86_64", 1, ESTABLISHED, UNATTESTED),
    Claim("c:tee-absent", "host", "has_tee_device", -1, ESTABLISHED, UNATTESTED),
]
eng = Engine(claims)
eng._check_contradictions()
eng.apply(Rule("and-isa-sha", MODE_EVIDENCE, ("c:sha256-known-vector", "c:isa-detected"), "composite", "software_process_verified"))
eng.apply(Rule("and-with-tee-absence", MODE_EVIDENCE, ("c:sha256-known-vector", "c:tee-absent"), "composite", "physical_attestation_available"))
(E / "ilogic_derivation.json").write_text(json.dumps(eng.receipt(), indent=2) + "\n")

KIND = {
    "gate_verification.json": "receipt",
    "mmr_5000.json": "receipt",
    "ilogic_derivation.json": "derivation",
    "host_capabilities.json": "log",
}
contents = []
for f in sorted(E.glob("*.json")):
    if f.name in {"MASTER_RUN_RECEIPT.json", "envelope.json"}:
        continue
    contents.append(Content(f.name, KIND.get(f.name, "log"), f.read_bytes()))

signer = Envelop(Envelop.keypair())
env = signer.seal(contents, purpose="run-all receipt set")
(E / "envelope.json").write_text(json.dumps(env, indent=2) + "\n")
v = verify(env, {c.path: c.data for c in contents})
assert v["ok"], v["errors"]
print("[iLogic] derivations=", len(eng.derived), "gate=", eng.receipt()["physical_gate"])
print("[Envelop] contents=", len(contents), "manifest_root=", v["manifest_mmr_root"])
print("[Envelop] gate=", v["physical_gate"], "self_verify=OK")
PY

python3 tools/mmr_pipeline.py 5000 "$OUT/mmr_5000.json"
python3 tools/master_run_receipt.py "$OUT"

echo
echo "======================================================================"
echo "RUN-ALL COMPLETE"
echo "======================================================================"
python3 - <<PY
import json
from pathlib import Path
r=json.loads(Path("$OUT/MASTER_RUN_RECEIPT.json").read_text())
print("artifacts:       ", r["artifact_count"])
print("receipts:        ", r["receipt_count"])
print("logs:            ", r["log_count"])
print("master_mmr_root: ", r["master_mmr_root"])
print("state:            ", r["state"])
print("physical_gate:   ", r["physical_gate"])
print("run_id:           ", r["run_id"])
PY
