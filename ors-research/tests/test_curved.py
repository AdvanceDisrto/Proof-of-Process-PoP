"""Curved polar-lattice regression tests, not material qualification tests."""
from dataclasses import replace
import math
import numpy as np
import pytest
from ors.curved import Material,CurvedConfig,CurvedRotorStator,A36_TYPICAL
from ors.physics import RingScenario

@pytest.fixture
def cfg():return CurvedConfig(nodes=32)
@pytest.fixture
def ring(cfg):return CurvedRotorStator(cfg)

def test_geometry_is_periodic_circle(ring,cfg):
    assert ring.ref.shape==(2,cfg.nodes,2)
    assert abs(np.linalg.norm(ring.ref[0,0])-np.linalg.norm(ring.ref[0,-1]))<1e-6
    assert np.allclose(ring.er[0],[1,0],atol=1e-14)
    assert cfg.dx*cfg.nodes==pytest.approx(2*math.pi*cfg.radius_m)

def test_zero_reference_has_zero_dynamics_when_explicitly_trimmed(ring):
    assert np.max(np.abs(ring.force()))<1e-5
    ring.step(.01)
    assert ring.peak_displacement_m<1e-9

def test_baseline_equal_mass_still_fails():
    cfg=CurvedConfig(nodes=32,stator_mass_kg=180e6)
    ring=CurvedRotorStator(cfg)
    assert ring.unbalanced_radial_proxy_n<0
    assert ring.report()['radial_support']['baseline_passes_simplified_proxy'] is False

def test_light_stator_proxy_passes_but_trim_still_required(ring):
    assert ring.unbalanced_radial_proxy_n>0
    assert ring.trim_force_norm_n>0
    assert ring.report()['trim']['physical_source']=='NOT_MODELED'

def test_untrimmed_reference_has_nonzero_force():
    ring=CurvedRotorStator(CurvedConfig(nodes=32,trim_static_residual=False))
    assert np.max(np.abs(ring.force()))>1
    ring.step(.01)
    assert ring.peak_displacement_m>0

def test_mass_area_density_consistency(cfg):
    for mass,area,mat in zip((cfg.stator_mass_kg,cfg.rotor_mass_kg),cfg.area_pair,cfg.materials):
        assert cfg.radius_m*2*math.pi*area*mat.density_kg_m3==pytest.approx(mass)

def test_newton_third_law_magnetic_forces(ring):
    u=np.zeros_like(ring.u)
    u[0]+=0.04*ring.er
    mag,gap,sat=ring._electromagnetic_force(u,np.zeros_like(u))
    assert np.allclose(mag[0]+mag[1],0)
    assert np.min(gap)>1.0
    assert not sat

def test_magnetic_actuator_saturation():
    cfg=CurvedConfig(nodes=32,magnetic_force_limit_n=1e4)
    ring=CurvedRotorStator(cfg)
    mag,gap,sat=ring._electromagnetic_force(ring.u,ring.v)
    assert sat
    assert np.max(np.linalg.norm(mag,axis=-1))<=cfg.magnetic_force_limit_n*(1+1e-12)

def test_coupling_is_restoring(ring):
    u=np.zeros_like(ring.u)
    u[0,0]=.1*ring.er[0]
    f1,_,_=ring._electromagnetic_force(u,np.zeros_like(u))
    f0,_,_=ring._electromagnetic_force(np.zeros_like(u),np.zeros_like(u))
    assert np.dot((f1-f0)[0,0],ring.er[0])<0

def test_positive_damping_opposes_relative_radial_velocity(ring):
    v=np.zeros_like(ring.v)
    v[0,0]=ring.er[0]
    f1,_,_=ring._electromagnetic_force(ring.u,v)
    f0,_,_=ring._electromagnetic_force(ring.u,np.zeros_like(v))
    assert np.dot((f1-f0)[0,0],ring.er[0])<0

