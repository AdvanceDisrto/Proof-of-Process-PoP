"""Read-only, explicitly synthetic ORS numerical smoke service."""
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from ors.fea3d import circular_arc,buckling
from ors.controls import simulate
from ors.materials import screen_free_ring,A36_ILLUSTRATIVE,KEVLAR_IDEALIZED
app=FastAPI(title='iNNOVULIS ORS Numerical Research API',version='0.4.1')
@app.get('/health')
def health():return {'status':'ok','service':'ors-numerical-simulation','physical_gate':'ACTION_REQUIRED'}
@app.get('/v1/ors/smoke')
def smoke():
    return {'material':screen_free_ring(A36_ILLUSTRATIVE,10000),
            'kevlar_idealized':screen_free_ring(KEVLAR_IDEALIZED,10000),
            'controller':simulate(seconds=1.),
            'buckling':buckling(circular_arc(elements=8)),
            'physical_gate':'ACTION_REQUIRED','external_anchor':'NOT_PERFORMED'}

# Proof-of-utility / provenance research additions. Public operations verify only.
from pathlib import Path
from fastapi import HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from ors.trust import verify as verify_trust, decision_authorized

class ReceiptRequest(BaseModel):
    receipt: dict
    pinned_public_key_hex: str = Field(min_length=64, max_length=64)

class ApprovalRequest(BaseModel):
    receipt: dict
    pinned_public_key_hex: str = Field(min_length=64, max_length=64)
    proposal: str
    policy_text: str

@app.post('/v1/trust/verify')
def verify_receipt(req: ReceiptRequest):
    return verify_trust(req.receipt, req.pinned_public_key_hex)

@app.post('/v1/trust/guardian-check')
def guardian_check(req: ApprovalRequest):
    # Key allowlist, if configured, must be provisioned by service operator.
    allowed = {x.strip() for x in __import__('os').getenv('INNOVULIS_TRUSTED_GUARDIAN_KEYS','').split(',') if x.strip()}
    return {'authorized':decision_authorized(req.receipt,req.pinned_public_key_hex,req.proposal,req.policy_text,allowed),
            'does_not_prove':['that the proposed action actually executed']}

STATIC_DIR=Path(__file__).resolve().parent/'static'
if STATIC_DIR.is_dir():
    app.mount('/static',StaticFiles(directory=str(STATIC_DIR)),name='static')

@app.get('/')
def trust_dashboard():
    p=STATIC_DIR/'index.html'
    if not p.is_file():raise HTTPException(404,'dashboard not packaged')
    return FileResponse(p,media_type='text/html')
