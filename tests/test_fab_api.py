from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


def test_fab_prepare_is_deterministic_and_not_execution_evidence() -> None:
    payload = {
        "commit": "d7f5c8c56eb84375648cbf4597f4cdfee98a6c64",
        "target": "x86_64-unknown-linux-gnu",
        "die_count": 64,
        "priority": "reliability",
    }
    first = client.post("/api/fab/prepare", json=payload)
    second = client.post("/api/fab/prepare", json=payload)

    assert first.status_code == 200
    assert second.status_code == 200
    first_data = first.json()
    second_data = second.json()

    assert first_data["status"] == "READY_FOR_EXECUTOR"
    assert first_data["provenance_hash"] == second_data["provenance_hash"]
    assert first_data["manifest"]["evidence_policy"]["simulated_execution"] is False
    assert "configured executor execution receipt" in first_data["next_required_evidence"]


def test_fab_prepare_rejects_non_git_commit_shape() -> None:
    response = client.post(
        "/api/fab/prepare",
        json={"commit": "not-a-commit", "target": "x86_64-unknown-linux-gnu", "die_count": 64},
    )
    assert response.status_code == 422
