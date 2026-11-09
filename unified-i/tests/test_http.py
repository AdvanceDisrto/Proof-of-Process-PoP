from fastapi.testclient import TestClient
import pytest
from unified_i.service import create_app

TOKEN='a'*50
@pytest.fixture
def client():return TestClient(create_app(operator_token=TOKEN))

def test_health_public(client):
 r=client.get('/health');assert r.status_code==200
 assert r.json()['physical']=='PENDING'

def test_status_auth_required(client):
 assert client.get('/v1/gates').status_code==401
 assert client.get('/v1/gates',headers={'x-operator-token':TOKEN+'x'}).status_code==401

def test_status_authorized(client):
 data=client.get('/v1/gates',headers={'x-operator-token':TOKEN}).json()
 assert data['physical_acceptance'] is False

def test_reject_no_consent(client):
 r=client.post('/v1/demo/claim',headers={'x-operator-token':TOKEN},json={'observed':2,'limit':3})
 assert r.status_code==403

def test_real_api_bounded_computation(client):
 r=client.post('/v1/demo/claim',headers={'x-operator-token':TOKEN},json={'observed':2,'limit':3,'explicit_demo_ack':True})
 assert r.status_code==200 and r.json()['status']=='PASS_BOUNDED_CLAIM'
 assert not r.json()['is_clinical_decision']

def test_real_api_bad_number(client):
 r=client.post('/v1/demo/claim',headers={'x-operator-token':TOKEN},json={'observed':10**30,'limit':3,'explicit_demo_ack':True})
 assert r.status_code==422

def test_api_free_text_never_clinical(client):
 r=client.post('/v1/audit/free-text',headers={'x-operator-token':TOKEN},json={'text':'The patient has cancer'})
 assert r.status_code==200 and r.json()['status']=='UNRESOLVED'

def test_api_free_text_missing_auth(client):
 assert client.post('/v1/audit/free-text',json={'text':'X'}).status_code==401

def test_api_bad_schema(client):
 assert client.post('/v1/audit/free-text',headers={'x-operator-token':TOKEN},json={'evil':'shell command'}).status_code==422

def test_api_long_text(client):
 assert client.post('/v1/audit/free-text',headers={'x-operator-token':TOKEN},json={'text':'a'*4001}).status_code==422

def test_short_token_rejected():
 with pytest.raises(ValueError):create_app(operator_token='weak')
