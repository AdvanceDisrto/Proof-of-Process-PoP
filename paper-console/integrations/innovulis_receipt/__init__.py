"""iNNOVULIS Open Receipt Verifier v1.0.

Verify signed *digital attestations*, not universal or physical truth.
The publisher's own receipts must be treated as untrusted input.
"""
__version__ = "1.0.0"
from .engine import verify, Verdict
from .codec import encode_qr_text, decode_qr_text
__all__ = ["verify", "Verdict", "encode_qr_text", "decode_qr_text"]
