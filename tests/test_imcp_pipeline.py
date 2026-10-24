"""Fail-closed iMCP authority pipeline tests."""
import time
import pytest
from intelligence.imcp_kernel import iMCPAuthorityKernel
class Table:
    def __init__(self,s): self.s=s; self.mode=None; self.f=None; self.data=None
    def select(self,*a,**k): self.mode="select"; return self
    def insert(self,d): self.mode="insert"; self.data=d; return self
    def eq(self,c,v): self.f=(c,v); return self
    def execute(self):
        class R:
            def __init__(self,d): self.data=d
        if self.mode=="insert":
            if self.s["fail"]: raise Exception("Simulated Supabase connection drop")
            self.s["rows"].append(self.data); return R([self.data])
        rows=list(self.s["rows"])
        if self.f: rows=[r for r in rows if r.get(self.f[0])==self.f[1]]
        return R(rows)
class DB:
    def __init__(self,fail=False): self.store={"rows":[],"fail":fail}
    def table(self,n): return Table(self.store)
class Server:
    name="test-inner-server"
    def __init__(self,raise_=False): self.call_count=0; self.raise_=raise_
    async def handle(self,req):
        self.call_count+=1
        if self.raise_: raise RuntimeError("Simulated tool crash")
        return {"jsonrpc":"2.0","id":req.get("id"),"result":{"data":"tool-success","secret":"TOOL-OUTPUT-PAYLOAD"}}
def verify(cert): return (False,"NONE") if cert in (None,"invalid_root") else (True,"iska_root_test_8f4a2b")
def req(method,id_="1",params=None): return {"jsonrpc":"2.0","id":id_,"method":method,"params":params or {}}
async def mint(k): return (await k.handle(req("i/mint_challenge"),{"caller_id":"agent-01","delegation_cert":"valid_cert"}))["result"]["challenge_nonce"]
def ctx(nonce,cert="valid_cert"): return {"caller_id":"agent-01","delegation_cert":cert,"nonce":nonce}
@pytest.fixture
def kernel():
    db,server=DB(),Server(); return iMCPAuthorityKernel(verify,db,server),db,server
@pytest.fixture
def failing():
    db,server=DB(True),Server(); return iMCPAuthorityKernel(verify,db,server),db,server
@pytest.mark.asyncio
async def test_missing_nonce_rejects_standard_mcp_call(kernel):
    k,db,s=kernel; r=await k.handle(req("tools/call"),ctx(None)); assert r["error"]["code"]==-32002; assert s.call_count==0 and not db.store["rows"]
@pytest.mark.asyncio
async def test_wrong_nonce_rejects_standard_mcp_call(kernel):
    k,db,s=kernel; await mint(k); r=await k.handle(req("tools/call"),ctx("wrong")); assert r["error"]["code"]==-32002; assert s.call_count==0 and not db.store["rows"]
@pytest.mark.asyncio
async def test_no_session_rejects_standard_mcp_call(kernel):
    k,db,s=kernel; r=await k.handle(req("tools/call"),ctx("never")); assert r["error"]["code"]==-32002; assert s.call_count==0 and not db.store["rows"]
@pytest.mark.asyncio
async def test_expired_challenge_rejects_call(kernel):
    k,db,s=kernel; n=await mint(k); k.active_challenges["agent-01"]["expires"]=time.time()-1; r=await k.handle(req("tools/call"),ctx(n)); assert r["error"]["code"]==-32002 and "CHALLENGE_EXPIRED" in r["error"]["message"] and s.call_count==0
@pytest.mark.asyncio
async def test_invalid_delegation_rejects_mint(kernel):
    k,_,_=kernel; r=await k.handle(req("i/mint_challenge"),{"caller_id":"agent-01","delegation_cert":"invalid_root"}); assert r["error"]["code"]==-32001
@pytest.mark.asyncio
async def test_invalid_delegation_rejects_dispatch_even_with_valid_nonce(kernel):
    k,db,s=kernel; n=await mint(k); r=await k.handle(req("tools/call"),ctx(n,"invalid_root")); assert r["error"]["code"]==-32001 and s.call_count==0 and not db.store["rows"]
@pytest.mark.asyncio
async def test_valid_nonce_allows_call_and_writes_receipt(kernel):
    k,db,s=kernel; n=await mint(k); r=await k.handle(req("tools/call","2",{"name":"x"}),ctx(n)); rec=db.store["rows"][0]; assert r["result"]["data"]=="tool-success"; assert s.call_count==1; assert rec["physical_gate"]=="ACTION_REQUIRED"; assert rec["execution_state"]=="VERIFIED_PROCESS"; assert rec["intent"]["nonce"]==n; assert "agent-01" not in k.active_challenges; assert (await k.handle(req("tools/call","3"),ctx(n)))["error"]["code"]==-32002
@pytest.mark.asyncio
async def test_db_write_failure_does_not_leak_tool_result(failing):
    k,db,s=failing; n=await mint(k); r=await k.handle(req("tools/call"),ctx(n)); assert r["error"]["code"]==-32003; assert "FAIL_CLOSED" in r["error"]["message"]; assert "TOOL-OUTPUT-PAYLOAD" not in str(r) and "tool-success" not in str(r); assert s.call_count==1
@pytest.mark.asyncio
async def test_seal_intent_returns_hash(kernel):
    k,_,_=kernel; r=await k.handle(req("i/seal_intent",params={"body":{"foo":"bar"}}),ctx(None)); assert r["result"]["intent_hash"].startswith("sha256:")
@pytest.mark.asyncio
async def test_seal_intent_missing_body_fails(kernel):
    k,_,_=kernel; r=await k.handle(req("i/seal_intent"),ctx(None)); assert r["error"]["code"]==-32602
@pytest.mark.asyncio
async def test_verify_receipt_found(kernel):
    k,db,_=kernel; n=await mint(k); await k.handle(req("tools/call"),ctx(n)); rid=db.store["rows"][0]["receipt_id"]; r=await k.handle(req("i/verify_receipt",params={"receipt_id":rid}),ctx(None)); assert r["result"]["verification"]=="PASS"
@pytest.mark.asyncio
async def test_verify_receipt_not_found(kernel):
    k,_,_=kernel; r=await k.handle(req("i/verify_receipt",params={"receipt_id":"missing"}),ctx(None)); assert r["error"]["code"]==-32000
@pytest.mark.asyncio
async def test_tool_exception_still_writes_receipt_with_tool_failed_state(kernel):
    k,db,_=kernel; k.server=Server(True); n=await mint(k); r=await k.handle(req("tools/call"),ctx(n)); assert r["error"]["code"]==-32603; assert db.store["rows"][0]["execution_state"]=="TOOL_FAILED"; assert db.store["rows"][0]["physical_gate"]=="ACTION_REQUIRED"
