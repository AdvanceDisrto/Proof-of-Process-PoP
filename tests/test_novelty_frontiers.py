from novelty_frontiers import (
    EpistemicStakeLedger, StakeAccount, ZKTEEProof, dna_archive_decode,
    dna_archive_encode, genesis_seed, global_anchor_seed, frontier_matrix,
    swarm_attestation, verify_zktee, sha256,
)

def test_stake_slashing():
    ledger = EpistemicStakeLedger([StakeAccount("n1", 100)])
    assert ledger.adjudicate("n1", False)["stake_after"] == 100
    out = ledger.adjudicate("n1", True)
    assert out["action"] == "SLASHED"
    assert out["stake_after"] == 0
    assert out["external_chain_execution"] is False

def test_zktee_commitment():
    p = ZKTEEProof.build("c1", sha256(b"m"), sha256(b"i"), sha256(b"o"), sha256(b"a"))
    out = verify_zktee(p)
    assert out["local_commitments_consistent"] is True
    assert out["external_snark_verified"] is False
    assert out["status"] == "WARRANTED"

def test_zktee_tamper_quarantines():
    p = ZKTEEProof.build("c1", sha256(b"m"), sha256(b"i"), sha256(b"o"), sha256(b"a"))
    bad = ZKTEEProof(p.circuit_id, p.model_commitment, p.input_commitment, p.output_commitment, p.attestation_commitment, sha256(b"tamper"))
    assert verify_zktee(bad)["status"] == "QUARANTINED"

def test_swarm_quorum():
    out = swarm_attestation([
        {"observer_id":"a","evidence_hash":sha256(b"a"),"signature":"ed25519:a"},
        {"observer_id":"a","evidence_hash":sha256(b"a2"),"signature":"ed25519:a2"},
        {"observer_id":"b","evidence_hash":sha256(b"b"),"signature":"ed25519:b"},
    ])
    assert out["quorum_met"] is True
    assert out["independent_observers"] == ["a", "b"]

def test_swarm_without_quorum():
    out = swarm_attestation([{"observer_id":"a","evidence_hash":sha256(b"a"),"signature":"ed25519:a"}])
    assert out["state"] == "ACTION_REQUIRED"

def test_dna_round_trip():
    root = sha256(b"root")
    enc = dna_archive_encode(root)
    assert enc["physical_synthesis_performed"] is False
    assert dna_archive_decode(enc["dna_sequence"]) == root

def test_genesis_seed_later_anchors():
    seed = genesis_seed({"observation":"demo"}, mesh_id="mesh-1")
    assert seed["global_anchor"] == "PENDING"
    anchored = global_anchor_seed(seed, {"anchor":"demo"})
    assert anchored["global_anchor"] == "VERIFIED_PROCESS"
    assert anchored["anchor_receipt_hash"].startswith("sha256:")

def test_frontier_matrix_honest():
    matrix = frontier_matrix()
    assert matrix == {
        "cryptoeconomic_enforcement":"SIMULATION_ONLY",
        "zk_tee":"COMMITMENT_ONLY",
        "swarm_actuator":"EVIDENCE_AGGREGATOR_ONLY",
        "dna_archive":"ENCODING_ONLY",
        "genesis_seed":"OFFLINE_RECEIPT_ONLY",
        "physical_gate":"ACTION_REQUIRED",
    }
