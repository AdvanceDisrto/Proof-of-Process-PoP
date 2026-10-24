"""Epidemic Genesis: generate, test, transmit, select, and quarantine epistemic variants.

This module is deliberately a simulation/accountability model. It does not claim
that a self-consistent receipt establishes external truth.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from math import exp
from random import Random
from typing import Callable, Iterable


UNEXPOSED = "U"
EXPOSED = "E"
TRIAL = "T"
ADOPTED = "A"
RETAINED = "R"
QUARANTINED = "Q"
SUPERSEDED = "S"
FAILED = "F"


@dataclass(frozen=True)
class Evidence:
    receipt_strength: float
    external_verification: float
    contradiction_rate: float = 0.0

    @property
    def verified_signal(self) -> float:
        # Receipt strength alone is not external verification.
        return max(0.0, min(1.0, 0.5 * self.receipt_strength + 0.5 * self.external_verification))


@dataclass(frozen=True)
class Variant:
    variant_id: str
    payload: str
    parent_id: str | None = None
    mutation: str | None = None


@dataclass
class AgentVariantState:
    state: str = UNEXPOSED
    trials: int = 0
    adoptions: int = 0
    rejections: int = 0


@dataclass
class Agent:
    agent_id: str
    repertoire: list[str] = field(default_factory=list)
    states: dict[str, AgentVariantState] = field(default_factory=dict)


class EpistemicGenerator:
    """Deterministic generate-and-test helper when a seed is supplied."""

    def __init__(self, repertoire: Iterable[str], seed: int = 0):
        self.repertoire = list(repertoire)
        self.rng = Random(seed)

    def generate(self, variant_id: str, *, mutation_rate: float = 0.25) -> Variant:
        if not self.repertoire:
            raise ValueError("generator repertoire is empty")
        parent = self.rng.choice(self.repertoire)
        mutations = ["recombination", "simplification", "parameter_drift", "goal_drift"]
        mutation = self.rng.choice(mutations) if self.rng.random() < mutation_rate else None
        suffix = f":{mutation}" if mutation else ":copy"
        return Variant(variant_id=variant_id, payload=parent + suffix, parent_id=None, mutation=mutation)

    def test(self, variant: Variant, evidence: Evidence, external_checker: Callable[[Variant], bool]) -> bool:
        external_pass = bool(external_checker(variant))
        score = 0.55 * evidence.verified_signal + 0.45 * float(external_pass)
        return score >= 0.65 and evidence.contradiction_rate < 0.5


@dataclass(frozen=True)
class EpidemicParameters:
    beta: float
    contacts: float
    alpha: float
    gamma: float
    delta: float
    kappa: float
    mutation: float
    fidelity: float = 1.0
    trust: float = 1.0

    @property
    def r0(self) -> float:
        denom = self.delta + self.kappa
        return 0.0 if denom <= 0 else (self.beta * self.contacts * self.gamma) / denom

    def effective_rt(self, *, susceptible: float = 1.0) -> float:
        return self.r0 * max(0.0, min(1.0, susceptible)) * max(0.0, min(1.0, self.fidelity * self.trust))


class EpidemicGenesis:
    def __init__(self, agents: list[Agent], adjacency: dict[str, list[str]], params: EpidemicParameters):
        self.agents = {a.agent_id: a for a in agents}
        self.adjacency = adjacency
        self.params = params

    def exposure_pressure(self, variant_id: str) -> dict[str, float]:
        out = {}
        for agent_id, agent in self.agents.items():
            pressure = 0.0
            for peer_id in self.adjacency.get(agent_id, []):
                peer = self.agents[peer_id]
                state = peer.states.get(variant_id)
                if state and state.state == ADOPTED:
                    pressure += self.params.beta * self.params.fidelity * self.params.trust
            out[agent_id] = pressure
        return out

    def supersede(self, variant_id: str) -> int:
        """Mark adopted/retained instances as displaced by a successor variant.

        Supersession is distinct from contradiction-driven quarantine: the older
        variant may remain historically valid while no longer being selected.
        """
        changed = 0
        for agent in self.agents.values():
            state = agent.states.get(variant_id)
            if state and state.state in {ADOPTED, RETAINED}:
                state.state = SUPERSEDED
                changed += 1
        return changed

    def step(self, variant_id: str, evidence: Evidence) -> dict[str, int | float]:
        pressure = self.exposure_pressure(variant_id)
        counts = {s: 0 for s in (UNEXPOSED, EXPOSED, TRIAL, ADOPTED, RETAINED, QUARANTINED, SUPERSEDED, FAILED)}

        for agent_id, agent in self.agents.items():
            av = agent.states.setdefault(variant_id, AgentVariantState())
            p = 1.0 - exp(-pressure[agent_id])
            if av.state == UNEXPOSED and p > 0:
                av.state = EXPOSED
            elif av.state == EXPOSED:
                av.state = TRIAL
            elif av.state == TRIAL:
                av.trials += 1
                if evidence.external_verification >= 0.5 and evidence.contradiction_rate < 0.5:
                    av.state = ADOPTED
                    av.adoptions += 1
                else:
                    av.state = FAILED
                    av.rejections += 1
            elif av.state == ADOPTED:
                if evidence.contradiction_rate >= 0.75:
                    av.state = QUARANTINED
                    av.rejections += 1
                elif self.params.delta > self.params.kappa:
                    av.state = RETAINED

            counts[av.state] += 1

        total = max(1, len(self.agents))
        susceptible = counts[UNEXPOSED] / total
        counts["R0"] = self.params.r0
        counts["Rt"] = self.params.effective_rt(susceptible=susceptible)
        counts["mutation_escape_pressure"] = self.params.mutation * (1.0 - self.params.fidelity)
        return counts
