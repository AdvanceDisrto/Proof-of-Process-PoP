import json
from pathlib import Path

def test_platform_matrix_contains_x86_and_arm64():
    data = json.loads(Path("schemas/platform_architecture_matrix.json").read_text())
    assert set(data["architectures"]) == {"x86_64", "aarch64"}
    assert data["architectures"]["x86_64"]["isa_family"] == "x86"
    assert data["architectures"]["aarch64"]["isa_family"] == "ARM"

def test_platform_contract_does_not_claim_physical_execution():
    data = json.loads(Path("schemas/platform_architecture_matrix.json").read_text())
    assert data["portable_contract"]["forbidden_assumption"]
    for arch in data["architectures"].values():
        assert arch["physical_execution_claim"] == "ACTION_REQUIRED"

def test_anchor_packages_are_optional():
    data = json.loads(Path("schemas/platform_architecture_matrix.json").read_text())
    for package in data["anchor_packages"].values():
        assert package["status"] == "external_dependency_not_required_by_pop"
