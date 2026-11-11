"""Auditable source registry; source presence is NOT proof of execution."""
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path

@dataclass(frozen=True)
class Component:
    ident:str
    path:str
    domain:str
    scope:str
    remaining_gate:str

COMPONENTS=(
 Component("IPQR_OPEN_VERIFIER","paper-console/integrations/innovulis_receipt/engine.py","crypto","signed synthetic receipts","independent anchors, witnesses, revocation"),
 Component("HUMAN_HUB","human-hub/human_hub/core.py","human","synthetic human review","qualified human authorization"),
 Component("PAPER_CONSOLE","paper-console/paper_console/escpos.py","output","ESC/POS preview","actual printed and rescanned receipt"),
 Component("RGPU_TERMINAL","rgpu-terminal/rgpu_terminal/server.py","runtime","local two-WebSocket demo","remote security and GPU telemetry"),
 Component("BROWSER_WEBCRYPTO","rgpu-terminal/rgpu_terminal/static/verify.mjs","crypto","browser Ed25519","independently pinned signer and mobile testing"),
 Component("IPCIH_CAPSULE","ipcih-capsule/ipcih/core.py","capsule","signed small capsule","sandbox security review"),
 Component("IMORPHUS","ipcih-capsule/ipcih/imorphus.py","optical","exact pixel decoding","real camera and JAB field tests"),
 Component("BUDDY_BOUNDED_AUDIT","ipcih-capsule/ipcih/auditor.py","epistemic","bounded model claims","independent source facts and formalization"),
 Component("TWINIONS","twinions-legal/twinions_legal/arbiter.py","epistemic","disagreement detection","independent expert adjudication"),
 Component("TWINIONS_LEGAL","twinions-legal/twinions_legal/rules.py","legal","document workflow","counsel-reviewed jurisdiction-specific gates"),
 Component("ITELEPATHY","itelepathy/core.py","messaging","typed opt-in local protocol","real BCI and peer consent"),
 Component("TESSERA_G_RTL","tessera-g/rtl/tessera_g_dag_tile.sv","rtl","sim/lint/synth","physical FPGA timing and readback"),
 Component("TESSERA_ARTY","tessera-g/fpga/arty_a7_100t/build_bitstream.tcl","rtl","Vivado instructions","actual Vivado .bit and board"),
 Component("POPC_PU_RTL","paper-console/rtl/popc_gate.sv","rtl","sign-request logic","real physical sign binding"),
 Component("ISTICK_CONCEPT","unified-i/hardware/istick_reference.json","manufacturing","candidate netlist","KiCad schematic, fab Gerber, DRC"),
 Component("ISTICK_HOST","twinions-legal/hardware/innovulis_istick.cpp","host","C++ local gate","MCU firmware and hardware"),
 Component("INA226","paper-console/paper_console/energy.py","sensor","numerical energy model","physical calibrated readings"),
 Component("MCP9808","unified-i/unified_i/hardware.py","sensor","I2C device driver","physical sensor and provenance"),
 Component("ATECC608_P256","paper-console/paper_console/p256_bridge.py","crypto","ECDSA P256 software validation","real chip attestation"),
 Component("DAGE_BRIDGE","tessera-g/ci/check_z3_vector.py","compute","headless trace bridge","real GPU/FPGA"),
 Component("REGULATORY_RELEASE","unified-i/docs/RELEASE_GATE_SPEC.md","policy","release hold","clinical/legal external review"),
 Component("UNIFIED_I_INTEGRATION","unified-i/unified_i/bridge.py","integration","synthetic closed loop","physical and external sources"),
)

def inventory(repo_root):
    root=Path(repo_root).resolve()
    items=[]
    for c in COMPONENTS:
        path=root/c.path
        exists=path.is_file() and not path.is_symlink()
        items.append({"id":c.ident,"domain":c.domain,"path":c.path,
            "source_present":exists,"scope":c.scope,"remaining_gate":c.remaining_gate,
            "acceptance":"SOURCE_PRESENT_UNTESTED" if exists else "MISSING_SOURCE"})
    return {"schema":"i-ecosystem-inventory/v1","components":items,
        "source_present":sum(x["source_present"] for x in items),
        "total_components":len(items),
        "does_not_prove":["software execution","physical hardware","security review","legal or clinical correctness"]}
