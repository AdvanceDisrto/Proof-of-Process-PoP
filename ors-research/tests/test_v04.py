import math
import numpy as np
import pytest
from fastapi.testclient import TestClient
from ors.fea3d import Section,FrameElement,circular_arc,assemble,buckling
from ors.controls import Bearing,simulate
from ors.materials import Material,A36_ILLUSTRATIVE,KEVLAR_IDEALIZED,screen_free_ring
from ors.service import app
from ors.receipts import mint_observation,verify

@pytest.mark.parametrize('coords', [([0,0,0],[1,0,0]),([0,0,0],[0,1,0]),([0,0,0],[0,0,1]),([0,0,0],[1,2,3])])
def test_frame_orientation(coords):
    e=FrameElement(*coords);r=e.T[:3,:3];assert np.allclose(r@r.T,np.eye(3),atol=1e-12)
@pytest.mark.parametrize('coords', [([0,0,0],[1,0,0]),([0,0,0],[.3,2,1])])
def test_element_symmetric(coords):
    e=FrameElement(*coords);K,G=e.matrices(-1e4);assert np.allclose(K,K.T);assert np.allclose(G,G.T)
def test_zero_length_rejected():
    with pytest.raises(ValueError):FrameElement([0,0,0],[0,0,0])
def test_invalid_section_rejected():
    with pytest.raises(ValueError):Section(A=-1)
def test_linear_rigid_translation_null():
    e=FrameElement([0,0,0],[10,2,0]);K,_=e.matrices();q=np.array([1,2,3,0,0,0]*2);assert np.linalg.norm(K@q)<.01
def test_tension_geometric_positive():
    e=FrameElement([0,0,0],[5,0,0]);kg=e.geometric_local(1e3);assert np.linalg.eigvalsh(kg).min()>-1e-9
def test_compression_geometric_negative():
    e=FrameElement([0,0,0],[5,0,0]);kg=e.geometric_local(-1e3);assert np.linalg.eigvalsh(kg).max()<1e-9
def test_assembled_symmetric():
    K,KG=assemble(circular_arc(elements=7));assert np.allclose(K,K.T);assert np.allclose(KG,KG.T)
@pytest.mark.parametrize('elements',[4,8,12])
def test_buckling_positive_and_residual(elements):
    r=buckling(circular_arc(elements=elements));assert r['status']=='NUMERICAL_MODE';assert r['critical_factor']>0;assert r['residual']<1e-5
@pytest.mark.parametrize('sweep',[.5,1.5])
def test_buckling_arc(sweep):
    r=buckling(circular_arc(sweep=sweep,elements=10));assert r['status']=='NUMERICAL_MODE'
def test_invalid_load():
    with pytest.raises(ValueError):buckling(circular_arc(),load_n=0)
def test_invalid_geometry():
    with pytest.raises(ValueError):circular_arc(radius=0)
def test_no_controller_outside_clearance():
    r=simulate(initial_m=.05);assert r['collision'];assert r['status']=='INITIAL_CLEARANCE_VIOLATION'
def test_controller_within_clearance():
    r=simulate(initial_m=.005);assert r['status']=='SIMULATED_NO_COLLISION';assert abs(r['final_m'])<.005
@pytest.mark.parametrize('offset',[.002,.005,-.005])
def test_controller_sign(offset):
    r=simulate(initial_m=offset,seconds=3);assert not r['collision'];assert abs(r['final_m'])<abs(offset)
def test_bad_timestep_rejected():
    with pytest.raises(ValueError):simulate(dt=.1)
def test_bad_plant():
    with pytest.raises(ValueError):Bearing(mass_kg=0)
def test_steel_free_ring_fail():
    r=screen_free_ring(A36_ILLUSTRATIVE,10000);assert r['stress_pa']==785e9;assert r['allowable_pa']==125e6;assert r['status']=='FAIL_SCREEN'
def test_kevlar_free_ring_fail():
    r=screen_free_ring(KEVLAR_IDEALIZED,10000);assert r['status']=='FAIL_SCREEN'
def test_zero_speed_pass():
    assert screen_free_ring(A36_ILLUSTRATIVE,0)['status']=='PASS_SCREEN'
def test_negative_speed_rejected():
    with pytest.raises(ValueError):screen_free_ring(A36_ILLUSTRATIVE,-1)
def test_material_requires_positive():
    with pytest.raises(ValueError):Material('bad',0,1,1)
def test_local_receipt_verifies_and_tamper_fails():
    r=mint_observation({'mode':'3d_fea_model','physical_gate':'ACTION_REQUIRED'});assert verify(r,r['public_key_hex'])['ok'];r['body']['input']['physical_gate']='PASS';assert not verify(r,r['public_key_hex'])['ok']
def test_health():
    r=TestClient(app).get('/health');assert r.status_code==200;assert r.json()['physical_gate']=='ACTION_REQUIRED'
def test_smoke_endpoint():
    r=TestClient(app).get('/v1/ors/smoke');assert r.status_code==200;d=r.json();assert d['material']['status']=='FAIL_SCREEN';assert d['buckling']['status']=='NUMERICAL_MODE';assert d['controller']['collision'] is False
