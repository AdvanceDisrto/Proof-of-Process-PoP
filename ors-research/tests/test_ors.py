import copy,math
import numpy as np
import pytest
from ors.physics import RingScenario,bootstrap_model,exact_potential_lift_energy_j,impact_energy_j,ideal_delta_kinetic_energy_j,ideal_average_power_w
from ors.debris import distance_to_ideal_ring,screen_synthetic_cloud,generate_synthetic_cloud
from ors.receipts import mint_observation,verify,sha,canonical

def test_circumference():assert 43_000_000<RingScenario().circumference_m<43_300_000
def test_circular_speed():assert 7600<RingScenario().circular_speed_m_s<7700
def test_energy_j():assert RingScenario().rotor_kinetic_j==9e15
def test_megatons():assert 2<RingScenario().rotor_kinetic_j/(4.184e15)<2.2
def test_baseline_fails_support_proxy():assert RingScenario().excess_radial_force_n<0
def test_faster_rotor_positive_proxy():assert RingScenario(rotor_speed_m_s=12000).excess_radial_force_n>0
def test_negative_proxy_when_slow():assert RingScenario(rotor_speed_m_s=7000).excess_radial_force_n<0
def test_mass_proxy():assert 120e6<RingScenario().max_stator_mass_proxy_kg<140e6
def test_exact_lift_less_than_mgh():assert 0<exact_potential_lift_energy_j(1e6)<4.905e12
def test_naive_mgh_units():assert (1e6*9.81*500000)/3.6e9==pytest.approx(1362.5)
def test_exact_lift_mwh():assert 1100<exact_potential_lift_energy_j(1e6)/3.6e9<1400
def test_impact():assert impact_energy_j(10,7600)==288800000
def test_mass_launch_estimate():assert bootstrap_model()['components_t']['pilot_wire_t']>1070
def test_launch_rounding():assert bootstrap_model()['optimistic_pooled_cargo_flights']==15

def test_ring_point_zero():
 r=RingScenario().radius_m
 assert distance_to_ideal_ring(np.array([[r,0,0]]),r)[0]==pytest.approx(0)
def test_ring_point_vertical_offset():
 r=RingScenario().radius_m
 assert distance_to_ideal_ring(np.array([[r,0,5000]]),r)[0]==pytest.approx(5000)
def test_stationary_centerline_detection():
 r=RingScenario().radius_m
 hits=screen_synthetic_cloud(np.array([[r,0,0]]),np.array([[0,0,0]]))
 assert hits[0]['screening_label']=='CRITICAL_GEOMETRIC_PROXIMITY'
def test_far_synthetic_object():
 r=RingScenario().radius_m
 assert not screen_synthetic_cloud(np.array([[r+1e6,0,0]]),np.array([[0,0,0]]))
def test_cloud_reproducibility():
 a,b=generate_synthetic_cloud(20,seed=42);c,d=generate_synthetic_cloud(20,seed=42)
 assert np.array_equal(a,c) and np.array_equal(b,d)
def test_cloud_input_not_mutated():
 p,v=generate_synthetic_cloud(20);orig=p.copy()
 screen_synthetic_cloud(p,v);assert np.array_equal(p,orig)
def test_receipt_pinned_verifies():
 r=mint_observation({'a':42});assert verify(r,r['public_key_hex'])['ok']
def test_receipt_tamper_rejected():
 r=mint_observation({'a':42});pin=r['public_key_hex'];r['body']['input']['a']=43
 assert not verify(r,pin)['ok']
def test_wrong_pin_rejected():
 r=mint_observation({'a':42});assert not verify(r,'00'*32)['ok']
def test_receipt_proof_limits():
 r=mint_observation({'a':42});assert 'independent trusted time' in r['body']['does_not_prove']
def test_no_collision_proof_claim():
 r=RingScenario().to_dict();assert 'NO containment or control model' in r['limitations']
def test_bad_mass():
 with pytest.raises(ValueError):RingScenario(rotor_mass_kg=-1)
def test_nan_rejected():
 with pytest.raises(ValueError):RingScenario(rotor_speed_m_s=float('nan'))
def test_bad_thresholds():
 with pytest.raises(ValueError):screen_synthetic_cloud(np.zeros((1,3)),np.zeros((1,3)),critical_m=50,warning_m=10)
def test_receipt_missing_signature():
 r=mint_observation({});del r['signature_hex'];assert not verify(r,r['public_key_hex'])['ok']
def test_receipt_reproducibility_of_hash():
 r=mint_observation({'x':1});assert sha(canonical(r['body']))==r['receipt_id']
def test_ideal_launch_kinetic_only():
 assert ideal_delta_kinetic_energy_j(1000,0,11200)==62_720_000_000
def test_power_efficiency_lower_bound():
 assert ideal_average_power_w(100,10,.5)==20
def test_power_bad_efficiency():
 with pytest.raises(ValueError):ideal_average_power_w(100,10,0)
