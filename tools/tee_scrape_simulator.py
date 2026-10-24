#!/usr/bin/env python3
"""Non-TEE memory-observability and fail-closed attestation simulation.

This is evidence about the current host and verifier behavior only. It cannot
prove or simulate hardware-rooted SEV-SNP/TDX protection.
"""
import hashlib, json, os, subprocess, sys, tempfile, time
from pathlib import Path

def _read(path):
    try:
        return Path(path).read_text().strip()
    except OSError:
        return ""

def detect_tee_hardware():
    indicators = {
        "amd_sev_snp_sysfs": os.path.exists("/sys/module/kvm_amd/parameters/sev_snp"),
        "amd_sev_guest_dev": os.path.exists("/dev/sev-guest"),
        "intel_tdx_guest_dev": os.path.exists("/dev/tdx-guest"),
        "intel_sgx_dev": os.path.exists("/dev/sgx_enclave"),
        "kernel_log_mentions_tee": False,
    }
    try:
        p = subprocess.run(["dmesg"], capture_output=True, text=True, timeout=2)
        text = (p.stdout + p.stderr).lower()
        indicators["kernel_log_mentions_tee"] = any(x in text for x in ("sev-snp", "sev_snp", "tdx", "sgx"))
    except (OSError, subprocess.TimeoutExpired):
        pass
    snp = _read("/sys/module/kvm_amd/parameters/sev_snp") == "Y"
    indicators["tee_present"] = bool(indicators["amd_sev_guest_dev"] or indicators["intel_tdx_guest_dev"] or indicators["intel_sgx_dev"] or (indicators["amd_sev_snp_sysfs"] and snp))
    return indicators

def simulate_host_memory_scrape():
    secret = b"HOST_SCRAPE_TARGET_SECRET_abcdef1234567890"
    code = "import sys,time; secret=%r; print(__import__('os').getpid(),flush=True); time.sleep(4)" % secret
    child = subprocess.Popen([sys.executable, "-c", code], stdout=subprocess.PIPE, text=True)
    result = {"child_pid": None, "maps_readable": False, "mem_openable": False, "secret_observable": False, "failure_reason": None, "ptrace_scope": _read("/proc/sys/kernel/yama/ptrace_scope") or "unavailable"}
    try:
        result["child_pid"] = int(child.stdout.readline().strip())
        maps = ""
        try:
            maps = Path(f"/proc/{result['child_pid']}/maps").read_text()
            result["maps_readable"] = bool(maps)
        except OSError as e:
            result["failure_reason"] = f"maps: {type(e).__name__}"
        try:
            with open(f"/proc/{result['child_pid']}/mem", "rb") as mem:
                result["mem_openable"] = True
                for line in maps.splitlines():
                    if "[heap]" in line:
                        start = int(line.split("-", 1)[0], 16)
                        mem.seek(start)
                        if secret in mem.read(1024 * 1024):
                            result["secret_observable"] = True
                        break
        except PermissionError:
            result["failure_reason"] = "mem: PermissionError (ptrace_scope restriction)"
        except OSError as e:
            result["failure_reason"] = f"mem: {type(e).__name__}"
        return result
    finally:
        child.terminate()
        try: child.wait(timeout=2)
        except subprocess.TimeoutExpired: child.kill()

def simulate_attestation_verifier(quote):
    roots = {"AMD_SEV_SNP_ROOT_CA", "INTEL_TDX_ROOT_CA", "NVIDIA_TEE_ROOT_CA_2026"}
    chain = quote.get("vendor_chain")
    if not isinstance(chain, list) or not chain:
        return {"verdict":"REJECT","reason":"NO_VENDOR_CHAIN","physical_gate":"ACTION_REQUIRED"}
    if chain[-1] not in roots:
        return {"verdict":"REJECT","reason":"UNTRUSTED_ROOT","physical_gate":"ACTION_REQUIRED"}
    if not quote.get("measurement_sha256"):
        return {"verdict":"REJECT","reason":"MISSING_MEASUREMENT","physical_gate":"ACTION_REQUIRED"}
    if not quote.get("nonce_match"):
        return {"verdict":"REJECT","reason":"NONCE_MISMATCH","physical_gate":"ACTION_REQUIRED"}
    return {"verdict":"PASS","reason":"ALL_GATES_SATISFIED","physical_gate":"MEASURED_PASS"}

def emit_evidence_receipt(out_path):
    tee = detect_tee_hardware()
    scrape = simulate_host_memory_scrape()
    rejections = {
        "empty_quote": simulate_attestation_verifier({}),
        "fake_chain": simulate_attestation_verifier({"vendor_chain":["FAKE_CA"],"measurement_sha256":"abc","nonce_match":True}),
        "no_measurement": simulate_attestation_verifier({"vendor_chain":["AMD_SEV_SNP_ROOT_CA"],"nonce_match":True}),
        "nonce_mismatch": simulate_attestation_verifier({"vendor_chain":["AMD_SEV_SNP_ROOT_CA"],"measurement_sha256":"abc","nonce_match":False}),
    }
    receipt = {
        "spec":"innovulis-tee-scrape-simulation/1.0",
        "timestamp_utc":time.time(),
        "host":{"platform":sys.platform,"machine":os.uname().machine,"kernel":os.uname().release},
        "tee_hardware_detected":tee,
        "host_scrape_attempt":scrape,
        "attestation_verifier_rejections":rejections,
        "physical_gate":"ACTION_REQUIRED",
        "proves":[
            "The current host's exposed TEE indicators are recorded.",
            "The fail-closed verifier rejects synthetic or incomplete quotes.",
            "Simulation cannot promote the physical gate."
        ],
        "does_not_prove":[
            "Real SEV-SNP or TDX memory confidentiality.",
            "A vendor-signed hardware quote.",
            "Physical silicon execution or measured energy."
        ],
        "the_central_rule":"The receipt can record reality; it cannot manufacture reality.",
    }
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    Path(out_path).write_text(json.dumps(receipt, indent=2) + "\n")
    return receipt

if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else "evidence/tee_scrape_evidence_receipt.json"
    print(json.dumps(emit_evidence_receipt(path), indent=2))
