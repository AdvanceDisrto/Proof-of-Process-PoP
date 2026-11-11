"""Evidence-linked deterministic execution transcript. No claim of immutable local storage."""
from __future__ import annotations
import hashlib,json,os,re,tempfile
from pathlib import Path

SHA256=re.compile(r"[0-9a-f]{64}\Z")
SHA1=re.compile(r"[0-9a-f]{40}\Z")
class EvidenceRejected(ValueError):pass

def canonical(obj):
    return json.dumps(obj,sort_keys=True,separators=(",",":"),ensure_ascii=False,allow_nan=False).encode()

def digest(data:bytes)->str:
    return hashlib.sha256(data).hexdigest()

def make_record(*,sequence,previous_hash,name,argv,returncode,output_bytes,elapsed_ms,commit_sha=None):
    if type(sequence) is not int or sequence<=0:raise EvidenceRejected("invalid sequence")
    if type(previous_hash) is not str or not SHA256.fullmatch(previous_hash):
        raise EvidenceRejected("invalid preceding root")
    if type(name) is not str or not re.fullmatch(r"[a-z0-9_]{2,64}",name):
        raise EvidenceRejected("invalid task name")
    if type(argv) is not list or not argv or any(type(s) is not str or not s or len(s)>1000 for s in argv):
        raise EvidenceRejected("invalid command")
    if type(returncode) is not int or type(elapsed_ms) is not int or elapsed_ms<0:
        raise EvidenceRejected("invalid exit/time")
    if type(output_bytes) is not bytes or len(output_bytes)>5_000_000:
        raise EvidenceRejected("invalid output length")
    if commit_sha is not None and (type(commit_sha) is not str or not SHA1.fullmatch(commit_sha)):
        raise EvidenceRejected("invalid commit")
    entry={"schema":"i-execution-evidence/v1","sequence":sequence,"previous_hash":previous_hash,
           "name":name,"argv":argv,"returncode":returncode,
           "result":"PASS_SOFTWARE_ONLY" if returncode==0 else "FAIL",
           "elapsed_ms":elapsed_ms,"log_sha256":digest(output_bytes),"log_size":len(output_bytes),
           "commit_sha":commit_sha,"origin":"LOCAL_OR_CI_RUNNER_UNATTESTED",
           "does_not_prove":"physical output, domain correctness or causality"}
    entry["entry_hash"]=digest(canonical(entry))
    return entry

def verify_chain(entries,logs):
    if type(entries) is not list or type(logs) is not dict:raise EvidenceRejected("bad chain")
    prev="0"*64
    for i,e in enumerate(entries,1):
        if type(e) is not dict or e.get("sequence")!=i or e.get("previous_hash")!=prev:
            raise EvidenceRejected("sequence or linkage broken")
        b=logs.get(e.get("name"))
        if type(b) is not bytes or digest(b)!=e.get("log_sha256") or len(b)!=e.get("log_size"):
            raise EvidenceRejected("log missing or tampered")
        h=e.get("entry_hash")
        if type(h) is not str or not SHA256.fullmatch(h):
            raise EvidenceRejected("bad entry hash")
        if digest(canonical({k:v for k,v in e.items() if k!="entry_hash"}))!=h:
            raise EvidenceRejected("entry changed")
        if e.get("result")!=("PASS_SOFTWARE_ONLY" if e.get("returncode")==0 else "FAIL"):
            raise EvidenceRejected("result altered")
        prev=h
    return True

def safe_atomic_json(path,obj):
    target=Path(path);target.parent.mkdir(parents=True,exist_ok=True)
    data=json.dumps(obj,sort_keys=True,ensure_ascii=False,indent=2,allow_nan=False).encode()+b"\n"
    with tempfile.NamedTemporaryFile(dir=target.parent,prefix=".pending-",delete=False) as handle:
        tmp=handle.name
        try:
            os.chmod(tmp,0o600)
            handle.write(data);handle.flush();os.fsync(handle.fileno())
        except BaseException:
            Path(tmp).unlink(missing_ok=True)
            raise
    try:os.replace(tmp,target)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise
