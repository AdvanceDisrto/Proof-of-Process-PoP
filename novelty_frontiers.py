"""Evidence-only frontier primitives for the PoP architecture.

These components model new evidence dimensions without pretending that
cryptocurrency staking, ZK proving, hardware attestation, autonomous drones,
or biological storage are already deployed.
"""
from __future__ import annotations
import hashlib, json
from dataclasses import dataclass

def canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode()

def sha256(value: object) -> str:
    data = value if isinstance(value, bytes) else canonical(value)
    return "sha256:" + hashlib.sha256(data).hexdigest()

@dataclass(frozen=True)
class StakeAccount:
    node_id: str
    stake_units: int

class EpistemicStakeLedger:
    def __init__(self, accounts: list[StakeAccount]):
        self._stakes = {a.node_id: a.stake_units for a in accounts}
    def adjudicate(self, node_id: str, contradiction: bool) -> dict:
        before = self._stakes.get(node_id, 0)
        slashed = before if contradiction else 0
        after = before - slashed
        self._stakes[node_id] = after
        return {
            "spec": "pop/epistemic-stake/v1",
            "node_id": node_id,
            "stake_before": before,
            "contradiction_detected": contradiction,
            "slashed_units": slashed,
            "stake_after": after,
            "action": "SLASHED" if contradiction else "RETAINED",
            "external_chain_execution": False,
        }

@dataclass(frozen=True)
class ZKTEEProof:
    circuit_id: str
    model_commitment: str
    input_commitment: str
    output_commitment: str
    attestation_commitment: str
    proof_digest: str

    @classmethod
    def build(cls, circuit_id, model_commitment, input_commitment, output_commitment, attestation_commitment):
        body = {
            "circuit_id": circuit_id,
            "model_commitment": model_commitment,
            "input_commitment": input_commitment,
            "output_commitment": output_commitment,
            "attestation_commitment": attestation_commitment,
        }
        return cls(**body, proof_digest=sha256(body))

    def verify(self) -> bool:
        expected = sha256({
            "circuit_id": self.circuit_id,
            "model_commitment": self.model_commitment,
            "input_commitment": self.input_commitment,
            "output_commitment": self.output_commitment,
            "attestation_commitment": self.attestation_commitment,
        })
        return expected == self.proof_digest

def verify_zktee(proof: ZKTEEProof, *, external_snark_verifier: bool = False) -> dict:
    consistent = proof.verify()
    return {
        "spec": "pop/zk-tee-evidence/v1",
        "local_commitments_consistent": consistent,
        "external_snark_verified": bool(external_snark_verifier),
        "status": "ANCHORED" if consistent and external_snark_verifier else "WARRANTED" if consistent else "QUARANTINED",
        "does_not_prove": [
            "real hardware attestation unless supplied",
            "a production ZK proof unless an external verifier is supplied",
            "correctness of the committed model or data",
        ],
    }

def swarm_attestation(observers: list[dict], *, required_independent: int = 2) -> dict:
    valid, seen = [], set()
    for observer in observers:
        observer_id = observer.get("observer_id")
        evidence_hash = observer.get("evidence_hash")
        signature = observer.get("signature")
        if not all(isinstance(v, str) and v for v in (observer_id, evidence_hash, signature)):
            continue
        if observer_id in seen:
            continue
        seen.add(observer_id)
        valid.append(observer_id)
    quorum = len(valid) >= required_independent
    return {
        "spec": "pop/swarm-attestation/v1",
        "independent_observers": valid,
        "quorum_required": required_independent,
        "quorum_met": quorum,
        "state": "VERIFIED_PROCESS" if quorum else "ACTION_REQUIRED",
        "does_not_prove": [
            "that the observers are honest",
            "that measurements are globally representative",
            "that physical sensors are accurate without calibration evidence",
        ],
    }

def dna_archive_encode(root_hash: str) -> dict:
    if not (isinstance(root_hash, str) and root_hash.startswith("sha256:") and len(root_hash) == 71):
        raise ValueError("expected sha256:<64 hex chars>")
    raw = bytes.fromhex(root_hash.split(":", 1)[1])
    bits = bin(int.from_bytes(raw, "big"))[2:].zfill(len(raw) * 8)
    alphabet = "ACGT"
    dna = "".join(alphabet[int(bits[i:i+2], 2)] for i in range(0, len(bits), 2))
    return {
        "spec": "pop/dna-archive-simulation/v1",
        "source_hash": root_hash,
        "dna_sequence": dna,
        "sequence_length_bases": len(dna),
        "reversible": True,
        "physical_synthesis_performed": False,
        "does_not_prove": ["physical DNA synthesis", "vault storage", "sequencing accuracy"],
    }

def dna_archive_decode(dna: str) -> str:
    alphabet = {"A": "00", "C": "01", "G": "10", "T": "11"}
    if not dna or any(base not in alphabet for base in dna):
        raise ValueError("DNA sequence must contain only A/C/G/T")
    bits = "".join(alphabet[x] for x in dna)
    raw = int(bits, 2).to_bytes(len(bits) // 8, "big")
    return "sha256:" + raw.hex()

def genesis_seed(payload: dict, *, mesh_id: str = "offline-mesh-0") -> dict:
    payload_hash = sha256(payload)
    seed = {
        "spec": "pop/genesis-seed/v1",
        "mesh_id": mesh_id,
        "payload_hash": payload_hash,
        "connectivity": "OFFLINE",
        "local_quorum": True,
        "global_anchor": "PENDING",
        "physical_gate": "ACTION_REQUIRED",
    }
    seed["seed_hash"] = sha256(seed)
    return seed

def global_anchor_seed(seed: dict, anchor_receipt: dict) -> dict:
    result = dict(seed)
    result["global_anchor"] = "VERIFIED_PROCESS"
    result["anchor_receipt_hash"] = sha256(anchor_receipt)
    result["seed_hash"] = sha256({k: v for k, v in result.items() if k != "seed_hash"})
    return result

def frontier_matrix() -> dict:
    return {
        "cryptoeconomic_enforcement": "SIMULATION_ONLY",
        "zk_tee": "COMMITMENT_ONLY",
        "swarm_actuator": "EVIDENCE_AGGREGATOR_ONLY",
        "dna_archive": "ENCODING_ONLY",
        "genesis_seed": "OFFLINE_RECEIPT_ONLY",
        "physical_gate": "ACTION_REQUIRED",
    }
