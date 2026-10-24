import pytest
from tools.omnipresent_mesh_verifier import *
def test_edge(): assert classify([HONEST_DEPLOYMENT["layers"][0]])["layer_verdicts"][0]["verdict"]=="LAYER_SELF_SUSTAINED"
def test_honest_grid(): assert classify(HONEST_DEPLOYMENT["layers"])["overall"]=="GRID_REQUIRED"
def test_orbital_grid(): assert classify([HONEST_DEPLOYMENT["layers"][1]])["overall"]=="GRID_REQUIRED"
def test_ai_grid(): assert classify([HONEST_DEPLOYMENT["layers"][2]])["overall"]=="GRID_REQUIRED"
def test_vision_gate(): assert emit_receipt("/tmp/m.json",VISION_CLAIM)["physical_gate"]=="ACTION_REQUIRED"
def test_arithmetic(): assert classify([HONEST_DEPLOYMENT["layers"][0]])["total_required_w"]==pytest.approx(25000.)
