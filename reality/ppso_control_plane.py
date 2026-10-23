from reality.gates import ACTION_REQUIRED,MEASURED_PASS
class PPSOControlPlane:
    def promote_physical(self,evidence):
        required=("artifact_hash","measurement","source","verification")
        if not isinstance(evidence,dict) or any(not evidence.get(k) for k in required): return ACTION_REQUIRED
        return MEASURED_PASS
