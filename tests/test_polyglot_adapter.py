import json
from pathlib import Path

from polyglot.adapter import catalog_languages, detect, receipt, sha256_bytes


def test_sha256_known_answer():
    assert sha256_bytes(b"abc") == (
        "sha256:ba7816bf8f01cfea414140de5dae2223"
        "b00361a396177a9cb410ff61f20015ad"
    )


def test_catalog_spans_major_realms():
    languages = set(catalog_languages())
    required = {
        "C", "Rust", "Assembly", "Python", "R", "JavaScript",
        "TypeScript", "Java", "C#", "SQL", "Haskell", "Erlang",
        "Clojure", "Prolog", "COBOL", "Fortran", "Solidity",
        "Verilog", "VHDL", "Lean", "Coq",
    }
    assert required <= languages


def test_detects_multiple_project_markers(tmp_path: Path):
    (tmp_path / "Cargo.toml").write_text("[package]\nname='x'\nversion='0.1.0'\n")
    (tmp_path / "go.mod").write_text("module example.test/x\n")
    detected = {item["language"] for item in detect(tmp_path)}
    assert {"Rust", "Go"} <= detected


def test_receipt_keeps_physical_truth_boundary(tmp_path: Path):
    (tmp_path / "requirements.txt").write_text("")
    out = receipt(tmp_path)
    assert out["body"]["state"] == "VERIFIED_PROCESS"
    assert out["receipt_id"].startswith("sha256:")
    boundaries = " ".join(out["body"]["does_not_prove"])
    assert "physical energy" in boundaries
    assert "TPM attestation" in boundaries
    assert "every programming language ever created" in boundaries


def test_catalog_is_valid_json():
    path = Path(__file__).parents[1] / "polyglot" / "languages.json"
    data = json.loads(path.read_text())
    assert data["spec"] == "innovulis-polyglot-catalog/1.0"
    assert len(catalog_languages()) >= 50
