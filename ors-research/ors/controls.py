"""Scalar active magnetic bearing control proxy. Not a magnetic field model."""
from dataclasses import dataclass
import numpy as np

@dataclass(frozen=True)
class Bearing:
    mass_kg:float=1000
    gap_m:float=.02
    kp:float=60000
    kd:float=16000
    ki:float=2000
    max_force_n:float=2000
    destablizing_stiffness_n_m:float=1500
    actuator_time_constant_s:float=.005
    def __post_init__(self):
        if min(self.mass_kg,self.gap_m,self.kp,self.kd,self.max_force_n,self.actuator_time_constant_s)<=0:
            raise ValueError('invalid plant')

def simulate(plant=Bearing(),initial_m=.005,dt=.001,seconds=3.,disturbance_n=0):
    if dt<=0 or dt>plant.actuator_time_constant_s/2:
        raise ValueError('timestep does not resolve actuator')
    if seconds<=0:raise ValueError('time must be positive')
    if abs(initial_m)>=plant.gap_m:
        return {'status':'INITIAL_CLEARANCE_VIOLATION','collision':True,
                'steps':0,'peak_m':abs(initial_m)}
    pos=float(initial_m);vel=0.;integral=0.;effort=0.;trace=[];collision=False
    n=int(seconds/dt)
    for i in range(n):
        err=-pos
        raw=plant.kp*err-plant.kd*vel+plant.ki*integral
        command=float(np.clip(raw,-plant.max_force_n,plant.max_force_n))
        if abs(raw)<plant.max_force_n:integral+=err*dt
        effort+=dt/plant.actuator_time_constant_s*(command-effort)
        acceleration=(effort+plant.destablizing_stiffness_n_m*pos+disturbance_n)/plant.mass_kg
        vel+=acceleration*dt;pos+=vel*dt
        trace.append(pos)
        if abs(pos)>=plant.gap_m:collision=True;break
    return {'status':'COLLISION' if collision else 'SIMULATED_NO_COLLISION','collision':collision,
            'steps':len(trace),'peak_m':max(map(abs,trace)),'final_m':pos,'final_velocity_m_s':vel,
            'rms_m':float(np.sqrt(np.mean(np.square(trace)))),
            'assumptions':['single translational axis','linearized destabilizing stiffness',
                           'first-order actuator lag','no electromagnetic field solution',
                           'not physical stability certification']}
