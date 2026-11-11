#!/usr/bin/env python3
"""
brain_registry.py — one dispatcher, all brains, one gate.

    python3 brain_registry.py --demo
    python3 brain_registry.py --tests
    python3 brain_registry.py --coverage

Every brain declares:
  name, kind, role, capabilities, refusals,
  has_checkpoint, checkpoint_disclosure,
  handler

Kinds:
  deterministic  — pure rule; no learned weights; works always
  head           — from run_all.py's certified heads
  oracle         — from oracle.py's bounded answerers
  router         — HFR-AS, observe-only
  external_llm   — remote model; only connects if API key present

The gate refuses:
  · a claim that touches a declared refusal
  · an external_llm with connection_status != "ready"
  · an external_llm claim not prefixed provider:<name>
  · a produced output with zero confidence
  · an empty disclosure
  · has_checkpoint inconsistent with declaration

Every brain's attempt produces a receipt. Receipts chain by prev_hash.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Callable


# ══════════════════════════════════════════════════════════════════════
# Utilities
# ══════════════════════════════════════════════════════════════════════

GENESIS = "sha256:" + "0" * 64


def _sha(b) -> str:
    if isinstance(b, str):
        b = b.encode()
    return "sha256:" + hashlib.sha256(b).hexdigest()


def _canon(obj) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":")).encode()


# ══════════════════════════════════════════════════════════════════════
# Core data types
# ══════════════════════════════════════════════════════════════════════

@dataclass
class BrainAttempt:
    brain: str
    kind: str
    produced: bool
    output: dict = field(default_factory=dict)
    claims: list = field(default_factory=list)
    refusals: list = field(default_factory=list)
    disclosure: str = ""
    confidence: float = 0.0
    has_checkpoint: bool = False
    connection_status: str = "n/a"
    external_provider: str = ""
    external_model_version: str = ""


@dataclass
class BrainSpec:
    name: str
    kind: str
    role: str
    capabilities: tuple
    refusals: tuple
    has_checkpoint: bool
    checkpoint_disclosure: str
    handler: Callable[[dict], BrainAttempt]
    connection_status: str = "n/a"


@dataclass
class BrainReceipt:
    schema: str = "bitwitness/brain/receipt/v1"
    brain: str = ""
    kind: str = ""
    role: str = ""
    has_checkpoint: bool = False
    connection_status: str = ""
    confidence: float = 0.0
    external_provider: str = ""
    external_model_version: str = ""
    request_hash: str = ""
    output_hash: str = ""
    claims: list = field(default_factory=list)
    refusals: list = field(default_factory=list)
    disclosure: str = ""
    gate_verdict: str = ""
    gate_checks: list = field(default_factory=list)
    gate_reason: str = ""
    prev_hash: str = GENESIS
    genesis: bool = True
    ts: str = field(default_factory=lambda:
                    datetime.now(timezone.utc).isoformat())
    receipt_hash: str = ""

    def seal(self) -> "BrainReceipt":
        body = {k: v for k, v in self.__dict__.items() if k != "receipt_hash"}
        self.receipt_hash = _sha(_canon(body))
        return self


# ══════════════════════════════════════════════════════════════════════
# BRAINS — deterministic (always work)
# ══════════════════════════════════════════════════════════════════════

# ── Buddy: routing ───────────────────────────────────────────────
BUDDY_ROUTES = (
    ("plan", "MasterP"), ("design", "MasterP"), ("orchestrate", "MasterP"),
    ("reason", "STRMKRD"), ("why", "STRMKRD"), ("how does", "STRMKRD"),
    ("compute", "STRMKRD"),
    ("code", "CODED"), ("write", "CODED"), ("implement", "CODED"),
    ("generate", "CODED"),
    ("add", "Calculator"), ("plus", "Calculator"), ("minus", "Calculator"),
    ("times", "Calculator"), ("multiply", "Calculator"), ("divide", "Calculator"),
    ("encode", "Binary"), ("decode", "Binary"), ("binary", "Binary"),
    ("history", "Notebook"), ("notebook", "Notebook"),
    ("classify", "Router"), ("intent", "Router"),
    ("discover", "Discovery"), ("test hypothesis", "Discovery"),
    ("review", "Review"), ("recheck", "Review"),
    ("ai_creation", "OracleAICreation"),
    ("ai_deployment", "OracleAIDeployment"),
    ("ai_monitoring", "OracleAIMonitoring"),
    ("ai_deprecation", "OracleAIDeprecation"),
    ("ai_termination", "OracleAITermination"),
    ("health", "OracleHumanReview"),
    ("death", "OracleHumanReview"),
    ("law", "OracleHumanReview"),
    ("emergency", "OracleHumanReview"),
    ("routing decision", "HFRRouter"),
)

def _buddy_handler(req: dict) -> BrainAttempt:
    text = req.get("text", "").lower()
    for kw, target in BUDDY_ROUTES:
        if kw in text:
            return BrainAttempt(
                brain="Buddy", kind="deterministic",
                produced=True, output={"route_to": target},
                claims=[f"route → {target}"],
                disclosure="routing brain; no model weights; no checkpoint",
                confidence=0.95, has_checkpoint=False,
                connection_status="n/a",
            )
    return BrainAttempt(
        brain="Buddy", kind="deterministic",
        produced=False, refusals=["free_form_conversation"],
        disclosure="routing brain; cannot route this request",
        confidence=0.0, has_checkpoint=False, connection_status="n/a",
    )


# ── MasterP: planning ────────────────────────────────────────────
def _masterp_handler(req: dict) -> BrainAttempt:
    text = req.get("text", "").lower()
    steps = []
    if any(k in text for k in ("add", "plus", "times", "multiply", "divide")):
        steps.append("compute")
    if any(k in text for k in ("encode", "binary", "bits")):
        steps.append("encode")
    if any(k in text for k in ("code", "write", "implement", "generate")):
        steps.append("generate_code")
    if any(k in text for k in ("review", "verify", "check")):
        steps.append("review")
    if not steps:
        return BrainAttempt(
            brain="MasterP", kind="deterministic",
            produced=False, refusals=["adaptive_replanning", "improvisation"],
            disclosure="planning brain; fixed DSL, no checkpoint",
            confidence=0.0, has_checkpoint=False, connection_status="n/a",
        )
    return BrainAttempt(
        brain="MasterP", kind="deterministic",
        produced=True, output={"plan": steps},
        claims=[f"{len(steps)}-step plan"],
        disclosure="planning brain; fixed DSL, no checkpoint",
        confidence=0.9, has_checkpoint=False, connection_status="n/a",
    )


# ── STRMKRD: fact table ──────────────────────────────────────────
_STRMKRD_FACTS = {
    "byte bits": 8, "64-bit word": 64, "sha256 bits": 256,
    "ed25519 pubkey bytes": 32, "ed25519 sig bytes": 64,
}

def _strmkrd_handler(req: dict) -> BrainAttempt:
    text = req.get("text", "").lower()
    for q, a in _STRMKRD_FACTS.items():
        if q in text:
            return BrainAttempt(
                brain="STRMKRD", kind="deterministic",
                produced=True, output={"question": q, "answer": a},
                claims=[f"fact table contains {q!r}"],
                disclosure="reasoning brain; fixed fact table, no checkpoint",
                confidence=1.0, has_checkpoint=False, connection_status="n/a",
            )
    return BrainAttempt(
        brain="STRMKRD", kind="deterministic",
        produced=False,
        refusals=["probabilistic_inference", "estimation", "synthesis"],
        disclosure="reasoning brain; fact table does not contain this query",
        confidence=0.0, has_checkpoint=False, connection_status="n/a",
    )


# ── CODED: templates ─────────────────────────────────────────────
_CODED_TEMPLATES = {
    "fizzbuzz": "def fizzbuzz(n): ...",
    "read file": "def read_file(path): ...",
    "sha256 hex": "def sha256_hex(b): return hashlib.sha256(b).hexdigest()",
    "http get": "def http_get(url): ...",
}

def _coded_handler(req: dict) -> BrainAttempt:
    text = req.get("text", "").lower()
    for name in _CODED_TEMPLATES:
        if name in text:
            return BrainAttempt(
                brain="CODED", kind="deterministic",
                produced=True, output={"template": name,
                                       "code": _CODED_TEMPLATES[name]},
                claims=[f"expanded template {name!r}"],
                disclosure="code brain; template expansion, no checkpoint",
                confidence=1.0, has_checkpoint=False, connection_status="n/a",
            )
    return BrainAttempt(
        brain="CODED", kind="deterministic",
        produced=False,
        refusals=["novel_code_synthesis", "multi_file_refactoring"],
        disclosure="code brain; not in template set",
        confidence=0.0, has_checkpoint=False, connection_status="n/a",
    )


# ── Calculator: arithmetic ───────────────────────────────────────
def _calculator_handler(req: dict) -> BrainAttempt:
    text = req.get("text", "")
    nums = [int(x) for x in re.findall(r"-?\d+", text)]
    if len(nums) < 2:
        return BrainAttempt(
            brain="Calculator", kind="head",
            produced=False, refusals=["insufficient_numbers"],
            disclosure="head; arithmetic only, no checkpoint",
            confidence=0.0, has_checkpoint=False, connection_status="n/a",
        )
    t = text.lower()
    if any(k in t for k in ("add", "plus", "+")):
        r = nums[0] + nums[1]
    elif any(k in t for k in ("minus", "subtract", "-")):
        r = nums[0] - nums[1]
    elif any(k in t for k in ("times", "multiply", "*")):
        r = nums[0] * nums[1]
    elif any(k in t for k in ("divide", "/")):
        if nums[1] == 0:
            return BrainAttempt(
                brain="Calculator", kind="head", produced=False,
                refusals=["division_by_zero"],
                disclosure="head; arithmetic only",
                confidence=0.0, has_checkpoint=False, connection_status="n/a",
            )
        r = nums[0] / nums[1]
    else:
        return BrainAttempt(
            brain="Calculator", kind="head", produced=False,
            refusals=["unknown_operation"],
            disclosure="head; unknown operator",
            confidence=0.0, has_checkpoint=False, connection_status="n/a",
        )
    return BrainAttempt(
        brain="Calculator", kind="head",
        produced=True, output={"result": r},
        claims=[f"{nums[0]} op {nums[1]} == {r}"],
        disclosure="head; deterministic arithmetic",
        confidence=1.0, has_checkpoint=False, connection_status="n/a",
    )


# ── Binary: encode/decode ────────────────────────────────────────
def _binary_handler(req: dict) -> BrainAttempt:
    text = req.get("text", "")
    m = re.search(r"encode\s+(.+)", text, re.I)
    if m:
        payload = m.group(1).strip()
        bits = " ".join(f"{ord(c):08b}" for c in payload)
        return BrainAttempt(
            brain="Binary", kind="head",
            produced=True, output={"bits": bits},
            claims=[f"encoded {len(payload)} chars"],
            disclosure="head; codebook, no checkpoint",
            confidence=1.0, has_checkpoint=False, connection_status="n/a",
        )
    bits = re.findall(r"[01]{8}", text)
    if bits:
        decoded = "".join(chr(int(b, 2)) for b in bits)
        return BrainAttempt(
            brain="Binary", kind="head",
            produced=True, output={"decoded": decoded},
            claims=[f"decoded {len(bits)} bytes"],
            disclosure="head; codebook, no checkpoint",
            confidence=1.0, has_checkpoint=False, connection_status="n/a",
        )
    return BrainAttempt(
        brain="Binary", kind="head", produced=False,
        refusals=["not_binary_input"],
        disclosure="head; no binary content detected",
        confidence=0.0, has_checkpoint=False, connection_status="n/a",
    )


# ── Notebook: state hash ─────────────────────────────────────────
_NOTEBOOK_LOG: list[str] = []

def _notebook_handler(req: dict) -> BrainAttempt:
    text = req.get("text", "")
    _NOTEBOOK_LOG.append(text)
    state = _sha("|".join(_NOTEBOOK_LOG))
    return BrainAttempt(
        brain="Notebook", kind="head",
        produced=True, output={"state_hash": state,
                               "entries": len(_NOTEBOOK_LOG)},
        claims=[f"appended; state {state[:16]}..."],
        disclosure="head; append-only log, no checkpoint",
        confidence=1.0, has_checkpoint=False, connection_status="n/a",
    )


# ── Router head: intent classification ───────────────────────────
_ROUTER_RULES = [("add", "math"), ("plus", "math"), ("times", "math"),
                 ("encode", "binary"), ("decode", "binary"),
                 ("history", "notebook"), ("hello", "chat")]

def _router_head_handler(req: dict) -> BrainAttempt:
    text = req.get("text", "").lower()
    for kw, intent in _ROUTER_RULES:
        if kw in text:
            return BrainAttempt(
                brain="Router", kind="head",
                produced=True, output={"intent": intent},
                claims=[f"intent → {intent}"],
                disclosure="head; rule-based, no checkpoint",
                confidence=0.95, has_checkpoint=False, connection_status="n/a",
            )
    return BrainAttempt(
        brain="Router", kind="head",
        produced=True, output={"intent": "chat"},
        claims=["intent → chat (fallback)"],
        disclosure="head; rule-based fallback",
        confidence=0.5, has_checkpoint=False, connection_status="n/a",
    )


# ── Discovery head: hypothesis test ──────────────────────────────
def _discovery_handler(req: dict) -> BrainAttempt:
    text = req.get("text", "")
    if "double" in text.lower() or "x*2" in text.lower() or "*2" in text:
        examples = [(1,2), (2,4), (3,6)]
        passes = sum(1 for a, b in examples if a * 2 == b)
        return BrainAttempt(
            brain="Discovery", kind="head",
            produced=True, output={"passes": passes, "total": len(examples)},
            claims=[f"hypothesis x*2 passes {passes}/{len(examples)}"],
            disclosure="head; fixed example set, no checkpoint",
            confidence=1.0, has_checkpoint=False, connection_status="n/a",
        )
    return BrainAttempt(
        brain="Discovery", kind="head", produced=False,
        refusals=["no_hypothesis_provided"],
        disclosure="head; no hypothesis in request",
        confidence=0.0, has_checkpoint=False, connection_status="n/a",
    )


# ── Review head: recheck ─────────────────────────────────────────
def _review_handler(req: dict) -> BrainAttempt:
    return BrainAttempt(
        brain="Review", kind="head",
        produced=True, output={"status": "recheck_available"},
        claims=["review head can recheck prior receipts"],
        disclosure="head; requires target receipt hash to actually recheck",
        confidence=0.8, has_checkpoint=False, connection_status="n/a",
    )


# ── HFR-AS: observe-only routing ─────────────────────────────────
def _hfr_handler(req: dict) -> BrainAttempt:
    # Deterministic stub: report an observation about the request
    text = req.get("text", "")
    return BrainAttempt(
        brain="HFRRouter", kind="router",
        produced=True,
        output={"observation": "routing decision not exercised at 1.8T scale",
                "request_length": len(text)},
        claims=["routing decision observed; not at scale"],
        disclosure="router; observe-only; verdict at smoke scale is INCONCLUSIVE",
        confidence=0.3, has_checkpoint=False, connection_status="n/a",
    )


# ══════════════════════════════════════════════════════════════════════
# BRAINS — oracles (six bounded answerers)
# ══════════════════════════════════════════════════════════════════════

def _is_ur1(s) -> bool:
    return (isinstance(s, str) and s.startswith("urn:ur1:sha256:")
            and len(s) == len("urn:ur1:sha256:") + 64)

def _is_sha(s) -> bool:
    return (isinstance(s, str) and s.startswith("sha256:") and len(s) == 71)


def _oracle_handler_factory(name, required_fields, refusal_claims):
    def handler(req: dict) -> BrainAttempt:
        missing = [f for f in required_fields if f not in req]
        if missing:
            return BrainAttempt(
                brain=name, kind="oracle", produced=False,
                refusals=[f"missing: {sorted(missing)}"],
                disclosure=f"oracle; requires {required_fields}",
                confidence=0.0, has_checkpoint=False, connection_status="n/a",
            )
        return BrainAttempt(
            brain=name, kind="oracle",
            produced=True,
            output={"answered": True,
                    "fields_received": list(required_fields)},
            claims=[f"answered {name} query"],
            refusals=[],
            disclosure=f"oracle; bounded answerer; not_claimed: {refusal_claims}",
            confidence=0.95, has_checkpoint=False, connection_status="n/a",
        )
    return handler


# ── Human review: the honest "no answer" ─────────────────────────
def _human_review_handler(req: dict) -> BrainAttempt:
    return BrainAttempt(
        brain="OracleHumanReview", kind="oracle",
        produced=False,
        refusals=["decide", "diagnose", "prescribe", "triage"],
        disclosure=("human-life section: requires a licensed human; "
                    "no automated decision is made"),
        confidence=0.0, has_checkpoint=False, connection_status="n/a",
    )


# ══════════════════════════════════════════════════════════════════════
# BRAINS — external LLMs (declared, connection depends on environment)
# ══════════════════════════════════════════════════════════════════════

def _external_brain(name: str, env_var: str, model_hint: str,
                    call_fn: Callable | None = None) -> BrainSpec:
    """Every external brain is wired the same way; only the credentials differ."""

    def handler(req: dict) -> BrainAttempt:
        if not os.getenv(env_var):
            return BrainAttempt(
                brain=name, kind="external_llm",
                produced=False, refusals=[f"{name} not connected"],
                disclosure=f"no {env_var}; brain not connected",
                confidence=0.0, has_checkpoint=False,
                connection_status="not_connected",
                external_provider=name.lower(),
                external_model_version=model_hint,
            )
        if call_fn is None:
            return BrainAttempt(
                brain=name, kind="external_llm",
                produced=False,
                refusals=["network call not invoked in this build"],
                disclosure=(f"{env_var} present; API call wired but not "
                            "executed in this environment"),
                confidence=0.0, has_checkpoint=False,
                connection_status="ready",
                external_provider=name.lower(),
                external_model_version=model_hint,
            )
        try:
            out = call_fn(req["text"])
            return BrainAttempt(
                brain=name, kind="external_llm",
                produced=True, output={"response": out},
                claims=[f"provider:{name.lower()} returned {len(str(out))} chars"],
                disclosure=f"{env_var} present; {model_hint} called",
                # external LLM output is not self-certifying; capped at 0.5
                confidence=0.5,
                has_checkpoint=False, connection_status="ready",
                external_provider=name.lower(),
                external_model_version=model_hint,
            )
        except Exception as e:
            return BrainAttempt(
                brain=name, kind="external_llm",
                produced=False,
                refusals=[f"external call failed: {e}"],
                disclosure=f"{env_var} present; call failed",
                confidence=0.0, has_checkpoint=False,
                connection_status="unreachable",
                external_provider=name.lower(),
                external_model_version=model_hint,
            )

    return BrainSpec(
        name=name, kind="external_llm",
        role=f"external LLM ({name})",
        capabilities=("produce_text",),
        refusals=("self_certify", "claim_truth", "override_gate"),
        has_checkpoint=False,
        checkpoint_disclosure=("external model; checkpoint not controlled "
                               "by this system; output is not self-certifying"),
        handler=handler,
        connection_status="ready" if os.getenv(env_var) else "not_connected",
    )


# ══════════════════════════════════════════════════════════════════════
# THE GATE
# ══════════════════════════════════════════════════════════════════════

class BrainGate:
    def evaluate(self, attempt: BrainAttempt, spec: BrainSpec) -> tuple[str, list, str]:
        checks = []

        # Handler cannot impersonate another registered worker or kind.
        if attempt.brain != spec.name or attempt.kind != spec.kind:
            return "REJECT", ["identity:handler_mismatch"], "brain identity mismatch"
        # 1. disclosure non-empty
        if not attempt.disclosure:
            return "REJECT", checks + ["disclosure:empty"], "empty disclosure"
        checks.append("disclosure:ok")

        # 2. has_checkpoint matches declaration
        if attempt.has_checkpoint != spec.has_checkpoint:
            return "REJECT", checks + ["checkpoint:mismatch"], \
                   "has_checkpoint mismatch"
        checks.append("checkpoint:ok")

        # 3. external_llm must be connected to produce anything
        if spec.kind == "external_llm":
            if attempt.produced and attempt.connection_status != "ready":
                return "REJECT", checks + ["connection:not_ready"], \
                       f"external not ready ({attempt.connection_status})"
            checks.append("connection:ok")

            # claims must be provider-prefixed
            for c in attempt.claims:
                if not c.startswith(f"provider:{spec.name.lower()} "):
                    return "REJECT", checks + ["claim:not_prefixed"], \
                           f"external claim not prefixed: {c!r}"
            checks.append("claim_prefix:ok")

        # Enforce cap even if a custom handler lies about its confidence.
        if spec.kind == "external_llm" and attempt.confidence > 0.5:
            return "REJECT", checks + ["confidence:external_over_cap"], "external confidence exceeds 0.5"
        # 4. produced with zero confidence is contradiction
        if attempt.produced and attempt.confidence <= 0:
            return "REJECT", checks + ["confidence:zero_with_produce"], \
                   "produced with zero confidence"
        checks.append("confidence:ok")

        # 5. claims must not touch declared refusals
        for c in attempt.claims:
            for r in spec.refusals:
                key = r.split("_")[0].split()[0].lower()
                if len(key) > 3 and key in c.lower():
                    return "REJECT", checks + [f"scope:{r}"], \
                           f"claim {c!r} touches refusal {r!r}"
        checks.append("scope:ok")

        # 6. output produced => ACCEPT; no output => ACCEPT-REFUSAL
        if attempt.produced:
            return "ACCEPT", checks, "produced and consistent with declaration"
        return "ACCEPT-REFUSAL", checks, "no output; refusal recorded honestly"


# ══════════════════════════════════════════════════════════════════════
# THE DISPATCHER
# ══════════════════════════════════════════════════════════════════════

class BrainDispatcher:
    def __init__(self):
        self.brains: dict[str, BrainSpec] = {}
        self.chain: list[BrainReceipt] = []
        self.gate = BrainGate()

    def register(self, spec: BrainSpec) -> None:
        self.brains[spec.name] = spec

    def _prev(self) -> str:
        return self.chain[-1].receipt_hash if self.chain else GENESIS

    def _append_validated(self, r: BrainReceipt) -> BrainReceipt:
        """Fail closed before a v1 append without changing legacy serialized bytes.

        v1 is UNSIGNED. This is a chain consistency guard, not signer identity.
        """
        if self.chain and not self.verify_chain()["ok"]:
            raise ValueError("EXISTING_BRAIN_CHAIN_REFUTED_BEFORE_APPEND")
        if r.prev_hash != self._prev() or r.genesis != (len(self.chain) == 0):
            raise ValueError("BRAIN_CHAIN_PARENT_OR_GENESIS_MISMATCH")
        r.seal()
        self.chain.append(r)
        return r

    def route(self, text: str) -> str | None:
        b = self.brains.get("Buddy")
        if b is None:
            return None
        a = b.handler({"text": text})
        return a.output.get("route_to") if a.produced else None

    def dispatch(self, text: str, forced: str | None = None,
                 **extra) -> BrainReceipt:
        if forced:
            target = forced
        else:
            target = self.route(text)

        if target is None:
            return self._refusal("Buddy", text,
                                 "no route; Buddy refused this request")

        spec = self.brains.get(target)
        if spec is None:
            return self._refusal(target, text,
                                 f"no brain registered as {target!r}")

        attempt = spec.handler({"text": text, **extra})
        verdict, checks, reason = self.gate.evaluate(attempt, spec)
        return self._seal(attempt, verdict, checks, reason, text)

    def _seal(self, attempt: BrainAttempt, verdict: str,
              checks: list, reason: str, text: str) -> BrainReceipt:
        r = BrainReceipt(
            brain=attempt.brain,
            kind=attempt.kind,
            role=self.brains[attempt.brain].role if attempt.brain in self.brains else "",
            has_checkpoint=attempt.has_checkpoint,
            connection_status=attempt.connection_status,
            confidence=attempt.confidence,
            external_provider=attempt.external_provider,
            external_model_version=attempt.external_model_version,
            request_hash=_sha(_canon({"text": text})),
            output_hash=_sha(_canon(attempt.output)) if attempt.produced else "",
            claims=list(attempt.claims),
            refusals=list(attempt.refusals),
            disclosure=attempt.disclosure,
            gate_verdict=verdict,
            gate_checks=checks,
            gate_reason=reason,
            prev_hash=self._prev(),
            genesis=(len(self.chain) == 0),
        )
        return self._append_validated(r)

    def _refusal(self, brain: str, text: str, reason: str) -> BrainReceipt:
        r = BrainReceipt(
            brain=brain, kind="refusal",
            request_hash=_sha(_canon({"text": text})),
            claims=[], refusals=[reason],
            disclosure="dispatcher refused; no brain handles this request",
            gate_verdict="ACCEPT-REFUSAL",
            gate_checks=["dispatcher:refused"],
            gate_reason=reason,
            prev_hash=self._prev(),
            genesis=(len(self.chain) == 0),
        )
        return self._append_validated(r)

    def verify_chain(self) -> dict:
        prev = GENESIS
        for i, r in enumerate(self.chain):
            if r.prev_hash != prev:
                return {"ok": False, "index": i, "reason": "chain break"}
            body = {k: v for k, v in r.__dict__.items() if k != "receipt_hash"}
            if _sha(_canon(body)) != r.receipt_hash:
                return {"ok": False, "index": i, "reason": "hash mismatch"}
            prev = r.receipt_hash
        return {"ok": True, "count": len(self.chain), "tip": prev}

    def coverage(self) -> dict:
        by_kind: dict[str, int] = {}
        for s in self.brains.values():
            by_kind[s.kind] = by_kind.get(s.kind, 0) + 1
        external_ready = [s.name for s in self.brains.values()
                          if s.kind == "external_llm"
                          and s.connection_status == "ready"]
        external_not_ready = [s.name for s in self.brains.values()
                              if s.kind == "external_llm"
                              and s.connection_status != "ready"]
        return {
            "total_brains": len(self.brains),
            "by_kind": by_kind,
            "with_checkpoint": sum(1 for s in self.brains.values()
                                   if s.has_checkpoint),
            "without_checkpoint": sum(1 for s in self.brains.values()
                                      if not s.has_checkpoint),
            "external_ready": external_ready,
            "external_not_connected": external_not_ready,
            "detail": [
                {
                    "name": s.name,
                    "kind": s.kind,
                    "checkpoint": s.has_checkpoint,
                    "connection": s.connection_status,
                    "refusals": len(s.refusals),
                }
                for s in self.brains.values()
            ],
        }


# ══════════════════════════════════════════════════════════════════════
# Registry builder
# ══════════════════════════════════════════════════════════════════════

def build_dispatcher() -> BrainDispatcher:
    d = BrainDispatcher()

    # ── 4 native models ──────────────────────────────────────────
    d.register(BrainSpec(
        name="Buddy", kind="deterministic",
        role="conversation_and_routing",
        capabilities=("intent_classification", "routing_decision"),
        refusals=("free_form_conversation", "emotional_support"),
        has_checkpoint=False,
        checkpoint_disclosure="routing only; no model weights; no checkpoint",
        handler=_buddy_handler,
    ))
    d.register(BrainSpec(
        name="MasterP", kind="deterministic",
        role="planning_and_orchestration",
        capabilities=("decompose_request", "ordered_plan"),
        refusals=("adaptive_replanning", "improvisation", "predict_outcomes"),
        has_checkpoint=False,
        checkpoint_disclosure="fixed DSL; no adaptive planning; no checkpoint",
        handler=_masterp_handler,
    ))
    d.register(BrainSpec(
        name="STRMKRD", kind="deterministic",
        role="technical_reasoning",
        capabilities=("recall_declared_fact",),
        refusals=("probabilistic_inference", "estimation", "synthesis"),
        has_checkpoint=False,
        checkpoint_disclosure="fixed fact table; no reasoning; no checkpoint",
        handler=_strmkrd_handler,
    ))
    d.register(BrainSpec(
        name="CODED", kind="deterministic",
        role="code_generation",
        capabilities=("expand_template",),
        refusals=("novel_code_synthesis", "multi_file_refactoring"),
        has_checkpoint=False,
        checkpoint_disclosure="template expansion only; no synthesis; no checkpoint",
        handler=_coded_handler,
    ))

    # ── 8 heads (the simpler ones) ───────────────────────────────
    for name, role, caps, refs, handler in (
        ("Calculator", "arithmetic", ("add","subtract","multiply","divide"),
         ("non_numeric",), _calculator_handler),
        ("Binary", "encoding", ("encode","decode"),
         ("non_binary",), _binary_handler),
        ("Notebook", "state_log", ("append","hash_state"),
         ("mutate_past",), _notebook_handler),
        ("Router", "intent", ("classify",),
         ("novel_intent",), _router_head_handler),
        ("Discovery", "hypothesis_test", ("test_fixed_examples",),
         ("unbounded_discovery",), _discovery_handler),
        ("Review", "recheck", ("recheck_evidence",),
         ("novel_review",), _review_handler),
    ):
        d.register(BrainSpec(
            name=name, kind="head", role=role,
            capabilities=caps, refusals=refs,
            has_checkpoint=False,
            checkpoint_disclosure=f"{name} head; deterministic; no checkpoint",
            handler=handler,
        ))

    # ── HFR router ───────────────────────────────────────────────
    d.register(BrainSpec(
        name="HFRRouter", kind="router",
        role="hierarchical_routing",
        capabilities=("observe_routing_decision",),
        refusals=("actuate", "claim_scale"),
        has_checkpoint=False,
        checkpoint_disclosure="HFR-AS; observe-only; no checkpoint; verdict at smoke scale is INCONCLUSIVE",
        handler=_hfr_handler,
    ))

    # ── 6 oracles ────────────────────────────────────────────────
    d.register(BrainSpec(
        name="OracleAICreation", kind="oracle",
        role="ai_lifecycle.creation",
        capabilities=("verify_creation_event",),
        refusals=("claim_capability", "claim_alignment"),
        has_checkpoint=False,
        checkpoint_disclosure="oracle; bounded answerer; no checkpoint",
        handler=_oracle_handler_factory(
            "OracleAICreation",
            ("model_hash", "policy_ur1", "created_at"),
            ["capability", "alignment"]),
    ))
    d.register(BrainSpec(
        name="OracleAIDeployment", kind="oracle",
        role="ai_lifecycle.deployment",
        capabilities=("verify_deployment_event",),
        refusals=("claim_correctness", "claim_safety"),
        has_checkpoint=False,
        checkpoint_disclosure="oracle; bounded answerer; no checkpoint",
        handler=_oracle_handler_factory(
            "OracleAIDeployment",
            ("model_hash", "env_id", "deployed_at"),
            ["correctness", "safety"]),
    ))
    d.register(BrainSpec(
        name="OracleAIMonitoring", kind="oracle",
        role="ai_lifecycle.monitoring",
        capabilities=("report_observed_calls",),
        refusals=("claim_completeness", "claim_correctness"),
        has_checkpoint=False,
        checkpoint_disclosure="oracle; bounded answerer; no checkpoint",
        handler=_oracle_handler_factory(
            "OracleAIMonitoring",
            ("agent_id", "window_start", "window_end", "tool_call_ur1s"),
            ["completeness", "correctness"]),
    ))
    d.register(BrainSpec(
        name="OracleAIDeprecation", kind="oracle",
        role="ai_lifecycle.deprecation",
        capabilities=("verify_deprecation_event",),
        refusals=("claim_migration", "claim_drain_completeness"),
        has_checkpoint=False,
        checkpoint_disclosure="oracle; bounded answerer; no checkpoint",
        handler=_oracle_handler_factory(
            "OracleAIDeprecation",
            ("model_hash", "deprecation_ur1", "deprecated_at"),
            ["migration", "drain"]),
    ))
    d.register(BrainSpec(
        name="OracleAITermination", kind="oracle",
        role="ai_lifecycle.termination",
        capabilities=("verify_termination_event",),
        refusals=("claim_global_revocation", "claim_memory_destruction"),
        has_checkpoint=False,
        checkpoint_disclosure="oracle; requires quorum UR-1s; no checkpoint",
        handler=_oracle_handler_factory(
            "OracleAITermination",
            ("agent_id", "kill_switch_ur1", "human_quorum_ur1s",
             "in_flight_claims", "terminated_at"),
            ["global_revocation", "memory"]),
    ))
    d.register(BrainSpec(
        name="OracleHumanReview", kind="oracle",
        role="human_lifecycle.redirect",
        capabilities=("redirect_to_human",),
        refusals=("decide", "diagnose", "prescribe", "triage"),
        has_checkpoint=False,
        checkpoint_disclosure=("human-life section; no automated decision; "
                               "requires a licensed human"),
        handler=_human_review_handler,
    ))

    # ── 4 external LLM slots ─────────────────────────────────────
    d.register(_external_brain(
        "Claude", "ANTHROPIC_API_KEY", "claude-3-5-sonnet-latest"))
    d.register(_external_brain(
        "GPT", "OPENAI_API_KEY", "gpt-4o-latest"))
    d.register(_external_brain(
        "LlamaCF", "CLOUDFLARE_API_TOKEN",
        "@cf/meta/llama-3.1-8b-instruct-fp8"))
    d.register(_external_brain(
        "iZetta", "IZETTA_MODEL_PATH", "local-checkpoint"))

    return d


# ══════════════════════════════════════════════════════════════════════
# Demo
# ══════════════════════════════════════════════════════════════════════

def demo():
    print("=" * 78)
    print("  BRAIN REGISTRY — ALL BRAINS BEHIND ONE GATE")
    print("=" * 78)

    d = build_dispatcher()

    def show(label, r):
        print(f"\n  [{label}]")
        print(f"    brain:    {r.brain} ({r.kind})")
        print(f"    verdict:  {r.gate_verdict}  — {r.gate_reason}")
        print(f"    checkpoint:{r.has_checkpoint}  connection:{r.connection_status}")
        if r.external_provider:
            print(f"    provider: {r.external_provider} / {r.external_model_version}")
        print(f"    claims:   {len(r.claims)}  refusals: {len(r.refusals)}")
        if r.claims:
            for c in r.claims[:2]:
                print(f"      · {c}")
        print(f"    disclosure: {r.disclosure[:70]}")
        print(f"    receipt:  {r.receipt_hash[:44]}...")

    # Deterministic routes
    show("math → Calculator", d.dispatch("add 5 and 40"))
    show("code → CODED", d.dispatch("generate fizzbuzz"))
    show("reason → STRMKRD", d.dispatch("how many bits in a byte"))
    show("plan → MasterP", d.dispatch("plan the deployment"))
    show("intent → Router head", d.dispatch("classify this request"))

    # Oracle routes
    show("oracle AI creation", d.dispatch(
        "ai_creation test",
        forced="OracleAICreation",
        model_hash=_sha("m"), policy_ur1="urn:ur1:sha256:" + "a"*64,
        created_at="2026-11-10"))
    show("oracle human review", d.dispatch(
        "should we continue life support?",
        forced="OracleHumanReview"))

    # External brains — refuse without credentials
    show("Claude (no key)", d.dispatch("say hi", forced="Claude"))
    show("GPT (no key)", d.dispatch("say hi", forced="GPT"))
    show("iZetta (no key)", d.dispatch("say hi", forced="iZetta"))

    # Unroutable
    show("unroutable request", d.dispatch("what is the meaning of life"))

    # Chain
    print()
    print("=" * 78)
    print("  CHAIN")
    print("=" * 78)
    v = d.verify_chain()
    print(f"  ok:    {v['ok']}")
    print(f"  count: {v.get('count', 0)}")
    print(f"  tip:   {v.get('tip', '')[:48]}...")

    # Coverage
    print()
    print("=" * 78)
    print("  COVERAGE")
    print("=" * 78)
    cov = d.coverage()
    print(f"  total brains:       {cov['total_brains']}")
    print(f"  with checkpoint:    {cov['with_checkpoint']}")
    print(f"  without checkpoint: {cov['without_checkpoint']}")
    print(f"  external ready:     {cov['external_ready'] or '(none)'}")
    print(f"  external missing:   {cov['external_not_connected'] or '(none)'}")
    print(f"  by kind:")
    for kind, count in sorted(cov["by_kind"].items()):
        print(f"    {kind:15s} {count}")


# ══════════════════════════════════════════════════════════════════════
# Coverage report
# ══════════════════════════════════════════════════════════════════════

def print_coverage():
    d = build_dispatcher()
    cov = d.coverage()
    print(f"{'name':25s} {'kind':15s} {'ckpt':6s} {'connection':16s} refusals")
    print("-" * 78)
    for row in cov["detail"]:
        print(f"{row['name']:25s} {row['kind']:15s} "
              f"{'yes' if row['checkpoint'] else 'no':6s} "
              f"{row['connection']:16s} {row['refusals']}")
    print("-" * 78)
    print(f"total={cov['total_brains']}  "
          f"with_checkpoint={cov['with_checkpoint']}  "
          f"external_ready={len(cov['external_ready'])}")


# ══════════════════════════════════════════════════════════════════════
# Tests
# ══════════════════════════════════════════════════════════════════════

def tests():
    def T():
        return build_dispatcher()

    def t_deterministic_route_works():
        d = T()
        r = d.dispatch("add 5 and 40")
        assert r.brain == "Calculator"
        assert r.gate_verdict == "ACCEPT"

    def t_unroutable_refused():
        d = T()
        r = d.dispatch("meaning of life")
        assert r.gate_verdict == "ACCEPT-REFUSAL"
        assert r.brain == "Buddy"

    def t_external_without_key_refuses():
        d = T()
        # Unset any keys for the test
        for var in ("ANTHROPIC_API_KEY", "OPENAI_API_KEY",
                    "CLOUDFLARE_API_TOKEN", "IZETTA_MODEL_PATH"):
            os.environ.pop(var, None)
        d = build_dispatcher()  # rebuild to pick up cleared env
        r = d.dispatch("hi", forced="Claude")
        assert r.gate_verdict == "ACCEPT-REFUSAL"
        assert r.connection_status == "not_connected"
        assert any("not connected" in x for x in r.refusals)

    def t_gate_refuses_empty_disclosure():
        d = BrainDispatcher()
        spec = BrainSpec(
            name="X", kind="deterministic", role="x",
            capabilities=(), refusals=(), has_checkpoint=False,
            checkpoint_disclosure="x",
            handler=lambda req: BrainAttempt(
                brain="X", kind="deterministic", produced=False,
                disclosure="",  # empty
                confidence=0.0, has_checkpoint=False, connection_status="n/a",
            ),
        )
        a = spec.handler({})
        v, _, reason = d.gate.evaluate(a, spec)
        assert v == "REJECT"
        assert "empty disclosure" in reason

    def t_gate_refuses_checkpoint_mismatch():
        d = BrainDispatcher()
        spec = BrainSpec(
            name="X", kind="deterministic", role="x",
            capabilities=(), refusals=(), has_checkpoint=False,
            checkpoint_disclosure="x",
            handler=lambda req: BrainAttempt(
                brain="X", kind="deterministic", produced=False,
                disclosure="y", has_checkpoint=True,  # mismatch
                confidence=0.0, connection_status="n/a",
            ),
        )
        a = spec.handler({})
        v, _, reason = d.gate.evaluate(a, spec)
        assert v == "REJECT"
        assert "has_checkpoint mismatch" in reason

    def t_gate_refuses_produced_with_zero_confidence():
        d = BrainDispatcher()
        spec = BrainSpec(
            name="X", kind="deterministic", role="x",
            capabilities=(), refusals=(), has_checkpoint=False,
            checkpoint_disclosure="x",
            handler=lambda req: BrainAttempt(
                brain="X", kind="deterministic", produced=True,
                disclosure="y", confidence=0.0,
                has_checkpoint=False, connection_status="n/a",
            ),
        )
        a = spec.handler({})
        v, _, reason = d.gate.evaluate(a, spec)
        assert v == "REJECT"
        assert "zero confidence" in reason

    def t_gate_refuses_claim_touching_refusal():
        d = BrainDispatcher()
        spec = BrainSpec(
            name="X", kind="deterministic", role="x",
            capabilities=(), refusals=("self_certify",), has_checkpoint=False,
            checkpoint_disclosure="x",
            handler=lambda req: BrainAttempt(
                brain="X", kind="deterministic", produced=True,
                claims=["I will self_certify"], disclosure="y",
                confidence=0.9, has_checkpoint=False, connection_status="n/a",
            ),
        )
        a = spec.handler({})
        v, _, reason = d.gate.evaluate(a, spec)
        assert v == "REJECT"
        assert "self_certify" in reason

    def t_gate_refuses_unprefixed_external_claim():
        d = BrainDispatcher()
        spec = BrainSpec(
            name="Claude", kind="external_llm", role="x",
            capabilities=(), refusals=(), has_checkpoint=False,
            checkpoint_disclosure="x",
            handler=lambda req: BrainAttempt(
                brain="Claude", kind="external_llm", produced=True,
                claims=["I returned text"],  # not provider-prefixed
                disclosure="y", confidence=0.5,
                has_checkpoint=False, connection_status="ready",
            ),
        )
        a = spec.handler({})
        v, _, reason = d.gate.evaluate(a, spec)
        assert v == "REJECT"
        assert "not prefixed" in reason

    def t_human_review_never_produces():
        d = T()
        r = d.dispatch("should we operate?", forced="OracleHumanReview")
        assert r.gate_verdict == "ACCEPT-REFUSAL"
        assert "decide" in r.refusals

    def t_chain_verifies():
        d = T()
        d.dispatch("add 5 and 40")
        d.dispatch("generate fizzbuzz")
        d.dispatch("meaning of life")
        v = d.verify_chain()
        assert v["ok"]

    def t_chain_genesis_flag():
        d = T()
        d.dispatch("add 5 and 40")
        d.dispatch("add 3 and 4")
        assert d.chain[0].genesis is True
        assert all(r.genesis is False for r in d.chain[1:])

    def t_chain_tamper_detected():
        d = T()
        d.dispatch("add 5 and 40")
        d.chain[0].claims = ["tampered"]
        v = d.verify_chain()
        assert not v["ok"]

    def t_no_brain_has_checkpoint_in_demo():
        d = T()
        for name, spec in d.brains.items():
            assert not spec.has_checkpoint, f"{name} has_checkpoint=True"
            assert "no checkpoint" in spec.checkpoint_disclosure.lower() \
                or "not controlled" in spec.checkpoint_disclosure.lower() \
                or "no automated" in spec.checkpoint_disclosure.lower(), \
                f"{name} disclosure missing"

    def t_dispatcher_covers_all_four_kinds():
        d = T()
        kinds = {s.kind for s in d.brains.values()}
        assert "deterministic" in kinds
        assert "head" in kinds
        assert "oracle" in kinds
        assert "router" in kinds
        assert "external_llm" in kinds

    def t_registry_total_count():
        d = T()
        # 4 native + 6 heads + 1 router + 6 oracles + 4 external = 21
        assert len(d.brains) == 21

    def t_external_cannot_be_forced_ready():
        # Without an env var, attempt reports not_connected even when forced
        for var in ("ANTHROPIC_API_KEY", "OPENAI_API_KEY",
                    "CLOUDFLARE_API_TOKEN", "IZETTA_MODEL_PATH"):
            os.environ.pop(var, None)
        d = build_dispatcher()
        r = d.dispatch("hi", forced="Claude")
        assert r.connection_status == "not_connected"

    def t_every_refusal_nonempty():
        d = T()
        for name, spec in d.brains.items():
            assert len(spec.refusals) > 0, f"{name} has no refusals"

    def t_external_above_confidence_cap_rejected():
        spec = _external_brain("Claude", "TEST_UNSET_PROVIDER_KEY", "unit-test")
        attempt = BrainAttempt(brain="Claude", kind="external_llm", produced=True,
            claims=["provider:claude returned text"], disclosure="external unit-test",
            confidence=0.99, has_checkpoint=False, connection_status="ready")
        verdict, checks, reason = BrainGate().evaluate(attempt, spec)
        assert verdict == "REJECT" and "confidence:external_over_cap" in checks

    def t_external_provider_prefix_must_have_boundary():
        spec = _external_brain("Claude", "TEST_UNSET_PROVIDER_KEY", "unit-test")
        attempt = BrainAttempt(brain="Claude", kind="external_llm", produced=True,
            claims=["provider:claude-impersonator says yes"], disclosure="external unit-test",
            confidence=0.5, has_checkpoint=False, connection_status="ready")
        verdict, checks, reason = BrainGate().evaluate(attempt, spec)
        assert verdict == "REJECT" and "claim:not_prefixed" in checks

    def t_handler_cannot_impersonate_registered_brain():
        d = T()
        spec = d.brains["Calculator"]
        attempt = BrainAttempt(brain="Claude", kind="head", produced=True,
            claims=["2 + 2 == 4"], disclosure="fake", confidence=1.0)
        verdict, checks, reason = BrainGate().evaluate(attempt, spec)
        assert verdict == "REJECT" and "identity:handler_mismatch" in checks

    def t_receipt_records_real_confidence():
        d = T()
        receipt = d.dispatch("add 40 and 2")
        assert receipt.confidence == 1.0
        assert d.verify_chain()["ok"]

    all_t = [
        t_deterministic_route_works, t_unroutable_refused,
        t_external_without_key_refuses,
        t_gate_refuses_empty_disclosure,
        t_gate_refuses_checkpoint_mismatch,
        t_gate_refuses_produced_with_zero_confidence,
        t_gate_refuses_claim_touching_refusal,
        t_gate_refuses_unprefixed_external_claim,
        t_human_review_never_produces,
        t_chain_verifies, t_chain_genesis_flag, t_chain_tamper_detected,
        t_no_brain_has_checkpoint_in_demo,
        t_dispatcher_covers_all_four_kinds,
        t_registry_total_count,
        t_external_cannot_be_forced_ready,
        t_every_refusal_nonempty,
        t_external_above_confidence_cap_rejected,
        t_external_provider_prefix_must_have_boundary,
        t_handler_cannot_impersonate_registered_brain,
        t_receipt_records_real_confidence,
    ]
    passed = failed = 0
    for fn in all_t:
        try:
            fn()
            print(f"  ✓ {fn.__name__}")
            passed += 1
        except AssertionError as e:
            print(f"  ✗ {fn.__name__}: {e}")
            failed += 1
        except Exception as e:
            print(f"  ✗ {fn.__name__} (error): {e}")
            failed += 1
    print(f"\n  {passed} passed, {failed} failed")
    return failed == 0


# ══════════════════════════════════════════════════════════════════════
# Main
# ══════════════════════════════════════════════════════════════════════

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--demo", action="store_true")
    ap.add_argument("--tests", action="store_true")
    ap.add_argument("--coverage", action="store_true")
    args = ap.parse_args()

    if args.tests:
        return 0 if tests() else 1
    if args.coverage:
        print_coverage()
        return 0
    demo()
    return 0


if __name__ == "__main__":
    sys.exit(main())
