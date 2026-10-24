from pqcrypto.sign import ml_dsa_87

def test_ml_dsa_87_sign_verify():
    public_key, secret_key = ml_dsa_87.generate_keypair()
    message = b"iSPU receipt ML-DSA-87 test vector"
    signature = ml_dsa_87.sign(secret_key, message)
    assert ml_dsa_87.verify(public_key, message, signature)
    assert not ml_dsa_87.verify(public_key, b"tampered", signature)
