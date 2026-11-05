"""Experimental curved two-layer rotor/stator lattice (NOT validated orbital-ring FEA).

Planar 2-DOF/node periodic geometry, axial nonlinear chord springs, reference-
relative bending, reference-relative gravity/kinematic radial acceleration,
paired saturating radial actuator force and damping, optional explicit static
reaction compensation. No fluid/plasma/hypervelocity/magnetic Maxwell solution.

The 'trimmed' scenario uses externally supplied radial trim forces calculated
from the residual base load; that is a mathematical perturbation equilibrium,
NOT an engineering mechanism or design-verified support solution.
"""
from dataclasses import dataclass, asdict
from math import pi, sqrt, isfinite
import numpy as np
from .physics import MU, EARTH_RADIUS

@dataclass(frozen=True)
class Material:
    label: str
    young_pa: float
    density_kg_m3: float
    yield_pa: float
    ultimate_pa: float
    source: str
    def __post_init__(self):
        if not self.label or not self.source or any(not isfinite(x) or x<=0 for x in
            (self.young_pa,self.density_kg_m3,self.yield_pa,self.ultimate_pa)):
            raise ValueError('material inputs must be positive finite sourced values')
        if self.ultimate_pa < self.yield_pa:
            raise ValueError('ultimate below yield')

A36_TYPICAL=Material('A36 indicative',200e9,7850.,250e6,400e6,
    'https://manufacturingprocesses.org/charts/material-properties ; typical A36 values, not certified lot data')

@dataclass(frozen=True)
class CurvedConfig:
    altitude_m: float=500_000.
    nodes: int=256
    rotor_mass_kg: float=180e6
    stator_mass_kg: float=100e6
    rotor_speed_m_s: float=10_000.
    rotor_pretension_n: float=1_000.
    stator_pretension_n: float=1_000.
    nominal_gap_m: float=1.0
    magnetic_radial_stiffness_n_m: float=1e5
    magnetic_damping_n_s_m: float=5e4
    magnetic_force_limit_n: float=10e7
    max_gap_excursion_m: float=2.0
    safety_factor: float=2.0
    rotor_material: Material=A36_TYPICAL
    stator_material: Material=A36_TYPICAL
    trim_static_residual: bool=True
    def __post_init__(self):
        if type(self.nodes) is not int or self.nodes<8:raise ValueError('nodes >= 8')
        positive=(self.altitude_m,self.rotor_mass_kg,self.stator_mass_kg,
                  self.nominal_gap_m,self.magnetic_force_limit_n,
                  self.max_gap_excursion_m,self.safety_factor)
        nonnegative=(self.rotor_speed_m_s,self.rotor_pretension_n,self.stator_pretension_n,
                     self.magnetic_radial_stiffness_n_m,self.magnetic_damping_n_s_m)
        if any(not isfinite(x) or x<=0 for x in positive) or any(not isfinite(x) or x<0 for x in nonnegative):
            raise ValueError('invalid scalar physical inputs')
        if self.safety_factor<1:raise ValueError('safety_factor must be >=1')
    @property
    def radius_m(self):return EARTH_RADIUS+self.altitude_m
    @property
    def dx(self):return 2*pi*self.radius_m/self.nodes
    @property
    def circular_speed(self):return sqrt(MU/self.radius_m)
    @property
    def mass_pair(self):return np.array([self.stator_mass_kg/self.nodes,self.rotor_mass_kg/self.nodes])
    @property
    def area_pair(self):
        return np.array([self.stator_mass_kg/(2*pi*self.radius_m*self.stator_material.density_kg_m3),
                         self.rotor_mass_kg/(2*pi*self.radius_m*self.rotor_material.density_kg_m3)])
    @property
    def materials(self):return (self.stator_material,self.rotor_material)
    @property
    def pretensions(self):return np.array([self.stator_pretension_n,self.rotor_pretension_n])
    @property
    def max_stator_mass_proxy_kg(self):return self.rotor_mass_kg*(self.rotor_speed_m_s**2*self.radius_m/MU-1)
    @property
    def total_radial_proxy_n(self):
        return self.rotor_mass_kg*self.rotor_speed_m_s**2/self.radius_m - MU*(self.rotor_mass_kg+self.stator_mass_kg)/self.radius_m**2

