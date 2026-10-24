from cryptography.hazmat.primitives.asymmetric.ml_dsa import MLDSA87PrivateKey
def test_ml_dsa_87_sign_verify():
    sk=MLDSA87PrivateKey.generate()
    pk=sk.public_key()
    msg=b"iSPU receipt ML-DSA-87 test vector"
    sig=sk.sign(msg)
    pk.verify(sig,msg)
    try: pk.verify(sig,b"tampered")
    except Exception: pass
    else: raise AssertionError("tamper accepted")