def test_radial_impulse_propagates_both_geometric_layers(ring):
    ring.inject_impulse('stator',2,radial_ns=76_000)
    for _ in range(250):ring.step(.01)
    assert ring.peak_displacement_m>0
    assert ring.material_check()['peak_utilization']>0
    assert abs(float(np.sum(ring.u[1]*ring.er)))>0

def test_tangential_impulse_makes_tangential_response(ring):
    ring.inject_impulse('stator',4,tangential_ns=40000)
    ring.step(.01)
    assert np.dot(ring.u[0,4],ring.et[4])>0

def test_wrapping_neighbor_force(ring):
    ring.u[0,0]=ring.er[0]*.2
    force=ring.force()
    assert np.linalg.norm(force[0,-1])>0

def test_preload_is_present_as_axial_tension(ring):
    t=ring.link_tension_n()
    assert np.allclose(t[0],ring.cfg.stator_pretension_n,rtol=2e-5)
    assert np.allclose(t[1],ring.cfg.rotor_pretension_n,rtol=2e-5)

def test_allowable_is_based_on_yield_and_safety_factor(ring):
    c=ring.material_check()
    assert c['assumed_allowables_pa'][0]==pytest.approx(A36_TYPICAL.yield_pa/2)
    assert c['material_data_status']=='TYPICAL_PUBLISHED_NOT_LOT_VALIDATED'

def test_excess_pretension_causes_material_failure_flag():
    cfg=CurvedConfig(nodes=32,stator_pretension_n=1e6)
    ring=CurvedRotorStator(cfg)
    assert ring.material_check()['exceeded_assumed_allowable']

def test_energy_stays_finite_for_finite_impulse(ring):
    ring.inject_impulse('rotor',1,radial_ns=5000)
    for _ in range(200):ring.step(.01)
    assert math.isfinite(ring.perturbation_energy_j())

def test_extreme_dt_is_rejected(ring):
    with pytest.raises(ValueError):ring.step(1e6)
    with pytest.raises(ValueError):ring.step(0)

def test_invalid_impulse_rejected(ring):
    for args in [('side',0,1,0),('rotor',-1,1,0),('rotor',0,float('nan'),0)]:
        with pytest.raises(ValueError):ring.inject_impulse(*args)

def test_too_small_actuator_force_cannot_carry_stator(ring):
    c=CurvedConfig(nodes=32,magnetic_force_limit_n=100)
    x=CurvedRotorStator(c)
    assert x._f_mag0>c.magnetic_force_limit_n
    assert x.report()['trim']['counterforce_norm_n']>0

def test_gap_excursion_alarm_works(ring):
    ring.u[0,0]+=3*ring.er[0]
    ring.step(.001)
    assert ring.gap_violation_any

def test_material_inputs_reject_invalid():
    with pytest.raises(ValueError):Material('bad',200e9,7850,500e6,200e6,'some source')
    with pytest.raises(ValueError):Material('bad',-2,7850,250e6,400e6,'source')

def test_config_validates_negative_quantities():
    with pytest.raises(ValueError):CurvedConfig(nodes=7)
    with pytest.raises(ValueError):CurvedConfig(stator_mass_kg=-1)
    with pytest.raises(ValueError):CurvedConfig(magnetic_force_limit_n=-1)
    with pytest.raises(ValueError):CurvedConfig(safety_factor=.5)

def test_no_unsupported_physical_claims(ring):
    rep=ring.report()
    assert rep['physical_gate']=='ACTION_REQUIRED'
    assert rep['status']=='SOFTWARE_EXPLORATORY_NOT_VALIDATED_FEA'
    assert rep['electromagnetism']['model']=='SATURATING_LINEAR_PD_PROXY_NOT_MAXWELL'
    assert len(rep['does_not_prove'])>=8

