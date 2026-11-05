"""Coupled 1-D periodic axial-displacement lattice: exploratory software only.

Two co-located discrete rings (rotor/stator) have independent axial spring chains
and distributed elastic coupling. This is NOT orbital-ring finite-element
validation: no curved-beam kinematics, gravity, rotor axial transport, Maxwell,
contact, fracture, or actual impact physics.
"""
from dataclasses import dataclass
from math import isfinite,sqrt
import numpy as np

@dataclass(frozen=True)
class LatticeConfig:
    length_m:float=100_000.
    nodes:int=1000
    stator_mass_kg:float=1e6
    rotor_mass_kg:float=1e6
    stator_young_pa:float=200e9
    stator_area_m2:float=.01
    rotor_young_pa:float=120e9
    rotor_area_m2:float=.01
    coupling_n_m:float=2e5
    coupling_damping_n_s_m:float=0.
    stator_allowable_incremental_n:float=1e8
    def __post_init__(self):
        if not isinstance(self.nodes,int) or self.nodes<4:
            raise ValueError('nodes must be integer >=4')
        values=(self.length_m,self.stator_mass_kg,self.rotor_mass_kg,self.stator_young_pa,self.stator_area_m2,
                self.rotor_young_pa,self.rotor_area_m2,self.stator_allowable_incremental_n)
        if not all(isfinite(v) and v>0 for v in values):
            raise ValueError('positive finite geometry/material values required')
        if not isfinite(self.coupling_n_m) or self.coupling_n_m<0:raise ValueError('invalid coupling')
        if not isfinite(self.coupling_damping_n_s_m) or self.coupling_damping_n_s_m<0:raise ValueError('invalid damping')
    @property
    def dx(self):return self.length_m/self.nodes
    @property
    def masses(self):return np.array([self.stator_mass_kg/self.nodes,self.rotor_mass_kg/self.nodes])
    @property
    def spring_constants(self):
        return np.array([self.stator_young_pa*self.stator_area_m2/self.dx,
                         self.rotor_young_pa*self.rotor_area_m2/self.dx])
    def stable_dt_upper_bound(self):
        rates=4*self.spring_constants/self.masses+2*self.coupling_n_m/self.masses
        return 2/sqrt(float(np.max(rates)))

class CoupledRingLattice:
    """Axial-only two-material periodic lattice; velocity Verlet for zero damping."""
    def __init__(self,cfg:LatticeConfig):
        self.cfg=cfg
        self.u=np.zeros((2,cfg.nodes),dtype=float)
        self.v=np.zeros_like(self.u)
        self.t=0.;self.steps=0;self.max_incremental_force_n=0.;self.external_impulse_n_s=0.
    def force(self):
        k=self.cfg.spring_constants[:,None]
        lap=np.roll(self.u,1,axis=1)-2*self.u+np.roll(self.u,-1,axis=1)
        f=k*lap
        relative=self.u[0]-self.u[1]
        damping=self.cfg.coupling_damping_n_s_m*(self.v[0]-self.v[1])
        bridge=self.cfg.coupling_n_m*relative+damping
        f[0]-=bridge;f[1]+=bridge
        return f
    def inject_impulse(self,node:int,impulse_n_s:float,ring:str='stator'):
        if not (0<=node<self.cfg.nodes) or ring not in ('stator','rotor') or not isfinite(impulse_n_s):
            raise ValueError('invalid impulse')
        i=0 if ring=='stator' else 1
        self.v[i,node]+=impulse_n_s/self.cfg.masses[i]
        self.external_impulse_n_s+=impulse_n_s
    def apply_force_for_duration(self,node:int,force_n:float,duration_s:float,dt:float,ring='stator'):
        if not (isfinite(force_n) and isfinite(duration_s)) or duration_s<=0 or dt<=0:
            raise ValueError('invalid force or time')
        remaining=duration_s
        while remaining>1e-13:
            h=min(dt,remaining)
            self.step(h,external_node=node,external_force_n=force_n,ring=ring)
            remaining-=h
    def step(self,dt:float,external_node=None,external_force_n=0.,ring='stator'):
        if not isfinite(dt) or dt<=0 or dt>=.8*self.cfg.stable_dt_upper_bound():
            raise ValueError('dt exceeds conservative step limit or is invalid')
        if self.cfg.coupling_damping_n_s_m:
            raise ValueError('this Verlet integrator supports zero damping only')
        extra=np.zeros_like(self.u)
        if external_node is not None:
            if not (0<=external_node<self.cfg.nodes) or ring not in ('stator','rotor'):
                raise ValueError('invalid external load node')
            extra[0 if ring=='stator' else 1,external_node]=external_force_n
            self.external_impulse_n_s+=external_force_n*dt
        m=self.cfg.masses[:,None]
        a=(self.force()+extra)/m
        self.u+=self.v*dt+.5*a*dt*dt
        a2=(self.force()+extra)/m
        self.v+=.5*(a+a2)*dt
        self.t+=dt;self.steps+=1
        tension=self.incremental_spring_forces()
        peak=float(np.max(tension))
        self.max_incremental_force_n=max(self.max_incremental_force_n,peak)
        return {'time_s':self.t,'peak_incremental_axial_force_n':peak,
                'allowable_exceeded':peak>self.cfg.stator_allowable_incremental_n,
                'energy_j':self.energy_j()}
    def incremental_spring_forces(self):
        return np.abs(self.cfg.spring_constants[:,None]*(np.roll(self.u,-1,axis=1)-self.u))
    def energy_j(self):
        elastic=.5*np.sum(self.cfg.spring_constants[:,None]*(np.roll(self.u,-1,axis=1)-self.u)**2)
        kinetic=.5*np.sum(self.cfg.masses[:,None]*self.v**2)
        coupling=.5*self.cfg.coupling_n_m*np.sum((self.u[0]-self.u[1])**2)
        return float(elastic+kinetic+coupling)
    def summary(self):
        forces=self.incremental_spring_forces()
        return {'spec':'ors/coupled-axial-lattice/0.2','nodes':self.cfg.nodes,
                'length_m':self.cfg.length_m,'dt_limit_s':self.cfg.stable_dt_upper_bound(),
                'steps':self.steps,'simulated_time_s':self.t,
                'peak_incremental_axial_force_n':self.max_incremental_force_n,
                'current_peak_stator_force_n':float(np.max(forces[0])),
                'current_peak_rotor_force_n':float(np.max(forces[1])),
                'total_energy_j':self.energy_j(),
                'exceeded_assumed_incremental_allowable':self.max_incremental_force_n>self.cfg.stator_allowable_incremental_n,
                'status':'SOFTWARE_ONLY_NOT_PHYSICAL_VALIDATION',
                'does_not_prove':['transverse debris survival','ring equilibrium or stability',
                                  'material failure threshold or fatigue','coupled magnetics and rotor motion',
                                  'real impact damage or shielding','physical hardware performance']}
