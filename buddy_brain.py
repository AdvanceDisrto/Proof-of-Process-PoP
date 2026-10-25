from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from typing import Literal

import httpx
from pydantic import BaseModel, Field


LANGUAGES: dict[str, list[str]] = {
    "systems": ["C", "C++", "Rust", "Zig", "Assembly", "CUDA", "OpenCL", "Verilog", "VHDL", "SystemVerilog"],
    "application": ["TypeScript", "JavaScript", "Python", "Java", "C#", "Go", "PHP", "Ruby", "Kotlin", "Swift", "Dart", "Scala", "F#", "Clojure", "Elixir", "Erlang", "Haskell", "OCaml"],
    "data": ["SQL", "R", "Julia", "MATLAB", "Octave", "SAS", "Fortran"],
    "web": ["HTML", "CSS", "SCSS", "GraphQL"],
    "smart_contracts": ["Solidity", "Vyper", "Move", "Cairo", "Clarity", "Circom", "Noir"],
    "scripting_config": ["Bash", "PowerShell", "YAML", "JSON", "HCL", "Lua", "Perl", "Groovy"],
    "logic_symbolic": ["Prolog", "Lisp", "Scheme", "Racket"],
    "graphics_compute": ["GLSL", "HLSL", "WGSL", "Nim", "Crystal"],
    "legacy_domain": ["COBOL", "Ada", "Pascal", "Delphi", "Brainfuck", "Malbolge", "Whitespace", "LOLCODE", "Befunge"],
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
        "capability_boundary": "Language coverage is a capability registry, not proof that generated code compiles or runs.",
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
                "Generated code must never be treated as verified until deterministic tests pass.",
                "Language registry describes intended coverage, not compiler/runtime success.",
            ],
        )

    system = (
        "You are Buddy, the i™ engineering brain. Read, understand, explain, and write software across the "
        "registered language catalog. Be precise. Never claim that generated code compiles, executes, is secure, "
        "or is physically verified unless evidence is provided. Prefer concrete code, tests, interfaces, and "
        "verification steps. For high-consequence physical actions, return ACTION_REQUIRED rather than authorizing execution."
    )
    if request.mode == "explain" and request.code:
        system += "\nExplain the supplied code and identify concrete failure modes before proposing changes."
    if request.mode == "generate":
        system += "\nGenerate production-oriented code with explicit types and tests. Do not fabricate external API responses."
    if request.language:
        system += f"\nTarget language: {request.language}."

    payload = {
        "model": config.model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": request.message + (f"\n\nCODE:\n{request.code}" if request.code else "")},
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