def test_changes_in_pretension_change_base_stress():
    low=CurvedRotorStator(CurvedConfig(nodes=32,stator_pretension_n=1000))
    high=CurvedRotorStator(CurvedConfig(nodes=32,stator_pretension_n=50_000))
    assert high.material_check()['peak_axial_stress_pa']>low.material_check()['peak_axial_stress_pa']

def test_speed_threshold_behaves_as_expected():
    a=CurvedRotorStator(CurvedConfig(nodes=32,stator_mass_kg=180e6,rotor_speed_m_s=10000))
    b=CurvedRotorStator(CurvedConfig(nodes=32,stator_mass_kg=180e6,rotor_speed_m_s=12000))
    assert a.unbalanced_radial_proxy_n<0<b.unbalanced_radial_proxy_n

def test_baseline_matches_existing_equilibrium_scenario(ring):
    old=RingScenario(rotor_mass_kg=ring.cfg.rotor_mass_kg,stator_mass_kg=ring.cfg.stator_mass_kg,
                     rotor_speed_m_s=ring.cfg.rotor_speed_m_s)
    assert ring.unbalanced_radial_proxy_n==pytest.approx(old.excess_radial_force_n)

def test_state_report_is_json_serializable(ring):
    import json
    ring.inject_impulse('stator',3,radial_ns=1e4)
    ring.step(.01)
    result=json.loads(json.dumps(ring.report(),allow_nan=False))
    assert result['response']['steps']==1

def test_internal_spring_forces_sum_zero(ring):
    u=np.zeros_like(ring.u)
    u[0,3]+=.12*ring.et[3]
    u[1,4]+=.04*ring.er[4]
    internal=ring._elastic_force(ring.ref+u)
    assert np.linalg.norm(internal.sum(axis=(0,1)))<1e-6

def test_magnetic_force_total_vector_zero(ring):
    u=np.zeros_like(ring.u)
    u[0,3]+=.25*ring.er[3]
    f,_,_=ring._electromagnetic_force(u,np.zeros_like(u))
    assert np.allclose(f.sum(axis=0),0)

def test_refinements_consistent_short_response():
    coarse=CurvedRotorStator(CurvedConfig(nodes=32))
    fine=CurvedRotorStator(CurvedConfig(nodes=32))
    coarse.inject_impulse('stator',2,radial_ns=5000)
    fine.inject_impulse('stator',2,radial_ns=5000)
    for _ in range(10):coarse.step(.01)
    for _ in range(20):fine.step(.005)
    assert coarse.peak_displacement_m==pytest.approx(fine.peak_displacement_m,rel=2e-3,abs=1e-8)

def test_untrimmed_bad_mass_speeds_inward():
    cfg=CurvedConfig(nodes=32,stator_mass_kg=180e6,trim_static_residual=False)
    ring=CurvedRotorStator(cfg)
    for _ in range(10):ring.step(.001)
    radial=float(np.sum(ring.cfg.mass_pair[:,None]*np.sum(ring.v*ring.er[None,:,:],axis=-1)))
    assert radial<0

def test_sensitivity_to_stricter_safety_factor():
    c1=CurvedRotorStator(CurvedConfig(nodes=32,safety_factor=1))
    c3=CurvedRotorStator(CurvedConfig(nodes=32,safety_factor=3))
    assert c3.material_check()['peak_utilization']==pytest.approx(3*c1.material_check()['peak_utilization'])

def test_screening_gates_require_unmodeled_trim(ring):
    g=ring.report()['software_screening_gates']
    assert g['requires_unmodeled_external_trim']
    assert g['flight_hardware_qualification']=='NOT_PERFORMED'
    assert g['material_lot_validation']=='NOT_PERFORMED'

def test_actuator_insufficiency_fails_explicit_screen():
    r=CurvedRotorStator(CurvedConfig(nodes=32,magnetic_force_limit_n=100))
    assert r.report()['software_screening_gates']['actuator_bias_within_assumed_limit'] is False
