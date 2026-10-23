from .identity import load_and_verify

class IDRSentinel:
    def __init__(self,idr_path="IDR_ROOT.json",trusted_public_key_hex=""):
        self.idr_path=idr_path; self.trusted_public_key_hex=trusted_public_key_hex; self.loaded=False; self.idr_data=None
    def verify_genesis(self):
        if not self.trusted_public_key_hex: raise RuntimeError("iDr requires a trusted genesis public key")
        self.idr_data=load_and_verify(self.idr_path,self.trusted_public_key_hex); self.loaded=True; return True
    def check_ai_authorization(self,requested_action):
        if not self.loaded: return False
        if requested_action in {"fabricate","measure_joules","assert_silicon"}:
            return self.idr_data.get("truth_boundary",{}).get("physical_gate")=="MEASURED_PASS"
        return True
