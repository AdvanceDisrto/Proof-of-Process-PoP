import asyncio
from proof.parallel_pop import Domain,aggregate,verify_domain
from proof.energy_pop import measure
from reality.ppso_control_plane import PPSOControlPlane

def test_parallel_receipts_verify():
 async def go():
  async def w():return {"state":"VERIFIED_PROCESS","x":1}
  rs=await asyncio.gather(*[Domain(x).execute(w) for x in ("A","B","C","D")]);return rs
 rs=asyncio.run(go());assert all(map(verify_domain,rs));m=aggregate(rs);assert m["body"]["state"]=="VERIFIED_PROCESS";assert m["body"]["merkle_root"].startswith("sha256:")
def test_fail_closed():
 async def go():
  async def ok():return {"state":"VERIFIED_PROCESS"}
  async def bad():return {"state":"ACTION_REQUIRED"}
  return await asyncio.gather(Domain("A").execute(ok),Domain("B").execute(bad))
 assert aggregate(asyncio.run(go()))["body"]["state"]=="INCOMPLETE"
def test_energy_unavailable(monkeypatch):
 import proof.energy_pop as e;monkeypatch.setattr(e,"read_energy_uj",lambda:None);r=measure(lambda:None);assert r["energy_consumed_uj"] is None and r["state"]=="ACTION_REQUIRED"
def test_ppso_requires_real_evidence():assert PPSOControlPlane().promote_physical({})=="ACTION_REQUIRED"
