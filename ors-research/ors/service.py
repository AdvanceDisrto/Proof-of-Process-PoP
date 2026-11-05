"""Read-only, explicitly synthetic ORS numerical smoke service."""
from fastapi import FastAPI
from ors.fea3d import circular_arc,buckling
from ors.controls import simulate
from ors.materials import screen_free_ring,A36_ILLUSTRATIVE,KEVLAR_IDEALIZED

app=FastAPI(title='iNNOVULIS ORS Numerical Research API',version='0.4.0')

@app.get('/health')
def health():
    return {'status':'ok','service':'ors-numerical-simulation','physical_gate':'ACTION_REQUIRED'}

@app.get('/v1/ors/smoke')
def smoke():
    return {'material':screen_free_ring(A36_ILLUSTRATIVE,10000),
            'kevlar_idealized':screen_free_ring(KEVLAR_IDEALIZED,10000),
            'controller':simulate(seconds=1.),
            'buckling':buckling(circular_arc(elements=8)),
            'physical_gate':'ACTION_REQUIRED','external_anchor':'NOT_PERFORMED'}
