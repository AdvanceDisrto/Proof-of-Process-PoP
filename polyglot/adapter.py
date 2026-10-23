from __future__ import annotations

import argparse
import hashlib
import json
import platform
import shutil
import subprocess
import time
from pathlib import Path

CATALOG = Path(__file__).with_name("languages.json")

DETECTORS = (
    ("Rust", ("Cargo.toml",), ("cargo", "test", "--locked")),
    ("Go", ("go.mod",), ("go", "test", "./...")),
    ("JavaScript/TypeScript", ("package.json",), None),
    ("Java/Maven", ("pom.xml",), ("mvn", "-B", "test")),
    ("Java/Gradle", ("build.gradle", "build.gradle.kts"), None),
    ("Python", ("pyproject.toml", "requirements.txt"), None),
    ("C/C++", ("Makefile", "CMakeLists.txt"), None),
    ("Haskell", ("stack.yaml", "cabal.project"), None),
    ("Elixir", ("mix.exs",), ("mix", "test")),
    ("Ruby", ("Gemfile",), None),
    ("PHP", ("composer.json",), None),
    ("Dart", ("pubspec.yaml",), None),
    ("Swift", ("Package.swift",), ("swift", "test")),
    ("Zig", ("build.zig",), ("zig", "build", "test")),
)

BOUNDARIES = {
    "Rust": ["memory safety does not prove algorithm correctness", "unsafe blocks and FFI require separate review"],
    "Go": ["race freedom is not implied by successful compilation", "network side effects require external evidence"],
    "JavaScript/TypeScript": ["browser/runtime state can be tampered with", "type checking does not prove runtime intent"],
    "Python": ["dynamic execution can change behavior", "AI/model outputs are not factual proof"],
    "C/C++": ["memory safety requires separate verification", "direct hardware access requires privilege and platform evidence"],
    "Haskell": ["purity can end at I/O boundaries", "determinism depends on external effects and runtime inputs"],
    "Elixir": ["actor isolation does not prove global ordering", "distributed nodes can partition"],
    "Java/Maven": ["JVM sandboxing does not prove application correctness", "GC timing is runtime-dependent"],
    "Java/Gradle": ["JVM sandboxing does not prove application correctness", "build plugins can execute external code"],
}

def sha256_bytes(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()

def canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()

def detect(root: Path) -> list[dict]:
    found = []
    for language, markers, command in DETECTORS:
        present = [marker for marker in markers if (root / marker).exists()]
        if present:
            found.append({"language": language, "markers": present, "suggested_test": list(command) if command else None})
    return found

def catalog_languages() -> list[str]:
    data = json.loads(CATALOG.read_text(encoding="utf-8"))
    return sorted({language for group in data["paradigms"].values() for language in group})

def receipt(root: Path) -> dict:
    detected = detect(root)
    catalog = catalog_languages()
    body = {
        "spec": "innovulis-polyglot-process/1.0",
        "state": "VERIFIED_PROCESS",
        "repository": root.name,
        "host_arch": platform.machine() or "unknown",
        "detected": detected,
        "catalog_language_count": len(catalog),
        "catalog_sha256": sha256_bytes(CATALOG.read_bytes()),
        "created_utc_ns": time.time_ns(),
        "proves": [
            "integrity of this adapter receipt",
            "which supported project markers were observed",
            "the declared language catalog hash",
        ],
        "does_not_prove": [
            "support for every programming language ever created",
            "that every cataloged compiler or interpreter is installed",
            "that cataloged languages were executed unless a separate execution receipt says so",
            "program correctness, memory safety, determinism, or absence of vulnerabilities",
            "physical energy use, CPU cycle counts, TPM attestation, silicon execution, or foundry evidence",
        ],
        "language_boundaries": {
            item["language"]: BOUNDARIES.get(
                item["language"],
                ["language/runtime semantics require separate verification"],
            )
            for item in detected
        },
    }
    return {"body": body, "receipt_id": sha256_bytes(canonical(body))}

def self_test() -> None:
    assert sha256_bytes(b"abc") == "sha256:ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"
    assert "C" in catalog_languages()
    assert "Prolog" in catalog_languages()
    assert "COBOL" in catalog_languages()
    assert "Lean" in catalog_languages()

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".")
    parser.add_argument("--output", default="POLYGLOT_PROCESS_RECEIPT.json")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        self_test()
        print("polyglot adapter self-test: PASS")
        return 0
    out = receipt(Path(args.root).resolve())
    Path(args.output).write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(out, indent=2))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
