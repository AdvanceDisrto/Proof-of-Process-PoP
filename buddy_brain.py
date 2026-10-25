from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from typing import Literal

import httpx
from pydantic import BaseModel, Field


LANGUAGES: dict[str, list[str]] = {
    # Backward-compatible public group used by the request contract/tests.
    # Keep this derived from the canonical systems_embedded/core_general groups below.
    "systems": ["Rust", "C", "C++", "Zig", "Go"],

    "core_general": [
        "Python","C","C++","C#","Java","JavaScript","TypeScript","Go","Rust","Swift","Kotlin",
        "Objective-C","Objective-C++","Dart","Ruby","PHP","Perl","Lua","Julia","Nim","Crystal",
        "D","Zig","V","Haxe","Groovy","Scala","Visual Basic","VB.NET","Delphi","Object Pascal",
        "Pascal","Fortran","Ada","COBOL",
    ],
    "systems_embedded": [
        "x86 Assembly","x86-64 Assembly","ARM Assembly","AArch64 Assembly","RISC-V Assembly",
        "MIPS Assembly","PowerPC Assembly","AVR Assembly","8051 Assembly","Chisel","Bluespec",
        "Verilog","SystemVerilog","VHDL","VHDL-AMS","Verilog-AMS","SpinalHDL",
    ],
    "web": [
        "HTML","CSS","SCSS","Sass","Less","JSX","TSX","WebAssembly","WAT","WGSL","GraphQL",
        "GLSL","SVG",
    ],
    "data_query": [
        "SQL","PL/pgSQL","MySQL SQL","T-SQL","PL/SQL","SQLite SQL","SPARQL","Cypher","Gremlin",
        "DAX","MDX","HiveQL","Pig Latin","LINQ",
    ],
    "scientific_ai_math": [
        "R","Julia","MATLAB","GNU Octave","Wolfram Language","Mathematica","SAS","Stata",
        "Maple","Scilab","Mathcad",
    ],
    "gpu_parallel": [
        "CUDA C/C++","CUDA PTX","OpenCL C","HLSL","Metal Shading Language","HIP","SYCL",
        "OpenMP","OpenACC","Triton",
    ],
    "functional_logic": [
        "Haskell","OCaml","F#","Erlang","Elixir","Clojure","Common Lisp","Scheme","Racket",
        "Emacs Lisp","Standard ML","Prolog","Mercury","Idris","PureScript","Elm","Reason","ReScript",
    ],
    "smart_contracts_zk": [
        "Solidity","Vyper","Move","Cairo","Clarity","Michelson","Yul","Fe","Cadence","Bitcoin Script",
        "Circom","Noir","Leo","Halo2",
    ],
    "shell_automation": [
        "Bash","sh","Zsh","Fish","PowerShell","Batch/CMD","AppleScript","VBScript","Tcl","AWK","sed",
    ],
    "infra_config": [
        "YAML","JSON","TOML","XML","HCL","Terraform","Nix","Dhall","Jsonnet","CUE","Dockerfile",
        "Make","CMake","Meson","Bazel/Starlark","GitHub Actions YAML","GitLab CI YAML",
        "CircleCI YAML","Kubernetes manifests","Helm templates","Ansible YAML",
    ],
    "mobile": [
        "React Native","Jetpack Compose","SwiftUI",
    ],
    "graphics_game": [
        "GDScript","ShaderLab","OpenGL Shading Language","Vulkan shader code","Metal shaders",
        "Unreal Engine Blueprint","Godot GDScript",
    ],
    "enterprise_legacy": [
        "RPG","PL/I","ABAP","Apex","ColdFusion/CFML","PowerBuilder","VBA",
    ],
    "markup_docs": [
        "Markdown","LaTeX","TeX","AsciiDoc","reStructuredText","Org-mode","Mermaid","PlantUML",
    ],
    "esoteric": [
        "Brainfuck","Befunge","Whitespace","Malbolge","INTERCAL","LOLCODE","Shakespeare","Piet",
        "Ook!","ArnoldC","Chef","Rockstar","GolfScript",
    ],
}


class BuddyRequest(BaseModel):
    message: str = Field(min_length=1, max_length=12000)
    mode: Literal["chat", "explain", "generate"] = "chat"
    language: str | None = None
    code: str | None = Field(default=None, max_length=120000)


class BuddyResponse(BaseModel):
    status: Literal["MODEL_RESPONSE", "ACTION_REQUIRED"]
    response: str
    model: str
    input_hash: str
    limitations: list[str]


@dataclass(frozen=True)
class BrainConfig:
    base_url: str
    api_key: str | None
    model: str
    timeout_seconds: float = 120.0


def brain_config() -> BrainConfig | None:
    base_url = os.getenv("BUDDY_AI_BASE_URL", "").rstrip("/")
    model = os.getenv("BUDDY_AI_MODEL", "").strip()
    api_key = os.getenv("BUDDY_AI_API_KEY")
    if not base_url or not model:
        return None
    return BrainConfig(base_url=base_url, api_key=api_key, model=model)


def language_catalog() -> dict[str, object]:
    languages = sorted({name for group in LANGUAGES.values() for name in group})
    return {
        "count": len(languages),
        "groups": {key: sorted(value) for key, value in LANGUAGES.items()},
        "languages": languages,
        "capability_boundary": (
            "Coverage is a capability registry. It does not prove compiler, runtime, security, "
            "compliance, hardware, or physical-world correctness."
        ),
        "custom_language_support": True,
        "custom_language_boundary": (
            "A custom DSL, grammar, bytecode, ISA, protocol, or AST can be handled when its "
            "specification/examples are supplied; execution still requires a deterministic verifier."
        ),
    }


async def ask_buddy(request: BuddyRequest) -> BuddyResponse:
    config = brain_config()
    input_material = request.message + (request.code or "")
    input_hash = hashlib.sha256(input_material.encode("utf-8")).hexdigest()

    if config is None:
        return BuddyResponse(
            status="ACTION_REQUIRED",
            response="Buddy AI is not configured. Set BUDDY_AI_BASE_URL and BUDDY_AI_MODEL before requesting model inference.",
            model="UNCONFIGURED",
            input_hash=input_hash,
            limitations=[
                "No model inference was performed.",
                "Generated code remains unverified until deterministic checks pass.",
                "Language coverage is a capability registry, not execution evidence.",
            ],
        )

    system = (
        "You are Buddy, the i™ engineering brain. Read, understand, explain, and write software "
        "across the full registered language catalog, including systems, web, data, AI, GPU, "
        "functional, smart-contract/ZK, shell, infrastructure, mobile, graphics, hardware, legacy, "
        "markup, esoteric, and custom languages. When a custom language is supplied, infer its rules "
        "only from the provided specification/examples. Be precise. Never claim compilation, execution, "
        "security, compliance, hardware attestation, or physical verification without evidence. Prefer "
        "concrete code, tests, interfaces, and deterministic verification. High-consequence physical "
        "actions remain ACTION_REQUIRED and are never authorized by model output."
    )
    if request.mode == "explain" and request.code:
        system += "
Explain the supplied code and identify concrete failure modes before proposing changes."
    if request.mode == "generate":
        system += "
Generate production-oriented code with explicit types and tests. Do not fabricate external API responses."
    if request.language:
        system += f"
Target language: {request.language}."

    payload = {
        "model": config.model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": request.message + (f"

CODE:
{request.code}" if request.code else "")},
        ],
        "temperature": 0.1,
    }
    headers = {"content-type": "application/json"}
    if config.api_key:
        headers["authorization"] = f"Bearer {config.api_key}"

    async with httpx.AsyncClient(timeout=config.timeout_seconds) as client:
        response = await client.post(f"{config.base_url}/chat/completions", headers=headers, json=payload)
        response.raise_for_status()
        data = response.json()
    choices = data.get("choices")
    if not isinstance(choices, list) or not choices:
        raise RuntimeError("Buddy model returned no choices.")
    message = choices[0].get("message", {})
    content = message.get("content") if isinstance(message, dict) else None
    if not isinstance(content, str) or not content.strip():
        raise RuntimeError("Buddy model returned an empty response.")

    return BuddyResponse(
        status="MODEL_RESPONSE",
        response=content,
        model=config.model,
        input_hash=input_hash,
        limitations=[
            "Model output is an unverified inference until deterministic checks run.",
            "No physical actuation is authorized by this endpoint.",
            "Code generation does not establish correctness, security, or compliance.",
        ],
    )


def export_language_catalog(path: str = "artifacts/buddy_language_catalog.json") -> str:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(language_catalog(), fh, indent=2, sort_keys=True)
    return path
