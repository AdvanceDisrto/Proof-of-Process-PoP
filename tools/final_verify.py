import argparse,hashlib,json,sys
from pathlib import Path
from tools.mmr import MMR,sha,jcs
def verify_arc(r):
 from tools.arc3_receipt import verify
 return verify(r)["errors"]
def main():
 ap=argparse.ArgumentParser();ap.add_argument("--evidence",default="evidence");ap.add_argument("--out",default="VERIFY_RESULTS.json");a=ap.parse_args();E=Path(a.evidence)
 mp=E/"MASTER_RUN_RECEIPT.json"
 if not mp.exists():print(f"FATAL: {mp} not found");sys.exit(1)
 master=json.loads(mp.read_text());m=MMR();checks=[];ok=True
 for f in sorted(E.glob("*.json")):
  if f.name=="MASTER_RUN_RECEIPT.json":continue
  m.append(f.read_bytes())
 root=m.root();match=root==master.get("master_mmr_root")
 if not match:ok=False;checks.append({"artifact":"MASTER","errors":["master_root_mismatch"]})
 for ent in master.get("artifacts",[]):
  p=E/ent["file"]
  errs=[]
  if not p.exists():errs=["missing"]
  elif sha(p.read_bytes())!=ent.get("sha256"):errs=["sha256_mismatch"]
  else:
   try:d=json.loads(p.read_bytes())
   except Exception:d=None
   if d is not None and ent.get("kind")=="receipt" and ent["file"].startswith("receipt_"):errs=verify_arc(d)
  if errs:ok=False
  checks.append({"artifact":ent["file"],"kind":ent.get("kind"),"errors":errs,"ok":not errs})
 res={"spec":"innovulis-final-verify/1.0","stored_master_root":master.get("master_mmr_root"),"recomputed_master_root":root,"master_root_match":match,"artifact_count":master.get("artifact_count"),"checks":checks,"ok":ok}
 res["verify_sha256"]=sha(jcs(res));Path(a.out).write_text(json.dumps(res,indent=2)+"\n")
 print(json.dumps({"master_root_match":match,"artifact_count":len(checks),"failed":sum(not x["ok"] for x in checks),"ok":ok},indent=2));sys.exit(0 if ok else 1)
if __name__=="__main__":main()
