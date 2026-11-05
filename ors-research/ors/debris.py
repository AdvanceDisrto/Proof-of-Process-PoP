"""Synthetic debris-to-idealized-equatorial-circle screening.

Short-horizon constant-velocity geometric proxy; NO real sensor, ECEF propagation,
uncertainty estimation, collision probability, or actionable avoidance guidance.
"""
import numpy as np
from .physics import RingScenario

def generate_synthetic_cloud(count=5000,seed=2026,earth_radius_m=6371000.):
    if not 0<=count<=500000:raise ValueError('count out of range')
    rng=np.random.default_rng(seed)
    altitude=rng.uniform(300e3,600e3,count)
    angles=rng.uniform(-np.pi,np.pi,count)
    offplane=rng.uniform(-500e3,500e3,count)
    distance=earth_radius_m+altitude
    positions=np.column_stack((distance*np.cos(angles),distance*np.sin(angles),offplane))
    velocities=np.column_stack((rng.uniform(-7600,7600,count),rng.uniform(-7600,7600,count),rng.uniform(-2000,2000,count)))
    return positions,velocities

def distance_to_ideal_ring(positions,ring_radius_m):
    positions=np.asarray(positions,dtype=float)
    if positions.ndim!=2 or positions.shape[1]!=3 or not np.isfinite(positions).all():
        raise ValueError('expected finite N x 3 vectors')
    return np.sqrt((np.hypot(positions[:,0],positions[:,1])-ring_radius_m)**2+positions[:,2]**2)

def screen_synthetic_cloud(positions,velocities,horizon_s=10.,step_s=1.,critical_m=10_000.,warning_m=50_000.):
    positions=np.array(positions,dtype=float,copy=True)
    velocities=np.asarray(velocities,dtype=float)
    if positions.shape!=velocities.shape or positions.ndim!=2 or positions.shape[1]!=3:
        raise ValueError('different debris shape')
    if not np.isfinite(velocities).all() or not all(np.isfinite(x) and x>0 for x in (horizon_s,step_s,critical_m,warning_m)):
        raise ValueError('invalid input parameters')
    if critical_m>=warning_m:raise ValueError('threshold ordering')
    ring=RingScenario().radius_m
    times=np.linspace(0.,horizon_s,max(2,int(np.ceil(horizon_s/step_s))+1))
    closest=np.full(len(positions),np.inf)
    closest_time=np.zeros(len(positions))
    for t in times:
        d=distance_to_ideal_ring(positions+velocities*t,ring)
        better=d<closest
        closest[better]=d[better]
        closest_time[better]=t
    results=[]
    for i in np.where(closest<warning_m)[0]:
        results.append({'synthetic_object_id':int(i),'sampled_min_distance_m':round(float(closest[i]),3),
                        'sampled_time_s':float(closest_time[i]),
                        'screening_label':'CRITICAL_GEOMETRIC_PROXIMITY' if closest[i]<critical_m else 'WARNING_GEOMETRIC_PROXIMITY',
                        'collision_probability':None,'real_world_alert':False})
    return sorted(results,key=lambda x:x['sampled_min_distance_m'])
