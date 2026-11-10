"""A green software test is NEVER a physically or professionally verified product."""
from __future__ import annotations

SOFTWARE_GATES=(
 "SOURCE_INVENTORY","PYTHON_UNIT_TESTS","WEBCRYPTO_TESTS","ITELEPATHY_TYPED_INTENT",
 "SYNTHETIC_IPQR_END_TO_END","HTTP_WEBSOCKET_SMOKE",
 "TESSERA_RTL_SIM","ARTY_BOARD_PRE_FLIGHT","POPC_RTL_SIM","STRICT_HDL_LINT","GENERIC_HDL_SYNTH",
)
EXTERNAL_GATES=(
 "FPGA_BITSTREAM_REAL","FPGA_PROGRAMMED_OBSERVED","INA226_PHYSICAL_CALIBRATED",
 "MCP9808_PHYSICAL_ATTESTED","P256_HARDWARE_SIGNER","PHYSICAL_PRINTER_SCAN",
 "CAMERA_IMORPHUS_STRESS","WEBSOCKET_REMOTE_IDENTITY",
 "INDEPENDENT_WITNESS_QUORUM","REVOCATION_EXTERNAL_ANCHOR","USB_PCB_ERC_DRC",
 "USB_CONTROLLED_IMPEDANCE","MANUFACTURING_DFM","BCI_VALIDATED_CONSENT",
 "GPU_NATIVE_EXECUTION","SECURITY_AUDIT","CLINICAL_VALIDATION",
 "LEGAL_REVIEW","PRIVACY_RISK_ASSESSMENT","PRODUCTION_DEPLOYMENT",
 "PATENT_LEGAL_REVIEW",
)
class PolicyViolation(ValueError): pass

def release_gate_report(observed=None):
    observed={} if observed is None else observed
    if type(observed) is not dict: raise PolicyViolation("dict required")
    states={}
    for k in SOFTWARE_GATES:
        x=observed.get(k)
        if x is None:
            states[k]={"status":"NOT_RUN","evidence_sha256":None}
            continue
        if type(x) is not dict or set(x)!={"status","evidence_sha256"}:
            raise PolicyViolation("invalid software evidence")
        status=x["status"];digest=x["evidence_sha256"]
        if status not in ("PASS_SOFTWARE_ONLY","FAIL","SKIPPED"):
            raise PolicyViolation("invalid result status")
        if type(digest) is not str or len(digest)!=64 or any(c not in "0123456789abcdef" for c in digest):
            raise PolicyViolation("invalid log SHA256")
        states[k]=dict(x)
    for k in EXTERNAL_GATES:
        if k in observed:raise PolicyViolation("external acceptance cannot be set by software: "+k)
        states[k]={"status":"PENDING_INDEPENDENT_EVIDENCE","evidence_sha256":None}
    if set(observed)-set(SOFTWARE_GATES):raise PolicyViolation("unknown gate")
    return {
        "schema":"i-release-gates/v1","gates":states,
        "software_only_release_candidate":all(states[k]["status"]=="PASS_SOFTWARE_ONLY" for k in SOFTWARE_GATES),
        "physical_acceptance":False,"production_ready":False,
        "clinical_approval":False,"legal_certification":False,
        "does_not_prove":["physical execution","calibrated physics","hardware identity",
            "independent witness chain","clinical diagnosis","legal merit",
            "manufacturability","hardware-origin signing"],
    }

def verify_policy_report(report):
    if type(report) is not dict or report.get("schema")!="i-release-gates/v1":
        raise PolicyViolation("wrong schema")
    for k in ("physical_acceptance","production_ready","clinical_approval","legal_certification"):
        if report.get(k) is not False:raise PolicyViolation("unauthorized release")
    gates=report.get("gates")
    if type(gates) is not dict or set(gates)!=(set(SOFTWARE_GATES)|set(EXTERNAL_GATES)):
        raise PolicyViolation("incomplete gate list")
    for k in EXTERNAL_GATES:
        if gates[k]!={"status":"PENDING_INDEPENDENT_EVIDENCE","evidence_sha256":None}:
            raise PolicyViolation("forged physical state")
    evidence={k:x for k,x in gates.items() if k in SOFTWARE_GATES and x["status"]!="NOT_RUN"}
    if release_gate_report(evidence)!=report:raise PolicyViolation("report not reproducible")
    return True
