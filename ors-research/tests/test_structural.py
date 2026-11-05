from dataclasses import replace
from math import sqrt
import numpy as np
import pytest
from ors.physics import RingScenario
from ors.structural import LatticeConfig,CoupledRingLattice

def test_10km_s_max_stator_mass_is_positive_not_negative():
    s=RingScenario()
    assert 1.29e8<s.max_stator_mass_proxy_kg<1.32e8
    assert s.excess_radial_force_n<0
def test_equal_mass_threshold_is_sqrt_two_circular_velocity():
    s=RingScenario()
    v=s.circular_speed_m_s*sqrt(2)
    scenario=replace(s,rotor_speed_m_s=v)
    assert scenario.excess_radial_force_n==pytest.approx(0,abs=1e-6)
    assert 10_700<v<10_850
def test_10km_rotor_supports_lighter_stator_in_proxy():
    s=replace(RingScenario(),stator_mass_kg=100e6)
    assert s.excess_radial_force_n>0
def test_periodic_grid_spacing_and_no_endpoints():
    c=LatticeConfig(length_m=1000,nodes=10)
    assert c.dx==100
    q=CoupledRingLattice(c);q.u[0,0]=1
    f=q.force()
    assert f[0,1]==pytest.approx(c.spring_constants[0])
    assert f[0,-1]==pytest.approx(c.spring_constants[0])
def test_total_internal_force_zero():
    q=CoupledRingLattice(LatticeConfig(nodes=20))
    q.u[0,5]=3;q.u[1,4]=-2
    assert float(q.force().sum())==pytest.approx(0,abs=1e-5)
def test_impulse_changes_momentum_by_exact_impulse():
    q=CoupledRingLattice(LatticeConfig(nodes=50))
    q.inject_impulse(25,76000.)
    assert float(np.sum(q.v*q.cfg.masses[:,None]))==pytest.approx(76000.)
    assert q.energy_j()>0
def test_no_impact_stays_zero():
    q=CoupledRingLattice(LatticeConfig())
    for _ in range(30):q.step(.001)
    assert q.energy_j()==0
def test_wave_propagates_both_directions():
    q=CoupledRingLattice(LatticeConfig(length_m=1000,nodes=50,coupling_n_m=0))
    q.inject_impulse(25,1000)
    for _ in range(20):q.step(.0005)
    assert q.u[0,24]!=0 and q.u[0,26]!=0
    assert q.u[0,24]==pytest.approx(q.u[0,26],rel=1e-9)
def test_coupling_transfers_motion_from_stator_to_rotor():
    q=CoupledRingLattice(LatticeConfig(length_m=1000,nodes=50,coupling_n_m=2e6))
    q.inject_impulse(25,1000)
    for _ in range(60):q.step(.0003)
    assert np.linalg.norm(q.u[1])>0
def test_uncoupled_rotor_remains_stationary():
    q=CoupledRingLattice(LatticeConfig(length_m=1000,nodes=50,coupling_n_m=0))
    q.inject_impulse(25,1000)
    for _ in range(60):q.step(.0003)
    assert np.all(q.u[1]==0)
def test_velocity_verlet_energy_small_drift():
    q=CoupledRingLattice(LatticeConfig(length_m=1000,nodes=50,coupling_n_m=1e6))
    q.inject_impulse(25,1000)
    e0=q.energy_j()
    for _ in range(1000):q.step(.0001)
    assert abs(q.energy_j()-e0)/e0<.001
def test_force_is_integrated_over_actual_duration():
    c=LatticeConfig(nodes=40,length_m=1000,coupling_n_m=0)
    q=CoupledRingLattice(c)
    q.apply_force_for_duration(20,1000,.009,.001)
    assert q.external_impulse_n_s==pytest.approx(9.)
    assert q.t==pytest.approx(.009)
def test_unstable_step_rejected():
    c=LatticeConfig()
    q=CoupledRingLattice(c)
    with pytest.raises(ValueError):q.step(c.stable_dt_upper_bound())
def test_allowable_flag_is_assumption_not_safety_proof():
    c=LatticeConfig(nodes=50,length_m=1000,stator_allowable_incremental_n=1)
    q=CoupledRingLattice(c)
    q.inject_impulse(25,1000)
    for _ in range(100):q.step(.001)
    s=q.summary()
    assert s['exceeded_assumed_incremental_allowable']
    assert 'transverse debris survival' in s['does_not_prove']
def test_nonphysical_parameters_rejected():
    for kwargs in [{'nodes':2},{'stator_mass_kg':-1},{'length_m':0},{'coupling_n_m':-1},{'coupling_damping_n_s_m':-1}]:
        with pytest.raises(ValueError):LatticeConfig(**kwargs)
