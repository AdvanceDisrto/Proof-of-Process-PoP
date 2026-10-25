"""Buddy — one identity, three disclosed device profiles, one receipt chain."""
from cryptography.hazmat.primitives.asymmetric import ed25519
from buddy import Buddy, verify_chain

PHONE={"arch":"aarch64","cores":8,"memory_available_mb":1800,"python":"3.11","features":[],"interfaces":["lo","wlan0"],"has_wifi":True,"has_ethernet":False,"in_container":False,"simulated_class":"phone"}
LAPTOP={"arch":"x86_64","cores":8,"memory_available_mb":8000,"python":"3.12","features":["avx2","sse4_2"],"interfaces":["lo","en0","wlan0"],"has_wifi":True,"has_ethernet":True,"in_container":False,"simulated_class":"laptop"}
SERVER={"arch":"x86_64","cores":32,"memory_available_mb":96000,"python":"3.12","features":["avx512f","avx2","sse4_2"],"interfaces":["lo","eth0"],"has_wifi":False,"has_ethernet":True,"in_container":False,"simulated_class":"server"}
TASK={"seed":"buddy-task-alpha","size":256,"data_size":32,"parallel_preference":4,"min_precision":"int8"}
SEED="buddy-alpha-2026-seed-phrase"

def show(b,d,r):
    print(f"\n=== Device: {d['class']} ===")
    print("  device_hash:",d["device_hash"][:24]+"…"); print("  precision:",d["precision"])
    print("  plan_hash:",r["plan"]["plan_hash"][:24]+"…"); print("  output_hash:",r["execution"]["output_hash"][:24]+"…")
    print("  seq:",r["seq"]); print("  prev_receipt:",(r["prev_receipt"] or "null")[:32])
    print("  receipt_id:",r["receipt_id"][:24]+"…"); print("  approved:",r["approval"] is not None); print("  simulated:",d["runtime"]["simulated"]); print("  lessons:",len(b.state["lessons"]))

if __name__=="__main__":
    print("="*72); print("BUDDY — portable intelligence demo"); print("="*72)
    b=Buddy(SEED); approver=ed25519.Ed25519PrivateKey.generate(); print("\nBuddy identity:",b.id[:40]+"…")
    for i,dprofile in enumerate((PHONE,LAPTOP,SERVER)):
        d=b.arrive(dprofile); r=b.execute_on(d,TASK,approver_priv=approver); show(b,d,r)
        if i<2: b=Buddy.from_handoff(b.handoff(),SEED); print(f"\n[handoff] exported {len(b.state['receipts'])} receipt(s)")
    v=verify_chain(b.state["receipts"]); print("\n"+"="*72); print("CHAIN VERIFICATION"); print("="*72); print("  ok:",v["ok"])
    for e in v["errors"]: print("  error:",e)
    print("\nOBSERVATIONS")
    print("  buddy_id constant across 3 devices:",len({r["buddy_id"] for r in b.state["receipts"]})==1)
    print("  device_hash varies:",len({r["device"]["device_hash"] for r in b.state["receipts"]})==3)
    print("  plan_hash varies:",len({r["plan"]["plan_hash"] for r in b.state["receipts"]})==3)
    print("  output_hash varies:",len({r["execution"]["output_hash"] for r in b.state["receipts"]})==3)
    print("  prev_receipt chain intact:",v["ok"]); print("  lessons accumulated:",len(b.state["lessons"]))
