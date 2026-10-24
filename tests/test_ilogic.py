import pytest
from tools.ilogic import *

def C(i,s,p,pol=1,status=ESTABLISHED,att=UNATTESTED): return Claim(i,s,p,pol,status,att)

def test_meet_two_established():
    e=Engine([C("a","x","a"),C("b","x","b")])
    d=e.apply(Rule("r",MODE_EVIDENCE,("a","b"),"x","c"))
    assert d["tier"]=="VERIFIED_PROCESS" and d["gate"]=="ACTION_REQUIRED"

def test_meet_with_open():
    e=Engine([C("a","x","a"),C("b","x","b",status=OPEN)])
    assert e.apply(Rule("r",MODE_EVIDENCE,("a","b"),"x","c"))["tier"]=="ACTION_REQUIRED"

def test_meet_with_refuted():
    e=Engine([C("a","x","a"),C("b","x","b",status=REFUTED)])
    assert e.apply(Rule("r",MODE_EVIDENCE,("a","b"),"x","c"))["tier"]=="REFUTED"

def test_contradiction_never_resolved():
    e=Engine([C("a","x","p",1),C("b","x","p",-1)])
    e._check_contradictions()
    assert e.claims["a"].status==CONTRADICTORY and e.claims["b"].status==CONTRADICTORY

def test_no_laundering_to_law():
    e=Engine([C("a","x","a"),C("b","x","b")])
    assert e.apply(Rule("r",MODE_EVIDENCE,("a","b"),"x","c"))["tier"]=="VERIFIED_PROCESS"

def test_law_requires_axioms():
    e=Engine([C("a","x","a",att=ATTESTED)])
    with pytest.raises(LogicError): e.apply(Rule("r",MODE_LAW,("a",),"x","c",True))

def test_attestation_not_manufactured():
    e=Engine([C("a","x","a",att=ATTESTED),C("b","x","b",att=ATTESTED)])
    d=e.apply(Rule("r",MODE_EVIDENCE,("a","b"),"x","c",False))
    assert d["claim"]["attestation"]==UNATTESTED and d["gate"]=="ACTION_REQUIRED"

def test_attestation_preserved():
    e=Engine([C("a","x","a",att=ATTESTED),C("b","x","b",att=ATTESTED)])
    d=e.apply(Rule("r",MODE_LAW,("a","b"),"x","c",True,("axiom-1",)))
    assert d["claim"]["attestation"]==ATTESTED and d["gate"]=="MEASURED_PASS"

def test_no_negation_as_failure():
    e=Engine([C("a","x","a")])
    with pytest.raises(LogicError): e.apply(Rule("r",MODE_EVIDENCE,("missing",),"x","c"))

def test_deterministic_root():
    def run():
        e=Engine([C("a","x","a"),C("b","x","b")])
        e.apply(Rule("r",MODE_EVIDENCE,("a","b"),"x","c"))
        return e.receipt()["derivation_mmr_root"]
    assert run()==run()
