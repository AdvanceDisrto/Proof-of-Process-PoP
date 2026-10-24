import pytest
from tools.antimatter_tiered_receipt import *
def test_energy(): assert compute()["e_per_collision_j"]/1.602176634e-13==pytest.approx(1876.544,rel=1e-4)
def test_density(): assert compute()["energy_density_j_per_kg"]==pytest.approx(AM_C*AM_C)
def test_tiers(): assert {c["tier"] for c in emit("/tmp/am.json")["claims"]}=={"LAW","OBSERVED","SIMULATED","INTEGRATED","FLIGHT"}
def test_engine_locked(): assert emit("/tmp/am2.json")["engine_physical_gate"]=="ACTION_REQUIRED"
def test_integrated_locked(): assert all(c["gate"]=="ACTION_REQUIRED" for c in emit("/tmp/am3.json")["claims"] if c["tier"] in {"INTEGRATED","FLIGHT"})
