"""Cross-repository smoke: real QoW receipts through the actual PoP bridge."""
import asyncio
import copy
import sys
from pathlib import Path
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"_qow_checkout"))
from qow.truthculator import pubkey_hex
from qow.truthculator_v2 import TruthculatorV2
from qow.independent_verifier import independent_check
from integrations.qow_pop_bridge import validate_qow,qow_domain_receipt

def main():
    sk=Ed25519PrivateKey.generate()
    pin=pubkey_hex(sk)
    engine=TruthculatorV2(sk,"pop-cross-repo-ci")
    good=engine.compute("CROSS_REPO_Z3","x>5 entails x>0",
        "(declare-const x Int)",["(> x 5)"],"(> x 0)")
    def recheck(r):
        return independent_check(r,pin)
    assert good["body"]["verdict"]=="PROVEN_TRUE"
    assert validate_qow(good,pin,recheck)["verdict"]=="PROVEN_TRUE"
    # Exercise actual PoP Domain.execute, not a mocked callback.
    result=asyncio.run(qow_domain_receipt(good,pin,recheck))
    print("PoP Domain.execute return:",repr(result)[:1000])
    tampered=copy.deepcopy(good)
    tampered["body"]["hypothesis"]="(> x 100)"
    try:
        validate_qow(tampered,pin,recheck)
    except Exception:
        pass
    else:
        raise AssertionError("tampered signed receipt was accepted")
    # Validly signed but false mathematical assertion must fail re-execution.
    wrong=copy.deepcopy(good)
    wrong["body"]["hypothesis"]="(> x 100)"
    from qow.truthculator import canonical,digest
    msg=canonical(wrong["body"])
    wrong["receipt_hash"]=digest(msg)
    wrong["signature"]=sk.sign(msg).hex()
    try:
        validate_qow(wrong,pin,recheck)
    except ValueError:
        pass
    else:
        raise AssertionError("independently false signed verdict was accepted")
    print("ACCEPT_REAL_CROSS_REPO_Z3_SMOKE: PASS (local CI tier)")
if __name__=="__main__":
    main()
