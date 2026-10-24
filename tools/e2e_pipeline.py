#!/usr/bin/env python3
import json, os, subprocess, sys

def run(cmd):
    return subprocess.check_output(cmd, text=True).strip()

render = run(["./build/render_combo"])
pairs = dict(line.split("=",1) for line in render.splitlines() if "=" in line)
fb = pairs["framebuffer_sha256"]
rtl_mode = "NOT_RUN"
rtl_receipt = None
if os.path.exists("build/ibare_rtl.vvp"):
    out = run(["vvp","build/ibare_rtl.vvp","+FB_HASH="+fb])
    rtl_receipt = next(line.split("=",1)[1] for line in out.splitlines() if line.startswith("RTL_RECEIPT="))
    rtl_mode = "RTL_SIMULATION"
manifest = {
 "spec":"innovulis-pop-e2e/1.0",
 "state":"VERIFIED_PROCESS",
 "software":{"framebuffer_hash":"sha256:"+fb,"receipt":"sha256:"+pairs["process_receipt"]},
 "rtl":{"mode":rtl_mode,"receipt":("sha256:"+rtl_receipt) if rtl_receipt else None},
 "physical_gate":"ACTION_REQUIRED",
 "does_not_prove":[
  "physical energy measurement when no validated meter reading is present",
  "TPM quote or hardware-rooted attestation",
  "fabricated silicon or foundry signoff",
  "that RTL simulation is physical hardware execution",
  "that Secure Enclave, StrongBox, PUF, or ZKP hardware claims were exercised"
 ]
}
with open("E2E_REALITY_MANIFEST.json","w",encoding="utf-8") as f:
    json.dump(manifest,f,indent=2,sort_keys=True); f.write("\n")
print(json.dumps(manifest,sort_keys=True))
