"""Physical gates: never silently advance based on developer assertions.

Software-only prototypes can submit evidence but not create authentic physical
observation or a trusted external witness from nothing.
"""
from __future__ import annotations
from dataclasses import dataclass
import hashlib
import json
import re
from .codec import ContractError, canonical, SHA

REQUIRED=(
    "RTL_SIMULATION", "RTL_LINT", "GENERIC_SYNTH",
    "FPGA_BITSTREAM", "FPGA_PROGRAMMED", "SENSOR_MCP9808", "SENSOR_INA226",
    "SECURE_ELEMENT_P256", "PHYSICAL_PRINTER", "OPTICAL_PHYSICAL_SCAN",
    "WITNESS_OPERATOR_INDEPENDENCE", "EXTERNAL_ANCHOR", "PRODUCTION_SECURITY_REVIEW",
    "REGULATORY_VALIDATION", "HUMAN_ACCOUNTABILITY")
TOOLS={
    "RTL_SIMULATION":"iverilog",
    "RTL_LINT":"verilator",
    "GENERIC_SYNTH":"yosys",
    "FPGA_BITSTREAM":"vivado_or_gowin",
    "FPGA_PROGRAMMED":"jtag_programming_readback",
    "SENSOR_MCP9808":"calibrated_i2c_temperature",
    "SENSOR_INA226":"calibrated_shunt_and_power_samples",
    "SECURE_ELEMENT_P256":"independently_authenticated_device_signing",
    "PHYSICAL_PRINTER":"physical_receipt_with_operator_evidence",
    "OPTICAL_PHYSICAL_SCAN":"physical_camera_decode_and_verify",
    "WITNESS_OPERATOR_INDEPENDENCE":"verified_organizations_and_pinned_keys",
    "EXTERNAL_ANCHOR":"independently_verified_anchor",
    "PRODUCTION_SECURITY_REVIEW":"third_party_security_review",
    "REGULATORY_VALIDATION":"domain_specific_regulatory_assessment",
    "HUMAN_ACCOUNTABILITY":"signed_responsible_review",
}

class PhysicalClaimRejected(ValueError):pass


def baseline():
    return {g:{"status":"PENDING","required_evidence":TOOLS[g],
               "evidence_sha256":None,"source":"NOT_EXECUTED_IN_THIS_BUILD"} for g in REQUIRED}


def record_report(local_checks:dict|None=None)->dict:
    """Never uses user-supplied words to upgrade a physical gate to PASS."""
    result=baseline()
    if local_checks:
        for name,entry in local_checks.items():
            if name not in ("RTL_SIMULATION","RTL_LINT","GENERIC_SYNTH"):
                raise PhysicalClaimRejected("only software HDL checks may be recorded automatically")
            if type(entry) is not dict or set(entry)!={"status","log_sha256"}:
                raise PhysicalClaimRejected("full local check record required")
            if entry["status"]!="PASSED" or not SHA.fullmatch(str(entry["log_sha256"])):
                raise PhysicalClaimRejected("only evidence-bound passed check can be recorded")
            result[name]={"status":"PASSED_SOFTWARE_ONLY", "required_evidence":TOOLS[name],
                          "evidence_sha256":entry["log_sha256"],"source":"LOCAL_EXECUTION_UNREVIEWED"}
    return {"schema":"i-physical-acceptance/v1","gates":result,
            "physical_acceptance":False,"production_ready":False,
            "does_not_prove":["physical board programming","sensor authenticity","hardware key provenance",
                              "clinical or legal authority","printer output","immunity to side-channel attacks"]}


def assert_no_upgrade(report:dict):
    if report.get("physical_acceptance") is not False or report.get("production_ready") is not False:
        raise PhysicalClaimRejected("hardware acceptance requires independent evidence and review")
    gates=report.get("gates")
    if type(gates) is not dict or set(gates)!=set(REQUIRED):
        raise PhysicalClaimRejected("incomplete physical-gate accounting")
    for n,item in gates.items():
        if item["status"] not in ("PENDING","PASSED_SOFTWARE_ONLY"):
            raise PhysicalClaimRejected(f"unauthorized upgrade of {n}")
    return True
