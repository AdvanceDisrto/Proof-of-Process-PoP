"""Simplified hoop material limit, explicitly only for unsupported continuous rotating rings."""
from dataclasses import dataclass

@dataclass(frozen=True)
class Material:
    name:str
    rho_kg_m3:float
    yield_pa:float
    uts_pa:float
    safety_factor:float=2.
    def __post_init__(self):
        if min(self.rho_kg_m3,self.yield_pa,self.uts_pa,self.safety_factor)<=0:
            raise ValueError('positive inputs')

def screen_free_ring(material:Material,velocity_m_s:float):
    if velocity_m_s<0:raise ValueError('negative speed')
    sigma=material.rho_kg_m3*velocity_m_s**2
    allowed=min(material.yield_pa,material.uts_pa)/material.safety_factor
    return {'material':material.name,'case':'unsupported_continuous_tensile_ring',
            'stress_pa':sigma,'allowable_pa':allowed,'utilization':sigma/allowed,
            'status':'PASS_SCREEN' if sigma<=allowed else 'FAIL_SCREEN',
            'does_not_prove':['segmented magnetically confined rotor stress',
                              'stator tether loads','qualified material allowables','hardware safety']}

A36_ILLUSTRATIVE=Material('A36-illustrative',7850,250e6,400e6,2)
KEVLAR_IDEALIZED=Material('Kevlar-idealized-fiber-tensile',1440,3600e6,3600e6,2)
