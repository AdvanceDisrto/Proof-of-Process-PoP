from tools.epidemic_genesis import (
    ADOPTED, FAILED, QUARANTINED, RETAINED, SUPERSEDED, UNEXPOSED, Agent, Evidence,
    EpidemicGenesis, EpidemicParameters, EpistemicGenerator,
)


def test_generator_and_tester_distinguish_self_consistency_from_external_check():
    generator = EpistemicGenerator(["method-A"], seed=7)
    variant = generator.generate("v1", mutation_rate=0.0)

    weak = Evidence(receipt_strength=1.0, external_verification=0.0)
    strong = Evidence(receipt_strength=1.0, external_verification=1.0)

    assert not generator.test(variant, weak, lambda _: False)
    assert generator.test(variant, strong, lambda _: True)


def test_epidemic_propagation_and_quarantine():
    agents = [Agent(f"a{i}") for i in range(3)]
    for agent in agents:
        agent.states["v1"] = __import__("tools.epidemic_genesis", fromlist=["AgentVariantState"]).AgentVariantState()
    agents[0].states["v1"].state = ADOPTED

    model = EpidemicGenesis(
        agents,
        {"a0": ["a1", "a2"], "a1": ["a0"], "a2": ["a0"]},
        EpidemicParameters(beta=0.8, contacts=2.0, alpha=1.0, gamma=1.0, delta=0.1, kappa=0.2, mutation=0.1, fidelity=0.9, trust=0.9),
    )

    first = model.step("v1", Evidence(1.0, 1.0))
    assert first["R0"] > 1.0
    assert first[UNEXPOSED] == 0

    failed = model.step("v1", Evidence(1.0, 0.0, contradiction_rate=0.9))
    assert failed[QUARANTINED] + failed[FAILED] >= 1


def test_high_mutation_low_fidelity_reduces_transmission_effectiveness():
    params = EpidemicParameters(beta=0.8, contacts=4.0, alpha=1.0, gamma=1.0, delta=0.2, kappa=0.2, mutation=0.9, fidelity=0.2, trust=1.0)
    assert params.effective_rt() < params.r0


def test_supersession_is_not_quarantine():
    agent = Agent('a0')
    agent.states['v-old'] = __import__('tools.epidemic_genesis', fromlist=['AgentVariantState']).AgentVariantState(state=ADOPTED)
    model = EpidemicGenesis([agent], {'a0': []}, EpidemicParameters(beta=0.1, contacts=1, alpha=1, gamma=1, delta=0.1, kappa=0.1, mutation=0.1))
    assert model.supersede('v-old') == 1
    assert agent.states['v-old'].state == SUPERSEDED
    assert agent.states['v-old'].state != QUARANTINED


def test_supersession_requires_successor_adoption():
    from tools.epidemic_genesis import AgentVariantState
    agent = Agent("a0")
    agent.states["v-old"] = AgentVariantState(state=ADOPTED)
    agent.states["v-new"] = AgentVariantState(state=TRIAL)
    model = EpidemicGenesis(
        [agent], {"a0": []},
        EpidemicParameters(beta=0.1, contacts=1, alpha=1, gamma=1, delta=0.1, kappa=0.1, mutation=0.1),
    )
    assert model.supersede_on_successor_adoption("v-old", "v-new") == 0
    assert agent.states["v-old"].state == ADOPTED
    agent.states["v-new"].state = ADOPTED
    assert model.supersede_on_successor_adoption("v-old", "v-new") == 1
    assert agent.states["v-old"].state == SUPERSEDED
