import argparse,json,sys
p=argparse.ArgumentParser(); p.add_argument("path"); p.add_argument("--expect-blocked",action="store_true"); a=p.parse_args()
d=json.load(open(a.path,encoding="utf-8"))
required=d["required_evidence"]; present=d.get("evidence",{})
missing=[x for x in required if not present.get(x)]
blocked=d.get("state")=="BLOCKED" and not d.get("promotion",{}).get("active",False)
print("i™ MATERIALIZATION GATE — FAIL-CLOSED TOPOLOGY VALIDATION")
print("Current State:",d.get("state"))
for x in required: print(("  [PASS]" if present.get(x) else "  [MISSING]"),x)
if a.expect_blocked and not blocked: print("FAIL: expected blocked state"); sys.exit(1)
if not blocked: print("FAIL: topology is promotable without all evidence"); sys.exit(1)
print("ACTION_REQUIRED: promotion denied; training authorization remains false")
