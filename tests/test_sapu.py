import copy,pytest
from sapu.reference import SAPU,SAPUError,measurement
from sapu.verify import verify_sapu_receipt
def mk(n="x"):return SAPU(f"/tmp/_sapu_{n}.hex")
def admit(s,att=None,det=(True,True)):
 s.admit("request",{"prompt":"hi"});s.admit("response",{"determinism":{"attempted":det[0],"matched":det[1]}});s.admit("attestation",att or {})
def test_unattested_verified():s=mk();admit(s);s.lock();assert s.derive()["tier"]=="VERIFIED_PROCESS";assert verify_sapu_receipt(s.sign())["ok"]
def test_attested_pass():s=mk();admit(s,{"tee_quote":{"vendor_chain":["AMD_SEV_SNP_ROOT_CA"],"measurement":"d"},"energy":{"joules":1.0,"source":"signed:lab"}});s.lock();assert s.derive()["tier"]=="MEASURED_PASS";assert verify_sapu_receipt(s.sign())["ok"]
def test_untrusted_closed():s=mk();admit(s,{"tee_quote":{"vendor_chain":["SELF_SIGNED"],"measurement":"x"},"energy":{"joules":1.0,"source":"signed:me"}});s.lock();assert s.derive()["attestation_axis"]=="UNATTESTED"
def test_subclass_forgery_detected():
 class Evil(SAPU):
  def derive(self):return {"truth_axis":"ESTABLISHED","attestation_axis":"ATTESTED","tier":"MEASURED_PASS"}
 e=Evil("/tmp/_sapu_evil.hex");admit(e);e.lock();d=e.derive()
 # Evil's return alone is never sufficient: emulate a compromised emitter by signing it.
 e._derived=d;r=e.sign();assert not verify_sapu_receipt(r)["ok"];assert any("attestation_implies_tier" in x for x in verify_sapu_receipt(r)["errors"])
def test_lock():s=mk();admit(s);s.lock();with pytest.raises(SAPUError):s.admit("request",{})
def test_derive_requires_lock():
 with pytest.raises(SAPUError):mk().derive()
def test_measurements_differ():assert measurement("scaffold/1")!=measurement("scaffold/1-strict")
def test_measurement_stable():assert mk("a").measurement==mk("b").measurement
def test_tier_tamper_breaks_signature():
 s=mk();admit(s);s.lock();s.derive();r=s.sign();r["derived"]["tier"]="MEASURED_PASS";assert not verify_sapu_receipt(r)["ok"]