class CurvedRotorStator:
    """Two concentric rings, each with N material points and 2 planar DoFs.

    Layer order: 0 stator (outside), 1 rotor (inside).
    Stable integration depends on the chosen timestep; no unconditional guarantee.
    """
    def __init__(self,cfg:CurvedConfig):
        self.cfg=cfg
        theta=np.arange(cfg.nodes)*2*pi/cfg.nodes
        self.er=np.stack((np.cos(theta),np.sin(theta)),axis=-1)
        self.et=np.stack((-np.sin(theta),np.cos(theta)),axis=-1)
        radii=np.array([cfg.radius_m+cfg.nominal_gap_m/2,cfg.radius_m-cfg.nominal_gap_m/2])
        self.ref=radii[:,None,None]*self.er[None,:,:]
        self.u=np.zeros_like(self.ref)
        self.v=np.zeros_like(self.ref)
        self.t=0.
        self.steps=0
        self.max_stress_ratio=0.
        self.peak_gap_m=cfg.nominal_gap_m
        self.min_gap_m=cfg.nominal_gap_m
        self.peak_displacement_m=0.
        self.peak_actuator_force_n=0.
        self.actuator_saturated_any=False
        self.gap_violation_any=False
        self._chord0=np.linalg.norm(np.roll(self.ref,-1,axis=1)-self.ref,axis=-1)[:,0]
        self._EA=np.array([m.young_pa*a for m,a in zip(cfg.materials,cfg.area_pair)])
        self._k=self._EA/self._chord0
        self._rest=self._chord0-cfg.pretensions/self._k
        if np.any(self._rest<=0):raise ValueError('pretension impossible for declared section')
        self._I=cfg.area_pair**2/(4*pi)
        self._kb=np.array([m.young_pa*I/d**3 for m,I,d in zip(cfg.materials,self._I,self._chord0)])
        self._f_mag0=self._magnetic_bias()
        self._f_el0=self._elastic_force(self.ref)
        self._f_grav0=self._radial_body_force(np.zeros_like(self.u))
        self._f_em0,_,_=self._electromagnetic_force(np.zeros_like(self.u),np.zeros_like(self.v))
        self.base_residual_n=self._f_el0+self._f_grav0+self._f_em0
        self.reference_trim_n=-self.base_residual_n
        self.trim_force_norm_n=float(np.linalg.norm(self.reference_trim_n))
        self.trim_max_per_node_n=float(np.linalg.norm(self.reference_trim_n,axis=-1).max())
        self.unbalanced_radial_proxy_n=cfg.total_radial_proxy_n
        self.total_energy_initial_j=self.perturbation_energy_j()

    def _magnetic_bias(self):
        g=MU/self.cfg.radius_m**2
        stator_el_r=np.sum(self._elastic_force(self.ref)[0]*self.er,axis=-1)
        return self.cfg.mass_pair[0]*g-float(np.mean(stator_el_r))

    def _elastic_force(self,p):
        f=np.zeros_like(p)
        for layer in range(2):
            links=np.roll(p[layer],-1,axis=0)-p[layer]
            lengths=np.linalg.norm(links,axis=-1)
            if np.any(lengths<=0):raise ValueError('collapsed link')
            tension=self._k[layer]*(lengths-self._rest[layer])
            q=tension[:,None]*links/lengths[:,None]
            f[layer]=q-np.roll(q,1,axis=0)
            delta=p[layer]-self.ref[layer]
            lap=np.roll(delta,1,axis=0)-2*delta+np.roll(delta,-1,axis=0)
            bilap=np.roll(lap,1,axis=0)-2*lap+np.roll(lap,-1,axis=0)
            f[layer]-=self._kb[layer]*bilap
        return f

    def _radial_body_force(self,u):
        out=np.zeros_like(u)
        radii=np.array([self.cfg.radius_m+self.cfg.nominal_gap_m/2,
                        self.cfg.radius_m-self.cfg.nominal_gap_m/2])
        for layer in range(2):
            r=radii[layer]+np.sum(u[layer]*self.er,axis=-1)
            if np.any(r<=EARTH_RADIUS):raise ValueError('object below assumed Earth radius')
            accel=-MU/r**2
            if layer==1:
                accel+=self.cfg.rotor_speed_m_s**2/r
            out[layer]=self.cfg.mass_pair[layer]*accel[:,None]*self.er
        return out

    def _electromagnetic_force(self,u,v):
        gap=self.cfg.nominal_gap_m+np.sum((u[0]-u[1])*self.er,axis=-1)
        gap_v=np.sum((v[0]-v[1])*self.er,axis=-1)
        raw=self._f_mag0-self.cfg.magnetic_radial_stiffness_n_m*(gap-self.cfg.nominal_gap_m)-self.cfg.magnetic_damping_n_s_m*gap_v
        force=np.clip(raw,-self.cfg.magnetic_force_limit_n,self.cfg.magnetic_force_limit_n)
        f=np.zeros_like(u)
        f[0]=force[:,None]*self.er
        f[1]=-force[:,None]*self.er
        return f,gap,bool(np.any(np.abs(raw)>self.cfg.magnetic_force_limit_n))

    def force(self,u=None,v=None):
        u=self.u if u is None else u
        v=self.v if v is None else v
        f=self._elastic_force(self.ref+u)+self._radial_body_force(u)
        mag,_,_=self._electromagnetic_force(u,v)
        f+=mag
        if self.cfg.trim_static_residual:
            f+=self.reference_trim_n
        return f

    def inject_impulse(self,layer:str,node:int,radial_ns=0.,tangential_ns=0.):
        if layer not in ('stator','rotor') or type(node) is not int or not 0<=node<self.cfg.nodes:
            raise ValueError('invalid layer/node')
        if not (isfinite(radial_ns) and isfinite(tangential_ns)):raise ValueError('invalid impulse')
        idx=0 if layer=='stator' else 1
        self.v[idx,node]+=(radial_ns*self.er[node]+tangential_ns*self.et[node])/self.cfg.mass_pair[idx]

    def link_tension_n(self):
        links=np.roll(self.ref+self.u,-1,axis=1)-(self.ref+self.u)
        lengths=np.linalg.norm(links,axis=-1)
        return self._k[:,None]*(lengths-self._rest[:,None])

    def material_check(self):
        tensions=self.link_tension_n()
        limits=np.array([min(m.yield_pa,m.ultimate_pa)/self.cfg.safety_factor for m in self.cfg.materials])
        axial_stresses=np.maximum(tensions,0)/self.cfg.area_pair[:,None]
        radial_radius=np.sqrt(self.cfg.area_pair/pi)
        lap=np.roll(self.u,1,axis=1)-2*self.u+np.roll(self.u,-1,axis=1)
        bending=np.array([m.young_pa*r for m,r in zip(self.cfg.materials,radial_radius)])[:,None]*np.linalg.norm(lap,axis=-1)/(self._chord0[:,None]**2)
        stress=axial_stresses+bending
        ratio=stress/limits[:,None]
        return {'peak_stress_pa':float(np.max(stress)),
                'peak_axial_stress_pa':float(np.max(axial_stresses)),
                'peak_approx_bending_stress_pa':float(np.max(bending)),
                'peak_utilization':float(np.max(ratio)),
                'layer_utilization':list(np.max(ratio,axis=1).astype(float)),
                'assumed_allowables_pa':list(limits.astype(float)),
                'exceeded_assumed_allowable':bool(np.any(ratio>1)),
                'material_data_status':'TYPICAL_PUBLISHED_NOT_LOT_VALIDATED'}

    def perturbation_energy_j(self):
        kinetic=.5*np.sum(self.cfg.mass_pair[:,None,None]*self.v**2)
        links=np.roll(self.ref+self.u,-1,axis=1)-(self.ref+self.u)
        lengths=np.linalg.norm(links,axis=-1)
        link_e=.5*np.sum(self._k[:,None]*(lengths-self._rest[:,None])**2)
        link_e0=.5*np.sum(self._k[:,None]*(self._chord0[:,None]-self._rest[:,None])**2)
        lap=np.roll(self.u,1,axis=1)-2*self.u+np.roll(self.u,-1,axis=1)
        bend=.5*np.sum(self._kb[:,None,None]*lap**2)
        gap=self.cfg.nominal_gap_m+np.sum((self.u[0]-self.u[1])*self.er,axis=-1)
        magnetic=.5*self.cfg.magnetic_radial_stiffness_n_m*np.sum((gap-self.cfg.nominal_gap_m)**2)
        return float(kinetic+(link_e-link_e0)+bend+magnetic)

    def step(self,dt):
        if not isfinite(dt) or dt<=0:raise ValueError('invalid dt')
        omega2=np.max(4*self._k/self.cfg.mass_pair+16*self._kb/self.cfg.mass_pair+2*self.cfg.magnetic_radial_stiffness_n_m/self.cfg.mass_pair)
        dt_limit=2/sqrt(omega2)
        if dt>=.2*dt_limit:raise ValueError('dt above conservative explicit limit')
        m=self.cfg.mass_pair[:,None,None]
        a0=self.force()/m
        self.u+=self.v*dt+.5*a0*dt*dt
        v_half=self.v+.5*a0*dt
        a1=self.force(self.u,v_half)/m
        self.v=v_half+.5*a1*dt
        self.t+=dt;self.steps+=1
        mag,gap,saturated=self._electromagnetic_force(self.u,self.v)
        self.max_stress_ratio=max(self.max_stress_ratio,self.material_check()['peak_utilization'])
        self.peak_displacement_m=max(self.peak_displacement_m,float(np.max(np.linalg.norm(self.u,axis=-1))))
        self.max_gap_m=float(max(self.peak_gap_m,float(gap.max())))
        self.peak_gap_m=self.max_gap_m
        self.min_gap_m=float(min(self.min_gap_m,float(gap.min())))
        self.peak_actuator_force_n=max(self.peak_actuator_force_n,float(np.max(np.linalg.norm(mag,axis=-1))))
        self.actuator_saturated_any|=saturated
        self.gap_violation_any|=bool(np.any(np.abs(gap-self.cfg.nominal_gap_m)>self.cfg.max_gap_excursion_m))
        return self.snapshot()

    def snapshot(self):
        return {'time_s':self.t,'steps':self.steps,'peak_displacement_m':self.peak_displacement_m,
                'min_gap_m':self.min_gap_m,'max_gap_m':self.peak_gap_m,
                'peak_actuator_force_n':self.peak_actuator_force_n,
                'actuator_saturated':self.actuator_saturated_any,
                'gap_excursion_limit_exceeded':self.gap_violation_any,
                'material':self.material_check()}

    def report(self):
        return {'spec':'ors/curved-rotor-stator-perturbation/0.3',
                'status':'SOFTWARE_EXPLORATORY_NOT_VALIDATED_FEA',
                'geometry':{'nodes_per_layer':self.cfg.nodes,'altitude_m':self.cfg.altitude_m,
                            'radius_m':self.cfg.radius_m,'circumference_m':2*pi*self.cfg.radius_m,
                            'arc_length_per_node_m':self.cfg.dx,'gap_m':self.cfg.nominal_gap_m},
                'radial_support':{'rotor_speed_m_s':self.cfg.rotor_speed_m_s,
                                  'circular_speed_m_s':self.cfg.circular_speed,
                                  'proxy_supported_stator_mass_kg':self.cfg.max_stator_mass_proxy_kg,
                                  'nominal_stator_mass_kg':self.cfg.stator_mass_kg,
                                  'overall_excess_force_n':self.unbalanced_radial_proxy_n,
                                  'baseline_passes_simplified_proxy':self.unbalanced_radial_proxy_n>=0},
                'trim':{'enabled':self.cfg.trim_static_residual,
                        'counterforce_norm_n':self.trim_force_norm_n,
                        'largest_node_counterforce_n':self.trim_max_per_node_n,
                        'physical_source':'NOT_MODELED'},
                'electromagnetism':{'model':'SATURATING_LINEAR_PD_PROXY_NOT_MAXWELL',
                                   'bias_force_per_node_n':self._f_mag0,
                                   'stiffness_n_per_m_per_node':self.cfg.magnetic_radial_stiffness_n_m,
                                   'damping_n_s_per_m_per_node':self.cfg.magnetic_damping_n_s_m,
                                   'limit_per_node_n':self.cfg.magnetic_force_limit_n},
                'materials':[{'layer':name,**asdict(mat),'area_m2':area,'pretension_n':p}
                             for name,mat,area,p in zip(('stator','rotor'),self.cfg.materials,
                                                        self.cfg.area_pair,self.cfg.pretensions)],
                'response':self.snapshot(),
                'software_screening_gates':{
                    'radial_proxy_nonnegative':bool(self.unbalanced_radial_proxy_n>=0),
                    'actuator_bias_within_assumed_limit':bool(abs(self._f_mag0)<=self.cfg.magnetic_force_limit_n),
                    'assumed_stress_allowable_not_exceeded':bool(not self.material_check()['exceeded_assumed_allowable']),
                    'assumed_gap_excursion_not_exceeded':bool(not self.gap_violation_any),
                    'requires_unmodeled_external_trim':bool(self.cfg.trim_static_residual and self.trim_force_norm_n>1e-5),
                    'flight_hardware_qualification':'NOT_PERFORMED',
                    'material_lot_validation':'NOT_PERFORMED'},
                'physical_gate':'ACTION_REQUIRED',
                'does_not_prove':['full curved beam finite-element structural validation',
                    'static support without external trim forces',
                    'actual Maxwell magnetic bearing feasibility or electrical power',
                    'material lot certification, fatigue or fracture toughness',
                    'hypervelocity impact damage or Whipple-shield survivability',
                    'rotor advection, Coriolis or rotating-frame gyroscopic couplings',
                    'transverse three-dimensional bending, torsion, tether dynamics',
                    'thermomechanical/vacuum/cryogenic behavior or control robustness',
                    'Earth geopotential, atmosphere, debris flux, hardware measurements']}
